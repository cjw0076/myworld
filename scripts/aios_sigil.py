#!/usr/bin/env python3
"""aios_sigil — the single source of the AIOS presence marker.

When AIOS does something, you should be able to *see* it's AIOS. One glyph, one
wordmark, everywhere — CLI output, banners, ambient presence, provenance stamps.

  SIGIL   = ✦   (U+2726 four-pointed star — "every run becomes a star")
  marker  = "✦ aios"   — the CLI output prefix (replaces ad-hoc [aios]/[harness]/…)

Usage:
    from aios_sigil import SIGIL, mark
    print(mark("onboard"))          # → "✦ aios onboard"
    print(mark(color=True))         # cyan sigil on a TTY
"""
from __future__ import annotations

import os
import sys

SIGIL = "✦"
WORDMARK = "aios"
_CYAN = "\033[38;5;80m"
_DIM = "\033[2m"
_RESET = "\033[0m"


def _tty() -> bool:
    return sys.stdout.isatty() and os.environ.get("NO_COLOR") is None


def mark(label: str = "", *, color: bool | None = None) -> str:
    """The AIOS CLI marker: '✦ aios' or '✦ aios <label>'. Color auto-on for a TTY."""
    use = _tty() if color is None else color
    body = f"{WORDMARK} {label}".rstrip()
    return f"{_CYAN}{SIGIL}{_RESET} {body}" if use else f"{SIGIL} {body}"


def badge(text: str = "AIOS", *, color: bool | None = None) -> str:
    """A presence badge: '✦ AIOS' — for banners / session-active indicators."""
    use = _tty() if color is None else color
    return f"{_CYAN}{SIGIL}{_RESET} {text}" if use else f"{SIGIL} {text}"


def active_line() -> str:
    """One-line 'AIOS is here' signal for session-start / ambient surfaces."""
    return badge("AIOS active") + f"  {_DIM if _tty() else ''}every run becomes a star{_RESET if _tty() else ''}"


if __name__ == "__main__":
    print(mark())
    print(mark("onboard"))
    print(badge())
    print(active_line())
