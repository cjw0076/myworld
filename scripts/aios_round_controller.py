#!/usr/bin/env python3
"""Persistent AIOS control-plane round controller.

This controller keeps MyWorld awake at the control-plane layer without making a
chat turn responsible for continuity. By default it runs bounded, provider-free
rounds: monitor, goal evolution, dispatch apply, and child watcher status.
Child agent execution is opt-in.
"""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


SCHEMA_VERSION = "aios.round_controller.v1"
REPOS = ("hivemind", "memoryOS", "CapabilityOS")
STATE_DIR = Path(".aios/state")
RUN_DIR = Path(".aios/run")
LOG_DIR = Path(".aios/logs")
EVENT_LOG = STATE_DIR / "round_controller.jsonl"
LATEST_FILE = STATE_DIR / "round_controller.latest.json"
PID_FILE = RUN_DIR / "aios_round_controller.pid"
STOP_FILE = RUN_DIR / "aios_round_controller.stop"
SUPERVISOR_LOG = LOG_DIR / "aios_round_controller.supervisor.log"
DEFAULT_GOAL = Path("docs/goals/AIOS-GOAL-0001-make-something-great.md")


def now_iso() -> str:
    return datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds")


def ensure_layout(root: Path) -> None:
    for path in (root / STATE_DIR, root / RUN_DIR, root / LOG_DIR):
        path.mkdir(parents=True, exist_ok=True)


def run_command(root: Path, command: list[str], *, timeout: int = 120) -> dict[str, Any]:
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


def json_step(root: Path, name: str, command: list[str], *, timeout: int = 120) -> dict[str, Any]:
    raw = run_command(root, command, timeout=timeout)
    parsed: Any = None
    error = ""
    if raw["stdout"].strip():
        try:
            parsed = json.loads(raw["stdout"])
        except json.JSONDecodeError as exc:
            error = f"invalid_json: {exc}"
    status = "passed" if raw["returncode"] == 0 and not error else "failed"
    return {
        "name": name,
        "status": status,
        "returncode": raw["returncode"],
        "timed_out": raw["timed_out"],
        "parsed": parsed,
        "error": error,
        "stderr_tail": raw["stderr"][-1000:],
    }


def text_step(root: Path, name: str, command: list[str], *, timeout: int = 120) -> dict[str, Any]:
    raw = run_command(root, command, timeout=timeout)
    return {
        "name": name,
        "status": "passed" if raw["returncode"] == 0 else "failed",
        "returncode": raw["returncode"],
        "timed_out": raw["timed_out"],
        "stdout": raw["stdout"],
        "stderr_tail": raw["stderr"][-1000:],
    }


def parse_child_status(stdout: str) -> dict[str, Any]:
    repos: dict[str, dict[str, Any]] = {}
    pending_total = 0
    for line in stdout.splitlines():
        parts = line.split()
        if not parts:
            continue
        repo = parts[0]
        values: dict[str, Any] = {}
        for item in parts[1:]:
            key, sep, value = item.partition("=")
            if not sep:
                continue
            if value.isdigit():
                values[key] = int(value)
            elif value in {"true", "false"}:
                values[key] = value == "true"
            else:
                values[key] = value
        repos[repo] = values
        pending_total += int(values.get("pending") or 0)
    return {"repos": repos, "pending_total": pending_total}


def child_watcher_status(root: Path) -> dict[str, Any]:
    script = root / "scripts/aios_child_watcher.sh"
    if not script.exists():
        return {"name": "child_watcher_status", "status": "skipped", "reason": "missing_child_watcher"}
    step = text_step(root, "child_watcher_status", [script.as_posix(), "status"], timeout=60)
    step["parsed"] = parse_child_status(step.get("stdout") or "")
    step.pop("stdout", None)
    return step


def execute_pending_children(root: Path, child_status: dict[str, Any]) -> list[dict[str, Any]]:
    script = root / "scripts/aios_child_watcher.sh"
    if not script.exists():
        return []
    parsed = child_status.get("parsed") or {}
    repos = parsed.get("repos") or {}
    executions: list[dict[str, Any]] = []
    for repo in REPOS:
        if int((repos.get(repo) or {}).get("pending") or 0) <= 0:
            continue
        executions.append(text_step(root, f"child_once_{repo}", [script.as_posix(), "once", "--repo", repo], timeout=1800))
    return executions


