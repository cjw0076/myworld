"""Deferred capability/skill discovery primitive.

Mirrors claude@myworld's ToolSearch. Returns just-in-time schema for
capability or skill candidates matching a query. Backed by CapabilityOS
recommendation when present, falls back to a local registry under
`.aios/primitives/tools/registry.json` if CapabilityOS is unreachable.

Pure discovery — does not execute or bind anything.
"""
from __future__ import annotations

import json
import subprocess
from pathlib import Path
from typing import Any

from . import events as ev


def _registry_path(root: Path | None = None) -> Path:
    return ev.ensure_dir("tools", root) / "registry.json"


def _load_registry(root: Path | None = None) -> list[dict[str, Any]]:
    p = _registry_path(root)
    if not p.exists():
        return []
    try:
        return json.loads(p.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return []


def register(entry: dict[str, Any], root: Path | None = None) -> dict[str, Any]:
    """Register a tool/skill schema (id, name, description, schema)."""
    entries = _load_registry(root)
    entries = [e for e in entries if e.get("id") != entry.get("id")]
    entries.append(entry)
    p = _registry_path(root)
    p.write_text(json.dumps(entries, indent=2, ensure_ascii=False), encoding="utf-8")
    ev.emit("tools.registered", entry.get("id", ""), {"name": entry.get("name")}, root)
    return entry


def _capabilityos_recommend(task: str, root: Path) -> list[dict[str, Any]]:
    """Best-effort call to CapabilityOS recommend CLI; returns list or empty."""
    capos = root / "CapabilityOS"
    if not capos.exists():
        return []
    try:
        result = subprocess.run(
            ["python", "-m", "capabilityos.cli", "recommend", "--task", task, "--json"],
            cwd=str(capos),
            capture_output=True,
            text=True,
            timeout=10,
        )
        if result.returncode != 0:
            return []
        data = json.loads(result.stdout)
        return data.get("recommendations", []) or []
    except (subprocess.SubprocessError, json.JSONDecodeError):
        return []


def discover(query: str, max_results: int = 5, root: Path | None = None) -> dict[str, Any]:
    """Return matching tool/skill schemas.

    Strategy: ask CapabilityOS first (it has the richer catalog), then
    union with local registry for items not covered.
    """
    root = Path(root) if root else Path.cwd()
    capos_results = _capabilityos_recommend(query, root)
    local = _load_registry(root)
    # Simple bag-of-terms over local registry.
    terms = [t for t in query.lower().split() if t]
    local_scored: list[tuple[int, dict[str, Any]]] = []
    for entry in local:
        text = " ".join([
            str(entry.get("name", "")),
            str(entry.get("description", "")),
            " ".join(entry.get("tags", []) or []),
        ]).lower()
        score = sum(1 for t in terms if t in text)
        if score > 0:
            local_scored.append((score, entry))
    local_scored.sort(key=lambda x: -x[0])
    local_top = [e for _, e in local_scored[:max_results]]
    ev.emit(
        "tools.discovered",
        query,
        {"capos_count": len(capos_results), "local_count": len(local_top)},
        root,
    )
    return {
        "query": query,
        "capabilityos": capos_results[:max_results],
        "local_registry": local_top,
    }
