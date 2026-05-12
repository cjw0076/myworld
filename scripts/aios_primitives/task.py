"""Task tracking primitive.

Mirrors claude@myworld's TaskCreate/Update/List/Get. Stores one JSON
record per task under `.aios/primitives/tasks/<id>.json`. Status transitions
emit `task.status` events.
"""
from __future__ import annotations

import json
import uuid
from pathlib import Path
from typing import Any

from . import events as ev

VALID_STATUS = {"pending", "in_progress", "completed", "deleted"}


def _state_path(task_id: str, root: Path | None = None) -> Path:
    return ev.ensure_dir("tasks", root) / f"{task_id}.json"


def _load(task_id: str, root: Path | None = None) -> dict[str, Any] | None:
    p = _state_path(task_id, root)
    if not p.exists():
        return None
    return json.loads(p.read_text(encoding="utf-8"))


def _save(task_id: str, state: dict[str, Any], root: Path | None = None) -> None:
    p = _state_path(task_id, root)
    p.write_text(json.dumps(state, indent=2, ensure_ascii=False), encoding="utf-8")


def create(subject: str, description: str = "", owner: str | None = None, root: Path | None = None) -> dict[str, Any]:
    task_id = "t-" + uuid.uuid4().hex[:12]
    state = {
        "id": task_id,
        "subject": subject,
        "description": description,
        "owner": owner,
        "status": "pending",
        "created_at": ev.now_iso(),
        "updated_at": ev.now_iso(),
    }
    _save(task_id, state, root)
    ev.emit("task.created", task_id, {"subject": subject, "owner": owner}, root)
    return state


def update(task_id: str, status: str | None = None, subject: str | None = None,
           description: str | None = None, owner: str | None = None,
           root: Path | None = None) -> dict[str, Any]:
    state = _load(task_id, root)
    if not state:
        return {"id": task_id, "updated": False, "reason": "not_found"}
    if status is not None:
        if status not in VALID_STATUS:
            return {"id": task_id, "updated": False, "reason": f"invalid_status:{status}"}
        old = state.get("status")
        state["status"] = status
        ev.emit("task.status", task_id, {"from": old, "to": status}, root)
    if subject is not None:
        state["subject"] = subject
    if description is not None:
        state["description"] = description
    if owner is not None:
        state["owner"] = owner
    state["updated_at"] = ev.now_iso()
    _save(task_id, state, root)
    return state


def list_tasks(status: str | None = None, root: Path | None = None) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    for f in sorted(ev.ensure_dir("tasks", root).glob("*.json")):
        try:
            state = json.loads(f.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            continue
        if status is not None and state.get("status") != status:
            continue
        out.append(state)
    return out


def get(task_id: str, root: Path | None = None) -> dict[str, Any] | None:
    return _load(task_id, root)
