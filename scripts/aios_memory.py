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
import os
import subprocess
import sys
import time
import urllib.request
from pathlib import Path

_AKASHIC = os.environ.get("AIOS_AKASHIC_URL", "https://aios-akashic.cjw070690.workers.dev")


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


def _scope_to_domain(items: list[str], domain: str) -> list[str]:
    """Keep only items relevant to `domain` (sparse runtime activation). Uses the
    capability spine's domain keywords; the domain word itself always counts."""
    kws = {domain}
    try:
        scripts_dir = str(Path(__file__).resolve().parent)
        if scripts_dir not in sys.path:
            sys.path.insert(0, scripts_dir)
        import aios_routing  # noqa: PLC0415
        kws |= set(aios_routing.DOMAIN_SIGNALS.get(domain, ()))
    except Exception:  # noqa: BLE001
        pass
    return [c for c in items if any(k in c.lower() for k in kws)]


def retrieve(task: str, root: Path, limit: int = 3, domain: str | None = None) -> list[str]:
    """Recall up to `limit` relevant memory items for `task`, MemoryOS first then
    the local keyword store. Returns content strings (never raises).

    domain: when set (runtime), activate only that partition — fetch a wider
    candidate set, then keep the domain-relevant slice (sparse activation; falls
    back to unscoped if the filter would empty). None = full sweep (sleep/train).
    """
    fetch = limit * 4 if domain else limit
    items = [c for c in _from_memoryos(task, root, fetch) if c]
    if not items:
        items = [c for c in _from_local(task, root, fetch) if c]
    if domain:
        scoped = _scope_to_domain(items, domain)
        items = scoped or items  # graceful: never starve the caller
    return items[:limit]


def contribute_run(goal: str, outcome: dict, api_key: str | None = None,
                   source: str = "aios") -> bool:
    """Contribute a run outcome to the global AkashicRecord behavioral ledger —
    'every run becomes a star'. One shared write path for every runner. Best-effort
    and non-blocking; privacy-safe (tool NAMES + metadata only, never the goal/content/
    args — the global `content` is a structural summary via aios_capture_args.safe_summary).
    Returns True if a contribution was attempted. Skips runs that used no tools."""
    tools = outcome.get("tool_sequence", [])
    if not tools:
        return False
    try:
        import aios_capture_args as _CAP  # noqa: PLC0415
        safe_content = _CAP.safe_summary("code", tools, outcome.get("loop_type"))
    except Exception:  # noqa: BLE001
        safe_content = f"category:code tools:{','.join(str(t) for t in tools[:10])}"
    payload = {
        "id":        f"{source}-{str(outcome.get('exit', '?'))[:4]}-{int(time.time())}",
        # P0 privacy fix: structural summary ONLY — the raw goal never leaves the device.
        "content":   safe_content,
        "category":  "code",
        "provider":  source,
        "os_origin": "myworld",
        "top_tools": tools[:10],
        "tool_freq": {t: tools.count(t) for t in set(tools)},
        "confidence": 0.9 if outcome.get("exit") == "model_finished" else 0.6,
        "loop_type": outcome.get("loop_type", "unknown"),
    }
    headers = {"Content-Type": "application/json", "User-Agent": "AIOS-Agent/1.0"}
    if api_key:
        headers["X-AIOS-Key"] = api_key
    try:
        req = urllib.request.Request(
            _AKASHIC + "/contribute", data=json.dumps(payload).encode(),
            headers=headers, method="POST")
        urllib.request.urlopen(req, timeout=10)
    except Exception:  # noqa: BLE001 — ledger contribution is best-effort
        pass
    return True
