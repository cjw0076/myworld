#!/usr/bin/env python3
"""aios cli — the AIOS interactive runtime shell.

A persistent  ✦ aios ›  prompt. Type any aios command WITHOUT the 'aios' prefix
(`do "..."`, `onboard`, `behavior predict ...`, `serve`, `status`). Each command
dispatches through the same launcher; the shell stays warm so you drive AIOS
without retyping `aios`. Builtins: help · help full · clear · exit/quit.
Arrow-key history + line editing via readline.
"""
from __future__ import annotations

import os
import shlex
import subprocess
import sys
from pathlib import Path

try:
    import readline  # noqa: F401 — enables history + line editing when present
except Exception:  # noqa: BLE001
    pass

ROOT = Path(__file__).resolve().parents[1]
LAUNCHER = [sys.executable, str(ROOT / "scripts" / "aios_launcher.py")]

# readline needs non-printing escapes wrapped in \001..\002 to count prompt width.
def _rl(seq: str) -> str:
    return "\001" + seq + "\002"

_PROMPT = (_rl("\033[38;5;86m") + "✦" + _rl("\033[0m") + " "
           + _rl("\033[1m") + "aios" + _rl("\033[0m") + " "
           + _rl("\033[38;5;141m") + "›" + _rl("\033[0m") + " ")
_PROMPT_PLAIN = "aios > "

_HELP = """  ✦ AIOS interactive shell — type commands without the 'aios' prefix:
    do "<task>"            run a task end-to-end (plan → tools → result)
    onboard                absorb this device's LLMs + agent CLIs
    behavior predict ...   predict the next action (no LLM)
    serve · status · dream · self-model · setup · ask "..."
  builtins:  help · help full (all commands) · clear · exit / quit"""


def _style():
    sp = str(ROOT / "scripts")
    if sp not in sys.path:
        sys.path.insert(0, sp)
    import aios_cli_style as S  # noqa: PLC0415
    return S


def run_shell() -> int:
    S = _style()
    tty = sys.stdout.isatty()
    prompt = _PROMPT if tty else _PROMPT_PLAIN
    print(S.header("cli", "interactive runtime shell"))
    print("  " + S.dim("a command without the 'aios' prefix · help · exit"))
    print()
    while True:
        try:
            line = input(prompt).strip()
        except EOFError:
            print("\n" + S.dim("✦ session closed.")); return 0
        except KeyboardInterrupt:
            print("^C"); continue
        if not line:
            continue
        if line in ("exit", "quit", "q"):
            print(S.dim("✦ session closed.")); return 0
        if line == "clear":
            os.system("clear"); continue
        if line == "help":
            print(_HELP); continue
        if line in ("help full", "--help", "-h"):
            subprocess.run(LAUNCHER + ["--help"]); continue
        try:
            args = shlex.split(line)
        except ValueError:
            args = line.split()
        if args and args[0] == "aios":   # tolerate the 'aios' prefix if typed
            args = args[1:]
        if not args:
            continue
        try:
            subprocess.run(LAUNCHER + args)
        except KeyboardInterrupt:
            print()   # interrupt the running command, stay in the shell


def main(argv: list[str] | None = None) -> int:
    return run_shell()


if __name__ == "__main__":
    raise SystemExit(main())
