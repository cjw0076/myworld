#!/usr/bin/env python3
"""Local AIOS control app launcher.

This script packages the static control surface into a repeatable on-prem
workflow: refresh local state, serve the app, inspect status, and stop it.
"""

from __future__ import annotations

import argparse
import hashlib
import http.server
import json
import os
import shutil
import signal
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


SCHEMA_VERSION = "aios.local_app.v1"
RUN_DIR = Path(".aios/run")
LOG_DIR = Path(".aios/logs")
PID_FILE = RUN_DIR / "aios_control_app.pid"
PORT_FILE = RUN_DIR / "aios_control_app.port"
WS_PID_FILE = RUN_DIR / "aios_control_ws.pid"
WS_PORT_FILE = RUN_DIR / "aios_control_ws.port"
SERVER_LOG = LOG_DIR / "aios_control_app.server.log"
WS_LOG = LOG_DIR / "aios_control_app.websocket.log"
SNAPSHOT_JSON = Path("apps/control/aios-control-snapshot.json")
SNAPSHOT_JS = Path("apps/control/aios-control-data.js")
CONTROL_DIR = Path("apps/control")
DEFAULT_PORT = 8765
DEFAULT_WS_PORT = 8766
MAX_ASK_CHARS = 4000
PROMOTION_SCHEMA = "aios.session_promotion.v1"
MEMORY_DRAFT_REVIEW_SCHEMA = "aios.memory_draft_review_request.v1"
CHAIR_RUNTIME_SCHEMA = "aios.gate.chair_runtime.v1"
CHAIR_RUNTIME_MODES = {"internal_evidence_synthesizer", "ollama", "claude", "codex", "gemini"}
PROVIDER_CHAIR_MODES = {"claude", "codex", "gemini"}
MAX_ARTIFACT_PREVIEW_CHARS = 20000
ARTIFACT_ALLOWED_PREFIXES = (".aios", "docs", "apps/control")
ARTIFACT_FORBIDDEN_MARKERS = (
    ".env",
    "credential",
    "credentials",
    "secret",
    "token",
    "api_key",
    "apikey",
    "pin",
    "raw_export",
    "raw-exports",
    "private_history",
)


def now_iso() -> str:
    return datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds")


def ensure_layout(root: Path) -> None:
    for path in (root / RUN_DIR, root / LOG_DIR, root / CONTROL_DIR):
        path.mkdir(parents=True, exist_ok=True)


def run_command(root: Path, command: list[str], *, timeout: int = 120) -> dict[str, Any]:
    started_at = now_iso()
    try:
        result = subprocess.run(command, cwd=root, text=True, capture_output=True, timeout=timeout, check=False)
    except subprocess.TimeoutExpired as exc:
        return {
            "command": command,
            "returncode": 124,
            "stdout": exc.stdout or "",
            "stderr": exc.stderr or "",
            "started_at": started_at,
            "finished_at": now_iso(),
            "timed_out": True,
        }
    return {
        "command": command,
        "returncode": result.returncode,
        "stdout": result.stdout,
        "stderr": result.stderr,
        "started_at": started_at,
        "finished_at": now_iso(),
        "timed_out": False,
    }


def parse_json_stdout(raw: dict[str, Any]) -> Any:
    if raw.get("returncode") != 0 or not str(raw.get("stdout") or "").strip():
        return None
    try:
        return json.loads(raw["stdout"])
    except json.JSONDecodeError:
        return None


