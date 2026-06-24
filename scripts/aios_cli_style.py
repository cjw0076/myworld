#!/usr/bin/env python3
"""aios_cli_style — the Cosmic Ledger design language, applied to the terminal.

The real CLI output should look as considered as the web. One palette (the brand
hex mapped to ANSI-256), one set of components (header / kv / bar / rule / status),
so every aios command reads like one designed thing. Color auto-off when piped or
NO_COLOR — escape codes never pollute logs.

Grounded in AIOS_BRAND.md (itself grounded in the founder's Uri Design System):
cyan #5EEAD4 · violet #A78BFA · amber #FFD166 · muted #8B94B2 · ink #EEF1FA.
"""
from __future__ import annotations

import os
import sys

SIGIL = "✦"

# Brand hex → nearest ANSI-256
_C = {"cyan": 86, "violet": 141, "amber": 221, "muted": 103, "ink": 255, "rose": 211}


def _tty() -> bool:
    return sys.stdout.isatty() and os.environ.get("NO_COLOR") is None


def _c(code: int, s: str) -> str:
    return f"\033[38;5;{code}m{s}\033[0m" if _tty() else s


def cyan(s):   return _c(_C["cyan"], s)
def violet(s): return _c(_C["violet"], s)
def amber(s):  return _c(_C["amber"], s)
def muted(s):  return _c(_C["muted"], s)
def ink(s):    return _c(_C["ink"], s)
def dim(s):    return f"\033[2m{s}\033[0m" if _tty() else s
def bold(s):   return f"\033[1m{s}\033[0m" if _tty() else s


def header(title: str, sub: str = "") -> str:
    """'✦ AIOS  <title>' with a faint rule under it."""
    line = f"{cyan(SIGIL)} {bold(ink('AIOS'))}  {ink(title)}"
    if sub:
        line += f"   {muted(sub)}"
    return line + "\n" + dim("─" * 56)


def kv(key: str, val: str, *, accent=None) -> str:
    """Aligned key : value row. accent = a color fn for the value."""
    v = accent(val) if accent else ink(val)
    return f"  {muted(key.ljust(9))} {v}"


def bar(frac: float, width: int = 22) -> str:
    """A gradient-feel progress/score bar using block glyphs."""
    frac = max(0.0, min(1.0, frac))
    filled = round(frac * width)
    return cyan("█" * filled) + dim("·" * (width - filled))


def ok(s):   return cyan(f"✓ {s}")
def star(s): return amber(f"{SIGIL} {s}")
def warn(s): return amber(f"▲ {s}")
def rule(width: int = 56) -> str:
    return dim("─" * width)


if __name__ == "__main__":
    print(header("onboard", "device capabilities"))
    print(kv("usable", "claude · codex · gemini · ollama", accent=cyan))
    print("  " + ok("ollama") + dim("  12 models"))
    print("  Bash  " + bar(0.74) + muted("  .74"))
    print("  " + star("every run becomes a star"))
