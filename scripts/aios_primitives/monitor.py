"""Named persistent watcher primitive.

Mirrors claude@myworld's Monitor tool: starts a background bash loop whose
stdout lines become events in `.aios/primitives/events.jsonl`. The watcher
survives the caller's session via `setsid` so codex/local agents do not
have to stay alive to keep monitoring.

State file: `.aios/primitives/monitors/<name>.json`
  pid              — current watcher PID (0 if stopped)
  command          — bash snippet
  started_at       — ISO timestamp
  stopped_at       — ISO timestamp or null
  last_event_at    — ISO timestamp of last emitted event or null
  events_count     — running count
"""
from __future__ import annotations

import json
import os
import shlex
import signal
import subprocess
from pathlib import Path
from typing import Any

from . import events as ev

_HERE = Path(__file__).resolve().parent
_EMITTER = _HERE / "_emitter.py"


def _state_path(name: str, root: Path | None = None) -> Path:
    return ev.ensure_dir("monitors", root) / f"{name}.json"


def _load(name: str, root: Path | None = None) -> dict[str, Any] | None:
    p = _state_path(name, root)
    if not p.exists():
        return None
    return json.loads(p.read_text(encoding="utf-8"))


def _save(name: str, state: dict[str, Any], root: Path | None = None) -> None:
    p = _state_path(name, root)
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(state, indent=2, ensure_ascii=False), encoding="utf-8")


def _alive(pid: int) -> bool:
    if pid <= 0:
        return False
    try:
        os.kill(pid, 0)
        return True
    except (OSError, ProcessLookupError):
        return False


def _wrap_command(name: str, command: str, root: Path) -> str:
    """Wrap user command so each stdout line is emitted as an event.

    Uses a separate emitter script (`_emitter.py`) to avoid inline-quoting
    issues. `stdbuf -oL` keeps the user command line-buffered through the
    pipe so events arrive as the user emits them, not at process exit.
    """
    events_path = ev.events_path(root).as_posix()
    emitter_cmd = (
        f"python3 -u {shlex.quote(str(_EMITTER))} "
        f"{shlex.quote(name)} {shlex.quote(events_path)}"
    )
    return f"({command}) 2>&1 | stdbuf -oL {emitter_cmd}"


def start(name: str, command: str, root: Path | None = None) -> dict[str, Any]:
    """Launch a named persistent watcher in the background.

    Idempotent: if a watcher with that name is already alive, returns its
    existing state with `already_running=True`.
    """
    root = Path(root) if root else Path.cwd()
    existing = _load(name, root)
    if existing and _alive(int(existing.get("pid", 0))):
        existing["already_running"] = True
        return existing

    wrapped = _wrap_command(name, command, root)
    # start_new_session=True calls os.setsid() in the child after fork so the
    # watcher survives the caller exiting. No need for a separate `setsid`
    # binary in argv — that caused double session creation and the
    # Popen.pid wrapping setsid's short-lived exec.
    proc = subprocess.Popen(
        ["bash", "-lc", wrapped],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        cwd=str(root),
        start_new_session=True,
    )
    state = {
        "name": name,
        "pid": proc.pid,
        "command": command,
        "started_at": ev.now_iso(),
        "stopped_at": None,
        "last_event_at": None,
        "events_count": 0,
    }
    _save(name, state, root)
    ev.emit("monitor.started", name, {"pid": proc.pid, "command": command}, root)
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
    state["stopped_at"] = ev.now_iso()
    _save(name, state, root)
    ev.emit("monitor.stopped", name, {"killed": killed, "previous_pid": pid}, root)
    return {"name": name, "stopped": True, "killed": killed}


def list_monitors(root: Path | None = None) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    for f in sorted(ev.ensure_dir("monitors", root).glob("*.json")):
        try:
            state = json.loads(f.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            continue
        state["alive"] = _alive(int(state.get("pid", 0)))
        # Compute last_event_at + events_count from event log.
        recs = ev.read_events(name=state.get("name"), kind="monitor.event", root=root)
        if recs:
            state["last_event_at"] = recs[-1]["ts_iso"]
            state["events_count"] = len(recs)
        out.append(state)
    return out


def get(name: str, root: Path | None = None) -> dict[str, Any] | None:
    state = _load(name, root)
    if not state:
        return None
    state["alive"] = _alive(int(state.get("pid", 0)))
    recs = ev.read_events(name=name, kind="monitor.event", root=root)
    state["last_event_at"] = recs[-1]["ts_iso"] if recs else None
    state["events_count"] = len(recs)
    return state
