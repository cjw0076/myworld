#!/usr/bin/env python3
"""aios_memory — the one memory read path (renewal Cycle 9 seed).

A single `retrieve(task)` that every runner uses to recall constraints/facts,
instead of each caller re-querying a different backend. Order:
  1. MemoryOS graph (accepted, provenance-stamped memory) — the substrate of record
  2. local keyword store (aios_local_memory) — always-available fallback

Graceful by construction: any backend failure degrades to the next, then to [].
This is the seed the other memory surfaces (AkashicRecord ledger, the per-run
constraint provider) converge into.
"""
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path


def memoryos_context(task: str, root: Path, timeout: int = 20) -> dict:
    """The single MemoryOS `context build` call. Returns the parsed payload (or {}).
    Every caller that needs MemoryOS recall goes through here — one subprocess
    invocation, no duplicate copies scattered across runners/tools."""
    try:
        p = subprocess.run(
            [sys.executable, "-m", "memoryos", "--root", ".", "context",
             "build", "--task", task[:200], "--json"],
            cwd=str(root / "memoryOS"), capture_output=True, text=True, timeout=timeout)
        if p.returncode == 0:
            return json.loads(p.stdout)
    except Exception:  # noqa: BLE001
        pass
    return {}


def _from_memoryos(task: str, root: Path, limit: int) -> list[str]:
    data = memoryos_context(task, root)
    items = (data.get("constraints") or []) + (data.get("decisions") or [])
    return [(it.get("content") or it.get("text") or "").strip()
            for it in items if isinstance(it, dict)][:limit]


def _from_local(task: str, root: Path, limit: int) -> list[str]:
    try:
        scripts_dir = str(Path(__file__).resolve().parent)
        if scripts_dir not in sys.path:
            sys.path.insert(0, scripts_dir)
        import aios_local_memory as lm  # noqa: PLC0415
        rows = lm.retrieve(root, task, top_k=limit)
        return [(r.get("content") or "").strip()
                for r in rows if isinstance(r, dict)][:limit]
    except Exception:  # noqa: BLE001
        return []


def retrieve(task: str, root: Path, limit: int = 3) -> list[str]:
    """Recall up to `limit` relevant memory items for `task`, MemoryOS first then
    the local keyword store. Returns content strings (never raises)."""
    items = [c for c in _from_memoryos(task, root, limit) if c]
    if items:
        return items
    return [c for c in _from_local(task, root, limit) if c]
