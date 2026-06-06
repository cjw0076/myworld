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
DEFAULT_DIR = ROOT / ".aios"  # whole capability family (copilot/grade/exam/…)


def load_receipts(directory: Path) -> list[dict]:
    out: list[dict] = []
    for fp in sorted(directory.rglob("receipt-*.json")):  # rglob: include per-student subdirs
        try:
            r = json.loads(fp.read_text())
        except (OSError, json.JSONDecodeError):
            continue
        if isinstance(r, dict) and r.get("schema_version"):  # real capability receipts only
            out.append(r)
    return out


def _metrics(rs: list[dict]) -> dict:
    """Per-capability metrics, tolerant of each capability's receipt shape
    (rates computed only over receipts that actually have that gate)."""
    verifiable = [r for r in rs if "verification" in r]
    gens = [r for r in rs if "genesis_critique" in r]
    subs = Counter(r.get("substrate") or "unknown" for r in rs)
    fallbacks = sum(
        1 for r in rs if any(t.get("result") != "ok" for t in (r.get("routing_trail") or [])[:-1])
    )
    repairable = [r for r in rs if "verify_attempts" in r]
    return {
        "outputs": len(rs),
        "verify_pass": sum(1 for r in verifiable if (r.get("verification") or {}).get("ok")),
        "verify_of": len(verifiable),
        "genesis_ok": sum(1 for r in gens if (r.get("genesis_critique") or {}).get("status") == "ok"),
        "genesis_of": len(gens),
        # how often the deterministic verifier had to drive a re-generation (>1 attempt)
        "repaired": sum(1 for r in repairable if int(r.get("verify_attempts") or 1) > 1),
        "repaired_of": len(repairable),
        "substrate_distribution": dict(sorted(subs.items(), key=lambda kv: -kv[1])),
        "churn_fallback_events": fallbacks,
    }


def aggregate(receipts: list[dict]) -> dict:
    by_cap: dict[str, list[dict]] = {}
    for r in receipts:
        by_cap.setdefault(r.get("schema_version") or "unknown", []).append(r)
    return {
        "schema_version": SCHEMA_VERSION,
        "total_outputs": len(receipts),
        "capabilities": {cap: _metrics(rs) for cap, rs in sorted(by_cap.items())},
    }


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
        print(f"value_ledger total_outputs={led['total_outputs']} across {len(led['capabilities'])} capabilities")
        for cap, m in led["capabilities"].items():
            print(
                f"  {cap}: outputs={m['outputs']} "
                f"verify={m['verify_pass']}/{m['verify_of']} repaired={m['repaired']}/{m['repaired_of']} "
                f"genesis={m['genesis_ok']}/{m['genesis_of']} "
                f"churn={m['churn_fallback_events']} subs={m['substrate_distribution']}"
            )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
