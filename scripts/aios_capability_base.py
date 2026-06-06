#!/usr/bin/env python3
"""Shared base for the AIOS outside-value capability factory.

The four capabilities (deadline / grade / exam / tuition copilots) all share the
same infrastructure: failover-routed local generation and provenance-receipt
writing. Centralizing it here makes the factory real (not copy-paste) and the next
capability trivial: import this, write a domain prompt + a pure deterministic
verifier, emit a receipt.

Schema: aios.capability_base.v1
"""
from __future__ import annotations

import json
import time
from pathlib import Path

import aios_substrate_router as router

ROOT = Path(__file__).resolve().parents[1]
# churn-resilient local fallback chain (preferred → backups)
SUBSTRATE_CHAIN = ["qwen3-coder:30b", "qwen3:30b-a3b", "deepseek-coder-v2:16b"]


def generate(prompt: str, prefer: list[str] | None = None) -> tuple[str, str | None, list[dict]]:
    """Failover-routed local generation. Returns (text, substrate_served, trail)."""
    res = router.generate(prompt, prefer=prefer or SUBSTRATE_CHAIN)
    return res["text"], res["substrate"], res["trail"]


def write_receipt(subdir: str, receipt: dict) -> tuple[Path, str]:
    """Write a provenance receipt under .aios/<subdir>/; returns (dir, stamp)."""
    out_dir = ROOT / ".aios" / subdir
    out_dir.mkdir(parents=True, exist_ok=True)
    stamp = time.strftime("%Y%m%dT%H%M%S")
    (out_dir / f"receipt-{stamp}.json").write_text(
        json.dumps(receipt, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    return out_dir, stamp
