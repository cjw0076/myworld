#!/usr/bin/env python3
"""Tiny CapabilityOS recommendation bridge for the goal-first head.

Recommendation-only: this never binds, installs, or executes capabilities.
It asks CapabilityOS for a route before the planner runs, and degrades with a
structured unavailable receipt when CapabilityOS is not present.
"""
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path
from typing import Any


def recommend(goal: str, root: Path) -> dict[str, Any]:
    cap_root = root / "CapabilityOS"
    cmd = [
        sys.executable, "-m", "capabilityos.cli", "recommend",
        "--task", goal, "--json",
    ]
    try:
        proc = subprocess.run(
            cmd, cwd=str(cap_root), capture_output=True, text=True, timeout=10,
        )
        if proc.returncode != 0:
            return {"status": "unavailable", "source": "CapabilityOS", "reason": "cli_failed"}
        data = json.loads(proc.stdout or "{}")
        return {"status": "ok", "source": "CapabilityOS", "data": data}
    except Exception as exc:  # noqa: BLE001 - recommendation must degrade honestly
        return {
            "status": "unavailable",
            "source": "CapabilityOS",
            "reason": type(exc).__name__,
        }
