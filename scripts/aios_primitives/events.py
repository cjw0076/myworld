"""Shared append-only event log for all AIOS primitives.

Writes to `.aios/primitives/events.jsonl`. One JSON record per line.
Pure O_APPEND so concurrent writers from different workers do not corrupt
prior lines. Readers must tolerate a partial last line during read-while-write.
"""
from __future__ import annotations

import json
import os
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

SCHEMA_VERSION = "aios.primitive_event.v1"


def primitives_root(root: Path | None = None) -> Path:
    base = Path(root) if root else Path.cwd()
    return base / ".aios" / "primitives"


def events_path(root: Path | None = None) -> Path:
    return primitives_root(root) / "events.jsonl"


def now_iso() -> str:
    return datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds")


def now_monotonic_ns() -> int:
    return time.monotonic_ns()


def emit(kind: str, name: str, payload: dict[str, Any], root: Path | None = None) -> dict[str, Any]:
    """Append one event record to the shared log.

    `kind`: dotted category like `monitor.event`, `task.update`, `ask.created`.
    `name`: stable identifier for the primitive instance (monitor name, task id,
            etc.). Multiple events share a `name` to form a per-instance stream.
    `payload`: kind-specific fields; must JSON-serialize.

    Returns the emitted record. Caller can use it as a return value.
    """
    record = {
        "schema_version": SCHEMA_VERSION,
        "kind": kind,
        "name": name,
        "ts_iso": now_iso(),
        "ts_monotonic_ns": now_monotonic_ns(),
        "payload": payload,
    }
    path = events_path(root)
    path.parent.mkdir(parents=True, exist_ok=True)
    line = json.dumps(record, ensure_ascii=False) + "\n"
    # Use os-level O_APPEND for concurrent-safe append on POSIX.
    fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_APPEND, 0o644)
    try:
        os.write(fd, line.encode("utf-8"))
    finally:
        os.close(fd)
    return record


def read_events(name: str | None = None, kind: str | None = None, root: Path | None = None) -> list[dict[str, Any]]:
    """Read all events; optionally filter by name/kind.

    Tolerates a partial trailing line (concurrent writer in mid-flight).
    """
    path = events_path(root)
    if not path.exists():
        return []
    out: list[dict[str, Any]] = []
    with path.open("r", encoding="utf-8") as fh:
        for line in fh:
            line = line.rstrip("\n")
            if not line:
                continue
            try:
                rec = json.loads(line)
            except json.JSONDecodeError:
                # Partial last line; skip silently.
                continue
            if name is not None and rec.get("name") != name:
                continue
            if kind is not None and rec.get("kind") != kind:
                continue
            out.append(rec)
    return out


def ensure_dir(kind_dir: str, root: Path | None = None) -> Path:
    p = primitives_root(root) / kind_dir
    p.mkdir(parents=True, exist_ok=True)
    return p
