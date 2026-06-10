#!/usr/bin/env python3
"""AIOS Outcome Bridge — product outcomes (Uri Ledger reputation) → substrate profiles.

Closes the self-resonance loop named in aios_substrate_character: profiles must be
LEARNED from what actually worked, and until now the only outcome source was AIOS's
own dogfood. Uri Ledger (uri/src/lib/uri-ledger.ts) emits per-contributor reputation
records from real paid campus jobs — this bridge feeds them into
update_from_outcome(), so product reality (not internal opinion) moves the routing.

Honesty rules:
  - Only EXPLICITLY mapped contributors update profiles (.aios/contributor_substrates
    .json: contributorId → substrate). Unmapped contributors are reported, never
    guessed — a uri agent id is not self-evidently a substrate.
  - Signal thresholds follow the NPS standard, not magic numbers: avgQuality is
    nps/10, so promoter (nps ≥ 9 → ≥ 0.9) counts as success, detractor (nps ≤ 6 →
    ≤ 0.6) as failure, and passives in between carry NO signal (skipped).
  - Records without an observed avgQuality are skipped (no outcome → no update).

Schema: aios.outcome_bridge.v1
Usage: python aios_outcome_bridge.py ingest --reputation <file.json> [--apply] [--json]
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

import aios_substrate_character as character

ROOT = Path(__file__).resolve().parents[1]
MAP_PATH = ROOT / ".aios" / "contributor_substrates.json"

# NPS standard cutpoints expressed on the 0..1 avgQuality scale (= nps/10).
PROMOTER = 0.9
DETRACTOR = 0.6
# Product delivery work exercises the completion axis unless the record says otherwise.
DEFAULT_DIMENSION = "completion"


def load_mapping(path: Path = MAP_PATH) -> dict[str, str]:
    if path.exists():
        try:
            d = json.loads(path.read_text(encoding="utf-8"))
            return d if isinstance(d, dict) else {}
        except json.JSONDecodeError:
            return {}
    return {}


def classify(avg_quality: float | None) -> bool | None:
    """NPS-standard signal: True (promoter), False (detractor), None (passive/no data)."""
    if avg_quality is None:
        return None
    if avg_quality >= PROMOTER:
        return True
    if avg_quality <= DETRACTOR:
        return False
    return None


def ingest(records: list[dict], *, mapping: dict[str, str], apply: bool,
           store: Path | None = None) -> dict:
    """Feed reputation records into substrate profiles. Returns a full report —
    including what was skipped and why — so nothing silently disappears."""
    updated, unmapped, passive, no_outcome = [], [], [], []
    for rec in records:
        cid = rec.get("contributorId", "")
        substrate = mapping.get(cid)
        if substrate is None:
            unmapped.append(cid)
            continue
        signal = classify(rec.get("avgQuality"))
        if rec.get("avgQuality") is None:
            no_outcome.append(cid)
            continue
        if signal is None:
            passive.append(cid)
            continue
        dim = rec.get("dimension", DEFAULT_DIMENSION)
        if apply:
            kwargs = {"store": store} if store else {}
            character.update_from_outcome(substrate, dim, signal, **kwargs)
        updated.append({"contributorId": cid, "substrate": substrate, "dimension": dim,
                        "success": signal, "jobs": rec.get("jobs"), "applied": apply})
    return {
        "schema_version": "aios.outcome_bridge.v1",
        "updated": updated,
        "unmapped": unmapped,        # reported, never guessed
        "passive": passive,          # NPS 7-8: no signal by design
        "no_outcome": no_outcome,    # quality never observed
        "applied": apply,
    }


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(description="Product outcomes → substrate profiles")
    p.add_argument("cmd", choices=["ingest"])
    p.add_argument("--reputation", required=True, help="JSON file of Uri Ledger reputation records")
    p.add_argument("--mapping", default=str(MAP_PATH))
    p.add_argument("--apply", action="store_true", help="actually update profiles (default: dry-run)")
    p.add_argument("--json", action="store_true")
    return p


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    records = json.loads(Path(args.reputation).read_text(encoding="utf-8"))
    if not isinstance(records, list):
        raise SystemExit("reputation file must be a JSON array of reputation records")
    report = ingest(records, mapping=load_mapping(Path(args.mapping)), apply=args.apply)
    print(json.dumps(report, ensure_ascii=False, indent=2) if args.json else report)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
