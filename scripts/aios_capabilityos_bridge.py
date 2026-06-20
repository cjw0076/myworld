#!/usr/bin/env python3
"""CapabilityOS bridge for the goal-first head.

Recommendation-only: this never binds, installs, or executes capabilities.
It asks CapabilityOS when present and otherwise returns a deterministic local
heuristic. It intentionally does not use LiteLLM.
"""
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path
from typing import Any


def _heuristic(goal: str, *, reason: str) -> dict[str, Any]:
    text = goal.lower()
    tools: list[str] = []
    rationale: list[str] = [reason]

    def add(tool: str, why: str) -> None:
        if tool not in tools:
            tools.append(tool)
            rationale.append(why)

    if any(k in text for k in ("web", "search", "research", "latest", "current", "url", "news")):
        add("WebSearch", "goal mentions external/current information")
    if any(k in text for k in ("read", "look", "inspect", "analyze", "review", "find", "diff")):
        add("Read", "goal needs repository inspection")
    if any(k in text for k in ("write", "edit", "implement", "fix", "create", "add", "wire")):
        add("Edit", "goal asks for source changes")
        add("Write", "goal may need a new artifact")
    if any(k in text for k in ("test", "lint", "typecheck", "build", "run", "smoke", "verify")):
        add("Bash", "goal needs command-based validation")
    if any(k in text for k in ("spec", "plan", "requirements", "ouroboros")):
        add("Ouroboros", "goal references spec-first planning")
    if "omx" in text or "skill" in text:
        add("OmxSkill", "goal references OMX skills")
    if not tools:
        tools = ["Read"]
        rationale.append("default to read-only inspection")

    provider_hint = "hivemind_harness" if any(t in tools for t in ("Edit", "Write", "Bash")) else "local_read_only"
    return {"recommended_tools": tools, "provider_hint": provider_hint, "rationale": rationale}


def _normalize(data: dict[str, Any], goal: str) -> dict[str, Any]:
    result = _heuristic(goal, reason="CapabilityOS route normalized to harness tools")
    recs = [r for r in data.get("recommendations", []) if isinstance(r, dict)]
    if not recs:
        return result
    if any(r.get("requires_network") for r in recs[:3]) and "WebSearch" not in result["recommended_tools"]:
        result["recommended_tools"].append("WebSearch")
    result["provider_hint"] = str(recs[0].get("id") or result["provider_hint"])
    result["rationale"].extend(
        f"{r.get('id', 'unknown')} score={r.get('score', '?')}" for r in recs[:3]
    )
    return result


def recommend(goal: str, root: Path) -> dict[str, Any]:
    cap_root = root / "CapabilityOS"
    if not (cap_root / "capabilityos").is_dir():
        return _heuristic(goal, reason="CapabilityOS not present; used keyword heuristic")
    cmd = [
        sys.executable, "-m", "capabilityos.cli", "recommend",
        "--task", goal, "--json",
    ]
    try:
        proc = subprocess.run(
            cmd, cwd=str(cap_root), capture_output=True, text=True, timeout=10,
        )
        if proc.returncode != 0:
            return _heuristic(goal, reason="CapabilityOS CLI failed; used keyword heuristic")
        data = json.loads(proc.stdout or "{}")
        return _normalize(data, goal)
    except Exception as exc:  # noqa: BLE001 - recommendation must degrade honestly
        return _heuristic(goal, reason=f"CapabilityOS unavailable ({type(exc).__name__}); used keyword heuristic")
