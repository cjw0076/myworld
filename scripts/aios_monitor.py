#!/usr/bin/env python3
"""AIOS control-plane monitor.

The monitor reads MyWorld control-plane artifacts and reports drift. It does
not execute child repo work and does not edit child repo files.
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


REPOS = ("hivemind", "memoryOS", "CapabilityOS")
STATE_LOG = Path(".aios/state/dispatches.jsonl")
MONITOR_LOG = Path(".aios/state/monitor.jsonl")


def now_iso() -> str:
    return datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds")


def parse_frontmatter(path: Path) -> dict[str, str]:
    if not path.exists():
        return {}
    text = path.read_text(encoding="utf-8")
    if not text.startswith("---\n"):
        return {}
    end = text.find("\n---\n", 4)
    if end == -1:
        return {}
    data: dict[str, str] = {}
    current_key: str | None = None
    for line in text[4:end].splitlines():
        if not line.strip():
            continue
        if line.startswith((" ", "\t")) and current_key:
            data[current_key] = f"{data[current_key]} {line.strip()}".strip()
            continue
        key, sep, value = line.partition(":")
        if sep:
            current_key = key.strip()
            data[current_key] = value.strip()
    return data


def load_events(root: Path) -> list[dict[str, Any]]:
    path = root / STATE_LOG
    if not path.exists():
        return []
    events: list[dict[str, Any]] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        if line.strip():
            events.append(json.loads(line))
    return events


def dispatch_summary(root: Path) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    events = load_events(root)
    rows: dict[str, dict[str, Any]] = {}
    alerts: list[dict[str, Any]] = []
    for event in events:
        dispatch_id = event.get("dispatch_id")
        if not dispatch_id:
            continue
        row = rows.setdefault(str(dispatch_id), {"dispatch_id": dispatch_id, "sent": [], "collected": []})
        if event.get("event") == "created":
            row.update(
                {
                    "contract_id": event.get("contract_id"),
                    "contract_path": event.get("contract_path"),
                    "recorded_contract_status": event.get("contract_status"),
                    "created_status": event.get("status"),
                }
            )
        elif event.get("event") == "sent":
            row["sent"].append(event.get("repo"))
        elif event.get("event") == "collected":
            row["collected"].append(event.get("repo"))
        elif event.get("event") == "stopped":
            row["stopped"] = True
            row["reason"] = event.get("reason")

    for row in rows.values():
        contract_path_value = str(row.get("contract_path") or "")
        contract_path = root / contract_path_value if contract_path_value else None
        if contract_path is None or not contract_path.is_file():
            frontmatter = {}
            if row.get("recorded_contract_status"):
                alerts.append(
                    {
                        "code": "dispatch_contract_path_missing",
                        "dispatch_id": row["dispatch_id"],
                        "contract_path": contract_path_value,
                    }
                )
        else:
            frontmatter = parse_frontmatter(contract_path)
        current_status = frontmatter.get("status")
        row["current_contract_status"] = current_status
        if current_status and row.get("recorded_contract_status") and current_status != row.get("recorded_contract_status"):
            alerts.append(
                {
                    "code": "dispatch_contract_status_stale",
                    "dispatch_id": row["dispatch_id"],
                    "recorded": row.get("recorded_contract_status"),
                    "current": current_status,
                    "contract_path": row.get("contract_path"),
                }
            )
        sent = set(str(repo) for repo in row.get("sent") or [])
        collected = set(str(repo) for repo in row.get("collected") or [])
        missing = sorted(sent - collected)
        if missing:
            alerts.append({"code": "dispatch_results_pending", "dispatch_id": row["dispatch_id"], "repos": missing})
    return list(rows.values()), alerts


def git_status(root: Path, repo: str) -> dict[str, Any]:
    path = root / repo
    if not path.exists():
        return {"repo": repo, "exists": False, "dirty": False, "entries": []}
    result = subprocess.run(
        ["git", "-C", path.as_posix(), "status", "--short", "--untracked-files=all"],
        text=True,
        capture_output=True,
        check=False,
    )
    entries = [line for line in result.stdout.splitlines() if line.strip()]
    generated = [line for line in entries if "__pycache__" in line or line.endswith(".pyc")]
    return {
        "repo": repo,
        "exists": True,
        "returncode": result.returncode,
        "dirty": bool(entries),
        "entries": entries,
        "generated_cache_entries": generated,
    }


def contract_rows(root: Path) -> list[dict[str, Any]]:
    rows = []
    for path in sorted((root / "docs/contracts").glob("ASC-*.md")):
        fm = parse_frontmatter(path)
        rows.append(
            {
                "path": path.relative_to(root).as_posix(),
                "contract_id": fm.get("contract_id"),
                "status": fm.get("status"),
                "accepted": fm.get("accepted"),
                "closed": fm.get("closed"),
            }
        )
    return rows


def snapshot(root: Path) -> dict[str, Any]:
    dispatches, alerts = dispatch_summary(root)
    repos = [git_status(root, repo) for repo in REPOS]
    for repo in repos:
        if repo["dirty"]:
            alerts.append({"code": "repo_dirty", "repo": repo["repo"], "entries": repo["entries"]})
        if repo.get("generated_cache_entries"):
            alerts.append(
                {
                    "code": "generated_cache_present",
                    "repo": repo["repo"],
                    "entries": repo["generated_cache_entries"],
                }
            )
    return {
        "schema_version": "aios.monitor.v1",
        "generated_at": now_iso(),
        "contracts": contract_rows(root),
        "dispatches": dispatches,
        "repos": repos,
        "alerts": alerts,
    }


def write_snapshot(root: Path, data: dict[str, Any]) -> None:
    path = root / MONITOR_LOG
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as fh:
        fh.write(json.dumps(data, ensure_ascii=False, sort_keys=True) + "\n")


def cmd_snapshot(args: argparse.Namespace) -> int:
    root = Path.cwd().resolve()
    data = snapshot(root)
    if args.write:
        write_snapshot(root, data)
    if args.json:
        print(json.dumps(data, ensure_ascii=False, indent=2, sort_keys=True))
    else:
        print(f"contracts={len(data['contracts'])} dispatches={len(data['dispatches'])} alerts={len(data['alerts'])}")
        for alert in data["alerts"]:
            print(f"- {alert['code']}: {alert}")
    if args.fail_on_alert and data["alerts"]:
        return 1
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="AIOS control-plane monitor")
    sub = parser.add_subparsers(dest="cmd", required=True)
    snap = sub.add_parser("snapshot", help="emit one control-plane monitor snapshot")
    snap.add_argument("--json", action="store_true")
    snap.add_argument("--write", action="store_true", help="append to .aios/state/monitor.jsonl")
    snap.add_argument("--fail-on-alert", action="store_true")
    snap.set_defaults(func=cmd_snapshot)
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    return int(args.func(args))


if __name__ == "__main__":
    sys.exit(main())
