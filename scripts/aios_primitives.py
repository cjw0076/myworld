#!/usr/bin/env python3
"""Thin shim so `python scripts/aios_primitives.py ...` works the same as
`python -m aios_primitives ...` for callers who prefer the script path.
"""
from __future__ import annotations

import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
if str(HERE) not in sys.path:
    sys.path.insert(0, str(HERE))

from aios_primitives.__main__ import main  # noqa: E402

if __name__ == "__main__":
    sys.exit(main())
