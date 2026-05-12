#!/usr/bin/env python3
"""Build a local AIOS control-plane snapshot for the static control app."""

from __future__ import annotations

import argparse
import json
import re
import subprocess
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


SCHEMA_VERSION = "aios.control_snapshot.v1"
REPOS = ("hivemind", "memoryOS", "CapabilityOS")


def now_iso() -> str:
    return datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds")


def parse_frontmatter(text: str) -> tuple[dict[str, str], str]:
    if not text.startswith("---\n"):
        return {}, text
    end = text.find("\n---\n", 4)
    if end == -1:
        return {}, text
    data: dict[str, str] = {}
    for raw in text[4:end].splitlines():
        key, sep, value = raw.partition(":")
        if sep:
            data[key.strip()] = value.strip()
    return data, text[end + 5 :]


def section(body: str, heading: str) -> str:
    marker = f"## {heading}"
    start = body.find(marker)
    if start == -1:
        return ""
    rest = body[start + len(marker) :]
    next_start = rest.find("\n## ")
    return rest[:next_start] if next_start != -1 else rest


def bullet_items(text: str, limit: int = 8) -> list[str]:
    items: list[str] = []
    current: str | None = None
    for raw in text.splitlines():
        stripped = raw.strip()
        if stripped.startswith("- "):
            if current:
                items.append(current)
            current = stripped[2:].strip()
        elif current and raw.startswith((" ", "\t")):
            current = f"{current} {stripped}".strip()
    if current:
        items.append(current)
    return items[:limit]


def read_json(path: Path) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None


def load_goals(root: Path) -> dict[str, Any]:
    goals: list[dict[str, Any]] = []
    for path in sorted((root / "docs" / "goals").glob("AIOS-GOAL-*.md")):
        text = path.read_text(encoding="utf-8", errors="replace")
        frontmatter, body = parse_frontmatter(text)
        if path.name.endswith("-evolution.md"):
            continue
        goals.append(
            {
                "id": frontmatter.get("goal_id") or path.stem,
                "slug": frontmatter.get("slug") or path.stem,
                "status": frontmatter.get("status") or "unknown",
                "path": path.relative_to(root).as_posix(),
                "north_star": section(body, "North Star").strip().splitlines()[:4],
                "preferred_next": bullet_items(section(body, "Preferred Next Improvements"), limit=6),
                "completed": bullet_items(section(body, "Completed Improvements"), limit=8),
            }
        )
    evolution = read_goal_evolution(root / "docs" / "goals" / "AIOS-GOAL-0001-evolution.md", root)
    return {"items": goals, "active": next((g for g in goals if g["status"] == "active"), goals[0] if goals else None), "evolution": evolution}


def read_goal_evolution(path: Path, root: Path) -> dict[str, Any] | None:
    if not path.exists():
        return None
    text = path.read_text(encoding="utf-8", errors="replace")
    rec = {"path": path.relative_to(root).as_posix(), "recommendation": None, "monitor_health": None, "readiness": None}
    for line in text.splitlines():
        stripped = line.strip()
        if stripped.startswith("- path:"):
            rec["recommendation"] = stripped.partition("`")[2].rpartition("`")[0]
        elif stripped.startswith("- monitor_health:"):
            rec["monitor_health"] = stripped.partition("`")[2].rpartition("`")[0]
        elif stripped.startswith("- readiness:"):
            rec["readiness"] = stripped.partition("`")[2].rpartition("`")[0]
    return rec


def load_contracts(root: Path) -> dict[str, Any]:
    rows: list[dict[str, Any]] = []
    for path in sorted((root / "docs" / "contracts").glob("ASC-*.md")):
        text = path.read_text(encoding="utf-8", errors="replace")
        frontmatter, body = parse_frontmatter(text)
        rows.append(
            {
                "id": frontmatter.get("contract_id") or path.stem.split("-")[0],
                "slug": frontmatter.get("slug") or path.stem,
                "status": frontmatter.get("status") or "unknown",
                "goal": frontmatter.get("goal") or first_heading(body),
                "created": frontmatter.get("created", ""),
                "accepted": frontmatter.get("accepted", ""),
                "closed": frontmatter.get("closed", ""),
                "path": path.relative_to(root).as_posix(),
                "stop_conditions": bullet_items(section(body, "Stop Conditions"), limit=8),
            }
        )
    counts = Counter(row["status"] for row in rows)
    latest = sorted(rows, key=lambda row: row["id"], reverse=True)[:10]
    return {"counts": dict(counts), "latest": latest, "total": len(rows)}


