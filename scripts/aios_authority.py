#!/usr/bin/env python3
"""AIOS citizenship and authority checks."""

from __future__ import annotations

import argparse
import json
import os
import sys
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

try:
    from scripts.aios_agent_registry import load_registry
except ModuleNotFoundError:  # pragma: no cover - direct script execution
    from aios_agent_registry import load_registry


SCHEMA_VERSION = "aios.authority.v1"
CITIZENSHIP_CLASSES = ("operator", "child_agent", "reviewer", "critic", "researcher", "outsider")
ACTION_REQUIREMENTS: dict[str, set[str]] = {
    "release_dispatch": {"operator"},
    "flip_status_to_accepted": {"operator"},
    "flip_status_to_held": {"operator"},
    "flip_status_to_stopped": {"operator"},
    "commit_to_child_repo": {"operator", "child_agent"},
    "accept_memory_draft": {"operator", "reviewer"},
    "propose_contract": set(CITIZENSHIP_CLASSES),
}
FORBIDDEN_ACTIONS = {"bind_capability"}
AUDIT_LOG = Path(".aios/state/authority.jsonl")


@dataclass(frozen=True)
class AuthorityResult:
    agent_id: str
    action: str
    allowed: bool
    reason: str
    citizenship: list[str]
    required: list[str]
    registry_available: bool
    soft_fail: bool = False

    def to_json(self) -> dict[str, Any]:
        return {
            "schema_version": SCHEMA_VERSION,
            "agent_id": self.agent_id,
            "action": self.action,
            "allowed": self.allowed,
            "reason": self.reason,
            "citizenship": self.citizenship,
            "required": self.required,
            "registry_available": self.registry_available,
            "soft_fail": self.soft_fail,
        }


def now_iso() -> str:
    return datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds")


def current_agent_id() -> str:
    return os.environ.get("AIOS_AGENT_ID") or "codex@myworld"


def normalize_capabilities(entry: dict[str, Any] | None) -> list[str]:
    if not isinstance(entry, dict):
        return ["outsider"]
    values = [str(item) for item in entry.get("capabilities") or []]
    classes = [value for value in values if value in CITIZENSHIP_CLASSES]
    return sorted(dict.fromkeys(classes or ["outsider"]))


def registry_payload() -> tuple[dict[str, Any] | None, bool]:
    try:
        return load_registry(), True
    except (OSError, ValueError, json.JSONDecodeError):
        return None, False


def verify_authority(agent_id: str, action: str) -> AuthorityResult:
    if action in FORBIDDEN_ACTIONS:
        return AuthorityResult(agent_id, action, False, "forbidden_action:bind_capability", [], [], True)
    payload, available = registry_payload()
    if not available:
        return AuthorityResult(agent_id, action, True, "registry_unavailable_allow_with_warning", [], [], False, soft_fail=True)
    agents = (payload or {}).get("agents") or {}
    entry = agents.get(agent_id)
    citizenship = normalize_capabilities(entry)
    if entry is None:
        citizenship = ["outsider"]
    required = ACTION_REQUIREMENTS.get(action)
    if required is None:
        return AuthorityResult(agent_id, action, True, "unknown_action_allow_with_warning", citizenship, [], True, soft_fail=True)
    if required.intersection(citizenship):
        return AuthorityResult(agent_id, action, True, "authority_allowed", citizenship, sorted(required), True)
    return AuthorityResult(
        agent_id,
        action,
        False,
        f"requires_citizenship:{','.join(sorted(required))}",
        citizenship,
        sorted(required),
        True,
    )


def audit_authority(root: Path, result: AuthorityResult, *, override: bool = False, reason: str = "") -> Path:
    path = root / AUDIT_LOG
    path.parent.mkdir(parents=True, exist_ok=True)
    event = {"timestamp": now_iso(), **result.to_json(), "override": override, "override_reason": reason}
    with path.open("a", encoding="utf-8") as fh:
        fh.write(json.dumps(event, ensure_ascii=False, sort_keys=True) + "\n")
    return path


def cmd_verify(args: argparse.Namespace) -> int:
    result = verify_authority(args.agent, args.action)
    if args.audit:
        audit_authority(Path(args.root).resolve(), result)
    payload = result.to_json()
    if args.json:
        print(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True))
    else:
        print(f"allowed={str(result.allowed).lower()} reason={result.reason}")
    return 0


def cmd_classes(args: argparse.Namespace) -> int:
    payload = {"schema_version": SCHEMA_VERSION, "classes": list(CITIZENSHIP_CLASSES), "actions": {k: sorted(v) for k, v in ACTION_REQUIREMENTS.items()}, "forbidden_actions": sorted(FORBIDDEN_ACTIONS)}
    if args.json:
        print(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True))
    else:
        for item in CITIZENSHIP_CLASSES:
            print(item)
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", default=".")
    sub = parser.add_subparsers(dest="command", required=True)

    verify = sub.add_parser("verify")
    verify.add_argument("--agent", default=current_agent_id())
    verify.add_argument("--action", required=True)
    verify.add_argument("--audit", action="store_true")
    verify.add_argument("--json", action="store_true")
    verify.set_defaults(func=cmd_verify)

    classes = sub.add_parser("classes")
    classes.add_argument("--json", action="store_true")
    classes.set_defaults(func=cmd_classes)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    return int(args.func(args))


if __name__ == "__main__":
    raise SystemExit(main())
