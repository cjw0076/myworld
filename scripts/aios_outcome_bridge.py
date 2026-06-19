#!/usr/bin/env python3
"""Outcome bridge: Uri Ledger reputation → substrate character profiles.

Maps contributor quality scores (NPS-style) to substrate profile updates
so real work results feed back into the self-resonance loop.

NPS cutpoints (quality 0..1):
  >= 0.9  → promoter  (True)  → profile dimension moves UP
  0.7–0.9 → passive   (None)  → no signal carried
  < 0.7   → detractor (False) → profile dimension moves DOWN
  None    → unobserved (None) → no signal carried
"""
from __future__ import annotations

from pathlib import Path

import aios_substrate_character as C


_PROMOTER_THRESHOLD = 0.9
_PASSIVE_THRESHOLD = 0.7
_DEFAULT_DIMENSION = "completion"


def classify(quality: float | None) -> bool | None:
    """NPS-style quality → promoter/passive/detractor signal."""
    if quality is None:
        return None
    if quality >= _PROMOTER_THRESHOLD:
        return True
    if quality >= _PASSIVE_THRESHOLD:
        return None   # passive — no signal
    return False      # detractor


def ingest(
    records: list[dict],
    mapping: dict[str, str],
    apply: bool = True,
    store: Path | None = None,
) -> dict:
    """Translate contributor quality records into substrate profile updates.

    Args:
        records:  list of contributor ledger records (contributorId, avgQuality, …)
        mapping:  contributorId → substrate name (e.g. {"agent:poster-v2": "local"})
        apply:    if False, report what would happen but don't write profiles
        store:    profile store path (passed to aios_substrate_character)

    Returns:
        {
            "updated":    [{"success": bool, "applied": bool, "dimension": str}, …],
            "unmapped":   [contributorId, …],
            "passive":    [contributorId, …],
            "no_outcome": [contributorId, …],
        }
    """
    updated: list[dict] = []
    unmapped: list[str] = []
    passive: list[str] = []
    no_outcome: list[str] = []

    store_kw: dict = {"store": store} if store is not None else {}

    for rec in records:
        cid = rec.get("contributorId", "")
        quality = rec.get("avgQuality")
        dimension = rec.get("dimension", _DEFAULT_DIMENSION)

        if cid not in mapping:
            unmapped.append(cid)
            continue

        signal = classify(quality)

        if quality is None:
            no_outcome.append(cid)
            continue

        if signal is None:
            passive.append(cid)
            continue

        # Real signal — promoter or detractor
        substrate = mapping[cid]
        if apply:
            C.update_from_outcome(substrate, dimension, signal, **store_kw)

        updated.append({
            "contributorId": cid,
            "substrate": substrate,
            "dimension": dimension,
            "success": signal,
            "applied": apply,
        })

    return {
        "updated": updated,
        "unmapped": unmapped,
        "passive": passive,
        "no_outcome": no_outcome,
    }
