#!/usr/bin/env python3
"""Consolidate AIOS chat/Gate traces into a personalized Gate pack.

This is the first "sleep" loop for the Gate Agent. It does not fine-tune a
model. It extracts prompt -> Gate decision -> substrate/OS route -> response
pairs from durable chat artifacts, overlays accepted MemoryOS hints when
available, and writes a small reviewed-input policy/few-shot pack that the chat
router can read on later turns.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


PAIR_SCHEMA = "aios.gate.loop_pair.v1"
PACK_SCHEMA = "aios.gate.pack.v1"
REPORT_SCHEMA = "aios.gate.sleep_report.v1"
PRIVATE_RE = re.compile(r"(_from_desktop|/dain/|/minyoung/|\\.env|secret|credential|token|api key|pin|q1q1e3e3|AIza[0-9A-Za-z_-]+|sk-[A-Za-z0-9_-]+)", re.IGNORECASE)


def now_iso() -> str:
    return datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds")


def canonical_json(data: Any) -> str:
    return json.dumps(data, ensure_ascii=False, indent=2, sort_keys=True)


def stable_id(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()[:16]


def clean(value: str, *, limit: int = 520) -> str:
    text = re.sub(r"\s+", " ", value).strip()
    text = PRIVATE_RE.sub("[REDACTED_PRIVATE]", text)
    return text[:limit].rstrip()


def write_json(path: Path, data: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(canonical_json(data) + "\n", encoding="utf-8")


def write_jsonl(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("".join(json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n" for row in rows), encoding="utf-8")


def read_json(path: Path) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    try:
        for raw in path.read_text(encoding="utf-8", errors="replace").splitlines():
            if not raw.strip():
                continue
            row = json.loads(raw)
            if isinstance(row, dict):
                rows.append(row)
    except (OSError, json.JSONDecodeError):
        return []
    return rows


def rel(path: Path, root: Path) -> str:
    try:
        return path.resolve().relative_to(root.resolve()).as_posix()
    except ValueError:
        return path.resolve().as_posix()


def safe_payload(data: Any) -> bool:
    return not PRIVATE_RE.search(json.dumps(data, ensure_ascii=False))


def load_gate_decisions(chat_dir: Path) -> dict[str, dict[str, Any]]:
    rows: dict[str, dict[str, Any]] = {}
    for path in sorted((chat_dir / "gate_decisions").glob("*.json")):
        payload = read_json(path)
        if isinstance(payload, dict) and payload.get("turn_id") and safe_payload(payload):
            rows[str(payload["turn_id"])] = {**payload, "artifact_path": path}
    return rows


def extract_loop_pairs(root: Path, *, limit: int = 200) -> list[dict[str, Any]]:
    base = root / ".aios" / "chat"
    pairs: list[dict[str, Any]] = []
    if not base.exists():
        return pairs
    for chat_dir in sorted(path for path in base.iterdir() if path.is_dir()):
        messages = read_jsonl(chat_dir / "messages.jsonl")
        gate_by_turn = load_gate_decisions(chat_dir)
        by_turn: dict[str, dict[str, dict[str, Any]]] = {}
        for row in messages:
            turn_id = str(row.get("turn_id") or "")
            role = str(row.get("role") or "")
            if turn_id and role in {"user", "assistant"}:
                by_turn.setdefault(turn_id, {})[role] = row
        for turn_id, roles in by_turn.items():
            user_row = roles.get("user")
            assistant_row = roles.get("assistant")
            gate = gate_by_turn.get(turn_id)
            if not user_row or not assistant_row or not gate:
                continue
            pair = {
                "schema_version": PAIR_SCHEMA,
                "id": f"gpair_{stable_id(chat_dir.name + ':' + turn_id)}",
                "conversation_id": chat_dir.name,
                "turn_id": turn_id,
                "created_at": assistant_row.get("created_at") or gate.get("created_at"),
                "prompt_excerpt": clean(str(user_row.get("content") or "")),
                "response_excerpt": clean(str(assistant_row.get("content") or "")),
                "gate_decision": gate.get("decision"),
                "input_class": gate.get("input_class"),
                "route": gate.get("route"),
                "provider_execution": gate.get("provider_execution"),
                "chosen_substrate": assistant_row.get("substrate"),
                "route_reason": assistant_row.get("route_reason"),
                "patterns_injected": assistant_row.get("patterns_injected") or [],
                "artifact_refs": [rel(gate["artifact_path"], root)] if isinstance(gate.get("artifact_path"), Path) else [],
                "outcome_signal": "observed",
            }
            if safe_payload(pair):
                pairs.append(pair)
                if len(pairs) >= limit:
                    return pairs
    pairs.sort(key=lambda row: str(row.get("created_at") or ""))
    return pairs[-limit:]


def accepted_memory_hints(root: Path, *, limit: int = 12) -> list[dict[str, Any]]:
    memory = root / "memoryOS" / "memory"
    objects = {str(row.get("id")): row for row in read_jsonl(memory / "objects.jsonl") if row.get("id")}
    statuses = {memory_id: str(row.get("status") or "unknown") for memory_id, row in objects.items()}
    for review in read_jsonl(memory / "reviews.jsonl"):
        memory_id = str(review.get("memory_object_id") or "")
        if memory_id and review.get("new_status"):
            statuses[memory_id] = str(review["new_status"])
    hints: list[dict[str, Any]] = []
    for memory_id, row in objects.items():
        if statuses.get(memory_id) != "accepted":
            continue
        content = str(row.get("content") or "")
        text = content.lower()
        if not any(token in text for token in ("gate", "chat", "aios", "provider", "capabilityos", "memoryos", "hive")):
            continue
        hint = {
            "id": memory_id,
            "project": row.get("project"),
            "type": row.get("type"),
            "content_excerpt": clean(content, limit=360),
            "raw_refs": [clean(str(ref), limit=180) for ref in (row.get("raw_refs") or [])[:3]],
        }
        if safe_payload(hint):
            hints.append(hint)
        if len(hints) >= limit:
            break
    return hints


def build_gate_pack(root: Path, *, user: str = "founder", pair_limit: int = 80) -> dict[str, Any]:
    pairs = extract_loop_pairs(root, limit=pair_limit)
    hints = accepted_memory_hints(root)
    decisions = Counter(str(pair.get("gate_decision") or "unknown") for pair in pairs)
    input_classes = Counter(str(pair.get("input_class") or "unknown") for pair in pairs)
    examples = []
    for wanted in ("clarify_location", "require_current_info_route", "answer_architecture", "route_normally"):
        example = next((pair for pair in reversed(pairs) if pair.get("gate_decision") == wanted), None)
        if example:
            examples.append(
                {
                    "id": example["id"],
                    "gate_decision": example.get("gate_decision"),
                    "input_class": example.get("input_class"),
                    "prompt_excerpt": example.get("prompt_excerpt"),
                    "response_excerpt": example.get("response_excerpt"),
                    "artifact_refs": example.get("artifact_refs") or [],
                }
            )
    pack_id = f"gatepack_{stable_id(user + ':' + str(len(pairs)) + ':' + now_iso())}"
    pack = {
        "schema_version": PACK_SCHEMA,
        "id": pack_id,
        "user": user,
        "status": "active",
        "generated_at": now_iso(),
        "source_pair_count": len(pairs),
        "accepted_memory_hint_count": len(hints),
        "decision_counts": dict(decisions),
        "input_class_counts": dict(input_classes),
        "rules": {
            "current_info_requires_source": decisions.get("clarify_location", 0) + decisions.get("require_current_info_route", 0) > 0,
            "provider_is_substrate_not_identity": decisions.get("answer_architecture", 0) > 0 or any("provider" in hint["content_excerpt"].lower() for hint in hints),
            "ask_missing_inputs_before_provider": decisions.get("clarify_location", 0) > 0,
            "memoryos_context_before_execution": True,
            "finetune_ready": False,
        },
        "sleep_consolidation": {
            "stage": "few_shot_policy_pack",
            "finetune_ready": False,
            "reason": "Use reviewed retrieval/policy packs before any model fine-tuning. Fine-tuning requires larger accepted datasets, evals, rollback, and privacy gates.",
        },
        "examples": examples[:8],
        "accepted_memory_hints": hints,
    }
    return pack


def write_report(root: Path, pack: dict[str, Any], pairs: list[dict[str, Any]], *, user: str) -> dict[str, Any]:
    base = root / ".aios" / "gate" / user
    pair_path = base / "loop_pairs.jsonl"
    pack_path = base / "gate_pack.json"
    report_path = base / "sleep_report.json"
    write_jsonl(pair_path, pairs)
    write_json(pack_path, pack)
    report = {
        "schema_version": REPORT_SCHEMA,
        "status": "passed",
        "generated_at": now_iso(),
        "user": user,
        "pair_path": rel(pair_path, root),
        "pack_path": rel(pack_path, root),
        "source_pair_count": len(pairs),
        "accepted_memory_hint_count": pack.get("accepted_memory_hint_count", 0),
        "gate_pack_id": pack.get("id"),
        "finetune_ready": False,
        "next": "Use this pack in chat Gate decisions; create a separate eval/rollback contract before any LoRA or model fine-tuning.",
    }
    write_json(report_path, report)
    return report


def run_sleep(root: Path, *, user: str = "founder", pair_limit: int = 80) -> dict[str, Any]:
    pairs = extract_loop_pairs(root, limit=pair_limit)
    pack = build_gate_pack(root, user=user, pair_limit=pair_limit)
    return write_report(root, pack, pairs, user=user)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=Path.cwd())
    parser.add_argument("--user", default="founder")
    parser.add_argument("--pair-limit", type=int, default=80)
    parser.add_argument("--json", action="store_true")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    report = run_sleep(args.root.resolve(), user=args.user, pair_limit=args.pair_limit)
    if args.json:
        print(canonical_json(report))
    else:
        print(f"wrote {report['pack_path']} from {report['source_pair_count']} pair(s)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
