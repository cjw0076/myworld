#!/usr/bin/env python3
"""4-OS decision-ritual token for the PreToolUse ritual gate.

`record` writes a fresh token after the 4-OS query (the aios-decide skill calls
it); `check` exits 0 if a fresh token exists, 3 otherwise. The contract-write
hook (aios_guard_hook.py) denies creating a contract until a fresh token exists,
so the mandated ritual can no longer be silently skipped.

Schema: aios.ritual_gate.v1
"""
from __future__ import annotations

import argparse
import json
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TOKEN = ROOT / ".aios" / "ritual" / "decide.token"


def record(note: str) -> None:
    TOKEN.parent.mkdir(parents=True, exist_ok=True)
    TOKEN.write_text(json.dumps({"ts": time.time(), "note": note}), encoding="utf-8")
    print(f"ritual token recorded: {TOKEN}")


def is_fresh(max_age_min: int) -> bool:
    if not TOKEN.exists():
        return False
    try:
        age = time.time() - float(json.loads(TOKEN.read_text()).get("ts", 0))
    except Exception:
        return False
    return age < max_age_min * 60


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="cmd", required=True)
    rec = sub.add_parser("record")
    rec.add_argument("--note", default="")
    chk = sub.add_parser("check")
    chk.add_argument("--max-age-min", type=int, default=60)
    args = parser.parse_args(argv)
    if args.cmd == "record":
        record(args.note)
        return 0
    return 0 if is_fresh(args.max_age_min) else 3


if __name__ == "__main__":
    raise SystemExit(main())
