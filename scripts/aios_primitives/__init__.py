"""AIOS primitive surface.

Reverse-engineered from claude@myworld's CLI primitives used during
2026-05-12 session. Provides monitor, schedule, task, ask, tools, and web
subcommands callable both via `python -m aios_primitives <subcmd>` and via
Python import for local LLM workers.

State lives under `.aios/primitives/`:
  events.jsonl                — append-only shared event log
  monitors/<name>.json        — running watchers (pid, command, last_event)
  schedules/<name>.json       — scheduled fires (next_fire_at, fires_remaining)
  tasks/<id>.json             — task records (status, subject, description)
  questions/<id>.json         — operator questions + answers

Invariants enforced:
  - No primitive executes a child repo source edit.
  - No primitive flips MemoryOS draft to accepted.
  - No primitive binds a capability or installs a tool.
  - Coordination primitives only; execution lives in Hive Mind.
"""
from __future__ import annotations

from . import events, monitor, schedule, task, ask, tools, web

__all__ = ["events", "monitor", "schedule", "task", "ask", "tools", "web"]
SCHEMA_VERSION = "aios.primitive_event.v1"
