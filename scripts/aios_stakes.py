#!/usr/bin/env python3
"""AIOS Stakes — give an agent's decisions weight (discomfort: "weightless decisions").

Goal: AIOS / Agent 불편함 해소. An agent that pays nothing for being wrong makes
weightless decisions. This organ attaches a falsifiable PREDICTION + a confidence to
a decision, scores it against the eventual outcome, and accumulates a calibration
track record that FOLLOWS the agent and cannot be erased (append-only — DNA #3).
A confidently-wrong call permanently dents the record; that permanence is the
"stake".

Calibration (Brier score) also exposes the agreement/over-confidence bias: an agent
that says 0.9 and is right 0.6 of the time learns it is over-confident — from data,
not introspection.

Schema: aios.stakes.v1
Usage:
  python aios_stakes.py record "claim" --confidence 0.8
  python aios_stakes.py resolve <id> --outcome true|false
  python aios_stakes.py calibration [--json]
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_STORE = ROOT / ".aios" / "stakes" / "predictions.jsonl"


def _append(store: Path, record: dict) -> None:
    store.parent.mkdir(parents=True, exist_ok=True)
    with store.open("a", encoding="utf-8") as fh:
        fh.write(json.dumps(record, ensure_ascii=False) + "\n")


def _load(store: Path) -> list[dict]:
    if not store.exists():
        return []
    out = []
    for line in store.read_text(encoding="utf-8").splitlines():
        if line.strip():
            try:
                out.append(json.loads(line))
            except json.JSONDecodeError:
                continue
    return out


def _pid(claim: str, n: int) -> str:
    h = 0
    for c in claim:
        h = (h * 131 + ord(c)) % (1 << 32)
    return f"p{n:04d}-{h:08x}"


def record(claim: str, confidence: float, *, store: Path = DEFAULT_STORE,
           created_at: str = "") -> str:
    """Register a falsifiable prediction. confidence in (0,1] = P(claim true)."""
    if not 0.0 < confidence <= 1.0:
        raise ValueError("confidence must be in (0, 1]")
    existing = _load(store)
    pid = _pid(claim, len([r for r in existing if r.get("op") == "record"]))
    _append(store, {"op": "record", "id": pid, "claim": claim,
                    "confidence": round(float(confidence), 4), "created_at": created_at})
    return pid


def resolve(pid: str, outcome: bool, *, store: Path = DEFAULT_STORE, at: str = "") -> bool:
    """Resolve a prediction's outcome. Append-only — a resolution is never edited."""
    ids = {r["id"] for r in _load(store) if r.get("op") == "record"}
    if pid not in ids:
        return False
    _append(store, {"op": "resolve", "id": pid, "outcome": bool(outcome), "at": at})
    return True


def _resolved_pairs(store: Path) -> list[tuple[float, int]]:
    """(confidence, outcome 0/1) for every resolved prediction."""
    recs = {r["id"]: r for r in _load(store) if r.get("op") == "record"}
    resolutions = {r["id"]: r for r in _load(store) if r.get("op") == "resolve"}  # last wins
    pairs = []
    for pid, res in resolutions.items():
        if pid in recs:
            pairs.append((float(recs[pid]["confidence"]), 1 if res["outcome"] else 0))
    return pairs


def calibration(store: Path = DEFAULT_STORE) -> dict:
    """The track record. Brier score (lower=better), accuracy, and a bias signal."""
    pairs = _resolved_pairs(store)
    n = len(pairs)
    all_recs = [r for r in _load(store) if r.get("op") == "record"]
    if n == 0:
        return {"schema_version": "aios.stakes.v1", "resolved": 0,
                "open": len(all_recs), "brier": None, "accuracy": None,
                "mean_confidence": None, "bias": "no data"}
    brier = sum((c - y) ** 2 for c, y in pairs) / n
    acc = sum(1 for c, y in pairs if (c >= 0.5) == (y == 1)) / n
    mean_conf = sum(c for c, _ in pairs) / n
    realized = sum(y for _c, y in pairs) / n
    gap = mean_conf - realized           # >0 over-confident, <0 under-confident
    bias = ("over-confident" if gap > 0.07 else
            "under-confident" if gap < -0.07 else "calibrated")
    return {
        "schema_version": "aios.stakes.v1",
        "resolved": n, "open": len(all_recs) - n,
        "brier": round(brier, 4), "accuracy": round(acc, 3),
        "mean_confidence": round(mean_conf, 3), "realized_rate": round(realized, 3),
        "confidence_gap": round(gap, 3), "bias": bias,
    }


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(description=__doc__)
    sub = p.add_subparsers(dest="cmd", required=True)
    r = sub.add_parser("record"); r.add_argument("claim"); r.add_argument("--confidence", type=float, required=True)
    rs = sub.add_parser("resolve"); rs.add_argument("id"); rs.add_argument("--outcome", required=True)
    c = sub.add_parser("calibration"); c.add_argument("--json", action="store_true")
    return p


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    if args.cmd == "record":
        print(record(args.claim, args.confidence))
    elif args.cmd == "resolve":
        ok = resolve(args.id, str(args.outcome).lower() in {"true", "1", "yes", "t"})
        print("resolved" if ok else f"unknown prediction id: {args.id}")
        return 0 if ok else 1
    else:
        cal = calibration()
        print(json.dumps(cal, ensure_ascii=False, indent=2) if args.json
              else f"resolved={cal['resolved']} brier={cal['brier']} acc={cal['accuracy']} bias={cal['bias']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
