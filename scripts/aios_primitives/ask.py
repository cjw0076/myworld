"""Operator question primitive.

Mirrors claude@myworld's AskUserQuestion. Creates a question record under
`.aios/primitives/questions/<id>.json` and (optionally) polls for an answer.

CLI usage typically `ask` and exits with the answer; programmatic usage can
register a question and poll separately.
"""
from __future__ import annotations

import json
import time
import uuid
from pathlib import Path
from typing import Any

from . import events as ev

DEFAULT_TIMEOUT_SECONDS = 600
DEFAULT_POLL_INTERVAL_SECONDS = 2
TIMEOUT_EXIT_CODE = 124


def _state_path(question_id: str, root: Path | None = None) -> Path:
    return ev.ensure_dir("questions", root) / f"{question_id}.json"


def _load(question_id: str, root: Path | None = None) -> dict[str, Any] | None:
    p = _state_path(question_id, root)
    if not p.exists():
        return None
    return json.loads(p.read_text(encoding="utf-8"))


def _save(question_id: str, state: dict[str, Any], root: Path | None = None) -> None:
    p = _state_path(question_id, root)
    p.write_text(json.dumps(state, indent=2, ensure_ascii=False), encoding="utf-8")


def create(question: str, options: list[str] | None = None, to: str = "operator",
           from_agent: str | None = None, multi_select: bool = False,
           root: Path | None = None) -> dict[str, Any]:
    qid = "q-" + uuid.uuid4().hex[:12]
    state = {
        "id": qid,
        "question": question,
        "options": list(options or []),
        "multi_select": bool(multi_select),
        "to": to,
        "from_agent": from_agent,
        "status": "open",
        "answer": None,
        "answered_at": None,
        "created_at": ev.now_iso(),
    }
    _save(qid, state, root)
    ev.emit("ask.created", qid, {"question": question, "to": to, "from_agent": from_agent}, root)
    return state


def answer(question_id: str, answer_text: str, answered_by: str | None = None,
           root: Path | None = None) -> dict[str, Any]:
    state = _load(question_id, root)
    if not state:
        return {"id": question_id, "answered": False, "reason": "not_found"}
    state["answer"] = answer_text
    state["answered_at"] = ev.now_iso()
    state["status"] = "answered"
    state["answered_by"] = answered_by
    _save(question_id, state, root)
    ev.emit("ask.answered", question_id, {"answer": answer_text, "by": answered_by}, root)
    return state


def wait(question_id: str, timeout_seconds: int = DEFAULT_TIMEOUT_SECONDS,
         poll_interval: int = DEFAULT_POLL_INTERVAL_SECONDS,
         root: Path | None = None) -> dict[str, Any]:
    """Block until the question is answered or timeout. Returns the state.

    On timeout, marks state status=timeout and emits ask.timeout event;
    caller can decide whether to treat as escalate.
    """
    deadline = time.monotonic() + timeout_seconds
    while time.monotonic() < deadline:
        state = _load(question_id, root)
        if not state:
            return {"id": question_id, "ok": False, "reason": "not_found"}
        if state.get("status") == "answered":
            return state
        time.sleep(poll_interval)
    # Timeout.
    state = _load(question_id, root) or {"id": question_id}
    state["status"] = "timeout"
    state["timed_out_at"] = ev.now_iso()
    _save(question_id, state, root)
    ev.emit("ask.timeout", question_id, {"timeout_seconds": timeout_seconds}, root)
    return state


def list_questions(status: str | None = None, root: Path | None = None) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    for f in sorted(ev.ensure_dir("questions", root).glob("*.json")):
        try:
            state = json.loads(f.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            continue
        if status is not None and state.get("status") != status:
            continue
        out.append(state)
    return out


def get(question_id: str, root: Path | None = None) -> dict[str, Any] | None:
    return _load(question_id, root)
