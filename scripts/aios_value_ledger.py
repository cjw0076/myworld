#!/usr/bin/env python3
"""Value ledger for AIOS outside-domain flows (panel item #3).

Turns a stream of capability receipts (e.g. Deadline Copilot) into an auditable
value signal: how many real outputs were produced, what fraction passed the
deterministic verify gate and the GenesisOS quality gate, which substrate served
them, and how often provider-churn fallback kicked in. This converts demos into a
trustworthy, provenance-tied product metric an operator/founder can act on.

Reads .aios/copilot/receipt-*.json by default (runtime artifacts, gitignored).
Schema: aios.value_ledger.v1
Usage: python scripts/aios_value_ledger.py [--dir PATH] [--json]
"""
from __future__ import annotations

import argparse
import json
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCHEMA_VERSION = "aios.value_ledger.v1"
DEFAULT_DIR = ROOT / ".aios" / "copilot"


def load_receipts(directory: Path) -> list[dict]:
    out: list[dict] = []
    for fp in sorted(directory.glob("receipt-*.json")):
        try:
            out.append(json.loads(fp.read_text()))
        except (OSError, json.JSONDecodeError):
            continue
    return out


def aggregate(receipts: list[dict]) -> dict:
    total = len(receipts)
    base = {
        "schema_version": SCHEMA_VERSION,
        "total_outputs": total,
        "verify_pass": 0,
        "verify_pass_rate": 0.0,
        "genesis_ok": 0,
        "genesis_ok_rate": 0.0,
        "substrate_distribution": {},
        "churn_fallback_events": 0,
    }
    if not total:
        return base
    verify_pass = sum(1 for r in receipts if (r.get("verification") or {}).get("ok"))
    genesis_ok = sum(1 for r in receipts if (r.get("genesis_critique") or {}).get("status") == "ok")
    subs = Counter(r.get("substrate") or "unknown" for r in receipts)
    # a fallback happened when something before the served substrate failed/was absent
    fallbacks = sum(
        1
        for r in receipts
        if any(t.get("result") != "ok" for t in (r.get("routing_trail") or [])[:-1])
    )
    base.update(
        {
            "verify_pass": verify_pass,
            "verify_pass_rate": round(verify_pass / total, 4),
            "genesis_ok": genesis_ok,
            "genesis_ok_rate": round(genesis_ok / total, 4),
            "substrate_distribution": dict(sorted(subs.items(), key=lambda kv: -kv[1])),
            "churn_fallback_events": fallbacks,
        }
    )
    return base


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--dir", type=Path, default=DEFAULT_DIR)
    p.add_argument("--json", action="store_true")
    return p


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    led = aggregate(load_receipts(args.dir))
    if args.json:
        print(json.dumps(led, ensure_ascii=False, indent=2, sort_keys=True))
    else:
        print(
            f"value_ledger outputs={led['total_outputs']} "
            f"verify_pass={led['verify_pass']}/{led['total_outputs']} ({led['verify_pass_rate']}) "
            f"genesis_ok={led['genesis_ok']}/{led['total_outputs']} ({led['genesis_ok_rate']}) "
            f"churn_fallbacks={led['churn_fallback_events']}"
        )
        for sub, n in led["substrate_distribution"].items():
            print(f"  substrate {sub}: {n}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
