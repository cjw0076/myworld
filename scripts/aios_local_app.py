#!/usr/bin/env python3
"""Local AIOS control app launcher.

This script packages the static control surface into a repeatable on-prem
workflow: refresh local state, serve the app, inspect status, and stop it.
"""

from __future__ import annotations

import argparse
import base64
import hashlib
import http.server
import json
import os
import re
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
PRIVATE_TEXT_RE = re.compile(
    r"("
    r"[\w.+-]+@[\w.-]+\.[A-Za-z]{2,}"
    r"|q1q1e3e3"
    r"|AIza[0-9A-Za-z_-]+"
    r"|sk-[A-Za-z0-9_-]+"
    r"|api[_ -]?key[=:]\S+"
    r"|token[=:]\S+"
    r")",
    re.IGNORECASE,
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


def read_jsonl_file(path: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    try:
        for line in path.read_text(encoding="utf-8").splitlines():
            if not line.strip():
                continue
            parsed = json.loads(line)
            if isinstance(parsed, dict):
                rows.append(parsed)
    except (OSError, json.JSONDecodeError):
        return []
    return rows


def redacted_preview(value: Any, *, max_chars: int = 260) -> str:
    text = re.sub(r"\s+", " ", str(value or "")).strip()
    text = PRIVATE_TEXT_RE.sub("[REDACTED_PRIVATE]", text)
    if len(text) > max_chars:
        return text[: max_chars - 3].rstrip() + "..."
    return text


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


def file_mtime_iso(path: Path) -> str:
    return datetime.fromtimestamp(path.stat().st_mtime, timezone.utc).astimezone().isoformat(timespec="seconds")


def visual_screenshot_item(root: Path, path: Path, *, kind: str) -> dict[str, Any]:
    raw = path.read_bytes()
    data_url = ""
    if len(raw) <= 900_000:
        data_url = "data:image/png;base64," + base64.b64encode(raw).decode("ascii")
    return {
        "kind": kind,
        "path": relative_ref(root, path),
        "bytes": len(raw),
        "updated_at": file_mtime_iso(path),
        "data_url": data_url,
    }


def latest_visual_receipt(root: Path) -> dict[str, Any] | None:
    receipt_root = root / ".aios" / "visual_verification"
    if not receipt_root.exists():
        return None
    receipts = sorted(receipt_root.glob("*/receipt.json"), key=lambda path: path.stat().st_mtime, reverse=True)
    for path in receipts[:20]:
        payload = read_json_file(root, relative_ref(root, path))
        if not isinstance(payload, dict):
            continue
        return {
            "kind": "receipt",
            "path": relative_ref(root, path),
            "updated_at": file_mtime_iso(path),
            "status": payload.get("status"),
            "screenshot_path": payload.get("screenshot_path"),
            "stop_conditions": payload.get("stop_conditions") if isinstance(payload.get("stop_conditions"), list) else [],
        }
    return None


def visual_workflow_action(receipt: dict[str, Any] | None) -> dict[str, Any] | None:
    if not receipt:
        return None
    status = str(receipt.get("status") or "")
    if status in {"", "passed"}:
        return None
    stops = receipt.get("stop_conditions") if isinstance(receipt.get("stop_conditions"), list) else []
    prompt = (
        "AIOS visual verification이 통과하지 못한 UI 증거를 work item으로 바꿔줘. "
        f"receipt={receipt.get('path')} status={status} "
        f"screenshot={receipt.get('screenshot_path') or 'none'} "
        f"stop_conditions={', '.join(str(item) for item in stops) or 'none'}. "
        "원인, 수정 범위, 검증 command, stop condition을 포함해줘."
    )
    return {
        "kind": "visual_fix_work_item",
        "label": "Create Visual Fix",
        "severity": "attention" if status == "degraded" else "held",
        "prompt": prompt,
        "receipt": receipt.get("path"),
        "status": status,
        "stop_conditions": stops,
    }


def safe_visual_receipt_ref(root: Path, ref: str) -> tuple[Path, str] | tuple[None, str]:
    path = safe_artifact_ref(root, ref)
    if path is None:
        return None, "artifact_ref_not_allowed"
    try:
        path.resolve().relative_to((root / ".aios" / "visual_verification").resolve())
    except ValueError:
        return None, "visual_receipt_outside_visual_verification"
    if path.name != "receipt.json":
        return None, "visual_receipt_invalid"
    return path, ""


def render_visual_fix_contract_seed(receipt_ref: str, receipt: dict[str, Any]) -> str:
    status = str(receipt.get("status") or "unknown")
    screenshot = str(receipt.get("screenshot_path") or "none")
    stops = receipt.get("stop_conditions") if isinstance(receipt.get("stop_conditions"), list) else []
    stop_text = "\n".join(f"- `{item}`" for item in stops) or "- `visual_issue_unclassified`"
    return f"""---
contract_id: ASC-XXXX
slug: visual-verification-fix
status: proposed
goal: Turn degraded visual verification evidence into a scoped UI fix.
created: {now_iso()}
accepted:
closed:
origin: AIOS visual workflow promotion
visual_receipt: {receipt_ref}
---

# ASC-XXXX Visual Verification Fix

## Why Now

The latest visual verification receipt did not pass cleanly. Preserve the
receipt as evidence and turn it into a bounded UI repair contract before
executor work starts.

- visual_receipt: `{receipt_ref}`
- visual_status: `{status}`
- screenshot: `{screenshot}`

## Scope

repos:

- `myworld`

allowed_files:

- `apps/control/index.html`
- `apps/control/app.js`
- `apps/control/styles.css`
- `scripts/aios_visual_verify.py`
- `scripts/aios_local_app.py`
- `tests/test_aios_visual_verify.py`
- `tests/test_aios_local_app.py`
- `docs/AIOS_CONTROL_APP.md`
- `docs/AGENT_WORKLOG.md`

forbidden_files:

- `.env`
- raw exports
- provider auth files
- child repo implementation files

## Required Work

- Inspect the visual receipt and screenshot.
- Identify whether the failure is UI layout, browser verifier, data freshness,
  or missing visual evidence.
- Make the smallest scoped fix.
- Re-run the visual verification command for the affected URL.

## Verification Gate

```bash
python scripts/aios_visual_verify.py 'http://127.0.0.1:8765/?mode=operator' --allow-degraded --json
```

## Stop Conditions

{stop_text}
- `visual_receipt_missing`
- `screenshot_missing`
- `fix_requires_private_or_credentialed_data`
- `executor_runs_before_operator_acceptance`
"""


def build_visual_fix_promotion_response(root: Path, payload: dict[str, Any]) -> tuple[int, dict[str, Any]]:
    if not payload.get("confirm"):
        return 409, {"ok": False, "reason": "confirmation_required", "stop_condition": "visual_fix_promotion_without_confirmation"}
    receipt_ref = str(payload.get("visual_receipt") or payload.get("receipt") or "").strip()
    receipt_path, reason = safe_visual_receipt_ref(root, receipt_ref)
    if receipt_path is None:
        return 400, {"ok": False, "reason": reason}
    receipt = read_json_file(root, relative_ref(root, receipt_path))
    if not isinstance(receipt, dict) or receipt.get("schema_version") != "aios.visual_verification.v1":
        return 400, {"ok": False, "reason": "visual_receipt_schema_invalid"}
    status = str(receipt.get("status") or "")
    if status not in {"degraded", "failed"}:
        return 409, {"ok": False, "reason": "visual_receipt_not_actionable", "status": status}
    promotion_id = "visual-fix-" + stable_hash(receipt_ref + "|" + status)[:12]
    receipt_out_ref = f".aios/promotions/{promotion_id}/promotion.json"
    contract_seed_ref = f".aios/promotions/{promotion_id}/contract_seed.md"
    promotion = {
        "schema_version": PROMOTION_SCHEMA,
        "promotion_id": promotion_id,
        "status": "proposed_contract_seed",
        "goal": "Turn degraded visual verification evidence into a scoped UI fix.",
        "created_at": now_iso(),
        "source": {
            "kind": "visual_verification_receipt",
            "ref": receipt_ref,
            "status": status,
            "screenshot_path": receipt.get("screenshot_path"),
            "stop_conditions": receipt.get("stop_conditions") if isinstance(receipt.get("stop_conditions"), list) else [],
        },
        "artifact_paths": {
            "receipt": receipt_out_ref,
            "contract_seed": contract_seed_ref,
            "visual_receipt": receipt_ref,
        },
        "materialization_recommended": True,
        "quality_warnings": [],
        "execution_started": False,
        "next_action": "operator_assign_asc_accept_and_dispatch",
        "stop_conditions": ["accepted_contract_missing", "visual_receipt_missing", "executor_runs_without_dispatch_packet"],
    }
    write_json(root / receipt_out_ref, promotion)
    write_text(root / contract_seed_ref, render_visual_fix_contract_seed(receipt_ref, receipt).rstrip() + "\n")
    return 200, {"ok": True, "receipt": promotion}


def build_visual_workflow_response(root: Path) -> tuple[int, dict[str, Any]]:
    screenshot_root = root / ".aios" / "screenshots"
    screenshots = sorted(screenshot_root.glob("*.png"), key=lambda path: path.stat().st_mtime, reverse=True) if screenshot_root.exists() else []
    receipt = latest_visual_receipt(root)
    reference = next((path for path in screenshots if re.search(r"(reference|before)", path.name, re.IGNORECASE)), None)
    after = next((path for path in screenshots if re.search(r"(after|workflow|markdown|turn)", path.name, re.IGNORECASE)), None)
    receipt_screenshot_ref = str((receipt or {}).get("screenshot_path") or "")
    receipt_screenshot = root / receipt_screenshot_ref if receipt_screenshot_ref and not Path(receipt_screenshot_ref).is_absolute() else None
    if receipt_screenshot and receipt_screenshot.exists():
        try:
            receipt_screenshot.resolve().relative_to(screenshot_root.resolve())
            after = receipt_screenshot
        except ValueError:
            pass
    if reference is None and screenshots:
        reference = screenshots[-1]
    if after is None and screenshots:
        after = screenshots[0]
    items: dict[str, Any] = {}
    try:
        if reference:
            items["reference"] = visual_screenshot_item(root, reference, kind="reference")
        if after:
            items["after"] = visual_screenshot_item(root, after, kind="after")
    except OSError as exc:
        return 502, {"ok": False, "reason": "visual_screenshot_read_failed", "error": str(exc)}
    if receipt:
        items["receipt"] = receipt
    action = visual_workflow_action(receipt)
    return 200, {
        "ok": True,
        "schema_version": "aios.visual_workflow.v1",
        "status": "ready" if items.get("reference") and items.get("after") else "missing_visual_evidence",
        "items": items,
        "action": action,
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


def safe_chat_friction_seed_ref(root: Path, ref: str) -> tuple[Path, str] | tuple[None, str]:
    path = safe_artifact_ref(root, ref)
    if path is None:
        return None, "artifact_ref_not_allowed"
    try:
        path.resolve().relative_to((root / ".aios" / "chat").resolve())
    except ValueError:
        return None, "friction_seed_source_outside_chat"
    if path.name != "friction_contract_seed.md":
        return None, "friction_seed_source_invalid"
    return path, ""


def extract_friction_seed_goal(text: str) -> str:
    marker = "## Proposed Goal"
    if marker not in text:
        return "Review GenesisOS friction contract seed"
    rest = text.split(marker, 1)[1]
    rest = rest.split("\n## ", 1)[0]
    goal = re.sub(r"\s+", " ", rest).strip()
    return goal[:500] or "Review GenesisOS friction contract seed"


def next_contract_id(root: Path) -> str:
    highest = 0
    for path in (root / "docs" / "contracts").glob("ASC-*.md"):
        match = re.match(r"ASC-(\d{4})", path.name)
        if match:
            highest = max(highest, int(match.group(1)))
    return f"ASC-{highest + 1:04d}"


def render_genesis_break_frame_seed(payload: dict[str, Any], source_seed_ref: str) -> str:
    contract_id = str(payload.get("contract_id") or "ASC-UNKNOWN").strip()[:80]
    contract_path = str(payload.get("contract_path") or payload.get("path") or "").strip()[:240]
    reason = str(payload.get("reason") or "GenesisOS flagged prompt-prison convergence.").strip()[:600]
    escape_vectors = [str(value).strip()[:240] for value in (payload.get("escape_vectors") or []) if str(value).strip()][:6]
    signatures = [row for row in (payload.get("signatures") or []) if isinstance(row, dict)][:6]
    goal = f"Break GenesisOS prompt-prison frame for {contract_id} into alternate worldlines and a verifiable AIOS work contract."
    escape_lines = "\n".join(f"- {value}" for value in escape_vectors) or "- produce a counter-default branch before implementation"
    signature_lines = "\n".join(
        f"- `{str(row.get('signature') or 'signature')}`: {str(row.get('evidence') or 'no evidence recorded')[:300]}"
        for row in signatures
    ) or "- no signature details captured"
    return f"""---
contract_id: ASC-XXXX
status: proposed
authority: speculative_only
goal: {goal}
source_contract: {contract_id}
---

# ASC-XXXX Genesis Break-Frame Seed

This file is not execution authority; it is a reviewable bridge from GenesisOS
discomfort to an operator-approved AIOS smart contract.

## Proposed Goal

{goal}

## Source Friction

- source_contract: `{contract_id}`
- source_path: `{contract_path}`
- source_seed: `{source_seed_ref}`
- reason: {reason}

## Escape Vectors

{escape_lines}

## Prompt-Prison Signatures

{signature_lines}

## Alternate Worldlines

1. Schema worldline: restate the target work as machine-checkable inputs,
   outputs, stop conditions, and verification gates before implementation.
2. Inversion worldline: negate the top three hidden assumptions and produce a
   counter-plan that intentionally avoids the default wording.
3. Distant-domain worldline: map the contract to a non-software operating
   system analogy, then import one concrete mechanism back into AIOS.

## Scope

repos:

- `myworld`
- `GenesisOS`

allowed_files:

- `{contract_path or 'docs/contracts/ASC-XXXX-genesis-break-frame-seed.md'}`
- `docs/contracts/ASC-XXXX-genesis-break-frame-seed.md`
- `.aios/promotions/**`

forbidden_files:

- `.env`
- raw exports
- private runtime auth files
- child repo implementation files

## Verification Gate

```bash
python -m py_compile scripts/aios_control_snapshot.py
python -m unittest tests.test_aios_control_snapshot -v
```

## Stop Conditions

- The seed is treated as accepted execution authority.
- GenesisOS critique loses the cited source contract or escape vectors.
- The generated contract cannot be reviewed independently of this chat turn.
"""


def build_genesis_break_frame_seed_response(root: Path, payload: dict[str, Any]) -> tuple[int, dict[str, Any]]:
    if not payload.get("confirm"):
        return 409, {"ok": False, "reason": "confirmation_required", "stop_condition": "genesis_break_frame_without_confirmation"}
    contract_path = str(payload.get("contract_path") or payload.get("path") or "").strip()
    if contract_path:
        source_path = safe_artifact_ref(root, contract_path)
        if source_path is None:
            return 400, {"ok": False, "reason": "source_contract_ref_not_allowed"}
        try:
            source_path.resolve().relative_to((root / "docs" / "contracts").resolve())
        except ValueError:
            return 400, {"ok": False, "reason": "source_contract_outside_contracts"}
    seed_id = stable_hash(json.dumps(payload, ensure_ascii=False, sort_keys=True))[:16]
    source_seed_ref = f".aios/chat/friction-radar-{seed_id}/friction_contract_seed.md"
    write_text(root / source_seed_ref, render_genesis_break_frame_seed(payload, source_seed_ref).rstrip() + "\n")
    status, promotion_payload = build_friction_seed_promotion_response(
        root,
        {"source_seed": source_seed_ref, "confirm": True},
    )
    if status != 200:
        return status, promotion_payload
    response: dict[str, Any] = {
        "ok": True,
        "schema_version": "aios.genesis_break_frame_seed.v1",
        "source_seed": source_seed_ref,
        "promotion": promotion_payload.get("receipt"),
        "execution_started": False,
    }
    if payload.get("materialize", True):
        receipt = promotion_payload.get("receipt") if isinstance(promotion_payload.get("receipt"), dict) else {}
        receipt_ref = str((receipt.get("artifact_paths") or {}).get("receipt") or "")
        material_status, material_payload = build_promotion_contract_materialization_response(
            root,
            {
                "promotion_receipt": receipt_ref,
                "asc_id": str(payload.get("asc_id") or next_contract_id(root)),
                "confirm": True,
            },
        )
        if material_status != 200:
            response["materialization_error"] = material_payload
            return material_status, response
        response["materialization"] = material_payload.get("materialization")
    return 200, response


def build_friction_seed_promotion_response(root: Path, payload: dict[str, Any]) -> tuple[int, dict[str, Any]]:
    if not payload.get("confirm"):
        return 409, {"ok": False, "reason": "confirmation_required", "stop_condition": "friction_seed_promotion_without_confirmation"}
    source_ref = str(payload.get("source_seed") or payload.get("path") or "").strip()
    source_path, reason = safe_chat_friction_seed_ref(root, source_ref)
    if source_path is None:
        return 400, {"ok": False, "reason": reason}
    try:
        seed_text = source_path.read_text(encoding="utf-8")
    except OSError as exc:
        return 404, {"ok": False, "reason": "friction_seed_read_failed", "error": str(exc)}
    if "authority: speculative_only" not in seed_text or "not execution authority" not in seed_text:
        return 409, {"ok": False, "reason": "friction_seed_guardrail_missing"}

    promotion_id = f"friction-{stable_hash(source_ref)[:12]}-{datetime.now(timezone.utc).astimezone().strftime('%Y%m%dT%H%M%S')}"
    receipt_ref = f".aios/promotions/{promotion_id}/promotion.json"
    contract_seed_ref = f".aios/promotions/{promotion_id}/contract_seed.md"
    goal = extract_friction_seed_goal(seed_text)
    receipt = {
        "schema_version": PROMOTION_SCHEMA,
        "promotion_id": promotion_id,
        "status": "proposed_contract_seed",
        "created_at": now_iso(),
        "session_envelope": {"ref": "", "schema_version": ""},
        "goal": goal,
        "source": "aios_chat_genesis_friction",
        "source_seed": source_ref,
        "artifact_paths": {
            "receipt": receipt_ref,
            "contract_seed": contract_seed_ref,
            "source_seed": source_ref,
            "dispatch_preview": "",
        },
        "execution_started": False,
        "next_action": "operator_assign_asc_accept_and_dispatch",
        "stop_conditions": ["accepted_contract_missing", "genesis_seed_used_as_execution_authority"],
    }
    write_json(root / receipt_ref, receipt)
    promoted_seed = seed_text.rstrip() + f"\n\n## Promotion Receipt\n\n- promotion_receipt: `{receipt_ref}`\n- source_seed: `{source_ref}`\n"
    write_text(root / contract_seed_ref, promoted_seed + "\n")
    return 200, {"ok": True, "receipt": receipt}


def safe_promotion_receipt_ref(root: Path, ref: str) -> tuple[Path, str] | tuple[None, str]:
    path = safe_artifact_ref(root, ref)
    if path is None:
        return None, "artifact_ref_not_allowed"
    try:
        path.resolve().relative_to((root / ".aios" / "promotions").resolve())
    except ValueError:
        return None, "promotion_receipt_outside_promotions"
    if path.name != "promotion.json":
        return None, "promotion_receipt_invalid"
    return path, ""


def safe_promotion_contract_seed_ref(root: Path, ref: str) -> tuple[Path, str] | tuple[None, str]:
    path = safe_artifact_ref(root, ref)
    if path is None:
        return None, "artifact_ref_not_allowed"
    try:
        path.resolve().relative_to((root / ".aios" / "promotions").resolve())
    except ValueError:
        return None, "promotion_seed_outside_promotions"
    if path.name != "contract_seed.md":
        return None, "promotion_seed_invalid"
    return path, ""


def safe_contract_ref(root: Path, ref: str) -> tuple[Path, str] | tuple[None, str]:
    path = safe_artifact_ref(root, ref)
    if path is None:
        return None, "artifact_ref_not_allowed"
    try:
        path.resolve().relative_to((root / "docs" / "contracts").resolve())
    except ValueError:
        return None, "contract_outside_contracts_dir"
    if not re.fullmatch(r"ASC-\d{4}.*\.md", path.name):
        return None, "contract_path_invalid"
    return path, ""


def frontmatter_value(text: str, key: str) -> str:
    if not text.startswith("---\n"):
        return ""
    try:
        header = text.split("---", 2)[1]
    except IndexError:
        return ""
    prefix = f"{key}:"
    for line in header.splitlines():
        if line.startswith(prefix):
            return line.partition(":")[2].strip()
    return ""


def set_frontmatter_fields(text: str, fields: dict[str, str]) -> str:
    if text.startswith("---\n") and "\n---" in text[4:]:
        _, header, body = text.split("---", 2)
        lines = header.strip("\n").splitlines()
    else:
        lines = []
        body = "\n" + text
    seen: set[str] = set()
    updated: list[str] = []
    for line in lines:
        key = line.partition(":")[0].strip()
        if key in fields:
            updated.append(f"{key}: {fields[key]}")
            seen.add(key)
        else:
            updated.append(line)
    for key, value in fields.items():
        if key not in seen:
            updated.append(f"{key}: {value}")
    return "---\n" + "\n".join(updated).rstrip() + "\n---" + body


def build_contract_review_action_response(root: Path, payload: dict[str, Any]) -> tuple[int, dict[str, Any]]:
    if not payload.get("confirm"):
        return 409, {"ok": False, "reason": "confirmation_required", "stop_condition": "contract_review_action_without_confirmation"}
    action = str(payload.get("action") or "").strip()
    if action != "mark_superseded":
        return 400, {"ok": False, "reason": "unsupported_contract_review_action", "expected": "mark_superseded"}
    contract_ref = str(payload.get("contract_path") or payload.get("path") or "").strip()
    contract_path, reason = safe_contract_ref(root, contract_ref)
    if contract_path is None:
        return 400, {"ok": False, "reason": reason}
    try:
        text = contract_path.read_text(encoding="utf-8")
    except OSError as exc:
        return 404, {"ok": False, "reason": "contract_read_failed", "error": str(exc)}
    status = frontmatter_value(text, "status")
    if status != "proposed":
        return 409, {"ok": False, "reason": "contract_not_proposed", "status": status}
    contract_id = frontmatter_value(text, "contract_id") or contract_path.stem.split("-")[0]
    review_reason = redacted_preview(payload.get("reason") or "weak proposed contract superseded before acceptance", max_chars=300)
    updated = set_frontmatter_fields(
        text,
        {
            "status": "superseded",
            "superseded": now_iso(),
            "superseded_reason": review_reason,
        },
    )
    write_text(contract_path, updated.rstrip() + "\n")
    review_id = f"{contract_id.lower()}-{stable_hash(contract_ref + '|' + review_reason + '|' + now_iso())[:12]}"
    receipt_ref = f".aios/contract_reviews/{review_id}/review_action.json"
    receipt = {
        "schema_version": "aios.contract_review_action.v1",
        "review_id": review_id,
        "contract_id": contract_id,
        "contract_path": relative_ref(root, contract_path),
        "action": action,
        "previous_status": status,
        "status": "superseded",
        "reason": review_reason,
        "created_at": now_iso(),
        "execution_started": False,
    }
    write_json(root / receipt_ref, receipt)
    return 200, {"ok": True, "receipt": receipt}


def build_promotion_contract_materialization_response(root: Path, payload: dict[str, Any]) -> tuple[int, dict[str, Any]]:
    if not payload.get("confirm"):
        return 409, {"ok": False, "reason": "confirmation_required", "stop_condition": "contract_materialization_without_confirmation"}
    asc_id = str(payload.get("asc_id") or payload.get("contract_id") or "").strip().upper()
    if not re.fullmatch(r"ASC-\d{4}", asc_id):
        return 400, {"ok": False, "reason": "contract_id_invalid", "expected": "ASC-NNNN"}
    receipt_ref = str(payload.get("promotion_receipt") or payload.get("receipt") or "").strip()
    receipt_path, reason = safe_promotion_receipt_ref(root, receipt_ref)
    if receipt_path is None:
        return 400, {"ok": False, "reason": reason}
    receipt = read_json_file(root, relative_ref(root, receipt_path))
    if not isinstance(receipt, dict) or receipt.get("schema_version") != PROMOTION_SCHEMA:
        return 400, {"ok": False, "reason": "promotion_receipt_schema_invalid"}
    if receipt.get("materialization_recommended") is False and not payload.get("override_quality_warning"):
        return 409, {
            "ok": False,
            "reason": "promotion_quality_warning",
            "quality_warnings": receipt.get("quality_warnings") or [],
            "stop_condition": "weak_route_materialization_requires_revision_or_override",
        }
    paths = receipt.get("artifact_paths") if isinstance(receipt.get("artifact_paths"), dict) else {}
    seed_ref = str(paths.get("contract_seed") or "")
    seed_path, seed_reason = safe_promotion_contract_seed_ref(root, seed_ref)
    if seed_path is None:
        return 400, {"ok": False, "reason": seed_reason}
    try:
        seed_text = seed_path.read_text(encoding="utf-8")
    except OSError as exc:
        return 404, {"ok": False, "reason": "promotion_seed_read_failed", "error": str(exc)}
    if "status: proposed" not in seed_text:
        return 409, {"ok": False, "reason": "promotion_seed_not_proposed"}

    slug = slugify(str(receipt.get("goal") or asc_id))
    target_ref = f"docs/contracts/{asc_id}-{slug}.md"
    target_path = root / target_ref
    if target_path.exists():
        return 409, {"ok": False, "reason": "contract_already_exists", "contract_path": target_ref}
    body = seed_text.replace("ASC-XXXX", asc_id)
    body = body.replace(f"docs/contracts/{asc_id}-genesis-break-frame-seed.md", target_ref)
    if f"contract_id: {asc_id}" not in body:
        body = f"---\ncontract_id: {asc_id}\nstatus: proposed\n---\n\n" + body
    write_text(target_path, body.rstrip() + "\n")

    materialization_ref = f".aios/promotions/{receipt_path.parent.name}/materialization.json"
    materialization = {
        "schema_version": "aios.promotion_contract_materialization.v1",
        "promotion_id": receipt.get("promotion_id") or receipt_path.parent.name,
        "promotion_receipt": receipt_ref,
        "contract_id": asc_id,
        "contract_path": target_ref,
        "status": "proposed_contract_materialized",
        "created_at": now_iso(),
        "execution_started": False,
        "next_action": "operator_review_accept_and_dispatch",
    }
    write_json(root / materialization_ref, materialization)
    return 200, {"ok": True, "materialization": materialization}


def safe_ask_receipt_ref(root: Path, ref: str) -> tuple[Path | None, str]:
    path = safe_artifact_ref(root, ref)
    if path is None:
        return None, "ask_receipt_ref_not_allowed"
    try:
        path.relative_to((root / ".aios" / "asks").resolve())
    except ValueError:
        return None, "ask_receipt_not_under_asks"
    if path.name != "receipt.json":
        return None, "ask_receipt_must_be_receipt_json"
    return path, ""


def safe_ask_contract_seed_ref(root: Path, ref: str) -> tuple[Path | None, str]:
    path = safe_artifact_ref(root, ref)
    if path is None:
        return None, "ask_contract_seed_ref_not_allowed"
    try:
        path.relative_to((root / ".aios" / "asks").resolve())
    except ValueError:
        return None, "ask_contract_seed_not_under_asks"
    if path.name != "contract_seed.md":
        return None, "ask_contract_seed_must_be_contract_seed_md"
    return path, ""


def build_ask_contract_materialization_response(root: Path, payload: dict[str, Any]) -> tuple[int, dict[str, Any]]:
    if not payload.get("confirm"):
        return 409, {"ok": False, "reason": "confirmation_required", "stop_condition": "ask_contract_materialization_without_confirmation"}
    asc_id = str(payload.get("asc_id") or payload.get("contract_id") or "").strip().upper()
    if not re.fullmatch(r"ASC-\d{4}", asc_id):
        return 400, {"ok": False, "reason": "contract_id_invalid", "expected": "ASC-NNNN"}
    receipt_ref = str(payload.get("ask_receipt") or payload.get("receipt") or "").strip()
    receipt_path, reason = safe_ask_receipt_ref(root, receipt_ref)
    if receipt_path is None:
        return 400, {"ok": False, "reason": reason}
    receipt = read_json_file(root, relative_ref(root, receipt_path))
    if not isinstance(receipt, dict) or receipt.get("schema_version") != "aios.ask.receipt.v1":
        return 400, {"ok": False, "reason": "ask_receipt_schema_invalid"}
    paths = receipt.get("artifact_paths") if isinstance(receipt.get("artifact_paths"), dict) else {}
    seed_ref = str(paths.get("contract_seed") or "")
    seed_path, seed_reason = safe_ask_contract_seed_ref(root, seed_ref)
    if seed_path is None:
        return 400, {"ok": False, "reason": seed_reason}
    try:
        seed_text = seed_path.read_text(encoding="utf-8")
    except OSError as exc:
        return 404, {"ok": False, "reason": "ask_seed_read_failed", "error": str(exc)}
    if "status: proposed" not in seed_text:
        return 409, {"ok": False, "reason": "ask_seed_not_proposed"}

    slug = slugify(str(receipt.get("goal") or asc_id))
    target_ref = f"docs/contracts/{asc_id}-{slug}.md"
    target_path = root / target_ref
    if target_path.exists():
        return 409, {"ok": False, "reason": "contract_already_exists", "contract_path": target_ref}
    body = seed_text.replace("ASC-XXXX", asc_id)
    if f"contract_id: {asc_id}" not in body:
        body = f"---\ncontract_id: {asc_id}\nstatus: proposed\n---\n\n" + body
    write_text(target_path, body.rstrip() + "\n")

    ask_id = str(receipt.get("ask_id") or receipt_path.parent.name)
    materialization_ref = f".aios/asks/{receipt_path.parent.name}/materialization.json"
    materialization = {
        "schema_version": "aios.ask_contract_materialization.v1",
        "ask_id": ask_id,
        "ask_receipt": receipt_ref,
        "contract_id": asc_id,
        "contract_path": target_ref,
        "status": "proposed_contract_materialized",
        "created_at": now_iso(),
        "execution_started": False,
        "next_action": "operator_review_accept_and_dispatch",
    }
    write_json(root / materialization_ref, materialization)
    return 200, {"ok": True, "materialization": materialization}


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


def memory_review_evidence_for(root: Path, source_ref: str, draft_id: str) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    state_path = root / ".aios" / "state" / "memory_review_evidence.jsonl"
    try:
        lines = state_path.read_text(encoding="utf-8").splitlines()
    except OSError:
        return rows
    for line in lines:
        if not line.strip():
            continue
        try:
            row = json.loads(line)
        except json.JSONDecodeError:
            continue
        if not isinstance(row, dict):
            continue
        if row.get("source_artifact") != source_ref or row.get("draft_id") != draft_id:
            continue
        paths = row.get("artifact_paths") if isinstance(row.get("artifact_paths"), dict) else {}
        evidence_ref = str(paths.get("evidence") or "")
        artifact_ref = str(row.get("evidence_artifact") or "")
        rows.append(
            {
                "evidence_id": row.get("evidence_id"),
                "created_at": row.get("created_at"),
                "note": row.get("note") or "",
                "evidence_ref": evidence_ref,
                "evidence_artifact": artifact_ref,
            }
        )
    rows.sort(key=lambda row: str(row.get("created_at") or ""))
    return rows[-5:]


def dedupe_strings(values: list[str]) -> list[str]:
    deduped: list[str] = []
    seen: set[str] = set()
    for value in values:
        text = str(value or "").strip()
        if not text or text in seen:
            continue
        seen.add(text)
        deduped.append(text)
    return deduped


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
    supplemental_evidence = memory_review_evidence_for(root, source_ref, resolved_draft_id)
    evidence_refs: list[str] = []
    for item in supplemental_evidence:
        evidence_refs.extend(str(ref) for ref in (item.get("evidence_ref"), item.get("evidence_artifact")) if ref)
    raw_refs = dedupe_strings([str(ref) for ref in draft.get("raw_refs") or [] if isinstance(ref, str)] + evidence_refs)
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
        "supplemental_evidence": supplemental_evidence,
        "must_produce": [
            "MemoryOS review receipt for this draft candidate",
            "review decision: accept, reject, or needs_more_evidence",
            "provenance link back to source_artifact and draft_id",
            "supplemental evidence refs preserved when provided",
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
        "supplemental_evidence_count": len(supplemental_evidence),
        "stop_conditions": packet["stop_conditions"],
    }
    write_json(root / request_ref, {**packet, "artifact_paths": receipt["artifact_paths"]})
    write_json(root / packet_ref, packet)
    state_path = root / ".aios" / "state" / "memory_draft_reviews.jsonl"
    state_path.parent.mkdir(parents=True, exist_ok=True)
    with state_path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(receipt, ensure_ascii=False, sort_keys=True) + "\n")
    return 200, {"ok": True, "receipt": receipt}


def build_memory_review_evidence_response(root: Path, payload: dict[str, Any]) -> tuple[int, dict[str, Any]]:
    if not payload.get("confirm"):
        return 409, {"ok": False, "reason": "confirmation_required", "stop_condition": "memory_review_evidence_without_confirmation"}
    source_ref = str(payload.get("source_artifact") or payload.get("path") or "").strip()
    draft_id = str(payload.get("draft_id") or "").strip()
    note = str(payload.get("note") or "").strip()
    evidence_ref = str(payload.get("evidence_artifact") or payload.get("artifact") or "").strip()
    if not source_ref or not draft_id:
        return 400, {"ok": False, "reason": "memory_review_evidence_ref_missing"}
    if len(note) > 2000:
        return 413, {"ok": False, "reason": "memory_review_note_too_large", "max_chars": 2000}
    if not note and not evidence_ref:
        return 400, {"ok": False, "reason": "memory_review_evidence_missing"}
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
    evidence_path = None
    if evidence_ref:
        evidence_path = safe_artifact_ref(root, evidence_ref)
        if evidence_path is None:
            return 400, {"ok": False, "reason": "evidence_artifact_ref_not_allowed"}
        evidence_ref = relative_ref(root, evidence_path)

    evidence_id = f"mrevd-{stable_hash(source_ref + '|' + resolved_draft_id + '|' + note + '|' + evidence_ref + '|' + now_iso())[:16]}"
    evidence_record_ref = f".aios/memory_review_evidence/{evidence_id}/evidence.json"
    receipt = {
        "schema_version": "aios.memory_review_evidence.v1",
        "evidence_id": evidence_id,
        "created_at": now_iso(),
        "status": "evidence_recorded",
        "source_artifact": source_ref,
        "draft_id": resolved_draft_id,
        "draft_index": draft_index,
        "draft_type": draft.get("type") or "memory_draft",
        "note": note,
        "evidence_artifact": evidence_ref,
        "artifact_paths": {
            "evidence": evidence_record_ref,
            "source_artifact": source_ref,
            "evidence_artifact": evidence_ref,
        },
        "execution_started": False,
        "next_action": "request_memoryos_review_again_when_evidence_is_sufficient",
        "stop_conditions": [
            "evidence_contains_private_data",
            "source_artifact_missing",
            "draft_id_missing",
            "auto_accept_attempted",
        ],
    }
    write_json(root / evidence_record_ref, receipt)
    state_path = root / ".aios" / "state" / "memory_review_evidence.jsonl"
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


def append_jsonl(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(payload, ensure_ascii=False, sort_keys=True) + "\n")


def write_text(path: Path, body: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(body, encoding="utf-8")


def slugify(text: str) -> str:
    return re.sub(r"[^A-Za-z0-9]+", "-", text).strip("-").lower()[:80] or "aios-session"


def extract_context_pack_evidence(root: Path, envelope: dict[str, Any]) -> dict[str, Any]:
    artifacts = envelope.get("role_artifacts") if isinstance(envelope.get("role_artifacts"), dict) else {}
    ref = str(artifacts.get("memory_context_pack") or "").strip()
    evidence: dict[str, Any] = {
        "context_pack": ref or "pending_or_not_required",
        "retrieval_trace": "pending_or_not_required",
        "selected_memory_ids": [],
        "signal_coverage": "not_reported",
    }
    if not ref:
        return evidence
    path = safe_artifact_ref(root, ref)
    if path is None:
        return evidence
    try:
        text = path.read_text(encoding="utf-8")
    except OSError:
        return evidence
    trace_match = re.search(r"\btrace_id:\s*(rtrace_[A-Za-z0-9]+)", text)
    if trace_match:
        evidence["retrieval_trace"] = trace_match.group(1)
    coverage_match = re.search(r"\bsignal_coverage:\s*([A-Za-z0-9_.+-]+)", text)
    if coverage_match:
        evidence["signal_coverage"] = coverage_match.group(1)
    selected_match = re.search(r"\bselected_memory_ids:\s*(\[.*?\])", text)
    if selected_match:
        try:
            parsed = json.loads(selected_match.group(1))
        except json.JSONDecodeError:
            parsed = []
        if isinstance(parsed, list):
            evidence["selected_memory_ids"] = [str(item) for item in parsed if item]
    return evidence


def render_aios_role_evidence_section(root: Path | None = None, envelope: dict[str, Any] | None = None) -> str:
    memory = extract_context_pack_evidence(root, envelope or {}) if root is not None and envelope is not None else {
        "context_pack": "pending_or_not_required",
        "retrieval_trace": "pending_or_not_required",
        "selected_memory_ids": [],
        "signal_coverage": "not_reported",
    }
    selected = memory.get("selected_memory_ids") or []
    selected_text = json.dumps(selected, ensure_ascii=False) if selected else "pending_or_not_required"
    artifacts = (envelope or {}).get("role_artifacts") if isinstance((envelope or {}).get("role_artifacts"), dict) else {}
    capability_ref = artifacts.get("capability_route") or "pending_or_not_required"
    genesis_ref = artifacts.get("genesis") or "pending_or_not_required"
    hive_ref = artifacts.get("hive_execution_plan") or "pending_after_acceptance"
    return f"""## AIOS Role Evidence

### MemoryOS

- context_pack: `{memory.get('context_pack')}`
- retrieval_trace: `{memory.get('retrieval_trace')}`
- accepted_memory_ids: `{selected_text}`
- signal_coverage: `{memory.get('signal_coverage')}`
- draft_memory_policy: `draft_first_no_auto_accept`

### CapabilityOS

- route: `{capability_ref}`
- recommended_tools: `pending_or_not_required`
- fallback_plan: `pending_or_not_required`
- authority: `recommendation_only`

### GenesisOS

- branch_set: `{genesis_ref}`
- assumption_mutations: `pending_or_not_required`
- semantic_alignment_notes: `pending_or_not_required`
- authority: `advisory_only`

### Hive Mind

- execution_plan: `{hive_ref}`
- provider_route: `pending_after_acceptance`
- verification_receipt: `pending_after_execution`
- degraded_or_fallback_receipt: `pending_if_triggered`

### 5-Persona Use

- Hive / Wrapper: `pending_after_acceptance` provider route or single-provider justification required before execution
- MemoryOS / Retriever: retrieval_trace `{memory.get('retrieval_trace')}`, signal_coverage: `{memory.get('signal_coverage')}`
- CapabilityOS / Router: route `{capability_ref}`
- GenesisOS / Philosophy: branch_set `{genesis_ref}`
- MyWorld / Sovereign: promotion receipt and operator acceptance are required before dispatch
"""


def render_promotion_contract_seed(root: Path, envelope_ref: str, envelope: dict[str, Any], receipt_ref: str) -> str:
    goal = str(envelope.get("goal") or "Promote reviewed AIOS session").strip()
    slug = slugify(goal)
    dispatch_ref = ((envelope.get("role_artifacts") or {}).get("dispatch_packets") or "")
    role_evidence = render_aios_role_evidence_section(root=root, envelope=envelope)
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


def session_promotion_quality(root: Path, envelope: dict[str, Any]) -> dict[str, Any]:
    warnings: list[str] = []
    goal = str(envelope.get("goal") or "").strip()
    memory = extract_context_pack_evidence(root, envelope)
    coverage_raw = str(memory.get("signal_coverage") or "not_reported")
    try:
        coverage = float(coverage_raw)
    except ValueError:
        coverage = 0.0
    artifacts = envelope.get("role_artifacts") if isinstance(envelope.get("role_artifacts"), dict) else {}
    if len(goal) < 20:
        warnings.append("goal_too_short_for_contract_materialization")
    if coverage <= 0:
        warnings.append("memory_signal_coverage_zero_or_missing")
    if not artifacts.get("capability_route"):
        warnings.append("capability_route_missing")
    if not artifacts.get("genesis"):
        warnings.append("genesis_branch_artifact_missing")
    if not artifacts.get("dispatch_packets"):
        warnings.append("dispatch_preview_missing")
    return {
        "materialization_recommended": not warnings,
        "quality_warnings": warnings,
        "memory_signal_coverage": coverage_raw,
    }


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
    quality = session_promotion_quality(root, envelope)
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
        "materialization_recommended": quality["materialization_recommended"],
        "quality_warnings": quality["quality_warnings"],
        "memory_signal_coverage": quality["memory_signal_coverage"],
        "next_action": "operator_assign_asc_accept_and_dispatch",
        "stop_conditions": ["accepted_contract_missing", "executor_runs_without_dispatch_packet"],
    }
    write_json(root / receipt_ref, receipt)
    write_text(root / contract_seed_ref, render_promotion_contract_seed(root, envelope_ref, envelope, receipt_ref))
    return 200, {"ok": True, "receipt": receipt}


def build_chat_route_promotion_response(root: Path, payload: dict[str, Any]) -> tuple[int, dict[str, Any]]:
    if not payload.get("confirm"):
        return 409, {"ok": False, "reason": "confirmation_required", "stop_condition": "chat_route_promotion_without_confirmation"}
    receipt_ref = str(payload.get("invocation_receipt") or payload.get("receipt") or "").strip()
    receipt_path = safe_invocation_ref(root, receipt_ref)
    if receipt_path is None:
        return 400, {"ok": False, "reason": "invocation_receipt_ref_outside_invocations"}
    if receipt_path.name != "receipt.json":
        return 400, {"ok": False, "reason": "invocation_receipt_invalid"}
    try:
        receipt = json.loads(receipt_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return 400, {"ok": False, "reason": "invocation_receipt_missing"}
    if not isinstance(receipt, dict) or receipt.get("schema_version") != "aios.invocation_receipt.v1":
        return 400, {"ok": False, "reason": "invocation_receipt_schema_invalid"}
    envelope_ref = str(receipt.get("session_envelope") or "").strip()
    if not envelope_ref:
        return 400, {"ok": False, "reason": "session_envelope_missing_from_receipt"}
    status, body = build_session_promotion_response(
        root,
        {"session_envelope": envelope_ref, "confirm": True},
    )
    if isinstance(body, dict):
        body["source_invocation_receipt"] = receipt_ref
        body["schema_version"] = "aios.chat_route_promotion.v1"
    return status, body


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


def build_chat_history_response(root: Path, limit: int = 24) -> tuple[int, dict[str, Any]]:
    chat_root = root / ".aios" / "chat"
    if not chat_root.exists():
        return 200, {"ok": True, "schema_version": "aios.chat.history.v1", "items": [], "total": 0}

    memory_reviews: dict[str, list[str]] = {}
    memory_outbox = root / ".aios" / "outbox" / "memoryOS"
    if memory_outbox.exists():
        for result_path in sorted(memory_outbox.glob("mdrev-*.memoryOS.result.json"), key=lambda path: path.stat().st_mtime, reverse=True)[:200]:
            payload = read_json_file(root, relative_ref(root, result_path))
            if not isinstance(payload, dict):
                continue
            review = payload.get("review_request") if isinstance(payload.get("review_request"), dict) else {}
            source_artifact = str(review.get("source_artifact") or "").strip()
            decision = str(review.get("review_decision") or "").strip()
            if not source_artifact or not decision:
                continue
            memory_reviews.setdefault(source_artifact, []).append(decision)

    items: list[dict[str, Any]] = []
    conversation_dirs = [path for path in chat_root.iterdir() if path.is_dir()]
    conversation_dirs.sort(key=lambda path: path.stat().st_mtime, reverse=True)
    for chat_dir in conversation_dirs[: max(1, limit)]:
        messages_path = chat_dir / "messages.jsonl"
        if not messages_path.exists():
            continue
        messages = read_jsonl_file(messages_path)
        if not messages:
            continue
        last_user = next((row for row in reversed(messages) if row.get("role") == "user"), {})
        last_assistant = next((row for row in reversed(messages) if row.get("role") == "assistant"), {})
        latest = last_assistant or messages[-1]
        chair_rows = read_jsonl_file(chat_dir / "gate_chair_turns.jsonl")
        latest_chair = chair_rows[-1] if chair_rows else {}
        chair_meta = latest_chair.get("chair_meta") if isinstance(latest_chair.get("chair_meta"), dict) else {}
        chair_config = chair_meta.get("meta") if isinstance(chair_meta.get("meta"), dict) else {}
        provider_rows = read_jsonl_file(chat_dir / "provider_turns.jsonl")
        artifact_paths: dict[str, str] = {"messages": relative_ref(root, messages_path)}
        if (chat_dir / "gate_chair_turns.jsonl").exists():
            artifact_paths["gate_chair_turns"] = relative_ref(root, chat_dir / "gate_chair_turns.jsonl")
        if (chat_dir / "provider_turns.jsonl").exists():
            artifact_paths["provider_turns"] = relative_ref(root, chat_dir / "provider_turns.jsonl")
        if (chat_dir / "memory_drafts.json").exists():
            artifact_paths["memory_drafts"] = relative_ref(root, chat_dir / "memory_drafts.json")
        if (chat_dir / "cost.json").exists():
            artifact_paths["cost"] = relative_ref(root, chat_dir / "cost.json")
        if (chat_dir / "run_state.json").exists():
            artifact_paths["run_state"] = relative_ref(root, chat_dir / "run_state.json")
        gate_files = sorted((chat_dir / "gate_decisions").glob("*.json"), key=lambda path: path.stat().st_mtime, reverse=True) if (chat_dir / "gate_decisions").exists() else []
        if gate_files:
            artifact_paths["gate_decision"] = relative_ref(root, gate_files[0])
        chair_status = str(chair_meta.get("status") or "not_attempted")
        chair_mode = str(chair_config.get("mode") or "")
        memory_decisions = memory_reviews.get(artifact_paths.get("memory_drafts", ""), [])
        provider_statuses = [
            str((row.get("provider_meta") if isinstance(row.get("provider_meta"), dict) else {}).get("status") or "")
            for row in provider_rows
        ]
        failed_provider_statuses = [
            status
            for status in [chair_status, *provider_statuses]
            if status
            and status
            not in {
                "success",
                "fallback_success",
                "not_attempted",
                "not_executed",
                "not_executing",
            }
        ]
        flags = []
        if latest_chair and chair_mode and chair_mode != "internal_evidence_synthesizer":
            flags.append("provider_chair")
        if not latest_chair or chair_mode in {"", "internal_evidence_synthesizer"}:
            flags.append("internal")
        if any(decision in {"needs_more_evidence", "queued_for_memoryos_review"} for decision in memory_decisions):
            flags.append("memory_review_needed")
        if failed_provider_statuses:
            flags.append("failed_provider")
        items.append(
            {
                "conversation_id": chat_dir.name,
                "updated_at": str(latest.get("created_at") or latest_chair.get("created_at") or ""),
                "message_count": len(messages),
                "last_user_preview": redacted_preview(last_user.get("content"), max_chars=180),
                "last_response_preview": redacted_preview(last_assistant.get("content"), max_chars=260),
                "substrate": latest.get("substrate"),
                "route_reason": latest.get("route_reason"),
                "intent": latest.get("intent"),
                "chair": {
                    "attempted": bool(latest_chair),
                    "status": chair_status,
                    "mode": chair_mode or None,
                    "model": chair_config.get("model"),
                    "executed": bool(latest_chair.get("executed")) if latest_chair else False,
                },
                "flags": flags,
                "memory_review_decisions": memory_decisions[:4],
                "provider_failure_statuses": failed_provider_statuses[:4],
                "artifact_paths": artifact_paths,
            }
        )

    counts = {
        "all": len(items),
        "provider_chair": sum(1 for item in items if "provider_chair" in item.get("flags", [])),
        "internal": sum(1 for item in items if "internal" in item.get("flags", [])),
        "memory_review_needed": sum(1 for item in items if "memory_review_needed" in item.get("flags", [])),
        "failed_provider": sum(1 for item in items if "failed_provider" in item.get("flags", [])),
    }
    return 200, {
        "ok": True,
        "schema_version": "aios.chat.history.v1",
        "items": items,
        "total": len(items),
        "counts": counts,
    }


def chat_history_item(root: Path, conversation_id: str) -> dict[str, Any] | None:
    status, payload = build_chat_history_response(root, limit=200)
    if status != 200 or not payload.get("ok"):
        return None
    wanted = re.sub(r"[^A-Za-z0-9]+", "-", conversation_id).strip("-").lower()[:64] or "chat"
    for item in payload.get("items") or []:
        if isinstance(item, dict) and item.get("conversation_id") == wanted:
            return item
    return None


def latest_memory_review_gap_for_source(root: Path, source_ref: str) -> dict[str, Any] | None:
    memory_outbox = root / ".aios" / "outbox" / "memoryOS"
    if not memory_outbox.exists():
        return None
    for result_path in sorted(memory_outbox.glob("mdrev-*.memoryOS.result.json"), key=lambda path: path.stat().st_mtime, reverse=True)[:200]:
        payload = read_json_file(root, relative_ref(root, result_path))
        if not isinstance(payload, dict):
            continue
        review = payload.get("review_request") if isinstance(payload.get("review_request"), dict) else {}
        if str(review.get("source_artifact") or "") != source_ref:
            continue
        if str(review.get("review_decision") or "") != "needs_more_evidence":
            continue
        draft_id = str(review.get("draft_id") or "").strip()
        if not draft_id:
            continue
        return {
            "draft_id": draft_id,
            "review_result": relative_ref(root, result_path),
            "review_decision": "needs_more_evidence",
            "memory_object_id": review.get("memory_object_id"),
            "review_id": review.get("review_id"),
        }
    return None


def assigned_agent_for_fallback(item: dict[str, Any]) -> str:
    chair = item.get("chair") if isinstance(item.get("chair"), dict) else {}
    for value in (chair.get("mode"), item.get("substrate")):
        agent = str(value or "").strip()
        if agent in {"codex", "claude", "gemini", "local"}:
            return agent
        if agent in {"local_llm", "ollama", "ollama_qwen"}:
            return "local"
    return "claude"


def build_capability_fallback_preview_response(root: Path, item: dict[str, Any]) -> tuple[int, dict[str, Any]]:
    flags = item.get("flags") if isinstance(item.get("flags"), list) else []
    if "failed_provider" not in flags:
        return 409, {"ok": False, "reason": "conversation_has_no_failed_provider_flag"}
    capability_root = root / "CapabilityOS"
    if not (capability_root / "capabilityos" / "cli.py").exists():
        return 502, {"ok": False, "reason": "capabilityos_cli_missing"}
    conversation_id = str(item.get("conversation_id") or "").strip()
    failure_statuses = [str(value) for value in (item.get("provider_failure_statuses") or []) if str(value).strip()]
    assigned_agent = assigned_agent_for_fallback(item)
    task = (
        "AIOS chat provider fallback after "
        + (", ".join(failure_statuses) if failure_statuses else "provider failure")
    )
    command = [
        sys.executable,
        "-m",
        "capabilityos.cli",
        "provider-route",
        "--task",
        task,
        "--assigned-agent",
        assigned_agent,
        "--observations-inbox",
        "../.aios/outbox",
        "--json",
    ]
    raw = run_command(capability_root, command, timeout=60)
    parsed = parse_json_stdout(raw)
    if raw["returncode"] != 0 or not isinstance(parsed, dict):
        return 502, {
            "ok": False,
            "reason": "capability_fallback_preview_failed",
            "returncode": raw["returncode"],
            "stderr_tail": str(raw.get("stderr") or "")[-1200:],
            "stdout_tail": str(raw.get("stdout") or "")[-1200:],
            "timed_out": raw.get("timed_out", False),
        }
    return 200, {
        "ok": True,
        "schema_version": "aios.capability_fallback_preview.v1",
        "conversation_id": conversation_id,
        "assigned_agent": assigned_agent,
        "failure_statuses": failure_statuses,
        "execution_started": False,
        "route_plan": parsed,
        "redacted_previews": {
            "last_user": item.get("last_user_preview") or "",
            "last_response": item.get("last_response_preview") or "",
        },
    }


def build_capability_fallback_review_response(root: Path, item: dict[str, Any]) -> tuple[int, dict[str, Any]]:
    flags = item.get("flags") if isinstance(item.get("flags"), list) else []
    if "failed_provider" not in flags:
        return 409, {"ok": False, "reason": "conversation_has_no_failed_provider_flag"}
    conversation_id = str(item.get("conversation_id") or "").strip()
    failure_statuses = [str(value) for value in (item.get("provider_failure_statuses") or []) if str(value).strip()]
    artifact_paths = item.get("artifact_paths") if isinstance(item.get("artifact_paths"), dict) else {}
    source_artifacts: dict[str, str] = {}
    for key in ("gate_chair_turns", "provider_turns", "gate_decision", "cost", "run_state"):
        ref = str(artifact_paths.get(key) or "").strip()
        if ref and safe_artifact_ref(root, ref):
            source_artifacts[key] = ref
    if not source_artifacts:
        return 409, {"ok": False, "reason": "no_safe_failure_artifacts"}

    dispatch_id = f"chfb-{stable_hash(conversation_id + '|' + '|'.join(failure_statuses) + '|' + now_iso())[:16]}"
    request_ref = f".aios/capability_fallback_reviews/{dispatch_id}/request.json"
    packet_ref = f".aios/inbox/CapabilityOS/{dispatch_id}.CapabilityOS.json"
    result_ref = f".aios/outbox/CapabilityOS/{dispatch_id}.CapabilityOS.result.json"
    source_allowed = list(source_artifacts.values())
    packet = {
        "schema_version": "aios.dispatch.v1",
        "result_schema_version": "aios.dispatch.result.v1",
        "dispatch_id": dispatch_id,
        "contract_id": "CHAT-HISTORY-FALLBACK-REVIEW",
        "contract_path": "docs/AIOS_CHAT.md",
        "created_at": now_iso(),
        "target_repo": "CapabilityOS",
        "agent": "capabilityos-router",
        "status": "sent",
        "goal": "Recommend a provider/tool fallback route for an AIOS chat turn that recorded provider or Gate Chair failure evidence.",
        "control_plane": {
            "root": "myworld",
            "rule": "myworld requests route recommendation; CapabilityOS recommends only and does not execute providers or tools",
        },
        "source_conversation_id": conversation_id,
        "failure_statuses": failure_statuses,
        "source_artifacts": source_artifacts,
        "redacted_previews": {
            "last_user": item.get("last_user_preview") or "",
            "last_response": item.get("last_response_preview") or "",
        },
        "must_produce": [
            "CapabilityOS recommendation-only fallback route",
            "provider fallback order with reason codes",
            "bad provider/tool evidence cited from source_artifacts",
            "stop conditions for credential, privacy, and verifier gaps",
        ],
        "scope": {
            "repos": ["CapabilityOS"],
            "allowed_files": [
                "CapabilityOS/capabilityos/catalog.py",
                "CapabilityOS/capabilityos/cli.py",
                "CapabilityOS/capabilityos/observation.py",
                "CapabilityOS/capabilityos/schema.py",
                "CapabilityOS/tests/test_cli.py",
                "CapabilityOS/tests/test_observation.py",
                "CapabilityOS/docs/AGENT_WORKLOG.md",
                *source_allowed,
            ],
            "forbidden_files": [
                ".env",
                "raw exports",
                "provider auth files",
                "private provider logs",
                ".aios/chat/*/messages.jsonl",
                "memoryOS/memory/objects.jsonl",
            ],
        },
        "verification_commands": [
            {
                "command": "python -m capabilityos.cli provider-route --task \"AIOS chat provider fallback after Gate Chair/provider failure\" --assigned-agent claude --observations-inbox ../.aios/outbox --json",
                "cwd": "/home/user/workspaces/jaewon/myworld/CapabilityOS",
            }
        ],
        "return_to": result_ref,
        "stop_conditions": [
            "privacy_violation",
            "capabilityos_executes_provider",
            "source_artifact_missing",
            "fallback_without_reason_codes",
            "verifier_gap_not_reported",
        ],
    }
    receipt = {
        "schema_version": "aios.capability_fallback_review.v1",
        "request_id": dispatch_id,
        "dispatch_id": dispatch_id,
        "created_at": packet["created_at"],
        "status": "sent_to_CapabilityOS_inbox",
        "conversation_id": conversation_id,
        "failure_statuses": failure_statuses,
        "artifact_paths": {
            "request": request_ref,
            "packet": packet_ref,
            "return_to": result_ref,
        },
        "execution_started": False,
        "next_action": "CapabilityOS_watcher_recommends_fallback_route",
        "stop_conditions": packet["stop_conditions"],
    }
    write_json(root / request_ref, {**packet, "artifact_paths": receipt["artifact_paths"]})
    write_json(root / packet_ref, packet)
    append_jsonl(root / ".aios" / "state" / "capability_fallback_reviews.jsonl", receipt)
    return 200, {"ok": True, "receipt": receipt}


def build_chat_history_action_response(root: Path, payload: dict[str, Any]) -> tuple[int, dict[str, Any]]:
    conversation_id = str(payload.get("conversation_id") or "").strip()
    action = str(payload.get("action") or "").strip()
    if action not in {"capability_fallback_preview", "capability_fallback_review", "memory_rereview"}:
        return 400, {"ok": False, "reason": "chat_history_action_invalid"}
    if action != "capability_fallback_preview" and not payload.get("confirm"):
        return 409, {"ok": False, "reason": "confirmation_required", "stop_condition": "chat_history_action_without_confirmation"}
    if not conversation_id:
        return 400, {"ok": False, "reason": "conversation_id_missing"}
    item = chat_history_item(root, conversation_id)
    if item is None:
        return 404, {"ok": False, "reason": "conversation_not_found"}
    flags = item.get("flags") if isinstance(item.get("flags"), list) else []
    if action == "capability_fallback_preview":
        return build_capability_fallback_preview_response(root, item)
    if action == "capability_fallback_review":
        return build_capability_fallback_review_response(root, item)

    if "memory_review_needed" not in flags:
        return 409, {"ok": False, "reason": "conversation_has_no_memory_review_gap"}
    artifact_paths = item.get("artifact_paths") if isinstance(item.get("artifact_paths"), dict) else {}
    source_ref = str(artifact_paths.get("memory_drafts") or "").strip()
    gap = latest_memory_review_gap_for_source(root, source_ref)
    if not source_ref or gap is None:
        return 409, {"ok": False, "reason": "memory_review_gap_not_resolvable"}
    return build_memory_draft_review_response(
        root,
        {
            "source_artifact": source_ref,
            "draft_id": gap["draft_id"],
            "confirm": True,
        },
    )


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
    candidate_matrix = bool(payload.get("candidate_matrix"))
    mode = str(payload.get("mode") or "both").strip()
    if not candidate_matrix and mode not in {"both", "internal", "current"}:
        return 400, {"ok": False, "reason": "gate_chair_eval_mode_invalid", "allowed_modes": ["both", "internal", "current"]}
    prompts = payload.get("prompts")
    command = [
        sys.executable,
        "scripts/aios_gate_chair_eval.py",
        "--root",
        root.as_posix(),
        "--json",
    ]
    if candidate_matrix:
        command.append("--candidate-matrix")
        candidates = payload.get("candidates")
        if isinstance(candidates, list):
            for candidate in candidates[:8]:
                candidate_text = str(candidate or "").strip()
                if candidate_text:
                    command.extend(["--candidate", candidate_text])
        if payload.get("request_memory_review"):
            command.append("--request-memory-review")
    else:
        command.extend(["--mode", mode])
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
    if parsed.get("schema_version") == "aios.gate_chair_candidate_matrix.v1":
        return 200, {
            "ok": True,
            "schema_version": "aios.gate_chair_eval_api.v1",
            "report_kind": "candidate_matrix",
            "matrix_id": parsed.get("matrix_id"),
            "recommendation": parsed.get("recommendation"),
            "promotion_ready": bool(parsed.get("promotion_ready")),
            "baseline": parsed.get("baseline") or {},
            "candidates": parsed.get("candidates") or [],
            "best_candidate": parsed.get("best_candidate"),
            "report_path": parsed.get("report_path"),
            "prompt_count": parsed.get("prompt_count"),
            "request_memory_review": bool(parsed.get("request_memory_review")),
        }
    return 200, {
        "ok": True,
        "schema_version": "aios.gate_chair_eval_api.v1",
        "report_kind": "single_eval",
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
            if self.path == "/api/visual_workflow":
                status, body = build_visual_workflow_response(root)
                json_response(self, body, status=status)
                return
            if self.path.startswith("/api/chat_history"):
                status, body = build_chat_history_response(root)
                json_response(self, body, status=status)
                return
            super().do_GET()

        def do_POST(self) -> None:  # noqa: N802 - http.server hook
            if self.path not in {"/api/ask", "/api/goal_bar", "/api/session", "/api/chat", "/api/chat_history_action", "/api/gate_chair_probe", "/api/gate_chair_eval", "/api/gate_chair_runtime", "/api/gate_chair_promote", "/api/promote_session", "/api/promote_chat_route", "/api/promote_friction_seed", "/api/promote_visual_fix", "/api/genesis_break_frame_seed", "/api/materialize_promotion_contract", "/api/materialize_ask_contract", "/api/contract_review_action", "/api/artifact", "/api/memory_draft_review", "/api/memory_review_evidence"}:
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
            elif self.path == "/api/promote_chat_route":
                status, body = build_chat_route_promotion_response(root, payload)
            elif self.path == "/api/promote_friction_seed":
                status, body = build_friction_seed_promotion_response(root, payload)
            elif self.path == "/api/promote_visual_fix":
                status, body = build_visual_fix_promotion_response(root, payload)
            elif self.path == "/api/genesis_break_frame_seed":
                status, body = build_genesis_break_frame_seed_response(root, payload)
            elif self.path == "/api/materialize_promotion_contract":
                status, body = build_promotion_contract_materialization_response(root, payload)
            elif self.path == "/api/materialize_ask_contract":
                status, body = build_ask_contract_materialization_response(root, payload)
            elif self.path == "/api/contract_review_action":
                status, body = build_contract_review_action_response(root, payload)
            elif self.path == "/api/chat":
                status, body = build_chat_response(root, payload)
            elif self.path == "/api/chat_history_action":
                status, body = build_chat_history_action_response(root, payload)
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
            elif self.path == "/api/memory_review_evidence":
                status, body = build_memory_review_evidence_response(root, payload)
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
