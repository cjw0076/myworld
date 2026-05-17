#!/usr/bin/env python3
"""AIOS-native runtime entrypoint.

This is the user-facing orchestration surface. Provider CLIs, Claude, Codex,
and repo-local scripts remain interchangeable substrates behind this command.
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from aios_primitives import events as primitive_events


STATUS_SCHEMA = "aios.runtime.status.v1"
STEP_SCHEMA = "aios.runtime.step.v1"
RUN_SCHEMA = "aios.runtime.run.v1"


def now_iso() -> str:
    return datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds")


def root_path(value: Path | None) -> Path:
    return (value or Path.cwd()).resolve()


def run_command(root: Path, command: list[str], *, timeout: int = 180) -> dict[str, Any]:
    started_at = now_iso()
    try:
        result = subprocess.run(
            command,
            cwd=root,
            text=True,
            capture_output=True,
            timeout=timeout,
            check=False,
        )
        return {
            "command": command,
            "started_at": started_at,
            "finished_at": now_iso(),
            "returncode": result.returncode,
            "stdout": result.stdout,
            "stderr": result.stderr,
            "timed_out": False,
        }
    except subprocess.TimeoutExpired as exc:
        return {
            "command": command,
            "started_at": started_at,
            "finished_at": now_iso(),
            "returncode": 124,
            "stdout": exc.stdout or "",
            "stderr": exc.stderr or "",
            "timed_out": True,
        }


def json_command(root: Path, name: str, command: list[str], *, timeout: int = 180) -> dict[str, Any]:
    raw = run_command(root, command, timeout=timeout)
    parsed = None
    parse_error = ""
    if raw["stdout"].strip():
        try:
            parsed = json.loads(raw["stdout"])
        except json.JSONDecodeError as exc:
            parse_error = str(exc)
    return {
        "name": name,
        "status": "passed" if raw["returncode"] == 0 and not parse_error else "failed",
        "returncode": raw["returncode"],
        "timed_out": raw["timed_out"],
        "parsed": parsed,
        "parse_error": parse_error,
        "stderr_tail": raw["stderr"][-1000:],
    }


def text_command(root: Path, name: str, command: list[str], *, timeout: int = 180) -> dict[str, Any]:
    raw = run_command(root, command, timeout=timeout)
    return {
        "name": name,
        "status": "passed" if raw["returncode"] == 0 else "failed",
        "returncode": raw["returncode"],
        "timed_out": raw["timed_out"],
        "stdout": raw["stdout"],
        "stderr_tail": raw["stderr"][-1000:],
    }


def parse_round_status(stdout: str) -> dict[str, Any]:
    parsed: dict[str, Any] = {}
    for line in stdout.splitlines():
        key, sep, value = line.partition("=")
        if not sep:
            continue
        value = value.strip()
        if value in {"true", "false"}:
            parsed[key.strip()] = value == "true"
        elif value.isdigit():
            parsed[key.strip()] = int(value)
        else:
            parsed[key.strip()] = value
    return parsed


def dispatch_summary(payload: dict[str, Any] | None) -> dict[str, Any]:
    rows = (payload or {}).get("dispatches") or []
    pending = [
        row
        for row in rows
        if row.get("status") in {"created", "sent", "collected"}
        and not row.get("reason")
    ]
    return {
        "total": len(rows),
        "pending": len(pending),
        "latest": rows[-1] if rows else None,
    }


def primitive_event_summary(root: Path) -> dict[str, Any]:
    rows = primitive_events.read_events(root=root)
    return {
        "count": len(rows),
        "last": rows[-1] if rows else None,
    }


def build_status(root: Path) -> dict[str, Any]:
    monitor = json_command(root, "monitor", [sys.executable, "scripts/aios_monitor.py", "assess", "--json"])
    readiness = json_command(root, "readiness", [sys.executable, "scripts/aios_readiness.py", "--json"])
    dispatch = json_command(root, "dispatch", [sys.executable, "scripts/aios_dispatch.py", "status", "--json"])
    round_raw = text_command(root, "round_controller", [sys.executable, "scripts/aios_round_controller.py", "status"])
    round_status = parse_round_status(round_raw.get("stdout", ""))
    monitor_health = ((monitor.get("parsed") or {}).get("health")) if monitor.get("parsed") else "unknown"
    return {
        "schema_version": STATUS_SCHEMA,
        "generated_at": now_iso(),
        "root": root.as_posix(),
        "status": "ready" if monitor_health == "clear" else "blocked",
        "monitor": monitor,
        "readiness": readiness,
        "dispatch": {
            "step": dispatch,
            "summary": dispatch_summary(dispatch.get("parsed")),
        },
        "round_controller": {
            "step": {k: v for k, v in round_raw.items() if k != "stdout"},
            "parsed": round_status,
        },
        "primitive_events": primitive_event_summary(root),
    }


def run_step(root: Path, *, execute_children: bool = False) -> dict[str, Any]:
    command = [sys.executable, "scripts/aios_round_controller.py", "once", "--json"]
    if execute_children:
        command.insert(-1, "--execute-children")
    step = json_command(root, "round_controller_once", command, timeout=600)
    parsed = step.get("parsed") or {}
    recommended_next = parsed.get("recommended_next")
    primitive_events.emit(
        "aios.runtime.step",
        "aios-runtime",
        {
            "status": step.get("status"),
            "round_status": parsed.get("status"),
            "recommended_next": recommended_next,
            "execute_children": execute_children,
        },
        root=root,
    )
    return {
        "schema_version": STEP_SCHEMA,
        "generated_at": now_iso(),
        "root": root.as_posix(),
        "status": step.get("status"),
        "step": step,
        "recommended_next": recommended_next,
    }


def run_loop(root: Path, *, max_rounds: int, interval_seconds: float, execute_children: bool = False) -> dict[str, Any]:
    if max_rounds <= 0:
        raise SystemExit("--max-rounds must be >= 1")
    rounds = []
    for idx in range(max_rounds):
        rounds.append(run_step(root, execute_children=execute_children))
        if idx < max_rounds - 1 and interval_seconds > 0:
            time.sleep(interval_seconds)
    status = "passed" if all(row.get("status") == "passed" for row in rounds) else "failed"
    return {
        "schema_version": RUN_SCHEMA,
        "generated_at": now_iso(),
        "root": root.as_posix(),
        "status": status,
        "rounds": rounds,
    }


def submit_goal(root: Path, args: argparse.Namespace) -> dict[str, Any]:
    command = [
        sys.executable,
        "scripts/aios_repo_goal.py",
        "submit",
        "--repo",
        args.repo,
        "--kind",
        args.kind,
        "--goal",
        args.goal,
        "--json",
    ]
    if args.summary:
        command.extend(["--summary", args.summary])
    if args.priority:
        command.extend(["--priority", args.priority])
    step = json_command(root, "repo_goal_submit", command)
    primitive_events.emit(
        "aios.runtime.submit_goal",
        "aios-runtime",
        {"repo": args.repo, "kind": args.kind, "status": step.get("status")},
        root=root,
    )
    return {
        "schema_version": "aios.runtime.submit_goal.v1",
        "generated_at": now_iso(),
        "root": root.as_posix(),
        "status": step.get("status"),
        "step": step,
    }


def sprint_loop(root: Path, args: argparse.Namespace) -> dict[str, Any]:
    command = [
        sys.executable,
        "scripts/aios_sprint_loop.py",
        "--root",
        root.as_posix(),
        *args.args,
    ]
    step = json_command(root, "sprint_loop", command, timeout=args.timeout)
    parsed = step.get("parsed") or {}
    primitive_events.emit(
        "aios.runtime.sprint_loop",
        "aios-runtime",
        {
            "status": step.get("status"),
            "sprint_status": parsed.get("status"),
            "sprint_file": parsed.get("sprint_file"),
            "next_task": parsed.get("next_task") or parsed.get("task"),
        },
        root=root,
    )
    return {
        "schema_version": "aios.runtime.sprint_loop.v1",
        "generated_at": now_iso(),
        "root": root.as_posix(),
        "status": step.get("status"),
        "step": step,
    }


def emit(payload: dict[str, Any], as_json: bool) -> None:
    if as_json:
        print(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True))
    else:
        print(f"{payload.get('schema_version')} status={payload.get('status')}")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="AIOS-native runtime entrypoint")
    parser.add_argument("--root", type=Path, default=None)
    sub = parser.add_subparsers(dest="cmd", required=True)

    status = sub.add_parser("status")
    status.add_argument("--json", action="store_true")

    step = sub.add_parser("step")
    step.add_argument("--execute-children", action="store_true")
    step.add_argument("--json", action="store_true")

    run = sub.add_parser("run")
    run.add_argument("--max-rounds", type=int, default=1)
    run.add_argument("--interval-seconds", type=float, default=30)
    run.add_argument("--execute-children", action="store_true")
    run.add_argument("--json", action="store_true")

    submit = sub.add_parser("submit-goal")
    submit.add_argument("--repo", required=True, choices=["myworld", "hivemind", "memoryOS", "CapabilityOS"])
    submit.add_argument("--kind", default="goal", choices=["goal", "friction", "blocker", "improvement", "observation"])
    submit.add_argument("--goal", required=True)
    submit.add_argument("--summary", default="")
    submit.add_argument("--priority", default="")
    submit.add_argument("--json", action="store_true")

    sprint = sub.add_parser("sprint-loop")
    sprint.add_argument("--timeout", type=int, default=1200)
    sprint.add_argument("--json", action="store_true")
    sprint.add_argument("args", nargs=argparse.REMAINDER)
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    root = root_path(args.root)
    if args.cmd == "status":
        payload = build_status(root)
    elif args.cmd == "step":
        payload = run_step(root, execute_children=args.execute_children)
    elif args.cmd == "run":
        payload = run_loop(root, max_rounds=args.max_rounds, interval_seconds=args.interval_seconds, execute_children=args.execute_children)
    elif args.cmd == "submit-goal":
        payload = submit_goal(root, args)
    elif args.cmd == "sprint-loop":
        if "--json" in args.args:
            args.json = True
        payload = sprint_loop(root, args)
    else:
        parser.error(f"unknown command: {args.cmd}")
    emit(payload, getattr(args, "json", False))
    if args.cmd == "status":
        return 0
    return 0 if payload.get("status") in {"ready", "passed"} else 1


if __name__ == "__main__":
    raise SystemExit(main())
