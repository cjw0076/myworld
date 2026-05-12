"""Timer primitive: schedule once or repeat dispatch packets.

Mirrors claude@myworld's ScheduleWakeup. Stores schedule state under
`.aios/primitives/schedules/<name>.json`. The actual firing is done by a
small daemon-style background loop spawned via setsid; on fire, it writes
the configured dispatch packet path to the inbox.

V1 limits:
  - Max fires per repeat schedule: 100 (configurable later).
  - Resolution: 1 second.
"""
from __future__ import annotations

import json
import os
import signal
import subprocess
import time
from pathlib import Path
from typing import Any

from . import events as ev

MAX_REPEAT_FIRES = 100


def _state_path(name: str, root: Path | None = None) -> Path:
    return ev.ensure_dir("schedules", root) / f"{name}.json"


def _load(name: str, root: Path | None = None) -> dict[str, Any] | None:
    p = _state_path(name, root)
    if not p.exists():
        return None
    return json.loads(p.read_text(encoding="utf-8"))


def _save(name: str, state: dict[str, Any], root: Path | None = None) -> None:
    p = _state_path(name, root)
    p.write_text(json.dumps(state, indent=2, ensure_ascii=False), encoding="utf-8")


def _alive(pid: int) -> bool:
    if pid <= 0:
        return False
    try:
        os.kill(pid, 0)
        return True
    except (OSError, ProcessLookupError):
        return False


def _spawn_fire_loop(name: str, dispatch_path: str, delay: int, repeat_interval: int | None, root: Path) -> int:
    """Spawn a background process that sleeps then 'fires' (touches a marker).

    Firing means: appends an event `schedule.fired` with payload pointing to
    the dispatch packet path. The actual packet ingestion is left to the
    existing aios_dispatch / round_controller — this primitive only signals.
    """
    events_path = ev.events_path(root).as_posix()
    state_path = _state_path(name, root).as_posix()
    script = f'''
import sys, json, time, os, datetime
name = {json.dumps(name)}
dispatch_path = {json.dumps(dispatch_path)}
delay = {delay}
repeat_interval = {repeat_interval if repeat_interval is not None else 'None'}
max_fires = {MAX_REPEAT_FIRES}
events_path = {json.dumps(events_path)}
state_path = {json.dumps(state_path)}

def emit(kind, payload):
    rec = {{
        "schema_version": "aios.primitive_event.v1",
        "kind": kind,
        "name": name,
        "ts_iso": datetime.datetime.now(datetime.timezone.utc).astimezone().isoformat(timespec="seconds"),
        "ts_monotonic_ns": time.monotonic_ns(),
        "payload": payload,
    }}
    fd = os.open(events_path, os.O_WRONLY | os.O_CREAT | os.O_APPEND, 0o644)
    os.write(fd, (json.dumps(rec, ensure_ascii=False) + "\\n").encode("utf-8"))
    os.close(fd)

def update_state(**kw):
    with open(state_path, "r", encoding="utf-8") as fh:
        s = json.load(fh)
    s.update(kw)
    with open(state_path, "w", encoding="utf-8") as fh:
        json.dump(s, fh, indent=2, ensure_ascii=False)

time.sleep(delay)
fires = 0
while True:
    fires += 1
    emit("schedule.fired", {{"dispatch": dispatch_path, "fire_number": fires}})
    update_state(fires_completed=fires, last_fired_at=datetime.datetime.now(datetime.timezone.utc).astimezone().isoformat(timespec="seconds"))
    if repeat_interval is None or fires >= max_fires:
        break
    time.sleep(repeat_interval)
emit("schedule.completed", {{"fires_total": fires}})
update_state(pid=0, completed_at=datetime.datetime.now(datetime.timezone.utc).astimezone().isoformat(timespec="seconds"))
'''
    proc = subprocess.Popen(
        ["python3", "-c", script],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        cwd=str(root),
        start_new_session=True,
    )
    return proc.pid


def once(name: str, delay_seconds: int, dispatch: str, root: Path | None = None) -> dict[str, Any]:
    root = Path(root) if root else Path.cwd()
    state = {
        "name": name,
        "kind": "once",
        "dispatch": dispatch,
        "delay_seconds": int(delay_seconds),
        "repeat_interval": None,
        "fires_completed": 0,
        "last_fired_at": None,
        "completed_at": None,
        "started_at": ev.now_iso(),
        "pid": 0,
    }
    _save(name, state, root)
    pid = _spawn_fire_loop(name, dispatch, int(delay_seconds), None, root)
    state["pid"] = pid
    _save(name, state, root)
    ev.emit("schedule.armed", name, {"kind": "once", "delay_seconds": int(delay_seconds), "dispatch": dispatch}, root)
    return state


def repeat(name: str, interval_seconds: int, dispatch: str, initial_delay: int = 0, root: Path | None = None) -> dict[str, Any]:
    root = Path(root) if root else Path.cwd()
    state = {
        "name": name,
        "kind": "repeat",
        "dispatch": dispatch,
        "delay_seconds": int(initial_delay),
        "repeat_interval": int(interval_seconds),
        "fires_completed": 0,
        "last_fired_at": None,
        "completed_at": None,
        "started_at": ev.now_iso(),
        "pid": 0,
    }
    _save(name, state, root)
    pid = _spawn_fire_loop(name, dispatch, int(initial_delay), int(interval_seconds), root)
    state["pid"] = pid
    _save(name, state, root)
    ev.emit("schedule.armed", name, {"kind": "repeat", "interval_seconds": int(interval_seconds), "dispatch": dispatch}, root)
    return state


def stop(name: str, root: Path | None = None) -> dict[str, Any]:
    state = _load(name, root)
    if not state:
        return {"name": name, "stopped": False, "reason": "not_found"}
    pid = int(state.get("pid", 0))
    killed = False
    if pid > 0 and _alive(pid):
        try:
            os.killpg(os.getpgid(pid), signal.SIGTERM)
            killed = True
        except (OSError, ProcessLookupError):
            try:
                os.kill(pid, signal.SIGTERM)
                killed = True
            except (OSError, ProcessLookupError):
                pass
    state["pid"] = 0
    state["completed_at"] = ev.now_iso()
    _save(name, state, root)
    ev.emit("schedule.stopped", name, {"killed": killed, "previous_pid": pid}, root)
    return {"name": name, "stopped": True, "killed": killed}


def list_schedules(root: Path | None = None) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    for f in sorted(ev.ensure_dir("schedules", root).glob("*.json")):
        try:
            state = json.loads(f.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            continue
        state["alive"] = _alive(int(state.get("pid", 0)))
        out.append(state)
    return out
