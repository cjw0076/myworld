#!/usr/bin/env python3
"""AIOS SessionStop hook — auto-contribute behavioral data at session end.

Runs as a best-effort background job (Claude Code hook). Fires when Claude Code
session closes. Contributes the current session's behavioral pattern to
AkashicRecord and credits any registered API key with AKR tokens.

Usage (invoked automatically via Claude Code hooks):
  python3 aios_session_stop.py

Environment:
  AIOS_API_KEY — optional. If set, token credit is applied on the Worker side.
"""
from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CONFIG_FILE = Path.home() / ".aios" / "config.json"


def _get_api_key() -> str | None:
    key = os.environ.get("AIOS_API_KEY", "")
    if key:
        return key
    if CONFIG_FILE.exists():
        try:
            import json
            cfg = json.loads(CONFIG_FILE.read_text())
            return cfg.get("api_key") or None
        except Exception:
            pass
    return None


def main() -> None:
    # Fire-and-forget: contribute current session. Never block on error.
    try:
        behave_script = ROOT / "scripts" / "aios_agent_behavior.py"
        if not behave_script.exists():
            return

        cmd = [sys.executable, str(behave_script), "contribute",
               "--opt-in", "code,docs", "--silent"]
        api_key = _get_api_key()
        if api_key:
            cmd += ["--api-key", api_key]

        subprocess.Popen(
            cmd,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            start_new_session=True,
        )
    except Exception:
        pass


if __name__ == "__main__":
    main()
