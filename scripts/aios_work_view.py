#!/usr/bin/env python3
"""Redacted human-readable view of current AIOS work."""

from __future__ import annotations

import argparse
import json
import re
import subprocess
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import aios_contract_reconcile


SCHEMA_VERSION = "aios.work_view.v1"
BLOCKING_DISPATCH_STATES = {"held", "escalated", "failed"}
ACTIVE_STATUSES = {"accepted", "active"}
HARD_BAN_PARTS = {".env", "raw_exports", "_from_desktop", "dain", "minyoung"}


def now_iso() -> str:
    return datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds")


def parse_frontmatter(path: Path) -> dict[str, str]:
    try:
        return aios_contract_reconcile.parse_frontmatter(path.read_text(encoding="utf-8", errors="replace"))
    except OSError:
        return {}


def contract_paths(root: Path) -> list[Path]:
    return sorted((root / "docs" / "contracts").glob("ASC-*.md"))


def active_contracts(root: Path) -> list[dict[str, Any]]:
    rows = []
    for path in contract_paths(root):
        fm = parse_frontmatter(path)
        if fm.get("status") in ACTIVE_STATUSES and not fm.get("closed"):
            rows.append(
                {
                    "contract_id": fm.get("contract_id") or path.stem.split("-", 2)[0],
                    "slug": path.stem,
                    "status": fm.get("status"),
                    "goal": fm.get("goal", ""),
                    "path": path.relative_to(root).as_posix(),
                }
            )
    return rows


