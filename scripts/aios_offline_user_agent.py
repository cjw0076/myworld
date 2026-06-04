#!/usr/bin/env python3
"""Create and validate AIOS offline-user-agent packets.

The offline user is an AIOS sense organ, not a credential dump. This helper
keeps that boundary mechanical: packets must name the unknown, request one
bounded observation, and keep private data out of shared artifacts.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


SCHEMA_VERSION = "aios.offline_user_agent_packet.v1"
MEMORY_DRAFTS_SCHEMA = "aios.chat.memory_drafts.v1"
ALLOWED_TYPES = {
    "unknown.frontier.question",
    "user.offline_task",
    "field_observation",
    "contradiction",
}
ALLOWED_REPOS = {"myworld", "hivemind", "memoryOS", "CapabilityOS", "GenesisOS", "uri"}
SENSITIVE_PATTERNS = (
    r"\.env\b",
    r"\bapi[_-]?key\b",
    r"\btoken\b",
    r"\bsecret\b",
    r"\bpassword\b",
    r"\bcredential",
    r"\bcookie\b",
    r"\braw[_ -]?export\b",
    r"\bprivate[_ -]?history\b",
)
SAFE_SENSITIVE_FIELDS = {"what_not_to_share", "privacy_boundary"}


def now_iso() -> str:
    return datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds")


def _slug(text: str) -> str:
    slug = re.sub(r"[^a-zA-Z0-9]+", "-", text.lower()).strip("-")
    return (slug or "offline-user-packet")[:64]


def _hash(value: str) -> str:
    return hashlib.sha1(value.encode("utf-8", "replace")).hexdigest()


def _as_list(value: Any) -> list[str]:
    if value is None:
        return []
    if isinstance(value, list):
        return [str(item).strip() for item in value if str(item).strip()]
    if isinstance(value, str):
        return [item.strip() for item in value.split(",") if item.strip()]
    return [str(value).strip()]


def base_packet(packet_type: str, *, contract_id: str = "ASC-0210") -> dict[str, Any]:
    if packet_type not in ALLOWED_TYPES:
        raise ValueError(f"unsupported packet type: {packet_type}")
    return {
        "schema_version": SCHEMA_VERSION,
        "packet_type": packet_type,
        "contract_id": contract_id,
        "created_at": now_iso(),
        "status": "draft",
        "review_policy": {
            "draft_first": True,
            "auto_accept": False,
            "requires_operator_review": True,
        },
    }


def unknown_frontier_question(
    *,
    question: str,
    why_known_context_is_insufficient: str,
    risk_if_we_guess: str,
    candidate_routes: list[str],
    stop_condition: str,
    contract_id: str = "ASC-0210",
) -> dict[str, Any]:
    packet = base_packet("unknown.frontier.question", contract_id=contract_id)
    packet.update(
        {
            "question": question,
            "why_known_context_is_insufficient": why_known_context_is_insufficient,
            "risk_if_we_guess": risk_if_we_guess,
            "candidate_routes": candidate_routes,
            "stop_condition": stop_condition,
        }
    )
    return packet


def user_offline_task(
    *,
    task: str,
    time_budget: str,
    what_to_observe: str,
    what_not_to_share: str,
    return_format: str,
    privacy_boundary: str,
    upstream_question: str | None = None,
    contract_id: str = "ASC-0210",
) -> dict[str, Any]:
    packet = base_packet("user.offline_task", contract_id=contract_id)
    packet.update(
        {
            "task": task,
            "time_budget": time_budget,
            "what_to_observe": what_to_observe,
            "what_not_to_share": what_not_to_share,
            "return_format": return_format,
            "privacy_boundary": privacy_boundary,
        }
    )
    if upstream_question:
        packet["upstream_question"] = upstream_question
    return packet


def field_observation(
    *,
    observed_at: str,
    summary: str,
    confidence: float,
    next_question: str,
    contract_id: str = "ASC-0210",
) -> dict[str, Any]:
    packet = base_packet("field_observation", contract_id=contract_id)
    packet.update(
        {
            "observed_by": "user@offline",
            "observed_at": observed_at,
            "summary": summary,
            "confidence": confidence,
            "private_data_included": False,
            "next_question": next_question,
        }
    )
    return packet


def contradiction(
    *,
    expected: str,
    observed: str,
    impact: str,
    owner_repo: str,
    next_contract_candidate: str,
    contract_id: str = "ASC-0210",
) -> dict[str, Any]:
    packet = base_packet("contradiction", contract_id=contract_id)
    packet.update(
        {
            "expected": expected,
            "observed": observed,
            "impact": impact,
            "owner_repo": owner_repo,
            "next_contract_candidate": next_contract_candidate,
        }
    )
    return packet


def required_fields(packet_type: str) -> list[str]:
    common = ["schema_version", "packet_type", "status", "review_policy"]
    specific = {
        "unknown.frontier.question": [
            "question",
            "why_known_context_is_insufficient",
            "risk_if_we_guess",
            "candidate_routes",
            "stop_condition",
        ],
        "user.offline_task": [
            "task",
            "time_budget",
            "what_to_observe",
            "what_not_to_share",
            "return_format",
            "privacy_boundary",
        ],
        "field_observation": [
            "observed_by",
            "observed_at",
            "summary",
            "confidence",
            "private_data_included",
            "next_question",
        ],
        "contradiction": [
            "expected",
            "observed",
            "impact",
            "owner_repo",
            "next_contract_candidate",
        ],
    }
    return common + specific.get(packet_type, [])


def sensitive_hits(packet: dict[str, Any]) -> list[str]:
    hits: list[str] = []

    def visit(value: Any, path: str) -> None:
        if path.split(".")[-1] in SAFE_SENSITIVE_FIELDS:
            return
        if isinstance(value, dict):
            for key, child in value.items():
                visit(child, f"{path}.{key}" if path else str(key))
            return
        if isinstance(value, list):
            for idx, child in enumerate(value):
                visit(child, f"{path}[{idx}]")
            return
        text = str(value)
        for pattern in SENSITIVE_PATTERNS:
            if re.search(pattern, text, re.IGNORECASE):
                hits.append(f"{path}:{pattern}")

    visit(packet, "")
    return hits


def validate_packet(packet: dict[str, Any]) -> dict[str, Any]:
    errors: list[str] = []
    warnings: list[str] = []

    packet_type = packet.get("packet_type")
    if packet.get("schema_version") != SCHEMA_VERSION:
        errors.append(f"schema_version must be {SCHEMA_VERSION}")
    if packet_type not in ALLOWED_TYPES:
        errors.append("packet_type must be one of " + ", ".join(sorted(ALLOWED_TYPES)))
        packet_type = ""

    for field in required_fields(str(packet_type)):
        if field not in packet:
            errors.append(f"missing required field: {field}")
            continue
        value = packet.get(field)
        if value is None or value == "" or value == []:
            errors.append(f"empty required field: {field}")

    policy = packet.get("review_policy")
    if not isinstance(policy, dict):
        errors.append("review_policy must be an object")
    else:
        if policy.get("draft_first") is not True:
            errors.append("review_policy.draft_first must be true")
        if policy.get("auto_accept") is not False:
            errors.append("review_policy.auto_accept must be false")

    if packet_type == "unknown.frontier.question":
        routes = _as_list(packet.get("candidate_routes"))
        if not routes:
            errors.append("candidate_routes must contain at least one route")
        if not any(route in " ".join(routes).lower() for route in ("genesis", "capability", "web", "local", "offline")):
            warnings.append("candidate_routes should mention GenesisOS, CapabilityOS, web, local, or offline-user evidence")

    if packet_type == "user.offline_task":
        if "do not" not in str(packet.get("what_not_to_share", "")).lower() and "never" not in str(packet.get("what_not_to_share", "")).lower():
            warnings.append("what_not_to_share should explicitly say what not to disclose")
        if "private" not in str(packet.get("privacy_boundary", "")).lower() and "raw" not in str(packet.get("privacy_boundary", "")).lower():
            warnings.append("privacy_boundary should state the private/raw-data boundary")

    if packet_type == "field_observation":
        if packet.get("observed_by") != "user@offline":
            errors.append("field_observation.observed_by must be user@offline")
        if packet.get("private_data_included") is not False:
            errors.append("field_observation.private_data_included must be false")
        confidence = packet.get("confidence")
        if not isinstance(confidence, (int, float)) or not 0 <= float(confidence) <= 1:
            errors.append("field_observation.confidence must be a number between 0 and 1")

    if packet_type == "contradiction" and packet.get("owner_repo") not in ALLOWED_REPOS:
        errors.append("contradiction.owner_repo must be a known AIOS repo")

    for hit in sensitive_hits(packet):
        errors.append(f"sensitive/private term outside boundary field: {hit}")

    return {
        "ok": not errors,
        "errors": errors,
        "warnings": warnings,
        "packet_type": packet.get("packet_type"),
    }


def write_packet(root: Path, packet: dict[str, Any], repo: str = "memoryOS") -> Path:
    validation = validate_packet(packet)
    if not validation["ok"]:
        raise ValueError("; ".join(validation["errors"]))
    packet_type = str(packet["packet_type"])
    title = str(packet.get("question") or packet.get("task") or packet.get("summary") or packet.get("observed") or packet_type)
    out_dir = root / ".aios" / "inbox" / repo
    out_dir.mkdir(parents=True, exist_ok=True)
    path = out_dir / f"{packet.get('contract_id', 'ASC-0210').lower()}.{packet_type.replace('.', '-')}.{_slug(title)}.json"
    path.write_text(json.dumps(packet, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return path


def relative_ref(root: Path, path: Path) -> str:
    try:
        return path.resolve().relative_to(root.resolve()).as_posix()
    except ValueError:
        return path.as_posix()


def memory_draft_from_field_observation(packet: dict[str, Any], *, source_packet_ref: str) -> dict[str, Any]:
    validation = validate_packet(packet)
    if not validation["ok"]:
        raise ValueError("; ".join(validation["errors"]))
    if packet.get("packet_type") != "field_observation":
        raise ValueError("only field_observation packets can become offline-user memory drafts")
    summary = str(packet.get("summary") or "").strip()
    draft_hash = _hash("|".join([
        str(packet.get("contract_id") or ""),
        str(packet.get("observed_at") or ""),
        summary,
    ]))[:12]
    return {
        "id": f"offline-user:{draft_hash}",
        "type": "field_observation",
        "origin": "offline_user_agent",
        "status": "draft",
        "confidence": packet.get("confidence"),
        "conversation_id": "offline-user",
        "project": "AIOS",
        "content": summary,
        "raw_refs": [source_packet_ref],
        "provenance": {
            "source": "aios_offline_user_agent",
            "contract_id": packet.get("contract_id") or "",
            "packet_type": packet.get("packet_type") or "",
            "source_packet": source_packet_ref,
            "observed_by": packet.get("observed_by") or "",
            "observed_at": packet.get("observed_at") or "",
            "next_question": packet.get("next_question") or "",
            "private_data_included": packet.get("private_data_included") is True,
            "created_at": now_iso(),
        },
    }


def append_field_observation_memory_draft(root: Path, packet_path: Path, packet: dict[str, Any]) -> Path:
    source_ref = relative_ref(root, packet_path)
    draft = memory_draft_from_field_observation(packet, source_packet_ref=source_ref)
    draft_path = root / ".aios" / "chat" / "offline-user" / "memory_drafts.json"
    payload: dict[str, Any] = {}
    if draft_path.exists():
        try:
            loaded = json.loads(draft_path.read_text(encoding="utf-8"))
            if isinstance(loaded, dict):
                payload = loaded
        except json.JSONDecodeError:
            payload = {}
    if payload.get("schema_version") != MEMORY_DRAFTS_SCHEMA or not isinstance(payload.get("memory_drafts"), list):
        payload = {
            "schema_version": MEMORY_DRAFTS_SCHEMA,
            "conversation_id": "offline-user",
            "created_at": now_iso(),
            "memory_drafts": [],
        }
    drafts = [item for item in payload["memory_drafts"] if isinstance(item, dict)]
    existing_ids = {str(item.get("id") or "") for item in drafts}
    if draft["id"] not in existing_ids:
        drafts.append(draft)
    payload["memory_drafts"] = drafts
    payload["updated_at"] = now_iso()
    draft_path.parent.mkdir(parents=True, exist_ok=True)
    draft_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return draft_path


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="cmd", required=True)

    val = sub.add_parser("validate", help="Validate an offline-user-agent packet")
    val.add_argument("path", type=Path)
    val.add_argument("--json", action="store_true")

    new = sub.add_parser("new-offline-task", help="Create a user.offline_task packet")
    new.add_argument("--task", required=True)
    new.add_argument("--time-budget", required=True)
    new.add_argument("--observe", required=True)
    new.add_argument("--not-share", required=True)
    new.add_argument("--return-format", required=True)
    new.add_argument("--privacy-boundary", required=True)
    new.add_argument("--upstream-question")
    new.add_argument("--contract-id", default="ASC-0210")
    new.add_argument("--root", type=Path, default=Path("."))
    new.add_argument("--repo", choices=sorted(ALLOWED_REPOS), default="memoryOS")
    new.add_argument("--dry-run", action="store_true")
    new.add_argument("--json", action="store_true")

    obs = sub.add_parser("new-field-observation", help="Create a field_observation packet and optional MemoryOS draft")
    obs.add_argument("--summary", required=True)
    obs.add_argument("--confidence", type=float, required=True)
    obs.add_argument("--next-question", required=True)
    obs.add_argument("--observed-at")
    obs.add_argument("--contract-id", default="ASC-0210")
    obs.add_argument("--root", type=Path, default=Path("."))
    obs.add_argument("--repo", choices=sorted(ALLOWED_REPOS), default="memoryOS")
    obs.add_argument("--no-memory-draft", action="store_true")
    obs.add_argument("--dry-run", action="store_true")
    obs.add_argument("--json", action="store_true")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    if args.cmd == "validate":
        result = validate_packet(load_json(args.path))
        if args.json:
            print(json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True))
        else:
            print("ok" if result["ok"] else "failed")
            for error in result["errors"]:
                print(f"error: {error}")
            for warning in result["warnings"]:
                print(f"warning: {warning}")
        return 0 if result["ok"] else 1

    if args.cmd == "new-offline-task":
        packet = user_offline_task(
            task=args.task,
            time_budget=args.time_budget,
            what_to_observe=args.observe,
            what_not_to_share=args.not_share,
            return_format=args.return_format,
            privacy_boundary=args.privacy_boundary,
            upstream_question=args.upstream_question,
            contract_id=args.contract_id,
        )
        validation = validate_packet(packet)
        if not validation["ok"]:
            print(json.dumps(validation, ensure_ascii=False, indent=2, sort_keys=True), file=sys.stderr)
            return 1
        if args.dry_run:
            print(json.dumps({"packet": packet, "validation": validation}, ensure_ascii=False, indent=2, sort_keys=True))
            return 0
        path = write_packet(args.root.resolve(), packet, repo=args.repo)
        payload = {"ok": True, "path": path.as_posix(), "validation": validation}
        if args.json:
            print(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True))
        else:
            print(path.as_posix())
        return 0

    if args.cmd == "new-field-observation":
        packet = field_observation(
            observed_at=args.observed_at or now_iso(),
            summary=args.summary,
            confidence=args.confidence,
            next_question=args.next_question,
            contract_id=args.contract_id,
        )
        validation = validate_packet(packet)
        if not validation["ok"]:
            print(json.dumps(validation, ensure_ascii=False, indent=2, sort_keys=True), file=sys.stderr)
            return 1
        if args.dry_run:
            source_ref = ".aios/inbox/memoryOS/dry-run.field-observation.json"
            draft = None if args.no_memory_draft else memory_draft_from_field_observation(packet, source_packet_ref=source_ref)
            print(json.dumps({"packet": packet, "memory_draft": draft, "validation": validation}, ensure_ascii=False, indent=2, sort_keys=True))
            return 0
        root = args.root.resolve()
        path = write_packet(root, packet, repo=args.repo)
        draft_path = None if args.no_memory_draft else append_field_observation_memory_draft(root, path, packet)
        payload = {
            "ok": True,
            "path": path.as_posix(),
            "memory_draft_path": draft_path.as_posix() if draft_path else "",
            "validation": validation,
        }
        if args.json:
            print(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True))
        else:
            print(path.as_posix())
        return 0

    return 2


if __name__ == "__main__":
    raise SystemExit(main())