def first_heading(body: str) -> str:
    for line in body.splitlines():
        if line.startswith("# "):
            return line[2:].strip()
    return ""


def load_dispatches(root: Path) -> dict[str, Any]:
    state_path = root / ".aios" / "state" / "dispatches.jsonl"
    events: list[dict[str, Any]] = []
    if state_path.exists():
        for raw in state_path.read_text(encoding="utf-8", errors="replace").splitlines():
            try:
                row = json.loads(raw)
            except json.JSONDecodeError:
                continue
            if isinstance(row, dict):
                events.append(row)
    by_id: dict[str, dict[str, Any]] = {}
    timeline: list[dict[str, Any]] = []
    for row in events:
        dispatch_id = str(row.get("dispatch_id") or "")
        if not dispatch_id:
            continue
        entry = by_id.setdefault(
            dispatch_id,
            {
                "dispatch_id": dispatch_id,
                "contract_id": row.get("contract_id"),
                "goal": row.get("goal"),
                "sent": set(),
                "collected": set(),
                "status": row.get("status") or row.get("event"),
                "reason": row.get("reason", ""),
                "timestamp": row.get("timestamp", ""),
            },
        )
        if row.get("repo") and row.get("event") == "sent":
            entry["sent"].add(row["repo"])
        if row.get("repo") and row.get("event") == "collected":
            entry["collected"].add(row["repo"])
        for key in ("contract_id", "goal", "reason", "timestamp"):
            if row.get(key):
                entry[key] = row[key]
        if row.get("status"):
            entry["status"] = row["status"]
        timeline.append({"dispatch_id": dispatch_id, "event": row.get("event"), "repo": row.get("repo"), "status": row.get("status"), "timestamp": row.get("timestamp")})
    rows = []
    for entry in by_id.values():
        rows.append({**entry, "sent": sorted(entry["sent"]), "collected": sorted(entry["collected"])})
    rows.sort(key=lambda row: row.get("timestamp") or "", reverse=True)
    counts = Counter(row["status"] for row in rows)
    return {"counts": dict(counts), "latest": rows[:12], "timeline": timeline[-30:], "total": len(rows)}


def git_status(root: Path, repo: str) -> dict[str, Any]:
    repo_path = root / repo
    if not repo_path.exists():
        return {"repo": repo, "exists": False, "dirty": None, "changes": []}
    try:
        result = subprocess.run(
            ["git", "-C", repo_path.as_posix(), "status", "--short", "--untracked-files=all"],
            text=True,
            capture_output=True,
            timeout=10,
            check=False,
        )
    except (OSError, subprocess.SubprocessError) as exc:
        return {"repo": repo, "exists": True, "dirty": None, "changes": [], "error": str(exc)}
    changes = [line for line in result.stdout.splitlines() if line.strip()]
    return {"repo": repo, "exists": True, "dirty": bool(changes), "changes": changes[:12]}


def load_repos(root: Path) -> dict[str, Any]:
    inbox = root / ".aios" / "inbox"
    outbox = root / ".aios" / "outbox"
    goal_inbox = root / ".aios" / "goal_inbox"
    goal_routes = root / ".aios" / "goal_routes"
    rows = []
    for repo in REPOS:
        rows.append(
            {
                **git_status(root, repo),
                "inbox_count": len(list((inbox / repo).glob("*.json"))) if (inbox / repo).exists() else 0,
                "outbox_count": len(list((outbox / repo).glob("*.json"))) if (outbox / repo).exists() else 0,
                "goal_count": len(list((goal_inbox / repo).glob("*.json"))) if (goal_inbox / repo).exists() else 0,
                "route_count": len(list((goal_routes / repo).glob("*.json"))) if (goal_routes / repo).exists() else 0,
            }
        )
    return {"items": rows}


