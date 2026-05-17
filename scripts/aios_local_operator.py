#!/usr/bin/env python3
"""aios local-operator — the operator-sovereignty organ.

The operator role is AIOS's last provider-dependent layer (sovereignty
audit: readiness 0.7; operator role = provider_dependent). This organ does
NOT replace the operator with a small model pretending to be a frontier
"chief" — that inverts the capability gradient. Instead, by the autopoiesis
thesis, it *shrinks the operator role*: a local LLM pre-digests the dream
cycle's proposals into a routine operator-review draft, so the decision
left for the deterministic kernel / human is small.

Analogy (the country-and-foreign-central-bank frame): sovereignty is won by
building domestic institutions that handle the routine, reserving the
foreign bank for rare large operations — not by a heroic domestic
replacement.

What it does each run:
  1. read the latest dream report
  2. call the operator-review specialist (local LLM, strong tier) to
     pre-digest each proposal into: <routine action> [ROUTINE-REVERSIBLE |
     NEEDS-REVIEW | ESCALATE]
  3. write an operator-review draft (proposals only — nothing accepted,
     nothing acted; DNA Invariant 2 draft-first, Invariant 6 override)
  4. record the local-handled vs escalated split — that ratio IS the
     operator-sovereignty measurement

Boundary: this organ pre-digests and proposes. It never accepts memory,
closes contracts, or acts on ESCALATE/NEEDS-REVIEW items. The deterministic
kernel + operator confirm. The local LLM is a clerk, not a chief.
"""

from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

REVIEW_HELPER = "cap_helper_operator_review"
DREAM_DIR = ".aios/dream"
OUT_DIR = ".aios/local_operator"


def now_iso() -> str:
    return datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds")


def now_stamp() -> str:
    return datetime.now(timezone.utc).astimezone().strftime("%Y%m%dT%H%M%S")


def latest_dream_report(root: Path) -> dict[str, Any] | None:
    latest = root / DREAM_DIR / "latest.json"
    if not latest.exists():
        return None
    try:
        name = json.loads(latest.read_text(encoding="utf-8")).get("latest_report")
        if not name:
            return None
        return json.loads((root / DREAM_DIR / name).read_text(encoding="utf-8"))
    except (ValueError, OSError):
        return None


def call_review_helper(root: Path, digest: str) -> tuple[bool, str]:
    proc = subprocess.run(
        [sys.executable, (root / "scripts" / "aios_helper.py").as_posix(),
         "--root", root.as_posix(), "run", "--helper", REVIEW_HELPER,
         "--input", digest, "--json"],
        cwd=root, capture_output=True, text=True,
    )
    if proc.returncode != 0:
        return False, (proc.stderr or proc.stdout or "review helper failed").strip()
    try:
        return True, str(json.loads(proc.stdout).get("result", "")).strip()
    except (ValueError, KeyError) as exc:
        return False, f"unparseable helper output: {exc}"


def classify_lines(review_text: str) -> dict[str, list[str]]:
    """Split the review into the three tags. The local LLM tags; the split
    is deterministic (a simple tag scan), so the kernel — not the model —
    owns which bucket each line lands in."""
    buckets: dict[str, list[str]] = {"routine_reversible": [], "needs_review": [], "escalate": []}
    for raw in review_text.splitlines():
        line = raw.strip()
        if not line:
            continue
        upper = line.upper()
        if "ROUTINE-REVERSIBLE" in upper or "ROUTINE REVERSIBLE" in upper:
            buckets["routine_reversible"].append(line)
        elif "ESCALATE" in upper:
            buckets["escalate"].append(line)
        elif "NEEDS-REVIEW" in upper or "NEEDS REVIEW" in upper:
            buckets["needs_review"].append(line)
    return buckets


