#!/usr/bin/env python3
"""Keep AIOS co-evolution pulse monitors alive."""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any


SCHEMA_VERSION = "aios.coevolution.persistent.v1"


@dataclass(frozen=True)
class Pulse:
    name: str
    command: str


PULSES = (
    Pulse(
        "aios-memory-pulse",
        "while true; do bash scripts/aios_coevolution/memory_pulse.sh; sleep 1800; done",
    ),
    Pulse(
        "aios-capability-pulse",
        "while true; do bash scripts/aios_coevolution/capability_pulse.sh; sleep 3600; done",
    ),
    Pulse(
        "aios-hive-pulse",
        "while true; do bash scripts/aios_coevolution/hive_pulse.sh; sleep 900; done",
    ),
)


def primitives_script(root: Path) -> Path:
    return root / "scripts" / "aios_primitives.py"


def run_json(root: Path, command: list[str]) -> tuple[int, Any, str]:
    result = subprocess.run(command, cwd=root, text=True, capture_output=True, check=False)
    parsed: Any = None
    if result.stdout.strip():
        try:
            parsed = json.loads(result.stdout)
        except json.JSONDecodeError:
            parsed = None
    return result.returncode, parsed, result.stderr


def list_monitors(root: Path) -> tuple[list[dict[str, Any]], str]:
    script = primitives_script(root)
    if not script.exists():
        return [], f"missing primitive script: {script.relative_to(root).as_posix()}"
    rc, parsed, stderr = run_json(
        root,
        [sys.executable, script.as_posix(), "--root", root.as_posix(), "monitor", "list", "--json"],
    )
    if rc != 0 or not isinstance(parsed, list):
        return [], stderr or "monitor list did not return a JSON list"
    return [row for row in parsed if isinstance(row, dict)], ""


def start_pulse(root: Path, pulse: Pulse) -> dict[str, Any]:
    script = primitives_script(root)
    rc, parsed, stderr = run_json(
        root,
        [
            sys.executable,
            script.as_posix(),
            "--root",
            root.as_posix(),
            "monitor",
            "start",
            "--name",
            pulse.name,
            "--command",
            pulse.command,
            "--json",
        ],
    )
    return {
        "returncode": rc,
        "status": "started" if rc == 0 else "failed",
        "parsed": parsed,
        "stderr_tail": stderr[-1000:],
    }


def ensure_pulses(root: Path) -> dict[str, Any]:
    root = root.resolve()
    monitors, error = list_monitors(root)
    by_name = {str(row.get("name")): row for row in monitors}
    pulses: dict[str, dict[str, Any]] = {}
    started = 0
    failed = 0
    for pulse in PULSES:
        current = by_name.get(pulse.name) or {}
        alive = bool(current.get("alive"))
        row: dict[str, Any] = {
            "alive_before": alive,
            "command": pulse.command,
            "action": "already_alive" if alive else "start",
        }
        if not alive and not error:
            result = start_pulse(root, pulse)
            row["start_result"] = result
            if result["status"] == "started":
                started += 1
            else:
                failed += 1
        elif error:
            row["action"] = "failed"
            row["error"] = error
            failed += 1
        pulses[pulse.name] = row
    return {
        "schema_version": SCHEMA_VERSION,
        "root": root.as_posix(),
        "status": "passed" if failed == 0 else "failed",
        "started": started,
        "failed": failed,
        "pulses": pulses,
    }


def assert_pulses_alive(root: Path) -> dict[str, Any]:
    root = root.resolve()
    monitors, error = list_monitors(root)
    by_name = {str(row.get("name")): row for row in monitors}
    pulses = {}
    missing_or_dead = []
    for pulse in PULSES:
        row = by_name.get(pulse.name) or {}
        alive = bool(row.get("alive"))
        pulses[pulse.name] = {"alive": alive, "pid": row.get("pid")}
        if not alive:
            missing_or_dead.append(pulse.name)
    return {
        "schema_version": SCHEMA_VERSION,
        "root": root.as_posix(),
        "status": "passed" if not error and not missing_or_dead else "failed",
        "error": error,
        "missing_or_dead": missing_or_dead,
        "pulses": pulses,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Ensure AIOS co-evolution pulse monitors are alive")
    parser.add_argument("--root", type=Path, default=Path.cwd())
    parser.add_argument("--assert-alive", action="store_true", help="check that all pulse monitors are alive without starting them")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args(argv)
    payload = assert_pulses_alive(args.root) if args.assert_alive else ensure_pulses(args.root)
    if args.json:
        print(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True))
    else:
        if args.assert_alive:
            print(f"status={payload['status']} missing_or_dead={','.join(payload['missing_or_dead'])}")
            return 0 if payload["status"] == "passed" else 1
        print(f"status={payload['status']} started={payload['started']} failed={payload['failed']}")
        for name, row in payload["pulses"].items():
            print(f"{name} action={row['action']} alive_before={row['alive_before']}")
    return 0 if payload["status"] == "passed" else 1


if __name__ == "__main__":
    raise SystemExit(main())