def load_monitor(root: Path) -> dict[str, Any] | None:
    return read_json(root / ".aios" / "state" / "monitor_assessment.latest.json")


def load_round(root: Path) -> dict[str, Any] | None:
    return read_json(root / ".aios" / "state" / "round_controller.latest.json")


def load_aios_inputs(root: Path) -> dict[str, Any]:
    contracts = sorted((root / "docs" / "contracts").glob("ASC-*.md"), reverse=True)
    trace_ids: list[str] = []
    route_ids: list[str] = []
    run_ids: list[str] = []
    for path in contracts[:8]:
        text = path.read_text(encoding="utf-8", errors="replace")
        trace_ids.extend(unique_tokens(text, "rtrace_"))
        route_ids.extend(unique_tokens(text, "cap_"))
        run_ids.extend(unique_tokens(text, "run_"))
    return {"memory_traces": trace_ids[:6], "capability_routes": route_ids[:8], "hive_runs": run_ids[:6]}


def unique_tokens(text: str, prefix: str) -> list[str]:
    pattern = re.compile(rf"{re.escape(prefix)}[A-Za-z0-9_]+")
    seen: list[str] = []
    for match in pattern.finditer(text):
        token = match.group(0)
        if token not in seen:
            seen.append(token)
    return seen


def load_stop_lanes(root: Path) -> dict[str, Any]:
    lanes: dict[str, list[str]] = defaultdict(list)
    for row in load_contracts(root)["latest"]:
        for stop in row.get("stop_conditions", []):
            lanes[stop].append(row["id"])
    return {"items": [{"name": name, "contracts": contracts[:5]} for name, contracts in sorted(lanes.items())[:12]]}


def build_snapshot(root: Path) -> dict[str, Any]:
    monitor = load_monitor(root)
    round_state = load_round(root)
    return {
        "schema_version": SCHEMA_VERSION,
        "generated_at": now_iso(),
        "root": root.as_posix(),
        "goals": load_goals(root),
        "contracts": load_contracts(root),
        "dispatches": load_dispatches(root),
        "repos": load_repos(root),
        "aios_inputs": load_aios_inputs(root),
        "monitor": monitor,
        "round_controller": round_state,
        "stop_lanes": load_stop_lanes(root),
        "next_actions": (monitor or {}).get("next_actions", []),
    }


def write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def write_js(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    body = json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True)
    path.write_text(f"window.AIOS_CONTROL_SNAPSHOT = {body};\n", encoding="utf-8")


def check_app_js(root: Path, path: str) -> dict[str, Any]:
    target = root / path
    if not target.exists():
        return {"ok": False, "path": path, "errors": ["app js not found"]}
    text = target.read_text(encoding="utf-8", errors="replace")
    errors: list[str] = []
    for required in ("AIOS_CONTROL_SNAPSHOT", "renderContracts", "renderDispatches", "renderRepos", "renderRoutes"):
        if required not in text:
            errors.append(f"missing marker: {required}")
    try:
        result = subprocess.run(["node", "--check", target.as_posix()], text=True, capture_output=True, timeout=10, check=False)
    except FileNotFoundError:
        result = None
    except (OSError, subprocess.SubprocessError) as exc:
        errors.append(f"node check failed: {exc}")
        result = None
    if result is not None and result.returncode != 0:
        errors.append(result.stderr.strip() or result.stdout.strip() or "node check failed")
    return {"ok": not errors, "path": path, "errors": errors, "node_checked": result is not None}


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", default=".")
    parser.add_argument("--write-json")
    parser.add_argument("--write-js")
    parser.add_argument("--check-app-js")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args(argv)

    root = Path(args.root).resolve()
    if args.check_app_js:
        result = check_app_js(root, args.check_app_js)
        if args.json:
            print(json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True))
        if not result["ok"]:
            raise SystemExit(1)
        return 0

    snapshot = build_snapshot(root)
    if args.write_json:
        write_json(root / args.write_json, snapshot)
    if args.write_js:
        write_js(root / args.write_js, snapshot)
    if args.json or not (args.write_json or args.write_js):
        print(json.dumps(snapshot, ensure_ascii=False, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
