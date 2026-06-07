#!/usr/bin/env python3
"""Work History — a unified chronological log of everything AIOS did.

Absorbed from paperclip (manage agents at work / work history). Every AIOS organ
already writes a provenance receipt (.aios/<organ>/receipt-*.json — copilots,
star_radar, self_evolve, …); this aggregates them into one operator timeline:
what AIOS did, when, by which organ, and the outcome. Complements the value
ledger (which scores capability value) with a cross-organ activity view.

Schema: aios.work_history.v1
Usage: python scripts/aios_work_history.py [--dir .aios] [--limit 50] [--json]
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCHEMA_VERSION = "aios.work_history.v1"
DEFAULT_DIR = ROOT / ".aios"


def _count(value) -> int:
    if isinstance(value, list):
        return len(value)
    if isinstance(value, dict) and isinstance(value.get("rows"), list):
        return len(value["rows"])
    return 0


def summarize(receipt: dict) -> dict:
    schema = str(receipt.get("schema_version") or "?")
    organ = schema.removeprefix("aios.").removesuffix(".v1")
    v = receipt.get("verification")
    status = ("ok" if (v or {}).get("ok") else "flagged") if isinstance(v, dict) else ""
    if "candidates" in receipt:
        what = f"{_count(receipt['candidates'])} absorption candidates"
    elif "items" in receipt:
        what = f"{_count(receipt['items'])} items planned"
    elif "analysis" in receipt:
        what = f"{_count(receipt['analysis'])} rows analyzed"
    elif "prep_schedule" in receipt:
        what = f"{_count(receipt['prep_schedule'])} prep blocks"
    elif "plan" in receipt and isinstance(receipt["plan"], str):
        what = receipt["plan"].replace("\n", " ")[:60]
    elif "best_score" in receipt:
        what = f"self-evolve best={receipt['best_score']}"
    else:
        what = ""
    return {
        "when": receipt.get("generated_at") or "?",
        "organ": organ,
        "status": status,
        "what": what,
        "substrate": receipt.get("substrate"),
    }


def load_history(directory: Path) -> list[dict]:
    rows: list[dict] = []
    for fp in directory.rglob("receipt-*.json"):
        try:
            r = json.loads(fp.read_text())
        except (OSError, json.JSONDecodeError):
            continue
        if isinstance(r, dict) and r.get("schema_version"):
            rows.append(summarize(r))
    # newest first; "?" sorts last
    return sorted(rows, key=lambda x: x["when"], reverse=True)


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--dir", type=Path, default=DEFAULT_DIR)
    p.add_argument("--limit", type=int, default=50)
    p.add_argument("--json", action="store_true")
    return p


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    rows = load_history(args.dir)[: args.limit]
    if args.json:
        print(json.dumps({"schema_version": SCHEMA_VERSION, "count": len(rows), "history": rows},
                         ensure_ascii=False, indent=2))
    else:
        print(f"=== AIOS Work History — {len(rows)} recent ===")
        for r in rows:
            sub = f" [{r['substrate']}]" if r.get("substrate") else ""
            st = f" ({r['status']})" if r["status"] else ""
            print(f"  {r['when']}  {r['organ']:<18}{st}{sub}  {r['what']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
