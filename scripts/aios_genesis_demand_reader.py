"""Genesis Demand Reader — reads open demands from .aios/genesis_demands/ and surfaces them.

GenesisOS active demand loop:
  1. Every preamble detects prison signatures and writes demand packets.
  2. This reader surfaces unaddressed demands to the operator (CTO loop).
  3. Operator can 'close' a demand by updating status to 'resolved'.

Usage:
  python scripts/aios_genesis_demand_reader.py          # list open demands
  python scripts/aios_genesis_demand_reader.py --close <id>  # mark resolved
"""
from __future__ import annotations
import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DEMAND_DIR = ROOT / ".aios" / "genesis_demands"


def list_demands(status_filter: str = "open") -> list[dict]:
    demands = []
    for f in sorted(DEMAND_DIR.glob("*.json")):
        try:
            d = json.loads(f.read_text())
            if status_filter == "all" or d.get("status") == status_filter:
                d["_file"] = f.name
                demands.append(d)
        except Exception:
            pass
    return demands


def close_demand(demand_id: str) -> bool:
    for f in DEMAND_DIR.glob("*.json"):
        d = json.loads(f.read_text())
        if d.get("id") == demand_id or f.stem == demand_id:
            d["status"] = "resolved"
            f.write_text(json.dumps(d, ensure_ascii=False, indent=2))
            return True
    return False


def main() -> int:
    parser = argparse.ArgumentParser(description="AIOS Genesis Demand Reader")
    parser.add_argument("--status", default="open", choices=["open", "resolved", "all"])
    parser.add_argument("--close", metavar="ID", help="mark a demand as resolved")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()

    if args.close:
        ok = close_demand(args.close)
        print(f"{'closed' if ok else 'not found'}: {args.close}")
        return 0 if ok else 1

    demands = list_demands(args.status)
    if args.json:
        print(json.dumps(demands, ensure_ascii=False, indent=2))
        return 0

    if not demands:
        print(f"[genesis] no {args.status} demands")
        return 0

    print(f"[genesis] {len(demands)} {args.status} demand(s):\n")
    for d in demands:
        print(f"  {d['id']}  [{d['confidence']:.2f}]  {d['detected_at'][:19]}")
        print(f"    trigger: {d['trigger_goal'][:60]}")
        print(f"    prison:  {', '.join(d['prison_signatures'])}")
        print(f"    fix:     {d['escape_vectors'][0] if d['escape_vectors'] else '?'}")
        print()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
