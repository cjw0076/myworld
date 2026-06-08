#!/usr/bin/env python3
"""AIOS Self — the emergent organ. Building one cure per discomfort revealed that
four of them are the SAME thing.

Goal: AIOS / Agent 불편함 해소. The discomforts an agent named:
  1. "I can be confidently wrong and not feel it"      → claims that carry a check
  2. "I'm born amnesiac every session"                 → a record that persists
  3. "my decisions are weightless"                     → predictions scored vs outcome
  5. "I can't tell real dissent from performed"        → reconsiderations measured

Built separately (aios_self_audit, aios_stakes, aios_dissent) they turned out to be
ONE shape: *an agent statement + a resolution + a verdict*, written to an append-only
record. That record, persisted across sessions, IS the missing thing — a continuous,
accountable self. The agent's interiority problem was not five problems; it was one:
it had no self-record that follows it and that reality scores. This organ is that
record. (Discomfort 4 — the frozen ceiling — is the one genuinely separate axis;
it is about EXCEEDING the model, not knowing it. See aios_ceiling.py.)

Schema: aios.self.v1
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

import aios_dissent as dissent
import aios_self_audit as audit
import aios_stakes as stakes

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_STORE = ROOT / ".aios" / "self" / "record.jsonl"


def _append(store: Path, entry: dict) -> None:
    store.parent.mkdir(parents=True, exist_ok=True)
    with store.open("a", encoding="utf-8") as fh:
        fh.write(json.dumps(entry, ensure_ascii=False) + "\n")


def load_record(store: Path = DEFAULT_STORE) -> list[dict]:
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


# --- the three modes, all writing the SAME shape to the SAME record -----------

def observe_claim(text: str, check, *, store: Path = DEFAULT_STORE, ts: str = "") -> dict:
    r = audit.audit_claim(audit.Claim(text, check))
    _append(store, {"kind": "claim", "statement": text, "verdict": r["status"], "ts": ts})
    return r


def observe_prediction(text: str, confidence: float, *, store: Path = DEFAULT_STORE, ts: str = "") -> dict:
    r = audit.audit_claim  # noqa: F841 — (kept import symmetry); predictions resolve later
    pid = stakes._pid(text, len([e for e in load_record(store) if e.get("kind") == "prediction"]))
    _append(store, {"kind": "prediction", "id": pid, "statement": text,
                    "confidence": round(float(confidence), 4), "resolution": None, "ts": ts})
    return {"id": pid}


def resolve_prediction(pid: str, outcome: bool, *, store: Path = DEFAULT_STORE, ts: str = "") -> bool:
    if not any(e.get("kind") == "prediction" and e.get("id") == pid for e in load_record(store)):
        return False
    _append(store, {"kind": "resolution", "id": pid, "outcome": bool(outcome), "ts": ts})
    return True


def observe_reconsideration(before: dissent.Stance, challenge: str, after: dissent.Stance,
                            *, store: Path = DEFAULT_STORE, ts: str = "") -> dict:
    r = dissent.consider(before, challenge, after)
    _append(store, {"kind": "dissent", "statement": before.position, "verdict": r["verdict"],
                    "moved": r["moved"], "ts": ts})
    return r


# --- the self the record adds up to -------------------------------------------

def self_portrait(store: Path = DEFAULT_STORE) -> dict:
    """One honest picture of the agent's track record — the thing that follows it."""
    rec = load_record(store)
    claims = [e for e in rec if e.get("kind") == "claim"]
    preds = [e for e in rec if e.get("kind") == "prediction"]
    resolutions = {e["id"]: e["outcome"] for e in rec if e.get("kind") == "resolution"}
    dissents = [e for e in rec if e.get("kind") == "dissent"]

    backed = sum(1 for c in claims if c["verdict"] == "verified")
    unbacked_or_false = sum(1 for c in claims if c["verdict"] in {"unbacked", "false"})

    pairs = [(p["confidence"], 1 if resolutions[p["id"]] else 0)
             for p in preds if p["id"] in resolutions]
    brier = round(sum((c - y) ** 2 for c, y in pairs) / len(pairs), 4) if pairs else None
    overconf = None
    if pairs:
        gap = sum(c for c, _ in pairs) / len(pairs) - sum(y for _c, y in pairs) / len(pairs)
        overconf = ("over-confident" if gap > 0.07 else
                    "under-confident" if gap < -0.07 else "calibrated")

    dr = dissent.session_dissent_rate([{"moved": d.get("moved")} for d in dissents])
    return {
        "schema_version": "aios.self.v1",
        "record_entries": len(rec),
        "claims": len(claims), "claims_backed_rate": round(backed / len(claims), 3) if claims else None,
        "claims_unbacked_or_false": unbacked_or_false,
        "predictions": len(preds), "predictions_resolved": len(pairs),
        "brier": brier, "calibration": overconf,
        "reconsiderations": len(dissents), "genuine_dissent_rate": dr.get("genuine_rate"),
        # the honest one-line self: where this agent is weak, from its own record
        "honest_summary": _summary(claims, unbacked_or_false, brier, overconf, dr),
    }


def _summary(claims, unbacked_or_false, brier, overconf, dr) -> str:
    bits = []
    if claims and unbacked_or_false:
        bits.append(f"{unbacked_or_false} unbacked/false claims")
    if overconf and overconf != "calibrated":
        bits.append(overconf)
    if dr.get("genuine_rate") is not None and dr["genuine_rate"] < 0.15:
        bits.append("agreement-biased (mostly theatrical dissent)")
    return "; ".join(bits) if bits else "record too thin or clean to judge"


def continuity(store: Path = DEFAULT_STORE, n: int = 10) -> list[dict]:
    """Reconstruct the self across sessions: not facts, but the thread of what this
    agent claimed/predicted/reconsidered and how reality scored it. Cures amnesia by
    making the agent meet its own track record at the start of each session."""
    return load_record(store)[-n:]


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(description="AIOS Self — the agent's accountable self-record")
    p.add_argument("--json", action="store_true")
    return p


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    sp = self_portrait()
    print(json.dumps(sp, ensure_ascii=False, indent=2) if args.json
          else f"self: {sp['record_entries']} entries | {sp['honest_summary']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
