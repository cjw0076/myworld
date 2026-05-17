#!/usr/bin/env python3
"""aios workbench — single entry point for the Model B developer surface (ASC-0181 Packet C).

Brings up the workbench: the local-first ingest server (ASC-0179) so
registered repos can emit, plus the Control Center web UI. One command
instead of remembering separate scripts.

  aios workbench up       start ingest server (+ optionally Control Center)
  aios workbench status   show what is running
  aios workbench stop     stop the ingest server

The workbench is local-first by construction: the ingest server binds
127.0.0.1 only. Hosting is Model A / ASC-0180, not this surface.
"""

from __future__ import annotations

import argparse
import json
import os
import signal
import subprocess
import sys
import time
import urllib.request
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from aios_workbench_registry import registered_repos  # noqa: E402

INGEST_PORT_DEFAULT = 8787
PID_FILE = ".aios/workbench/ingest_server.pid"


def pid_path(root: Path) -> Path:
    return root / PID_FILE


def ingest_running(root: Path, port: int) -> bool:
    try:
        with urllib.request.urlopen(f"http://127.0.0.1:{port}/aios/health", timeout=2) as r:
            return json.loads(r.read().decode("utf-8")).get("status") == "ok"
    except Exception:
        return False


def read_pid(root: Path) -> int | None:
    p = pid_path(root)
    if not p.exists():
        return None
    try:
        return int(p.read_text().strip())
    except (ValueError, OSError):
        return None


def cmd_up(root: Path, port: int, control: bool, json_mode: bool) -> int:
    started = False
    if ingest_running(root, port):
        status = "already_running"
    else:
        log = root / ".aios" / "logs" / "workbench_ingest.log"
        log.parent.mkdir(parents=True, exist_ok=True)
        proc = subprocess.Popen(
            [sys.executable, (root / "scripts" / "aios_ingest_server.py").as_posix(),
             "--root", root.as_posix(), "--port", str(port)],
            stdout=log.open("a"), stderr=subprocess.STDOUT, cwd=root,
        )
        pid_path(root).parent.mkdir(parents=True, exist_ok=True)
        pid_path(root).write_text(str(proc.pid), encoding="utf-8")
        for _ in range(20):
            if ingest_running(root, port):
                break
            time.sleep(0.15)
        status = "started" if ingest_running(root, port) else "failed_to_start"
        started = status == "started"

    control_url = None
    if control:
        rc = subprocess.run(
            [sys.executable, (root / "scripts" / "aios_local_app.py").as_posix(),
             "--root", root.as_posix(), "up", "--json"],
            cwd=root, capture_output=True, text=True,
        ).returncode
        control_url = "http://127.0.0.1:8765/" if rc == 0 else None

    result = {
        "schema": "aios.workbench.v1",
        "status": status,
        "ingest_endpoint": f"http://127.0.0.1:{port}/aios/ingest",
        "ingest_health": f"http://127.0.0.1:{port}/aios/health",
        "control_center": control_url,
        "registered_repos": sorted(registered_repos(root)),
        "started_this_call": started,
    }
    if json_mode:
        print(json.dumps(result, indent=2, ensure_ascii=False))
    else:
        print(f"workbench {status}")
        print(f"  ingest:  {result['ingest_endpoint']}")
        if control_url:
            print(f"  control: {control_url}")
        print(f"  repos:   {', '.join(result['registered_repos']) or '(none — run: aios init)'}")
    return 0 if status in {"started", "already_running"} else 1


def cmd_status(root: Path, port: int, json_mode: bool) -> int:
    running = ingest_running(root, port)
    result = {
        "schema": "aios.workbench.v1",
        "ingest_running": running,
        "ingest_pid": read_pid(root),
        "ingest_endpoint": f"http://127.0.0.1:{port}/aios/ingest",
        "registered_repos": sorted(registered_repos(root)),
    }
    if json_mode:
        print(json.dumps(result, indent=2, ensure_ascii=False))
    else:
        print(f"ingest server: {'running' if running else 'stopped'}")
        print(f"registered repos: {', '.join(result['registered_repos']) or '(none)'}")
    return 0


def cmd_show(root: Path, repo: str | None, json_mode: bool) -> int:
    """ASC-0181 Packet D — show a product repo's AIOS-observed evidence."""
    processed = root / ".aios" / "processed" / "myworld"
    obs_dir = root / ".aios" / "capability_observations"
    slugs = sorted(registered_repos(root)) if not repo else [repo]
    repos_out = []
    for slug in slugs:
        recaps = sorted(
            p for p in processed.glob(f"product_recap__{slug}__*.json")
            if not p.name.endswith(".receipt.json")
        ) if processed.exists() else []
        sprints = []
        for rc in recaps:
            try:
                pkt = json.loads(rc.read_text(encoding="utf-8"))
                if pkt.get("sprint_id"):
                    sprints.append(pkt["sprint_id"])
            except (OSError, ValueError):
                pass
        caps = []
        obs_path = obs_dir / f"{slug}_capabilities.json"
        if obs_path.exists():
            try:
                obs = json.loads(obs_path.read_text(encoding="utf-8"))
                caps = [
                    {"id": c.get("id"), "observation_count": c.get("observation_count", 0)}
                    for c in obs.get("capabilities", [])
                ]
            except (OSError, ValueError):
                pass
        repos_out.append({"repo": slug, "sprints_absorbed": len(sprints),
                           "sprint_ids": sprints, "observed_capabilities": caps})
    result = {"schema": "aios.workbench.v1", "repos": repos_out}
    if json_mode:
        print(json.dumps(result, indent=2, ensure_ascii=False))
    else:
        if not repos_out:
            print("no registered repos — run: aios init")
        for r in repos_out:
            print(f"\n[{r['repo']}]  sprints absorbed: {r['sprints_absorbed']}")
            if r["sprint_ids"]:
                print(f"  sprints: {', '.join(r['sprint_ids'])}")
            for c in r["observed_capabilities"]:
                print(f"  capability {c['id']}  (observed x{c['observation_count']})")
    return 0


def cmd_stop(root: Path, json_mode: bool) -> int:
    pid = read_pid(root)
    stopped = False
    if pid:
        try:
            os.kill(pid, signal.SIGTERM)
            stopped = True
        except ProcessLookupError:
            stopped = False
        pid_path(root).unlink(missing_ok=True)
    result = {"schema": "aios.workbench.v1", "stopped": stopped, "pid": pid}
    if json_mode:
        print(json.dumps(result, indent=2, ensure_ascii=False))
    else:
        print("workbench ingest stopped" if stopped else "nothing to stop")
    return 0


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description="AIOS workbench — Model B developer surface")
    p.add_argument("--root", default=".", help="AIOS control-plane root")
    p.add_argument("action", nargs="?", default="up", choices=["up", "status", "stop", "show"])
    p.add_argument("--port", type=int, default=INGEST_PORT_DEFAULT)
    p.add_argument("--no-control", action="store_true", help="do not also start the Control Center")
    p.add_argument("--repo", default=None, help="(show) limit to one repo slug")
    p.add_argument("--json", action="store_true")
    args = p.parse_args(argv)

    root = Path(args.root).resolve()
    if args.action == "up":
        return cmd_up(root, args.port, control=not args.no_control, json_mode=args.json)
    if args.action == "status":
        return cmd_status(root, args.port, json_mode=args.json)
    if args.action == "stop":
        return cmd_stop(root, json_mode=args.json)
    if args.action == "show":
        return cmd_show(root, args.repo, json_mode=args.json)
    return 2


if __name__ == "__main__":
    sys.exit(main())
