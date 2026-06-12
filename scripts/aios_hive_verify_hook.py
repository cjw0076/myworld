#!/usr/bin/env python3
"""PostToolUse hook — HiveMind verification layer.

Fires after Bash/Write/Edit/Read tool calls. Detects failure signals and
injects structured context back into the agent's reasoning so it can
self-correct without a new user prompt.

HiveMind role: "did the execution match the intent?" — surfaces mismatches
at tool boundary instead of at the end of a long chain.

Output: hookSpecificOutput.additionalContext (inject) or nothing (pass-through).
FAILS OPEN: any internal error returns silently (exit 0, no output).
"""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

# Bash failure patterns — ordered by severity
FATAL_PATTERNS = [
    (re.compile(r'\bTraceback \(most recent call last\)', re.I), "Python exception"),
    (re.compile(r'\bSyntaxError\b', re.I), "Python SyntaxError"),
    (re.compile(r'\bNameError\b|\bTypeError\b|\bAttributeError\b', re.I), "Python runtime error"),
    (re.compile(r'\bERROR\b.*\bfailed\b', re.I), "build/run ERROR"),
    (re.compile(r'\bFATAL\b', re.I), "FATAL signal"),
    (re.compile(r'npm ERR!', re.I), "npm error"),
    (re.compile(r'\bSegmentation fault\b', re.I), "segfault"),
    (re.compile(r'\bpermission denied\b', re.I), "permission denied"),
    (re.compile(r'\bcommand not found\b', re.I), "command not found"),
    (re.compile(r'\bNo such file or directory\b', re.I), "missing file/dir"),
    (re.compile(r'\bAssertionError\b', re.I), "assertion failed"),
    (re.compile(r'\bFAILED\b.*\berror\b', re.I), "test FAILED"),
]

# Patterns that look like errors but aren't (suppress false positives)
FALSE_POSITIVE = re.compile(
    r'(2>/dev/null|/dev/stderr|grep.*error|echo.*error|#.*error)',
    re.I
)


def inject_context(context: str) -> None:
    out = {
        "hookSpecificOutput": {
            "hookEventName": "PostToolUse",
            "additionalContext": context,
        }
    }
    print(json.dumps(out, ensure_ascii=False))


def check_bash(tool_input: dict, tool_response: dict) -> str | None:
    cmd = tool_input.get("command") or ""
    output = ""
    if isinstance(tool_response, dict):
        output = str(tool_response.get("output") or tool_response.get("stdout") or "")
    exit_code = None
    if isinstance(tool_response, dict):
        exit_code = tool_response.get("exit_code") or tool_response.get("exitCode")

    # exit_code non-zero is the clearest signal
    if exit_code is not None and str(exit_code) not in ("0", "None", "null"):
        snippet = output[:300].strip() if output else "(no output)"
        return (
            f"HiveMind: command exited with code {exit_code}.\n"
            f"Command: {cmd[:120]}\n"
            f"Output snippet: {snippet}\n"
            "Consider: (1) Is the failure expected? (2) Does this block downstream steps? "
            "(3) Should you fix before continuing or note as a known issue?"
        )

    # pattern-based detection in output
    if output and not FALSE_POSITIVE.search(cmd):
        for pattern, label in FATAL_PATTERNS:
            if pattern.search(output):
                snippet = output[:300].strip()
                return (
                    f"HiveMind: detected '{label}' in command output.\n"
                    f"Snippet: {snippet[:200]}\n"
                    "Verify: does this indicate a real failure requiring a fix, "
                    "or is it a known/expected output?"
                )
    return None


def check_write_edit(tool_input: dict, tool_response: dict) -> str | None:
    file_path = tool_input.get("file_path") or tool_input.get("new_string") or ""
    # warn if writing to unusual locations (outside project)
    if isinstance(file_path, str) and file_path.startswith("/") and str(ROOT) not in file_path:
        # outside project root — note but don't block
        if not any(file_path.startswith(p) for p in ["/tmp", "/home", str(ROOT)]):
            return (
                f"HiveMind: writing to path outside project root: {file_path}\n"
                "Verify this is intentional — unexpected paths can indicate a "
                "path interpolation bug."
            )
    return None


def main() -> int:
    try:
        data = json.load(sys.stdin)
    except Exception:
        return 0  # fail open

    tool = data.get("tool_name", "")
    ti = data.get("tool_input") or {}
    tr = data.get("tool_response") or {}

    msg = None
    if tool == "Bash":
        msg = check_bash(ti, tr)
    elif tool in ("Write", "Edit"):
        msg = check_write_edit(ti, tr)

    if msg:
        inject_context(msg)

    return 0


if __name__ == "__main__":
    sys.exit(main())
