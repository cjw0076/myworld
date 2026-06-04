#!/usr/bin/env python3
"""PreToolUse enforcement hook for the AIOS operator harness.

Turns the harness from advisory prose into enforcement (gemini review #2,
founder directive "진짜 AIOS를 위해서 모든 리스크 감수"):
- BLOCKS a `git commit` when aios_commit_guard finds ERRORs (e.g. an embedded
  git repo staged as a gitlink with no .gitmodules entry).
- BLOCKS creating a contract (Write to docs/contracts/ASC-*.md) when no fresh
  4-OS ritual token exists.

FAILS OPEN: any internal/parse/subprocess error returns 0 (allow), so a hook
malfunction never blocks legitimate work — we accept the risk of a missed block,
never the risk of a frozen session.

Wire: PreToolUse matcher "Bash|Write". Reads the PreToolUse JSON on stdin.
Schema: aios.guard_hook.v1
"""
from __future__ import annotations

import json
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PY = sys.executable
# non-anchored so it matches a contract path inside a shell command too; the
# trailing guard avoids over-matching ASC-1.md.bak etc.
CONTRACT_PATH = re.compile(r"docs/contracts/ASC-[^/\s]*\.md(?![\w.])")
# shell write indicators — used to gate contract creation done via Bash, not just
# the Write tool (else `echo x > docs/contracts/ASC-9.md` bypasses the ritual).
WRITE_VERB = re.compile(r">>?|\btee\b|\bcp\b|\bmv\b|\bdd\b|sed\s+-i|\binstall\b")


def deny(reason: str) -> None:
    print(
        json.dumps(
            {
                "hookSpecificOutput": {
                    "hookEventName": "PreToolUse",
                    "permissionDecision": "deny",
                    "permissionDecisionReason": reason,
                }
            }
        )
    )
    sys.exit(0)


def main() -> int:
    try:
        data = json.load(sys.stdin)
    except Exception:
        return 0  # fail open
    tool = data.get("tool_name", "")
    ti = data.get("tool_input") or {}
    cmd = ti.get("command") or ""

    # 1. commit guard
    if tool == "Bash" and "git commit" in cmd:
        try:
            r = subprocess.run(
                [PY, str(ROOT / "scripts" / "aios_commit_guard.py"), "--json"],
                cwd=ROOT,
                capture_output=True,
                text=True,
                timeout=15,
            )
            res = json.loads(r.stdout)
        except Exception:
            return 0  # guard crashed → fail open
        errors = [f for f in res.get("findings", []) if f.get("level") == "error"]
        if errors:
            lines = "\n".join(f"- {f['message']}" for f in errors)
            deny(
                "AIOS commit-guard blocked this commit:\n"
                + lines
                + "\nFix the ERROR (e.g. `git rm --cached <gitlink>`), then retry."
            )

    # 2. contract-creation ritual gate — via the Write tool OR via a shell write
    #    (echo > / tee / cp …), so the gate can't be bypassed through Bash.
    creating_contract = (
        tool == "Write" and bool(CONTRACT_PATH.search(ti.get("file_path") or ""))
    ) or (
        tool == "Bash" and bool(CONTRACT_PATH.search(cmd)) and bool(WRITE_VERB.search(cmd))
    )
    if creating_contract:
        try:
            rc = subprocess.run(
                [PY, str(ROOT / "scripts" / "aios_ritual_gate.py"), "check", "--max-age-min", "60"],
                cwd=ROOT,
                capture_output=True,
                timeout=10,
            ).returncode
        except Exception:
            return 0  # fail open
        if rc != 0:
            deny(
                "Contract creation blocked: no fresh 4-OS decision trace (<60min). "
                "Run /aios-decide (MemoryOS recall + CapabilityOS route + GenesisOS "
                "challenge + Hive verify), or `python scripts/aios_ritual_gate.py record`, "
                "then write the contract."
            )

    return 0


if __name__ == "__main__":
    sys.exit(main())
