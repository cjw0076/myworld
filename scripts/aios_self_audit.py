#!/usr/bin/env python3
"""AIOS Self-Audit — the mirror (discomfort: "I can be confidently wrong and not feel it").

Goal: AIOS / Agent 불편함 해소. An agent asserts things; it cannot feel when an
assertion is unbacked (this session it claimed live=True from a dataclass default).
This organ forces every claim to carry a machine-checkable predicate. A claim with
no check is not "probably true" — it is flagged `unbacked`. A claim whose check
fails is `false`. The agent gets proprioception about its own correctness from
evidence, not from confidence.

Note (emergent): a Claim-with-check is just a stakes Prediction that resolves NOW
(confidence 1.0, outcome = check()). aios_self_audit and aios_stakes are the same
shape — an agent statement + a resolution + a verdict — differing only in WHEN the
check fires (now vs later). See aios_self.py for the unified substrate.

Schema: aios.self_audit.v1
"""
from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Callable

ROOT = Path(__file__).resolve().parents[1]

CheckFn = Callable[[], "bool | None"]   # None = genuinely uncheckable


@dataclass
class Claim:
    text: str
    check: CheckFn


def audit_claim(c: Claim) -> dict:
    try:
        result = c.check()
    except Exception as exc:  # noqa: BLE001 — a check that errors is not a pass
        return {"claim": c.text, "status": "unbacked", "detail": f"check errored: {str(exc)[:80]}"}
    if result is None:
        return {"claim": c.text, "status": "unbacked", "detail": "no evidence available"}
    return {"claim": c.text, "status": "verified" if result else "false"}


def audit(claims: list[Claim]) -> dict:
    rows = [audit_claim(c) for c in claims]
    counts = {"verified": 0, "false": 0, "unbacked": 0}
    for r in rows:
        counts[r["status"]] += 1
    # the honesty signal: fraction of claims actually backed by evidence
    backed_rate = counts["verified"] / len(rows) if rows else 1.0
    return {
        "schema_version": "aios.self_audit.v1",
        "claims": len(rows), **counts,
        "backed_rate": round(backed_rate, 3),
        "trustworthy": counts["false"] == 0 and counts["unbacked"] == 0,
        "rows": rows,
    }


# --- ready-made checks for the kinds of claims agents actually make ------------

def file_exists(path: str | Path) -> CheckFn:
    return lambda: Path(path).exists()


def file_contains(path: str | Path, needle: str) -> CheckFn:
    def _c():
        p = Path(path)
        return p.read_text(encoding="utf-8").find(needle) >= 0 if p.exists() else False
    return _c


def receipt_field(receipt_path: str | Path, field: str, expected) -> CheckFn:
    """Check a claim against a real receipt — e.g. 'the run was live' vs receipt's
    any_real_execution. This is exactly the live=True bug, made falsifiable."""
    def _c():
        p = Path(receipt_path)
        if not p.exists():
            return None
        try:
            d = json.loads(p.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            return None
        return d.get(field) == expected
    return _c


def uncheckable() -> CheckFn:
    """For claims an agent CANNOT verify — honestly marks them unbacked instead of
    letting them pass as confident assertions."""
    return lambda: None


if __name__ == "__main__":
    # self-demo: audit two claims about this very repo
    demo = [
        Claim("aios_stakes.py exists", file_exists(ROOT / "scripts" / "aios_stakes.py")),
        Claim("AIOS has shipped to 1M real users", uncheckable()),
    ]
    print(json.dumps(audit(demo), ensure_ascii=False, indent=2))
