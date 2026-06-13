#!/usr/bin/env python3
"""Create deterministic AIOS end-user serving session records.

The record is a non-UI boundary primitive. It creates only local state under
``.aios/serving/**`` and never records credential values or raw provider logs.
"""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path
from typing import Any, Final


SCHEMA_VERSION: Final = "aios.serving_session.v1"
SEGMENT_RE: Final = re.compile(r"[A-Za-z0-9][A-Za-z0-9_.-]{0,63}")
SERVING_ROOT: Final = Path(".aios/serving")


def validate_segment(value: str, label: str) -> str:
    if not value:
        raise ValueError(f"{label} is required")
    if value in {".", ".."} or not SEGMENT_RE.fullmatch(value):
        raise ValueError(f"{label} must be a safe path segment")
    return value


def workspace_rel(user_id: str, session_id: str) -> Path:
    return SERVING_ROOT / "workspaces" / user_id / session_id


def build_record(root: Path, user_id: str, session_id: str) -> dict[str, Any]:
    root.resolve()
    safe_user = validate_segment(user_id, "user_id")
    safe_session = validate_segment(session_id, "session_id")
    workspace = workspace_rel(safe_user, safe_session)
    artifact = workspace / "serving_session.json"
    return {
        "schema_version": SCHEMA_VERSION,
        "user_id": safe_user,
        "session_id": safe_session,
        "workspace_path": workspace.as_posix(),
        "approval_policy": {
            "sensitive_actions_require_approval": True,
            "default_sensitive_action": "hold_for_user_approval",
            "approved_actions": [],
        },
        "memory_policy": {
            "write_policy": "draft_only",
            "accepted_memory_writes": "forbidden",
            "draft_review_required": True,
        },
        "privacy_policy": {
            "credential_values": "forbidden",
            "raw_provider_logs": "forbidden",
            "artifact_scope": ".aios/serving/**",
        },
        "artifact_path": artifact.as_posix(),
    }


def create_session(root: Path, user_id: str, session_id: str) -> dict[str, Any]:
    record = build_record(root, user_id, session_id)
    artifact = root / record["artifact_path"]
    artifact.parent.mkdir(parents=True, exist_ok=True)
    artifact.write_text(json.dumps(record, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return record


def cmd_create(args: argparse.Namespace) -> int:
    root = Path(args.root).resolve()
    try:
        record = create_session(root, args.user_id, args.session_id)
    except ValueError as exc:
        if args.json:
            print(json.dumps({"ok": False, "error": str(exc)}, ensure_ascii=False, indent=2, sort_keys=True))
        else:
            print(f"error: {exc}")
        return 2
    if args.json:
        print(json.dumps({"ok": True, "record": record}, ensure_ascii=False, indent=2, sort_keys=True))
    else:
        print(f"serving_session={record['artifact_path']}")
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Create an AIOS end-user serving session record")
    sub = parser.add_subparsers(dest="cmd", required=True)
    create = sub.add_parser("create", help="write a deterministic serving-session artifact")
    create.add_argument("--root", default=".")
    create.add_argument("--user-id", required=True)
    create.add_argument("--session-id", required=True)
    create.add_argument("--json", action="store_true")
    create.set_defaults(func=cmd_create)
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
