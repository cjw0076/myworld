#!/usr/bin/env python3
"""aios self-evolve — per-specialist self-evolution organ (자기진화).

Founder thesis (2026-05-17): a small model, used well through AIOS and made
self-evolving, has no fixed ceiling — a society of self-evolving specialists
has an expanding coverage frontier. The dream organ consolidates AIOS-wide;
this organ evolves each specialist helper individually.

How (non-parametric self-evolution — the first cut):
  - each helper invocation is logged with input/output excerpts and a
    `verified` field (scripts/aios_helper.py)
  - `mark` records a verified outcome (good/bad) for an invocation
  - `run` distills, per helper, the VERIFIED-GOOD invocations into a
    principles file — the helper's accumulated "what good output looks
    like" — which aios_helper.py then prepends to the helper's prompt

Critical safety (skeptic-voice, 2026-05-15): a helper is NEVER evolved from
its own raw outputs — that is self-distillation collapse. Evolution draws
ONLY from invocations with an explicit positive verification. No verified
data → no evolution (the organ honestly waits for signal).

Parametric self-evolution (LoRA/QLoRA retrain of the local model on the
verified set) is the named heavier follow-on; this organ produces the
verified dataset it would train on.
"""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

OBSERVATIONS_REL = ".aios/helpers/observations.jsonl"
EVOLUTION_DIR = ".aios/helpers/evolution"
CATALOG_REL = ".aios/helpers/catalog.json"


def now_iso() -> str:
    return datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds")


def load_observations(root: Path) -> list[dict[str, Any]]:
    path = root / OBSERVATIONS_REL
    if not path.exists():
        return []
    rows = []
    for line in path.read_text(encoding="utf-8", errors="replace").splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            rows.append(json.loads(line))
        except ValueError:
            continue
    return rows


def write_observations(root: Path, rows: list[dict[str, Any]]) -> None:
    path = root / OBSERVATIONS_REL
    path.write_text("".join(json.dumps(r, ensure_ascii=False) + "\n" for r in rows), encoding="utf-8")


def cmd_mark(root: Path, invocation_id: str, verdict: str, json_mode: bool) -> int:
    """Record a verified outcome for one helper invocation."""
    rows = load_observations(root)
    hit = False
    for r in rows:
        if r.get("invocation_id") == invocation_id:
            r["verified"] = (verdict == "good")
            r["verified_at"] = now_iso()
            hit = True
    if not hit:
        print(f"error: invocation {invocation_id!r} not found", file=sys.stderr)
        return 2
    write_observations(root, rows)
    msg = f"marked {invocation_id} verified={verdict}"
    print(json.dumps({"status": "ok", "invocation_id": invocation_id, "verified": verdict})
          if json_mode else msg)
    return 0


def distill_principles(helper_id: str, good: list[dict[str, Any]]) -> str:
    """Build the principles file for a helper from its verified-good runs.

    Deterministic distillation — the verified-good outputs ARE the principles.
    No model call here: the verification is the signal, the operator/kernel
    did the judging. The helper sees its own proven-good exemplars."""
    lines = [
        f"# Self-evolved principles — {helper_id}",
        "",
        f"- evolved_at: {now_iso()}",
        f"- distilled from {len(good)} VERIFIED-GOOD past invocations",
        "- safety: verified outcomes only — never raw self-distillation",
        "",
        "## Proven-good output patterns (follow these)",
        "",
    ]
    for i, r in enumerate(good[-8:], 1):  # most recent 8 verified-good
        out = (r.get("output_excerpt", "") or "").strip().replace("\n", " ")
        lines.append(f"{i}. {out[:280]}")
    lines += [
        "",
        "These are this specialist's own outputs that AIOS verified as good. "
        "Match their shape and quality.",
    ]
    return "\n".join(lines)


def cmd_run(root: Path, json_mode: bool) -> int:
    rows = load_observations(root)
    catalog = root / CATALOG_REL
    helper_ids = []
    if catalog.exists():
        try:
            helper_ids = [c["id"] for c in json.loads(catalog.read_text(encoding="utf-8")).get("capabilities", [])
                          if isinstance(c.get("helper"), dict)]
        except (ValueError, OSError):
            pass

    evo_dir = root / EVOLUTION_DIR
    evo_dir.mkdir(parents=True, exist_ok=True)
    results = []
    for hid in helper_ids:
        good = [r for r in rows if r.get("helper_id") == hid and r.get("verified") is True
                and r.get("output_excerpt")]
        if len(good) < 2:
            results.append({"helper_id": hid, "status": "waiting_for_verified_signal",
                             "verified_good": len(good)})
            continue
        principles = distill_principles(hid, good)
        (evo_dir / f"{hid}.principles.md").write_text(principles, encoding="utf-8")
        results.append({"helper_id": hid, "status": "evolved", "verified_good": len(good)})

    summary = {
        "schema": "aios.self_evolve.v1",
        "ran_at": now_iso(),
        "boundary": "non-parametric self-evolution from VERIFIED outcomes only; "
                    "parametric LoRA retrain is the named follow-on",
        "helpers": results,
        "evolved": sum(1 for r in results if r["status"] == "evolved"),
        "waiting": sum(1 for r in results if r["status"] == "waiting_for_verified_signal"),
    }
    if json_mode:
        print(json.dumps(summary, indent=2, ensure_ascii=False))
    else:
        for r in results:
            print(f"  {r['helper_id']}: {r['status']} (verified-good: {r['verified_good']})")
        print(f"-- {summary['evolved']} evolved, {summary['waiting']} waiting for verified signal")
    return 0


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description="AIOS per-specialist self-evolution organ")
    p.add_argument("--root", default=".")
    sub = p.add_subparsers(dest="cmd", required=True)

    pr = sub.add_parser("run", help="distill principles for each helper from verified outcomes")
    pr.add_argument("--json", action="store_true")

    pm = sub.add_parser("mark", help="record a verified outcome for one invocation")
    pm.add_argument("--invocation", required=True)
    pm.add_argument("--verdict", required=True, choices=["good", "bad"])
    pm.add_argument("--json", action="store_true")

    args = p.parse_args(argv)
    root = Path(args.root).resolve()
    if args.cmd == "run":
        return cmd_run(root, args.json)
    if args.cmd == "mark":
        return cmd_mark(root, args.invocation, args.verdict, args.json)
    return 2


if __name__ == "__main__":
    sys.exit(main())
