#!/usr/bin/env python3
"""Line-to-event emitter for monitor primitive.

Reads lines from stdin, appends one `monitor.event` record per line to the
shared events log. Used by `aios_primitives.monitor.start` so each watcher
stdout line becomes a structured event without inline-quoting hell.

Usage:
  (your_command) | python3 -u _emitter.py <monitor_name> <events_jsonl_path>
"""
from __future__ import annotations

import json
import os
import sys
import time
from datetime import datetime, timezone


def main(argv: list[str]) -> int:
    if len(argv) < 3:
        print("usage: _emitter.py <name> <events_jsonl_path>", file=sys.stderr)
        return 2
    name = argv[1]
    path = argv[2]
    for line in sys.stdin:
        rec = {
            "schema_version": "aios.primitive_event.v1",
            "kind": "monitor.event",
            "name": name,
            "ts_iso": datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds"),
            "ts_monotonic_ns": time.monotonic_ns(),
            "payload": {"line": line.rstrip("\n")},
        }
        fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_APPEND, 0o644)
        try:
            os.write(fd, (json.dumps(rec, ensure_ascii=False) + "\n").encode("utf-8"))
        finally:
            os.close(fd)
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
