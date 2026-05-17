#!/usr/bin/env python3
"""Report recent AIOS OS-role activity from inbox packets and invocation receipts."""

from __future__ import annotations

import argparse
import json
import time
from pathlib import Path
from typing import Any


SCHEMA_VERSION = "aios.os_activity.v1"
ROLE_BY_REPO = {
    "GenesisOS": "genesis",
    "memoryOS": "memory",
    "CapabilityOS": "capability",
    "hivemind": "hive",
}
ACTIVE_ROLE_STATUSES = {"passed", "degraded"}


def load_json(path: Path) -> dict[str, Any]:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}
    return payload if isinstance(payload, dict) else {}


def recent_files(paths: list[Path], since_epoch: float) -> list[str]:
    recent: list[str] = []
    for path in paths:
        try:
            if path.stat().st_mtime >= since_epoch:
                recent.append(path.as_posix())
        except OSError:
            continue
    return sorted(recent)


def invocation_role_receipts(root: Path, role: str, since_epoch: float) -> list[str]:
    matches: list[str] = []
    for receipt in sorted((root / ".aios" / "invocations").glob("*/receipt.json")):
        try:
            if receipt.stat().st_mtime < since_epoch:
                continue
        except OSError:
            continue
        payload = load_json(receipt)
        role_status = (payload.get("role_statuses") or {}).get(role)
        if role_status in ACTIVE_ROLE_STATUSES:
            matches.append(receipt.as_posix())
    return matches


def build_activity(root: Path, window_hours: float) -> dict[str, Any]:
    since_epoch = time.time() - (window_hours * 3600)
    rows: list[dict[str, Any]] = []
    ghost_repos: list[str] = []
    for repo, role in ROLE_BY_REPO.items():
        inbox_paths = recent_files(list((root / ".aios" / "inbox" / repo).glob("*.json")), since_epoch)
        invocation_paths = invocation_role_receipts(root, role, since_epoch)
        active = bool(inbox_paths or invocation_paths)
        if not active:
            ghost_repos.append(repo)
        rows.append(
            {
                "repo": repo,
                "role": role,
                "active": active,
                "inbox_recent_count": len(inbox_paths),
                "invocation_recent_count": len(invocation_paths),
                "evidence": {
                    "inbox": inbox_paths[:5],
                    "invocations": invocation_paths[:5],
                },
            }
        )
    return {
        "schema_version": SCHEMA_VERSION,
        "root": root.as_posix(),
        "window_hours": window_hours,
        "ghost_repos": ghost_repos,
        "repos": rows,
    }


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=Path.cwd())
    parser.add_argument("--window-hours", type=float, default=24)
    parser.add_argument("--json", action="store_true")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    payload = build_activity(args.root.resolve(), args.window_hours)
    if args.json:
        print(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True))
    else:
        ghosts = " ".join(payload["ghost_repos"]) or "none"
        print(f"os_activity ghosts={ghosts} window_hours={payload['window_hours']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
