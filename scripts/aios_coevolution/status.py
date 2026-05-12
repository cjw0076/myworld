#!/usr/bin/env python3
"""Summarize AIOS co-evolution pulse monitor events."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any


PULSE_NAMES = ("aios-memory-pulse", "aios-capability-pulse", "aios-hive-pulse")


def events_path(root: Path) -> Path:
    return root / ".aios" / "primitives" / "events.jsonl"


def read_events(root: Path) -> list[dict[str, Any]]:
    path = events_path(root)
    if not path.exists():
        return []
    rows: list[dict[str, Any]] = []
    for line in path.read_text(encoding="utf-8", errors="replace").splitlines():
        if not line.strip():
            continue
        try:
            row = json.loads(line)
        except json.JSONDecodeError:
            continue
        if isinstance(row, dict):
            rows.append(row)
    return rows


def summarize(root: Path) -> dict[str, Any]:
    latest = {name: None for name in PULSE_NAMES}
    counts = {name: 0 for name in PULSE_NAMES}
    for row in read_events(root):
        name = str(row.get("name") or "")
        if name not in latest or row.get("kind") != "monitor.event":
            continue
        counts[name] += 1
        latest[name] = row
    pulses = {}
    for name in PULSE_NAMES:
        row = latest[name]
        pulses[name] = {
            "events": counts[name],
            "last_at": row.get("ts_iso") if row else None,
            "last_line": ((row.get("payload") or {}).get("line")) if row else None,
        }
    return {
        "schema_version": "aios.coevolution.status.v1",
        "root": root.as_posix(),
        "events_path": events_path(root).as_posix(),
        "pulses": pulses,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Summarize AIOS co-evolution pulse events")
    parser.add_argument("--root", type=Path, default=Path.cwd())
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args(argv)
    payload = summarize(args.root.resolve())
    if args.json:
        print(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True))
    else:
        for name, state in payload["pulses"].items():
            print(f"{name} events={state['events']} last_at={state['last_at']} last_line={state['last_line']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
