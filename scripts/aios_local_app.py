#!/usr/bin/env python3
"""Local AIOS control app launcher.

This script packages the static control surface into a repeatable on-prem
workflow: refresh local state, serve the app, inspect status, and stop it.
"""

from __future__ import annotations

import argparse
import json
import os
import signal
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


SCHEMA_VERSION = "aios.local_app.v1"
RUN_DIR = Path(".aios/run")
LOG_DIR = Path(".aios/logs")
PID_FILE = RUN_DIR / "aios_control_app.pid"
PORT_FILE = RUN_DIR / "aios_control_app.port"
SERVER_LOG = LOG_DIR / "aios_control_app.server.log"
SNAPSHOT_JSON = Path("apps/control/aios-control-snapshot.json")
SNAPSHOT_JS = Path("apps/control/aios-control-data.js")
CONTROL_DIR = Path("apps/control")
DEFAULT_PORT = 8765


def now_iso() -> str:
    return datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds")


def ensure_layout(root: Path) -> None:
    for path in (root / RUN_DIR, root / LOG_DIR, root / CONTROL_DIR):
        path.mkdir(parents=True, exist_ok=True)


def run_command(root: Path, command: list[str], *, timeout: int = 120) -> dict[str, Any]:
    started_at = now_iso()
    try:
        result = subprocess.run(command, cwd=root, text=True, capture_output=True, timeout=timeout, check=False)
    except subprocess.TimeoutExpired as exc:
        return {
            "command": command,
            "returncode": 124,
            "stdout": exc.stdout or "",
            "stderr": exc.stderr or "",
            "started_at": started_at,
            "finished_at": now_iso(),
            "timed_out": True,
        }
    return {
        "command": command,
        "returncode": result.returncode,
        "stdout": result.stdout,
        "stderr": result.stderr,
        "started_at": started_at,
        "finished_at": now_iso(),
        "timed_out": False,
    }


def parse_json_stdout(raw: dict[str, Any]) -> Any:
    if raw.get("returncode") != 0 or not str(raw.get("stdout") or "").strip():
        return None
    try:
        return json.loads(raw["stdout"])
    except json.JSONDecodeError:
        return None


def pid_running(pid: int) -> bool:
    try:
        os.kill(pid, 0)
    except ProcessLookupError:
        return False
    except PermissionError:
        return True
    return True


def read_pid(root: Path) -> int | None:
    path = root / PID_FILE
    if not path.exists():
        return None
    try:
        return int(path.read_text(encoding="utf-8").strip())
    except ValueError:
        return None


def server_status(root: Path) -> dict[str, Any]:
    pid = read_pid(root)
    port = DEFAULT_PORT
    port_path = root / PORT_FILE
    if port_path.exists():
        try:
            port = int(port_path.read_text(encoding="utf-8").strip())
        except ValueError:
            port = DEFAULT_PORT
    running = bool(pid and pid_running(pid))
    return {
        "running": running,
        "pid": pid,
        "port": port,
        "url": f"http://127.0.0.1:{port}/",
        "pid_file": PID_FILE.as_posix(),
        "log_file": SERVER_LOG.as_posix(),
    }


def refresh(root: Path) -> dict[str, Any]:
    ensure_layout(root)
    monitor = run_command(root, [sys.executable, "scripts/aios_monitor.py", "assess", "--write", "--json"], timeout=120)
    snapshot = run_command(
        root,
        [
            sys.executable,
            "scripts/aios_control_snapshot.py",
            "--write-json",
            SNAPSHOT_JSON.as_posix(),
            "--write-js",
            SNAPSHOT_JS.as_posix(),
            "--json",
        ],
        timeout=120,
    )
    check = run_command(root, [sys.executable, "scripts/aios_control_snapshot.py", "--check-app-js", "apps/control/app.js", "--json"], timeout=60)
    ok = monitor["returncode"] == 0 and snapshot["returncode"] == 0 and check["returncode"] == 0
    return {
        "ok": ok,
        "generated_at": now_iso(),
        "monitor": parse_json_stdout(monitor),
        "snapshot": parse_json_stdout(snapshot),
        "app_check": parse_json_stdout(check),
        "snapshot_json": SNAPSHOT_JSON.as_posix(),
        "snapshot_js": SNAPSHOT_JS.as_posix(),
        "errors": compact_errors({"monitor": monitor, "snapshot": snapshot, "app_check": check}),
    }


def compact_errors(steps: dict[str, dict[str, Any]]) -> list[dict[str, Any]]:
    errors: list[dict[str, Any]] = []
    for name, raw in steps.items():
        if raw.get("returncode") != 0:
            errors.append(
                {
                    "step": name,
                    "returncode": raw.get("returncode"),
                    "stderr_tail": str(raw.get("stderr") or "")[-800:],
                    "stdout_tail": str(raw.get("stdout") or "")[-800:],
                }
            )
    return errors