def build_recommended_next(steps: dict[str, Any], child_status: dict[str, Any], child_executions: list[dict[str, Any]]) -> dict[str, Any]:
    monitor = ((steps.get("monitor") or {}).get("parsed") or {})
    if monitor.get("health") not in (None, "clear"):
        return {"action": "hold_for_monitor", "reason": monitor.get("health")}

    goal = ((steps.get("goal_evolution") or {}).get("parsed") or {})
    goal_stops = goal.get("stop_conditions") or []
    if goal_stops:
        return {"action": "hold_for_goal_stop_conditions", "reason": goal_stops}

    loop = ((steps.get("dispatch_loop") or {}).get("parsed") or {})
    actions = loop.get("actions") or []
    if actions:
        return {"action": "continue_dispatch", "reason": f"{len(actions)} dispatch action(s) recorded"}
    pending_results = [
        {
            "contract_id": item.get("contract_id"),
            "dispatch_id": item.get("dispatch_id"),
            "pending_results": item.get("pending_results"),
        }
        for item in loop.get("observations") or []
        if item.get("pending_results")
    ]
    if pending_results:
        return {"action": "run_dispatch_watcher", "pending": pending_results}

    pending_total = int(((child_status.get("parsed") or {}).get("pending_total")) or 0)
    if pending_total and not child_executions:
        return {"action": "run_child_watchers", "reason": f"{pending_total} pending packet(s)"}
    if any(item.get("status") != "passed" for item in child_executions):
        return {"action": "hold_for_child_execution", "reason": "child watcher execution failed"}

    recommendation = goal.get("recommendation") or {}
    if recommendation.get("path"):
        return {
            "action": "open_next_contract",
            "path": recommendation.get("path"),
            "candidate_task": recommendation.get("candidate_task"),
        }
    return {"action": "continue_observing", "reason": "no actionable recommendation"}