def stable_hash(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def json_response(handler: http.server.BaseHTTPRequestHandler, payload: dict[str, Any], *, status: int = 200) -> None:
    body = (json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n").encode("utf-8")
    handler.send_response(status)
    handler.send_header("Content-Type", "application/json; charset=utf-8")
    handler.send_header("Content-Length", str(len(body)))
    handler.send_header("Cache-Control", "no-store")
    handler.end_headers()
    handler.wfile.write(body)


def read_json_file(root: Path, relative_path: str) -> dict[str, Any] | None:
    path = root / relative_path
    try:
        resolved = path.resolve()
        resolved.relative_to(root.resolve())
    except ValueError:
        return None
    if not resolved.exists():
        return None
    try:
        parsed = json.loads(resolved.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return None
    return parsed if isinstance(parsed, dict) else None


def safe_artifact_ref(root: Path, ref: str) -> Path | None:
    if not ref or "\x00" in ref:
        return None
    raw = ref.strip()
    if raw.startswith("aios://"):
        return None
    path = Path(raw)
    if path.is_absolute():
        return None
    lowered = raw.lower()
    if any(marker in lowered for marker in ARTIFACT_FORBIDDEN_MARKERS):
        return None
    normalized = path.as_posix()
    if not any(normalized == prefix or normalized.startswith(f"{prefix}/") for prefix in ARTIFACT_ALLOWED_PREFIXES):
        return None
    candidate = (root / path).resolve()
    try:
        candidate.relative_to(root.resolve())
    except ValueError:
        return None
    if not candidate.exists() or not candidate.is_file():
        return None
    return candidate


def build_artifact_response(root: Path, payload: dict[str, Any]) -> tuple[int, dict[str, Any]]:
    ref = str(payload.get("path") or payload.get("ref") or "").strip()
    path = safe_artifact_ref(root, ref)
    if path is None:
        return 400, {"ok": False, "reason": "artifact_ref_not_allowed"}
    try:
        raw = path.read_bytes()
    except OSError as exc:
        return 404, {"ok": False, "reason": "artifact_read_failed", "error": str(exc)}
    truncated = len(raw) > MAX_ARTIFACT_PREVIEW_CHARS
    raw = raw[:MAX_ARTIFACT_PREVIEW_CHARS]
    text_body = raw.decode("utf-8", errors="replace")
    parsed_json: Any = None
    if path.suffix.lower() == ".json":
        try:
            parsed_json = json.loads(text_body)
        except json.JSONDecodeError:
            parsed_json = None
    return 200, {
        "ok": True,
        "schema_version": "aios.artifact_preview.v1",
        "path": relative_ref(root, path),
        "bytes_read": len(raw),
        "truncated": truncated,
        "format": "json" if parsed_json is not None else ("jsonl" if path.suffix.lower() == ".jsonl" else "text"),
        "text": text_body,
        "json": parsed_json,
    }


def safe_chat_memory_drafts_ref(root: Path, ref: str) -> tuple[Path, str] | tuple[None, str]:
    path = safe_artifact_ref(root, ref)
    if path is None:
        return None, "artifact_ref_not_allowed"
    try:
        path.resolve().relative_to((root / ".aios" / "chat").resolve())
    except ValueError:
        return None, "memory_draft_source_outside_chat"
    if path.name != "memory_drafts.json":
        return None, "memory_draft_source_invalid"
    return path, ""


def select_memory_draft(payload: dict[str, Any], source_path: Path, draft_id: str) -> tuple[dict[str, Any] | None, int, str]:
    drafts = payload.get("memory_drafts") if isinstance(payload.get("memory_drafts"), list) else []
    conversation_id = source_path.parent.name
    for index, draft in enumerate(drafts):
        if not isinstance(draft, dict):
            continue
        candidate_id = str(draft.get("id") or f"{conversation_id}:{index}")
        if candidate_id == draft_id or str(index) == draft_id:
            return draft, index, candidate_id
    return None, -1, ""


def build_memory_draft_review_response(root: Path, payload: dict[str, Any]) -> tuple[int, dict[str, Any]]:
    if not payload.get("confirm"):
        return 409, {"ok": False, "reason": "confirmation_required", "stop_condition": "memory_review_without_confirmation"}
    source_ref = str(payload.get("source_artifact") or payload.get("path") or "").strip()
    draft_id = str(payload.get("draft_id") or "").strip()
    if not source_ref or not draft_id:
        return 400, {"ok": False, "reason": "memory_draft_ref_missing"}
    source_path, reason = safe_chat_memory_drafts_ref(root, source_ref)
    if source_path is None:
        return 400, {"ok": False, "reason": reason}
    try:
        draft_payload = json.loads(source_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return 400, {"ok": False, "reason": "memory_draft_source_unreadable"}
    if not isinstance(draft_payload, dict) or draft_payload.get("schema_version") != "aios.chat.memory_drafts.v1":
        return 400, {"ok": False, "reason": "memory_draft_schema_invalid"}
    draft, draft_index, resolved_draft_id = select_memory_draft(draft_payload, source_path, draft_id)
    if draft is None:
        return 404, {"ok": False, "reason": "memory_draft_not_found"}
    status = str(draft.get("status") or "draft")
    if status not in {"draft", "proposed", "pending_review"}:
        return 409, {"ok": False, "reason": "memory_draft_not_reviewable", "status": status}

    request_id = f"mdrev-{stable_hash(source_ref + '|' + resolved_draft_id + '|' + now_iso())[:16]}"
    request_ref = f".aios/memory_draft_reviews/{request_id}/request.json"
    packet_ref = f".aios/inbox/memoryOS/{request_id}.memoryOS.json"
    result_ref = f".aios/outbox/memoryOS/{request_id}.memoryOS.result.json"
    content = str(draft.get("content") or "")
    raw_refs = [str(ref) for ref in draft.get("raw_refs") or [] if isinstance(ref, str)]
    provenance = draft.get("provenance") if isinstance(draft.get("provenance"), dict) else {}
    packet = {
        "schema_version": MEMORY_DRAFT_REVIEW_SCHEMA,
        "result_schema_version": "aios.dispatch.result.v1",
        "request_id": request_id,
        "dispatch_id": request_id,
        "contract_id": "MEMORY-DRAFT-REVIEW",
        "contract_path": "docs/AIOS_CHAT.md",
        "created_at": now_iso(),
        "target_repo": "memoryOS",
        "agent": "memoryOS-reviewer",
        "goal": "Review one AIOS chat memory draft candidate through the MemoryOS draft-first lifecycle.",
        "status": "sent",
        "control_plane": {
            "root": "myworld",
            "rule": "myworld requests review; MemoryOS owns approval, rejection, and persistence",
        },
        "source_artifact": source_ref,
        "draft_id": resolved_draft_id,
        "draft_index": draft_index,
        "draft": {
            "type": draft.get("type") or "memory_draft",
            "origin": draft.get("origin") or "unknown",
            "status": status,
            "confidence": draft.get("confidence"),
            "conversation_id": draft.get("conversation_id") or source_path.parent.name,
            "project": draft.get("project") or "",
            "content": content,
            "raw_refs": raw_refs,
            "provenance": provenance,
        },
        "must_produce": [
            "MemoryOS review receipt for this draft candidate",
            "review decision: accept, reject, or needs_more_evidence",
            "provenance link back to source_artifact and draft_id",
        ],
        "scope": {
            "repos": ["memoryOS"],
            "allowed_files": [
                "memoryOS/memoryos/cli.py",
                "memoryOS/memoryos/store.py",
                "memoryOS/memory/reviews.jsonl",
                "memoryOS/memory/objects.jsonl",
                source_ref,
            ],
            "forbidden_files": [
                ".env",
                "raw exports",
                "provider auth files",
                ".aios/chat/*/provider_turns.jsonl",
            ],
        },
        "review_policy": {
            "auto_accept": False,
            "draft_first": True,
            "operator_confirmed_request": True,
        },
        "return_to": result_ref,
        "stop_conditions": [
            "privacy_violation",
            "source_artifact_missing",
            "draft_id_missing",
            "provenance_missing",
            "memoryos_review_schema_drift",
        ],
    }
    receipt = {
        "schema_version": MEMORY_DRAFT_REVIEW_SCHEMA,
        "request_id": request_id,
        "created_at": packet["created_at"],
        "status": "sent_to_memoryOS_inbox",
        "source_artifact": source_ref,
        "draft_id": resolved_draft_id,
        "draft_type": packet["draft"]["type"],
        "artifact_paths": {
            "request": request_ref,
            "packet": packet_ref,
            "return_to": result_ref,
        },
        "next_action": "memoryOS_watcher_reviews_candidate",
        "execution_started": False,
        "stop_conditions": packet["stop_conditions"],
    }
    write_json(root / request_ref, {**packet, "artifact_paths": receipt["artifact_paths"]})
    write_json(root / packet_ref, packet)
    state_path = root / ".aios" / "state" / "memory_draft_reviews.jsonl"
    state_path.parent.mkdir(parents=True, exist_ok=True)
    with state_path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(receipt, ensure_ascii=False, sort_keys=True) + "\n")
    return 200, {"ok": True, "receipt": receipt}


def safe_invocation_ref(root: Path, ref: str) -> Path | None:
    if not ref:
        return None
    candidate = (root / ref).resolve() if not Path(ref).is_absolute() else Path(ref).resolve()
    try:
        candidate.relative_to((root / ".aios" / "invocations").resolve())
        candidate.relative_to(root.resolve())
    except ValueError:
        return None
    return candidate


def relative_ref(root: Path, path: Path) -> str:
    try:
        return path.resolve().relative_to(root.resolve()).as_posix()
    except ValueError:
        return path.resolve().as_posix()


def write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def write_text(path: Path, body: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(body, encoding="utf-8")


def slugify(text: str) -> str:
    import re

    return re.sub(r"[^A-Za-z0-9]+", "-", text).strip("-").lower()[:80] or "aios-session"


def render_aios_role_evidence_section() -> str:
    return """## AIOS Role Evidence

### MemoryOS

- context_pack: `pending_or_not_required`
- retrieval_trace: `pending_or_not_required`
- accepted_memory_ids: `pending_or_not_required`
- draft_memory_policy: `draft_first_no_auto_accept`

### CapabilityOS

- route: `pending_or_not_required`
- recommended_tools: `pending_or_not_required`
- fallback_plan: `pending_or_not_required`
- authority: `recommendation_only`

### GenesisOS

- branch_set: `pending_or_not_required`
- assumption_mutations: `pending_or_not_required`
- semantic_alignment_notes: `pending_or_not_required`
- authority: `advisory_only`

### Hive Mind

- execution_plan: `pending_after_acceptance`
- provider_route: `pending_after_acceptance`
- verification_receipt: `pending_after_execution`
- degraded_or_fallback_receipt: `pending_if_triggered`
"""


def render_promotion_contract_seed(envelope_ref: str, envelope: dict[str, Any], receipt_ref: str) -> str:
    goal = str(envelope.get("goal") or "Promote reviewed AIOS session").strip()
    slug = slugify(goal)
    dispatch_ref = ((envelope.get("role_artifacts") or {}).get("dispatch_packets") or "")
    role_evidence = render_aios_role_evidence_section()
    return f"""---
contract_id: ASC-XXXX
slug: {slug}
status: proposed
goal: {goal}
created: {now_iso()}
accepted:
closed:
origin: AIOS reviewed session promotion
session_envelope_ref: {envelope_ref}
promotion_receipt: {receipt_ref}
---

# ASC-XXXX {slug.replace("-", " ").title()}

## Why Now

This proposed contract was promoted from a reviewed AIOS session envelope.

- session_envelope: `{envelope_ref}`
- promotion_receipt: `{receipt_ref}`
- dispatch_preview: `{dispatch_ref or "not_available"}`

Operator must assign the final ASC id, narrow scope, accept the contract, and
dispatch through `scripts/aios_dispatch.py` before any executor work starts.

## Scope

repos:

- `myworld`

allowed_files:

- `docs/contracts/ASC-XXXX-{slug}.md`
- `docs/AGENT_WORKLOG.md`

forbidden_files:

- `.env`
- raw exports
- provider auth files
- child repo implementation files unless explicitly assigned

{role_evidence}

## Verification Gate

```bash
cd /home/user/workspaces/jaewon/myworld
python scripts/aios_monitor.py assess --json
```

## Stop Conditions

- `scope_not_narrowed_before_dispatch`
- `accepted_contract_missing`
- `dispatch_packet_missing_envelope_ref`
- `executor_runs_without_dispatch_packet`
"""


def build_session_promotion_response(root: Path, payload: dict[str, Any]) -> tuple[int, dict[str, Any]]:
    if not payload.get("confirm"):
        return 409, {"ok": False, "reason": "confirmation_required", "stop_condition": "promotion_without_confirmation"}
    envelope_ref = str(payload.get("session_envelope") or payload.get("session_envelope_ref") or "").strip()
    envelope_path = safe_invocation_ref(root, envelope_ref)
    if envelope_path is None:
        return 400, {"ok": False, "reason": "session_envelope_ref_outside_invocations"}
    if envelope_path.name != "session_envelope.json":
        return 400, {"ok": False, "reason": "session_envelope_missing"}
    try:
        envelope = json.loads(envelope_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return 400, {"ok": False, "reason": "session_envelope_missing"}
    if not isinstance(envelope, dict) or envelope.get("schema_version") != "aios.session_envelope.v1":
        return 400, {"ok": False, "reason": "session_envelope_schema_invalid"}

    promotion_id = f"promotion-{stable_hash(envelope_ref)[:12]}-{datetime.now(timezone.utc).astimezone().strftime('%Y%m%dT%H%M%S')}"
    promotion_dir = root / ".aios" / "promotions" / promotion_id
    receipt_ref = f".aios/promotions/{promotion_id}/promotion.json"
    contract_seed_ref = f".aios/promotions/{promotion_id}/contract_seed.md"
    dispatch_preview_ref = str(((envelope.get("role_artifacts") or {}).get("dispatch_packets") or ""))
    receipt = {
        "schema_version": PROMOTION_SCHEMA,
        "promotion_id": promotion_id,
        "status": "proposed_contract_seed",
        "created_at": now_iso(),
        "session_envelope": {"ref": envelope_ref, "schema_version": envelope.get("schema_version")},
        "goal": envelope.get("goal") or "",
        "artifact_paths": {
            "receipt": receipt_ref,
            "contract_seed": contract_seed_ref,
            "dispatch_preview": dispatch_preview_ref,
        },
        "execution_started": False,
        "next_action": "operator_assign_asc_accept_and_dispatch",
        "stop_conditions": ["accepted_contract_missing", "executor_runs_without_dispatch_packet"],
    }
    write_json(root / receipt_ref, receipt)
    write_text(root / contract_seed_ref, render_promotion_contract_seed(envelope_ref, envelope, receipt_ref))
    return 200, {"ok": True, "receipt": receipt}


def build_session_response(root: Path, payload: dict[str, Any]) -> tuple[int, dict[str, Any]]:
    goal = str(payload.get("goal") or "").strip()
    if not goal:
        return 400, {"ok": False, "reason": "goal_missing"}
    if len(goal) > MAX_ASK_CHARS:
        return 413, {"ok": False, "reason": "goal_too_large", "max_chars": MAX_ASK_CHARS}
    suffix = f"{stable_hash(goal)[:10]}-{datetime.now(timezone.utc).astimezone().strftime('%Y%m%dT%H%M%S')}"
    write_dir = f".aios/invocations/end-user-{suffix}"
    command = [
        sys.executable,
        "scripts/aios_invoke.py",
        "--root",
        root.as_posix(),
        "--goal",
        goal,
        "--write",
        write_dir,
        "--plan-only",
        "--json",
    ]
    contract_id = str(payload.get("contract_id") or "").strip()
    if contract_id:
        command.extend(["--contract-id", contract_id])
    raw = run_command(root, command, timeout=180)
    parsed = parse_json_stdout(raw)
    if raw["returncode"] != 0 or not isinstance(parsed, dict):
        return 502, {
            "ok": False,
            "reason": "session_failed",
            "returncode": raw["returncode"],
            "stderr_tail": str(raw.get("stderr") or "")[-1200:],
            "stdout_tail": str(raw.get("stdout") or "")[-1200:],
            "timed_out": raw.get("timed_out", False),
        }
    envelope = read_json_file(root, str(parsed.get("session_envelope") or ""))
    if not isinstance(envelope, dict):
        return 502, {
            "ok": False,
            "reason": "session_envelope_missing",
            "receipt": parsed,
        }
    return 200, {"ok": True, "receipt": parsed, "session_envelope": envelope}


def build_chat_response(root: Path, payload: dict[str, Any]) -> tuple[int, dict[str, Any]]:
    message = str(payload.get("message") or "").strip()
    if not message:
        return 400, {"ok": False, "reason": "message_missing"}
    if len(message) > 8000:
        return 413, {"ok": False, "reason": "message_too_large", "max_chars": 8000}
    conversation = str(payload.get("conversation_id") or "control-center").strip() or "control-center"
    command = [
        sys.executable,
        "scripts/aios_chat.py",
        "--root",
        root.as_posix(),
        "--conversation",
        conversation,
        "--message",
        message,
        "--json",
    ]
    raw = run_command(root, command, timeout=180)
    parsed = parse_json_stdout(raw)
    if raw["returncode"] != 0 or not isinstance(parsed, dict):
        return 502, {
            "ok": False,
            "reason": "chat_failed",
            "returncode": raw["returncode"],
            "stderr_tail": str(raw.get("stderr") or "")[-1200:],
            "stdout_tail": str(raw.get("stdout") or "")[-1200:],
            "timed_out": raw.get("timed_out", False),
        }
    parsed["ok"] = True
    return 200, {"ok": True, "result": parsed}


def build_gate_chair_probe_response(root: Path, payload: dict[str, Any]) -> tuple[int, dict[str, Any]]:
    message = str(payload.get("message") or "나에 대한 기억은 ?").strip()
    if not message:
        return 400, {"ok": False, "reason": "message_missing"}
    if len(message) > 8000:
        return 413, {"ok": False, "reason": "message_too_large", "max_chars": 8000}
    conversation = str(payload.get("conversation_id") or "gate-chair-probe").strip() or "gate-chair-probe"
    command = [
        sys.executable,
        "scripts/aios_chat.py",
        "--root",
        root.as_posix(),
        "--conversation",
        conversation,
        "--message",
        message,
        "--json",
    ]
    raw = run_command(root, command, timeout=180)
    parsed = parse_json_stdout(raw)
    if raw["returncode"] != 0 or not isinstance(parsed, dict):
        return 502, {
            "ok": False,
            "reason": "gate_chair_probe_failed",
            "returncode": raw["returncode"],
            "stderr_tail": str(raw.get("stderr") or "")[-1200:],
            "stdout_tail": str(raw.get("stdout") or "")[-1200:],
            "timed_out": raw.get("timed_out", False),
        }
    return 200, {
        "ok": True,
        "schema_version": "aios.gate_chair_probe.v1",
        "conversation_id": parsed.get("conversation_id"),
        "gate_chair_status": parsed.get("gate_chair_status") or {"attempted": False, "executed": False, "status": "missing"},
        "gate_chair_turn": parsed.get("gate_chair_turn"),
        "chosen_substrate": parsed.get("chosen_substrate"),
        "route_reason": parsed.get("route_reason"),
        "artifact_paths": parsed.get("artifact_paths") or {},
    }


def build_gate_chair_eval_response(root: Path, payload: dict[str, Any]) -> tuple[int, dict[str, Any]]:
    mode = str(payload.get("mode") or "both").strip()
    if mode not in {"both", "internal", "current"}:
        return 400, {"ok": False, "reason": "gate_chair_eval_mode_invalid", "allowed_modes": ["both", "internal", "current"]}
    prompts = payload.get("prompts")
    command = [
        sys.executable,
        "scripts/aios_gate_chair_eval.py",
        "--root",
        root.as_posix(),
        "--mode",
        mode,
        "--json",
    ]
    if isinstance(prompts, list):
        for prompt in prompts[:8]:
            text = str(prompt or "").strip()
            if text:
                if len(text) > 8000:
                    return 413, {"ok": False, "reason": "prompt_too_large", "max_chars": 8000}
                command.extend(["--prompt", text])
    raw = run_command(root, command, timeout=240)
    parsed = parse_json_stdout(raw)
    if raw["returncode"] != 0 or not isinstance(parsed, dict):
        return 502, {
            "ok": False,
            "reason": "gate_chair_eval_failed",
            "returncode": raw["returncode"],
            "stderr_tail": str(raw.get("stderr") or "")[-1200:],
            "stdout_tail": str(raw.get("stdout") or "")[-1200:],
            "timed_out": raw.get("timed_out", False),
        }
    return 200, {
        "ok": True,
        "schema_version": "aios.gate_chair_eval_api.v1",
        "eval_id": parsed.get("eval_id"),
        "verdict": parsed.get("verdict"),
        "scores": parsed.get("scores") or {},
        "promotion_ready": bool(parsed.get("promotion_ready")),
        "readiness_reason": parsed.get("readiness_reason"),
        "current_runtime_external": bool(parsed.get("current_runtime_external")),
        "current_runtime_modes": parsed.get("current_runtime_modes") or [],
        "report_path": parsed.get("report_path"),
        "prompt_count": parsed.get("prompt_count"),
        "modes": parsed.get("modes") or [],
    }


def build_gate_chair_runtime_response(root: Path, payload: dict[str, Any]) -> tuple[int, dict[str, Any]]:
    if not payload.get("confirm"):
        return 409, {"ok": False, "reason": "confirmation_required", "stop_condition": "chair_runtime_without_confirmation"}
    mode = str(payload.get("mode") or "").strip()
    if mode not in CHAIR_RUNTIME_MODES:
        return 400, {"ok": False, "reason": "chair_runtime_mode_invalid", "allowed_modes": sorted(CHAIR_RUNTIME_MODES)}
    model = str(payload.get("model") or "").strip()
    if model and len(model) > 120:
        return 413, {"ok": False, "reason": "model_too_large", "max_chars": 120}
    if any(marker in model.lower() for marker in ARTIFACT_FORBIDDEN_MARKERS):
        return 400, {"ok": False, "reason": "model_contains_private_marker"}
    if mode == "ollama" and not model:
        model = "qwen2.5:7b"
    if mode == "claude" and not model:
        model = os.environ.get("AIOS_CLAUDE_MODEL", "claude-opus-4-6")
    activate = bool(payload.get("activate")) or mode == "internal_evidence_synthesizer"
    runtime_path = root / ".aios" / "gate" / "founder" / ("chair_runtime.json" if activate else "chair_candidate_runtime.json")
    payload_out = {
        "schema_version": CHAIR_RUNTIME_SCHEMA,
        "status": "active" if activate else "candidate",
        "mode": mode,
        "model": model if mode in {"ollama", "claude"} else "",
        "updated_at": now_iso(),
        "reason": str(payload.get("reason") or "Set from AIOS Control Center runtime switch.")[:500],
    }
    previous = read_json_file(root, relative_ref(root, runtime_path))
    if isinstance(previous, dict) and previous.get("created_at"):
        payload_out["created_at"] = previous["created_at"]
    else:
        payload_out["created_at"] = payload_out["updated_at"]
    if mode == "ollama":
        payload_out["command_available"] = bool(shutil.which("ollama"))
        if not payload_out["command_available"]:
            payload_out["fallback_expected"] = "internal_evidence_synthesizer_until_ollama_exists"
    elif mode in PROVIDER_CHAIR_MODES:
        payload_out["command_available"] = bool(shutil.which(mode))
        payload_out["provider_substrate"] = mode
        if not payload_out["command_available"]:
            payload_out["fallback_expected"] = f"internal_evidence_synthesizer_until_{mode}_exists"
    write_json(runtime_path, payload_out)
    return 200, {
        "ok": True,
        "schema_version": "aios.gate_chair_runtime_api.v1",
        "runtime_config": payload_out,
        "runtime_config_path": relative_ref(root, runtime_path),
        "activation_required": not activate,
    }


def build_gate_chair_promote_response(root: Path, payload: dict[str, Any]) -> tuple[int, dict[str, Any]]:
    if not payload.get("confirm"):
        return 409, {"ok": False, "reason": "confirmation_required", "stop_condition": "chair_promotion_without_confirmation"}
    report_ref = str(payload.get("report_path") or "").strip()
    if not report_ref.startswith(".aios/evals/gate_chair/") or not report_ref.endswith("/report.json"):
        return 400, {"ok": False, "reason": "report_path_invalid"}
    report = read_json_file(root, report_ref)
    if not isinstance(report, dict) or report.get("schema_version") != "aios.gate_chair_eval.v1":
        return 400, {"ok": False, "reason": "report_invalid"}
    if not report.get("promotion_ready"):
        return 409, {"ok": False, "reason": "promotion_not_ready", "readiness_reason": report.get("readiness_reason")}
    candidate_ref = str(report.get("candidate_runtime_path") or ".aios/gate/founder/chair_candidate_runtime.json")
    if candidate_ref != ".aios/gate/founder/chair_candidate_runtime.json":
        return 400, {"ok": False, "reason": "candidate_path_invalid"}
    candidate = read_json_file(root, candidate_ref)
    if not isinstance(candidate, dict) or candidate.get("schema_version") != CHAIR_RUNTIME_SCHEMA:
        return 400, {"ok": False, "reason": "candidate_invalid"}
    if candidate.get("status") != "candidate":
        return 409, {"ok": False, "reason": "candidate_not_pending"}
    mode = str(candidate.get("mode") or "")
    if mode not in CHAIR_RUNTIME_MODES or mode == "internal_evidence_synthesizer":
        return 400, {"ok": False, "reason": "candidate_mode_invalid"}
    promoted = {
        **candidate,
        "status": "active",
        "promoted_at": now_iso(),
        "promotion_report": report_ref,
        "reason": str(payload.get("reason") or "Promoted after Gate Chair eval readiness.")[:500],
    }
    runtime_path = root / ".aios" / "gate" / "founder" / "chair_runtime.json"
    previous = read_json_file(root, ".aios/gate/founder/chair_runtime.json")
    if isinstance(previous, dict) and previous.get("created_at"):
        promoted["created_at"] = previous["created_at"]
    else:
        promoted["created_at"] = promoted["promoted_at"]
    promoted["updated_at"] = promoted["promoted_at"]
    write_json(runtime_path, promoted)
    return 200, {
        "ok": True,
        "schema_version": "aios.gate_chair_promote_api.v1",
        "runtime_config": promoted,
        "runtime_config_path": relative_ref(root, runtime_path),
        "source_candidate_path": candidate_ref,
        "promotion_report": report_ref,
    }


def build_ask_response(root: Path, payload: dict[str, Any]) -> tuple[int, dict[str, Any]]:
    goal = str(payload.get("goal") or "").strip()
    if not goal:
        return 400, {"ok": False, "reason": "goal_missing"}
    if len(goal) > MAX_ASK_CHARS:
        return 413, {"ok": False, "reason": "goal_too_large", "max_chars": MAX_ASK_CHARS}
    command = [
        sys.executable,
        "scripts/aios_ask.py",
        "--root",
        root.as_posix(),
        "--json",
    ]
    if payload.get("draft_contract", True):
        command.append("--draft-contract")
    command.append(goal)
    raw = run_command(root, command, timeout=180)
    parsed = parse_json_stdout(raw)
    if raw["returncode"] != 0 or not isinstance(parsed, dict):
        return 502, {
            "ok": False,
            "reason": "ask_failed",
            "returncode": raw["returncode"],
            "stderr_tail": str(raw.get("stderr") or "")[-1200:],
            "stdout_tail": str(raw.get("stdout") or "")[-1200:],
            "timed_out": raw.get("timed_out", False),
        }
    return 200, {"ok": True, "receipt": parsed}


def build_goal_bar_response(root: Path, payload: dict[str, Any]) -> tuple[int, dict[str, Any]]:
    goal = str(payload.get("goal") or "").strip()
    if not goal:
        return 400, {"ok": False, "reason": "goal_missing"}
    if len(goal) > MAX_ASK_CHARS:
        return 413, {"ok": False, "reason": "goal_too_large", "max_chars": MAX_ASK_CHARS}
    command = [
        sys.executable,
        "scripts/aios_goal_bar.py",
        "--root",
        root.as_posix(),
        "--json",
    ]
    if payload.get("execute"):
        if not payload.get("confirm"):
            return 409, {"ok": False, "reason": "confirmation_required"}
        command.append("--execute")
    command.append(goal)
    raw = run_command(root, command, timeout=120)
    parsed = parse_json_stdout(raw)
    if raw["returncode"] != 0 or not isinstance(parsed, dict):
        return 502, {
            "ok": False,
            "reason": "goal_bar_failed",
            "returncode": raw["returncode"],
            "stderr_tail": str(raw.get("stderr") or "")[-1200:],
            "stdout_tail": str(raw.get("stdout") or "")[-1200:],
            "timed_out": raw.get("timed_out", False),
        }
    return 200, {"ok": True, "result": parsed}


def make_control_handler(root: Path) -> type[http.server.SimpleHTTPRequestHandler]:
    control_dir = root / CONTROL_DIR

    class ControlHandler(http.server.SimpleHTTPRequestHandler):
        server_version = "AIOSControlHTTP/1.0"

        def __init__(self, *args: Any, **kwargs: Any) -> None:
            super().__init__(*args, directory=control_dir.as_posix(), **kwargs)

        def log_message(self, format: str, *args: Any) -> None:
            print(f"{now_iso()} {self.address_string()} {format % args}")

        def do_GET(self) -> None:  # noqa: N802 - http.server hook
            if self.path == "/api/health":
                json_response(self, {"ok": True, "schema_version": SCHEMA_VERSION, "root": root.as_posix()})
                return
            super().do_GET()

        def do_POST(self) -> None:  # noqa: N802 - http.server hook
            if self.path not in {"/api/ask", "/api/goal_bar", "/api/session", "/api/chat", "/api/gate_chair_probe", "/api/gate_chair_eval", "/api/gate_chair_runtime", "/api/gate_chair_promote", "/api/promote_session", "/api/artifact", "/api/memory_draft_review"}:
                json_response(self, {"ok": False, "reason": "not_found"}, status=404)
                return
            try:
                size = int(self.headers.get("Content-Length", "0"))
            except ValueError:
                json_response(self, {"ok": False, "reason": "content_length_invalid"}, status=400)
                return
            if size <= 0 or size > 20000:
                json_response(self, {"ok": False, "reason": "request_size_invalid"}, status=413)
                return
            try:
                payload = json.loads(self.rfile.read(size).decode("utf-8"))
            except (UnicodeDecodeError, json.JSONDecodeError):
                json_response(self, {"ok": False, "reason": "json_invalid"}, status=400)
                return
            if not isinstance(payload, dict):
                json_response(self, {"ok": False, "reason": "json_object_required"}, status=400)
                return
            if self.path == "/api/goal_bar":
                status, body = build_goal_bar_response(root, payload)
            elif self.path == "/api/session":
                status, body = build_session_response(root, payload)
            elif self.path == "/api/promote_session":
                status, body = build_session_promotion_response(root, payload)
            elif self.path == "/api/chat":
                status, body = build_chat_response(root, payload)
            elif self.path == "/api/gate_chair_probe":
                status, body = build_gate_chair_probe_response(root, payload)
            elif self.path == "/api/gate_chair_eval":
                status, body = build_gate_chair_eval_response(root, payload)
            elif self.path == "/api/gate_chair_runtime":
                status, body = build_gate_chair_runtime_response(root, payload)
            elif self.path == "/api/gate_chair_promote":
                status, body = build_gate_chair_promote_response(root, payload)
            elif self.path == "/api/artifact":
                status, body = build_artifact_response(root, payload)
            elif self.path == "/api/memory_draft_review":
                status, body = build_memory_draft_review_response(root, payload)
            else:
                status, body = build_ask_response(root, payload)
            json_response(self, body, status=status)

    return ControlHandler


def serve_control_app(root: Path, *, port: int) -> None:
    ensure_layout(root)
    handler = make_control_handler(root)
    with http.server.ThreadingHTTPServer(("127.0.0.1", port), handler) as server:
        server.serve_forever()


def pid_running(pid: int) -> bool:
    try:
        os.kill(pid, 0)
    except ProcessLookupError:
        return False
    except PermissionError:
        return True
    return True


def read_pid(root: Path) -> int | None:
    path = root / PID_FILE
    if not path.exists():
        return None
    try:
        return int(path.read_text(encoding="utf-8").strip())
    except ValueError:
        return None


def read_pid_file(root: Path, relative_path: Path) -> int | None:
    path = root / relative_path
    if not path.exists():
        return None
    try:
        return int(path.read_text(encoding="utf-8").strip())
    except ValueError:
        return None


def read_port_file(root: Path, relative_path: Path, default: int) -> int:
    path = root / relative_path
    if not path.exists():
        return default
    try:
        return int(path.read_text(encoding="utf-8").strip())
    except ValueError:
        return default


def server_status(root: Path) -> dict[str, Any]:
    pid = read_pid_file(root, PID_FILE)
    port = read_port_file(root, PORT_FILE, DEFAULT_PORT)
    running = bool(pid and pid_running(pid))
    return {
        "running": running,
        "pid": pid,
        "port": port,
        "url": f"http://127.0.0.1:{port}/",
        "pid_file": PID_FILE.as_posix(),
        "log_file": SERVER_LOG.as_posix(),
    }


def websocket_status(root: Path) -> dict[str, Any]:
    pid = read_pid_file(root, WS_PID_FILE)
    port = read_port_file(root, WS_PORT_FILE, DEFAULT_WS_PORT)
    running = bool(pid and pid_running(pid))
    return {
        "running": running,
        "pid": pid,
        "port": port,
        "url": f"ws://127.0.0.1:{port}/events",
        "pid_file": WS_PID_FILE.as_posix(),
        "log_file": WS_LOG.as_posix(),
    }


def refresh(root: Path) -> dict[str, Any]:
    ensure_layout(root)
    monitor = run_command(root, [sys.executable, "scripts/aios_monitor.py", "assess", "--write", "--json"], timeout=120)
    snapshot = run_command(
        root,
        [
            sys.executable,
            "scripts/aios_control_snapshot.py",
            "--write-json",
            SNAPSHOT_JSON.as_posix(),
            "--write-js",
            SNAPSHOT_JS.as_posix(),
            "--json",
        ],
        timeout=120,
    )
    check = run_command(root, [sys.executable, "scripts/aios_control_snapshot.py", "--check-app-js", "apps/control/app.js", "--json"], timeout=60)
    ok = monitor["returncode"] == 0 and snapshot["returncode"] == 0 and check["returncode"] == 0
    return {
        "ok": ok,
        "generated_at": now_iso(),
        "monitor": parse_json_stdout(monitor),
        "snapshot": parse_json_stdout(snapshot),
        "app_check": parse_json_stdout(check),
        "snapshot_json": SNAPSHOT_JSON.as_posix(),
        "snapshot_js": SNAPSHOT_JS.as_posix(),
        "errors": compact_errors({"monitor": monitor, "snapshot": snapshot, "app_check": check}),
    }


def compact_errors(steps: dict[str, dict[str, Any]]) -> list[dict[str, Any]]:
    errors: list[dict[str, Any]] = []
    for name, raw in steps.items():
        if raw.get("returncode") != 0:
            errors.append(
                {
                    "step": name,
                    "returncode": raw.get("returncode"),
                    "stderr_tail": str(raw.get("stderr") or "")[-800:],
                    "stdout_tail": str(raw.get("stdout") or "")[-800:],
                }
            )
    return errors


def start_server(root: Path, *, port: int) -> dict[str, Any]:
    ensure_layout(root)
    current = server_status(root)
    if current["running"]:
        return {"ok": True, "started": False, "server": current}
    if not (root / CONTROL_DIR / "index.html").exists():
        raise SystemExit("control app missing; run refresh after ASC-0039")
    log_fh = (root / SERVER_LOG).open("a", encoding="utf-8")
    process = subprocess.Popen(
        [sys.executable, "scripts/aios_local_app.py", "--root", root.as_posix(), "serve", "--port", str(port)],
        cwd=root,
        stdout=log_fh,
        stderr=log_fh,
        start_new_session=True,
    )
    (root / PID_FILE).write_text(str(process.pid), encoding="utf-8")
    (root / PORT_FILE).write_text(str(port), encoding="utf-8")
    time.sleep(0.2)
    return {"ok": True, "started": True, "server": server_status(root)}


def start_websocket(root: Path, *, port: int) -> dict[str, Any]:
    ensure_layout(root)
    current = websocket_status(root)
    if current["running"]:
        return {"ok": True, "started": False, "websocket": current}
    log_fh = (root / WS_LOG).open("a", encoding="utf-8")
    process = subprocess.Popen(
        [
            sys.executable,
            "scripts/aios_dashboard_ws.py",
            "--root",
            root.as_posix(),
            "serve",
            "--host",
            "127.0.0.1",
            "--port",
            str(port),
        ],
        cwd=root,
        stdout=log_fh,
        stderr=log_fh,
        start_new_session=True,
    )
    (root / WS_PID_FILE).write_text(str(process.pid), encoding="utf-8")
    (root / WS_PORT_FILE).write_text(str(port), encoding="utf-8")
    time.sleep(0.2)
    return {"ok": True, "started": True, "websocket": websocket_status(root)}


def stop_server(root: Path) -> dict[str, Any]:
    status = server_status(root)
    pid = status.get("pid")
    stopped = False
    if status["running"] and pid:
        os.kill(int(pid), signal.SIGTERM)
        for _ in range(20):
            if not pid_running(int(pid)):
                stopped = True
                break
            time.sleep(0.1)
        if not stopped and pid_running(int(pid)):
            os.kill(int(pid), signal.SIGKILL)
            stopped = True
    for path in (root / PID_FILE, root / PORT_FILE):
        if path.exists():
            path.unlink()
    ws = stop_websocket(root)
    return {"ok": True, "stopped": stopped, "server": server_status(root), "websocket": ws["websocket"]}


def stop_websocket(root: Path) -> dict[str, Any]:
    status = websocket_status(root)
    pid = status.get("pid")
    stopped = False
    if status["running"] and pid:
        os.kill(int(pid), signal.SIGTERM)
        for _ in range(20):
            if not pid_running(int(pid)):
                stopped = True
                break
            time.sleep(0.1)
        if not stopped and pid_running(int(pid)):
            os.kill(int(pid), signal.SIGKILL)
            stopped = True
    for path in (root / WS_PID_FILE, root / WS_PORT_FILE):
        if path.exists():
            path.unlink()
    return {"ok": True, "stopped": stopped, "websocket": websocket_status(root)}


def round_status(root: Path) -> dict[str, Any]:
    raw = run_command(root, [sys.executable, "scripts/aios_round_controller.py", "status"], timeout=30)
    parsed: dict[str, Any] = {"returncode": raw["returncode"], "stdout": raw["stdout"].strip()}
    for line in raw["stdout"].splitlines():
        parts = line.split()
        for part in parts:
            key, sep, value = part.partition("=")
            if not sep:
                continue
            parsed[key.strip()] = coerce(value.strip())
    return parsed


def coerce(value: str) -> Any:
    if value in {"True", "False", "true", "false"}:
        return value.lower() == "true"
    if value.isdigit():
        return int(value)
    return value


def assert_live_websocket(root: Path) -> dict[str, Any]:
    ws = websocket_status(root)
    if not ws["running"]:
        return {"ok": False, "reason": "websocket_not_running"}
    raw = run_command(
        root,
        [
            sys.executable,
            "scripts/aios_dashboard_ws.py",
            "--root",
            root.as_posix(),
            "check",
            "--port",
            str(ws["port"]),
            "--json",
        ],
        timeout=10,
    )
    parsed = parse_json_stdout(raw)
    return parsed if isinstance(parsed, dict) else {"ok": False, "reason": "check_failed", "raw": raw}


def app_status(root: Path, *, assert_live: bool = False) -> dict[str, Any]:
    monitor = None
    monitor_path = root / ".aios/state/monitor_assessment.latest.json"
    if monitor_path.exists():
        try:
            monitor = json.loads(monitor_path.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            monitor = None
    snapshot_exists = (root / SNAPSHOT_JSON).exists() and (root / SNAPSHOT_JS).exists()
    result = {
        "schema_version": SCHEMA_VERSION,
        "generated_at": now_iso(),
        "root": root.as_posix(),
        "server": server_status(root),
        "websocket": websocket_status(root),
        "snapshot": {
            "exists": snapshot_exists,
            "json": SNAPSHOT_JSON.as_posix(),
            "js": SNAPSHOT_JS.as_posix(),
            "html": (CONTROL_DIR / "index.html").as_posix(),
        },
        "monitor_health": (monitor or {}).get("health"),
        "round_controller": round_status(root),
    }
    if assert_live:
        result["live_check"] = assert_live_websocket(root)
    return result


def command_refresh(args: argparse.Namespace) -> int:
    result = refresh(Path(args.root).resolve())
    print(json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True))
    return 0 if result["ok"] else 1


def command_start(args: argparse.Namespace) -> int:
    result = start_server(Path(args.root).resolve(), port=args.port)
    print(json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True))
    return 0


def command_stop(args: argparse.Namespace) -> int:
    result = stop_server(Path(args.root).resolve())
    print(json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True))
    return 0


def command_status(args: argparse.Namespace) -> int:
    result = app_status(Path(args.root).resolve(), assert_live=args.assert_live)
    print(json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True))
    if args.assert_live and not result.get("live_check", {}).get("ok"):
        return 1
    return 0


def command_up(args: argparse.Namespace) -> int:
    root = Path(args.root).resolve()
    refreshed = refresh(root)
    if not refreshed["ok"]:
        print(json.dumps({"ok": False, "refresh": refreshed}, ensure_ascii=False, indent=2, sort_keys=True))
        return 1
    started = start_server(root, port=args.port)
    websocket = start_websocket(root, port=args.ws_port)
    status = app_status(root)
    print(json.dumps({"ok": True, "refresh": refreshed, "start": started, "websocket": websocket, "status": status}, ensure_ascii=False, indent=2, sort_keys=True))
    return 0


def command_serve(args: argparse.Namespace) -> int:
    serve_control_app(Path(args.root).resolve(), port=args.port)
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", default=".")
    sub = parser.add_subparsers(dest="command", required=True)

    refresh_parser = sub.add_parser("refresh")
    refresh_parser.add_argument("--json", action="store_true")
    refresh_parser.set_defaults(func=command_refresh)

    start_parser = sub.add_parser("start")
    start_parser.add_argument("--port", type=int, default=DEFAULT_PORT)
    start_parser.add_argument("--json", action="store_true")
    start_parser.set_defaults(func=command_start)

    serve_parser = sub.add_parser("serve")
    serve_parser.add_argument("--port", type=int, default=DEFAULT_PORT)
    serve_parser.set_defaults(func=command_serve)

    stop_parser = sub.add_parser("stop")
    stop_parser.add_argument("--json", action="store_true")
    stop_parser.set_defaults(func=command_stop)

    status_parser = sub.add_parser("status")
    status_parser.add_argument("--json", action="store_true")
    status_parser.add_argument("--assert-live", action="store_true")
    status_parser.set_defaults(func=command_status)

    up_parser = sub.add_parser("up")
    up_parser.add_argument("--port", type=int, default=DEFAULT_PORT)
    up_parser.add_argument("--ws-port", type=int, default=DEFAULT_WS_PORT)
    up_parser.add_argument("--json", action="store_true")
    up_parser.set_defaults(func=command_up)
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    return int(args.func(args))


if __name__ == "__main__":
    raise SystemExit(main())