def run(root: Path, json_mode: bool) -> int:
    report = latest_dream_report(root)
    if report is None:
        msg = "no dream report yet — run `aios dream` first"
        print(json.dumps({"status": "no_input", "reason": msg}) if json_mode else msg)
        return 1

    consolidation = report.get("consolidation", "")
    triage = report.get("triage", {})
    digest = (
        "DREAM CYCLE PROPOSALS\n\n"
        f"{consolidation}\n\n"
        f"operator-level questions: {triage.get('operator_level', [])}\n"
        f"already escalated (vision-level): "
        f"{[v.get('question') for v in triage.get('vision_level_escalated', [])]}"
    )
    ok, review = call_review_helper(root, digest)
    out_dir = root / OUT_DIR
    out_dir.mkdir(parents=True, exist_ok=True)
    stamp = now_stamp()

    if not ok:
        rec = {"schema": "aios.local_operator.v1", "status": "review_failed",
               "generated_at": now_iso(), "reason": review}
        (out_dir / f"review-{stamp}.json").write_text(
            json.dumps(rec, indent=2, ensure_ascii=False), encoding="utf-8")
        print(json.dumps(rec) if json_mode else f"local-operator FAILED: {review}")
        return 1

    buckets = classify_lines(review)
    handled = len(buckets["routine_reversible"])
    flagged = len(buckets["needs_review"])
    escalated = len(buckets["escalate"])
    total = handled + flagged + escalated
    # operator-sovereignty ratio: fraction the local operator could pre-digest
    # as routine (the kernel may auto-confirm) vs what still needs a human/founder
    local_ratio = round(handled / total, 2) if total else 0.0

    rec = {
        "schema": "aios.local_operator.v1",
        "status": "ok",
        "generated_at": now_iso(),
        "source_dream_report": report.get("generated_at"),
        "boundary": "operator-review DRAFT — pre-digested proposals; nothing accepted or acted. "
                    "kernel/operator confirms; ROUTINE-REVERSIBLE items the kernel may auto-confirm.",
        "review": review,
        "buckets": buckets,
        "counts": {"routine_reversible": handled, "needs_review": flagged,
                   "escalate": escalated, "total": total},
        "operator_sovereignty_ratio": local_ratio,
        "reading": "fraction of operator decisions the local operator pre-digested as routine; "
                   "the rest still needs human/founder — this ratio is the operator-sovereignty measurement",
    }
    report_path = out_dir / f"review-{stamp}.json"
    report_path.write_text(json.dumps(rec, indent=2, ensure_ascii=False), encoding="utf-8")
    (out_dir / "latest.json").write_text(
        json.dumps({"latest_review": report_path.name, "generated_at": rec["generated_at"],
                    "operator_sovereignty_ratio": local_ratio}, indent=2, ensure_ascii=False),
        encoding="utf-8")

    if json_mode:
        print(json.dumps({"status": "ok", "review": str(report_path.relative_to(root)),
                          "counts": rec["counts"],
                          "operator_sovereignty_ratio": local_ratio}, indent=2, ensure_ascii=False))
    else:
        print("local-operator review complete")
        print(f"  review draft:  {report_path.relative_to(root)}")
        print(f"  routine-reversible (kernel may auto-confirm): {handled}")
        print(f"  needs-review: {flagged}   escalate: {escalated}")
        print(f"  operator-sovereignty ratio: {local_ratio}")
        print("--- operator-review draft (pre-digested, nothing accepted) ---")
        print(review)
    return 0


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description="AIOS local-operator — operator-sovereignty organ")
    p.add_argument("--root", default=".")
    p.add_argument("action", nargs="?", default="run", choices=["run", "latest"])
    p.add_argument("--json", action="store_true")
    args = p.parse_args(argv)
    root = Path(args.root).resolve()

    if args.action == "latest":
        latest = root / OUT_DIR / "latest.json"
        if not latest.exists():
            print("no local-operator review yet")
            return 1
        print(latest.read_text(encoding="utf-8"))
        return 0
    return run(root, args.json)


if __name__ == "__main__":
    sys.exit(main())