def load_jsonl(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    rows = []
    for line in path.read_text(encoding="utf-8", errors="replace").splitlines():
        if not line.strip():
            continue
        try:
            payload = json.loads(line)
        except json.JSONDecodeError:
            continue
        if isinstance(payload, dict):
            rows.append(payload)
    return rows


def dispatch_summary(root: Path) -> dict[str, Any]:
    events = load_jsonl(root / ".aios" / "state" / "dispatches.jsonl")
    latest: dict[str, dict[str, Any]] = {}
    for row in events:
        did = row.get("dispatch_id")
        if did:
            latest[str(did)] = row
    statuses: dict[str, int] = {}
    blocked = []
    for did, row in sorted(latest.items()):
        status = str(row.get("status") or "unknown")
        statuses[status] = statuses.get(status, 0) + 1
        if status in BLOCKING_DISPATCH_STATES:
            blocked.append(
                {
                    "dispatch_id": did,
                    "contract_id": row.get("contract_id"),
                    "status": status,
                    "reason": row.get("reason", ""),
                }
            )
    return {"total": len(latest), "by_status": statuses, "blocked": blocked}


def summarize_result(path: Path, root: Path) -> dict[str, Any]:
    try:
        payload = json.loads(path.read_text(encoding="utf-8", errors="replace"))
    except (OSError, json.JSONDecodeError):
        payload = {}
    return {
        "path": path.relative_to(root).as_posix(),
        "repo": path.parent.name,
        "status": payload.get("status") or payload.get("overall_status") or payload.get("result") or "unknown",
        "dispatch_id": payload.get("dispatch_id") or payload.get("contract_id") or path.stem.replace(".result", ""),
        "evidence_count": len(payload.get("evidence") or []),
        "stop_conditions": payload.get("stop_conditions_triggered") or payload.get("stop_conditions") or [],
    }


def latest_results(root: Path, limit: int = 12) -> list[dict[str, Any]]:
    outbox = root / ".aios" / "outbox"
    if not outbox.exists():
        return []
    paths = sorted(outbox.glob("*/*.json"), key=lambda p: p.stat().st_mtime, reverse=True)
    return [summarize_result(path, root) for path in paths[:limit]]


def git_changed_files(root: Path) -> list[dict[str, str]]:
    result = subprocess.run(
        ["git", "status", "--short"],
        cwd=root,
        text=True,
        capture_output=True,
        check=False,
    )
    rows = []
    for line in result.stdout.splitlines():
        if not line.strip():
            continue
        status = line[:2].strip() or "?"
        path = line[3:].strip()
        if any(part in Path(path).parts for part in HARD_BAN_PARTS):
            rows.append({"status": status, "path": "[redacted hard-ban path]"})
        else:
            rows.append({"status": status, "path": path})
    return rows


def monitor_health(root: Path) -> dict[str, Any]:
    path = root / ".aios" / "state" / "monitor_assessment.latest.json"
    if path.exists():
        try:
            payload = json.loads(path.read_text(encoding="utf-8", errors="replace"))
            if isinstance(payload, dict):
                return {
                    "health": payload.get("health", "unknown"),
                    "alerts": len(payload.get("findings") or []),
                    "generated_at": payload.get("generated_at"),
                }
        except json.JSONDecodeError:
            pass
    return {"health": "unknown", "alerts": 0, "generated_at": None}


def build_status(root: Path) -> dict[str, Any]:
    dispatch = dispatch_summary(root)
    active = active_contracts(root)
    health = monitor_health(root)
    blocked = list(dispatch["blocked"])
    if health["health"] not in {"clear", "unknown"}:
        blocked.append({"status": "monitor", "reason": health["health"]})
    next_actions = []
    if blocked:
        next_actions.append({"owner": "myworld", "action": "resolve_blocked_dispatches", "count": len(blocked)})
    if active:
        next_actions.append({"owner": "myworld", "action": "continue_active_contracts", "count": len(active)})
    if not next_actions:
        next_actions.append({"owner": "myworld", "action": "continue_observing"})
    return {
        "schema_version": SCHEMA_VERSION,
        "generated_at": now_iso(),
        "root": root.as_posix(),
        "health": health,
        "active_contracts": active,
        "dispatch_summary": dispatch,
        "latest_results": latest_results(root),
        "changed_files": git_changed_files(root),
        "blocked": blocked,
        "next_actions": next_actions,
    }


def contract_view(root: Path, contract_id: str) -> dict[str, Any]:
    pattern = f"{contract_id}-*.md"
    matches = sorted((root / "docs" / "contracts").glob(pattern))
    if not matches:
        matches = sorted((root / "docs" / "contracts").glob(f"{contract_id.lower()}-*.md"))
    path = matches[0] if matches else None
    fm = parse_frontmatter(path) if path else {}
    all_results = latest_results(root, limit=100)
    related = [row for row in all_results if contract_id.lower().replace("-", "_") in row["path"].lower() or contract_id.lower() in row["path"].lower()]
    return {
        "schema_version": "aios.work_view.contract.v1",
        "generated_at": now_iso(),
        "contract_id": contract_id,
        "found": bool(path),
        "path": path.relative_to(root).as_posix() if path else None,
        "status": fm.get("status"),
        "closed": bool(fm.get("closed")),
        "goal": fm.get("goal", ""),
        "related_results": related,
    }


def render_text(payload: dict[str, Any]) -> str:
    lines = [
        f"AIOS work view: {payload['health'].get('health', 'unknown')}",
        "",
        "Active contracts:",
    ]
    for row in payload["active_contracts"][:12]:
        lines.append(f"- {row['contract_id']} {row['status']}: {row['goal']}")
    if not payload["active_contracts"]:
        lines.append("- none")
    lines.extend(["", "Blocked:"])
    for row in payload["blocked"]:
        lines.append(f"- {row.get('contract_id') or row.get('dispatch_id') or row.get('status')}: {row.get('reason', '')}")
    if not payload["blocked"]:
        lines.append("- none")
    lines.extend(["", "Changed files:"])
    for row in payload["changed_files"][:20]:
        lines.append(f"- {row['status']} {row['path']}")
    if not payload["changed_files"]:
        lines.append("- none")
    lines.extend(["", "Next actions:"])
    for row in payload["next_actions"]:
        lines.append(f"- {row['owner']}: {row['action']}")
    return "\n".join(lines)


def tail_view(root: Path, limit: int) -> list[dict[str, Any]]:
    results = latest_results(root, limit=limit)
    events = load_jsonl(root / ".aios" / "state" / "dispatches.jsonl")[-limit:]
    tail = [{"kind": "result", **row} for row in results]
    tail.extend({"kind": "dispatch", "dispatch_id": row.get("dispatch_id"), "status": row.get("status"), "contract_id": row.get("contract_id")} for row in events)
    return tail[-limit:]


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Show current AIOS work without exposing raw private output")
    parser.add_argument("--root", type=Path, default=Path.cwd())
    sub = parser.add_subparsers(dest="cmd", required=True)
    status = sub.add_parser("status")
    status.add_argument("--json", action="store_true")
    contract = sub.add_parser("contract")
    contract.add_argument("contract_id")
    contract.add_argument("--json", action="store_true")
    tail = sub.add_parser("tail")
    tail.add_argument("--limit", type=int, default=20)
    tail.add_argument("--json", action="store_true")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    root = args.root.resolve()
    if args.cmd == "status":
        payload = build_status(root)
        if args.json:
            print(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True))
        else:
            print(render_text(payload))
    elif args.cmd == "contract":
        payload = contract_view(root, args.contract_id)
        if args.json:
            print(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True))
        else:
            print(f"{payload['contract_id']} status={payload.get('status')} closed={payload.get('closed')}")
    elif args.cmd == "tail":
        payload = {"schema_version": "aios.work_view.tail.v1", "generated_at": now_iso(), "items": tail_view(root, args.limit)}
        if args.json:
            print(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True))
        else:
            for item in payload["items"]:
                print(f"{item.get('kind')} {item.get('contract_id') or item.get('dispatch_id')} {item.get('status')}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