def append_receipt(root: Path, receipt: dict[str, Any]) -> None:
    ensure_layout(root)
    with (root / EVENT_LOG).open("a", encoding="utf-8") as fh:
        fh.write(json.dumps(receipt, ensure_ascii=False, sort_keys=True) + "\n")
    (root / LATEST_FILE).write_text(json.dumps(receipt, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def run_round(root: Path, *, goal: Path, execute_children: bool) -> dict[str, Any]:
    ensure_layout(root)
    steps: dict[str, Any] = {}

    monitor_script = root / "scripts/aios_monitor.py"
    if monitor_script.exists():
        steps["monitor"] = json_step(root, "monitor", [sys.executable, monitor_script.as_posix(), "assess", "--json"])
    else:
        steps["monitor"] = {"name": "monitor", "status": "skipped", "reason": "missing_monitor"}

    goal_script = root / "scripts/aios_goal_evolution.py"
    goal_path = goal if goal.is_absolute() else root / goal
    if goal_script.exists() and goal_path.exists():
        steps["goal_evolution"] = json_step(
            root,
            "goal_evolution",
            [sys.executable, goal_script.as_posix(), "plan", "--goal", goal.relative_to(root).as_posix() if goal.is_absolute() and goal.is_relative_to(root) else goal.as_posix(), "--json"],
        )
    else:
        steps["goal_evolution"] = {"name": "goal_evolution", "status": "skipped", "reason": "missing_goal_or_script"}

    loop_script = root / "scripts/aios_loop.py"
    if loop_script.exists():
        steps["dispatch_loop"] = json_step(root, "dispatch_loop", [sys.executable, loop_script.as_posix(), "once", "--apply", "--json"])
    else:
        steps["dispatch_loop"] = {"name": "dispatch_loop", "status": "skipped", "reason": "missing_dispatch_loop"}

    child_status = child_watcher_status(root)
    child_executions = execute_pending_children(root, child_status) if execute_children else []
    recommended_next = build_recommended_next(steps, child_status, child_executions)
    failed_steps = [name for name, step in steps.items() if step.get("status") == "failed"]
    if child_status.get("status") == "failed":
        failed_steps.append("child_watcher_status")

    receipt = {
        "schema_version": SCHEMA_VERSION,
        "generated_at": now_iso(),
        "root": root.as_posix(),
        "mode": "execute_children" if execute_children else "control_only",
        "status": "passed" if not failed_steps else "failed",
        "steps": steps,
        "child_watcher_status": child_status,
        "child_executions": child_executions,
        "failed_steps": failed_steps,
        "recommended_next": recommended_next,
    }
    append_receipt(root, receipt)
    return receipt


def pid_running(pid_path: Path) -> bool:
    if not pid_path.exists():
        return False
    try:
        pid = int(pid_path.read_text(encoding="utf-8").strip())
    except ValueError:
        return False
    try:
        os.kill(pid, 0)
    except OSError:
        return False
    return True


def cmd_once(args: argparse.Namespace) -> int:
    root = Path(args.root).resolve()
    receipt = run_round(root, goal=Path(args.goal), execute_children=args.execute_children)
    if args.json:
        print(json.dumps(receipt, ensure_ascii=False, indent=2, sort_keys=True))
    else:
        next_action = receipt["recommended_next"]["action"]
        print(f"status={receipt['status']} next={next_action}")
    return 0 if receipt["status"] == "passed" else 1


def cmd_run(args: argparse.Namespace) -> int:
    root = Path(args.root).resolve()
    ensure_layout(root)
    stop_path = root / STOP_FILE
    stop_path.unlink(missing_ok=True)
    iterations = 0
    while True:
        if stop_path.exists():
            return 0
        receipt = run_round(root, goal=Path(args.goal), execute_children=args.execute_children)
        iterations += 1
        if args.iterations and iterations >= args.iterations:
            return 0 if receipt["status"] == "passed" else 1
        time.sleep(args.interval)


def cmd_start(args: argparse.Namespace) -> int:
    root = Path(args.root).resolve()
    ensure_layout(root)
    pid_path = root / PID_FILE
    if pid_running(pid_path):
        print(f"AIOS round controller already running: pid {pid_path.read_text(encoding='utf-8').strip()}")
        return 0
    (root / STOP_FILE).unlink(missing_ok=True)
    log_fh = (root / SUPERVISOR_LOG).open("a", encoding="utf-8")
    command = [
        sys.executable,
        Path(__file__).resolve().as_posix(),
        "run",
        "--root",
        root.as_posix(),
        "--goal",
        args.goal,
        "--interval",
        str(args.interval),
    ]
    if args.execute_children:
        command.append("--execute-children")
    process = subprocess.Popen(command, cwd=root, stdout=log_fh, stderr=subprocess.STDOUT, start_new_session=True)
    pid_path.write_text(f"{process.pid}\n", encoding="utf-8")
    print(f"started AIOS round controller pid {process.pid}")
    return 0


def cmd_stop(args: argparse.Namespace) -> int:
    root = Path(args.root).resolve()
    ensure_layout(root)
    (root / STOP_FILE).write_text(f"{now_iso()}\n", encoding="utf-8")
    pid_path = root / PID_FILE
    if pid_running(pid_path):
        pid = int(pid_path.read_text(encoding="utf-8").strip())
        try:
            os.kill(pid, 15)
        except OSError:
            pass
        print(f"stop requested for AIOS round controller pid {pid}")
    else:
        print("stop requested; no running AIOS round controller")
    return 0


def cmd_status(args: argparse.Namespace) -> int:
    root = Path(args.root).resolve()
    pid_path = root / PID_FILE
    latest_path = root / LATEST_FILE
    print(f"root={root}")
    if pid_running(pid_path):
        print(f"running=true pid={pid_path.read_text(encoding='utf-8').strip()}")
    else:
        print("running=false")
    print(f"stop_file={(root / STOP_FILE).exists()}")
    if latest_path.exists():
        latest = json.loads(latest_path.read_text(encoding="utf-8"))
        print(f"latest_status={latest.get('status')}")
        print(f"latest_generated_at={latest.get('generated_at')}")
        print(f"latest_next={((latest.get('recommended_next') or {}).get('action'))}")
    else:
        print("latest_status=none")
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Run persistent AIOS control-plane rounds")
    sub = parser.add_subparsers(dest="cmd", required=True)

    def add_common(p: argparse.ArgumentParser) -> None:
        p.add_argument("--root", default=".", help="workspace root")
        p.add_argument("--goal", default=DEFAULT_GOAL.as_posix(), help="active goal file")

    once = sub.add_parser("once", help="run one bounded control-plane round")
    add_common(once)
    once.add_argument("--execute-children", action="store_true", help="also run one pending child watcher packet per repo")
    once.add_argument("--json", action="store_true")
    once.set_defaults(func=cmd_once)

    run = sub.add_parser("run", help="run foreground rounds until stopped")
    add_common(run)
    run.add_argument("--interval", type=float, default=30.0)
    run.add_argument("--iterations", type=int, default=0, help="0 means run until stopped")
    run.add_argument("--execute-children", action="store_true")
    run.set_defaults(func=cmd_run)

    start = sub.add_parser("start", help="start background round controller")
    add_common(start)
    start.add_argument("--interval", type=float, default=30.0)
    start.add_argument("--execute-children", action="store_true")
    start.set_defaults(func=cmd_start)

    stop = sub.add_parser("stop", help="request background controller stop")
    stop.add_argument("--root", default=".")
    stop.set_defaults(func=cmd_stop)

    status = sub.add_parser("status", help="show background/latest round state")
    status.add_argument("--root", default=".")
    status.set_defaults(func=cmd_status)
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    return int(args.func(args))


if __name__ == "__main__":
    sys.exit(main())