def start_server(root: Path, *, port: int) -> dict[str, Any]:
    ensure_layout(root)
    current = server_status(root)
    if current["running"]:
        return {"ok": True, "started": False, "server": current}
    if not (root / CONTROL_DIR / "index.html").exists():
        raise SystemExit("control app missing; run refresh after ASC-0039")
    log_fh = (root / SERVER_LOG).open("a", encoding="utf-8")
    process = subprocess.Popen(
        [sys.executable, "-m", "http.server", str(port), "--bind", "127.0.0.1"],
        cwd=root / CONTROL_DIR,
        stdout=log_fh,
        stderr=log_fh,
        start_new_session=True,
    )
    (root / PID_FILE).write_text(str(process.pid), encoding="utf-8")
    (root / PORT_FILE).write_text(str(port), encoding="utf-8")
    time.sleep(0.2)
    return {"ok": True, "started": True, "server": server_status(root)}


def stop_server(root: Path) -> dict[str, Any]:
    status = server_status(root)
    pid = status.get("pid")
    stopped = False
    if status["running"] and pid:
        os.kill(int(pid), signal.SIGTERM)
        for _ in range(20):
            if not pid_running(int(pid)):
                stopped = True
                break
            time.sleep(0.1)
        if not stopped and pid_running(int(pid)):
            os.kill(int(pid), signal.SIGKILL)
            stopped = True
    for path in (root / PID_FILE, root / PORT_FILE):
        if path.exists():
            path.unlink()
    return {"ok": True, "stopped": stopped, "server": server_status(root)}


def round_status(root: Path) -> dict[str, Any]:
    raw = run_command(root, [sys.executable, "scripts/aios_round_controller.py", "status"], timeout=30)
    parsed: dict[str, Any] = {"returncode": raw["returncode"], "stdout": raw["stdout"].strip()}
    for line in raw["stdout"].splitlines():
        parts = line.split()
        for part in parts:
            key, sep, value = part.partition("=")
            if not sep:
                continue
            parsed[key.strip()] = coerce(value.strip())
    return parsed


def coerce(value: str) -> Any:
    if value in {"True", "False", "true", "false"}:
        return value.lower() == "true"
    if value.isdigit():
        return int(value)
    return value


def app_status(root: Path) -> dict[str, Any]:
    monitor = None
    monitor_path = root / ".aios/state/monitor_assessment.latest.json"
    if monitor_path.exists():
        try:
            monitor = json.loads(monitor_path.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            monitor = None
    snapshot_exists = (root / SNAPSHOT_JSON).exists() and (root / SNAPSHOT_JS).exists()
    return {
        "schema_version": SCHEMA_VERSION,
        "generated_at": now_iso(),
        "root": root.as_posix(),
        "server": server_status(root),
        "snapshot": {
            "exists": snapshot_exists,
            "json": SNAPSHOT_JSON.as_posix(),
            "js": SNAPSHOT_JS.as_posix(),
            "html": (CONTROL_DIR / "index.html").as_posix(),
        },
        "monitor_health": (monitor or {}).get("health"),
        "round_controller": round_status(root),
    }


def command_refresh(args: argparse.Namespace) -> int:
    result = refresh(Path(args.root).resolve())
    print(json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True))
    return 0 if result["ok"] else 1


def command_start(args: argparse.Namespace) -> int:
    result = start_server(Path(args.root).resolve(), port=args.port)
    print(json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True))
    return 0


def command_stop(args: argparse.Namespace) -> int:
    result = stop_server(Path(args.root).resolve())
    print(json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True))
    return 0


def command_status(args: argparse.Namespace) -> int:
    result = app_status(Path(args.root).resolve())
    print(json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True))
    return 0


def command_up(args: argparse.Namespace) -> int:
    root = Path(args.root).resolve()
    refreshed = refresh(root)
    if not refreshed["ok"]:
        print(json.dumps({"ok": False, "refresh": refreshed}, ensure_ascii=False, indent=2, sort_keys=True))
        return 1
    started = start_server(root, port=args.port)
    status = app_status(root)
    print(json.dumps({"ok": True, "refresh": refreshed, "start": started, "status": status}, ensure_ascii=False, indent=2, sort_keys=True))
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", default=".")
    sub = parser.add_subparsers(dest="command", required=True)

    refresh_parser = sub.add_parser("refresh")
    refresh_parser.add_argument("--json", action="store_true")
    refresh_parser.set_defaults(func=command_refresh)

    start_parser = sub.add_parser("start")
    start_parser.add_argument("--port", type=int, default=DEFAULT_PORT)
    start_parser.add_argument("--json", action="store_true")
    start_parser.set_defaults(func=command_start)

    stop_parser = sub.add_parser("stop")
    stop_parser.add_argument("--json", action="store_true")
    stop_parser.set_defaults(func=command_stop)

    status_parser = sub.add_parser("status")
    status_parser.add_argument("--json", action="store_true")
    status_parser.set_defaults(func=command_status)

    up_parser = sub.add_parser("up")
    up_parser.add_argument("--port", type=int, default=DEFAULT_PORT)
    up_parser.add_argument("--json", action="store_true")
    up_parser.set_defaults(func=command_up)
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    return int(args.func(args))


if __name__ == "__main__":
    raise SystemExit(main())
