#!/usr/bin/env python3
"""aios verify — auto-verification organ: makes self-evolution fully autonomous.

Self-evolution (scripts/aios_self_evolve.py) evolves a specialist only from
its VERIFIED outcomes — never raw self-distillation. Until now `verified` was
set by a human `mark`. That kept the loop heteropoietic: the specialists could
not self-evolve without the operator.

This organ closes that gap with **deterministic, non-circular** structural
checks — NOT an LLM judging an LLM (that has correlated errors). For each
unmarked helper invocation it applies a structural check appropriate to the
helper's expected output shape:

  - structural FAIL  → verified = bad   (decisive — keeps malformed/garbage
                       output out of the self-evolution exemplar pool)
  - structural PASS  → verified = good  (a conservative bar: well-formed and
                       usable; for narrow specialists, valid output shape is
                       most of the value)

A human `aios self-evolve mark` can still override. This organ provides the
autonomous baseline so the round controller can chain
dream → local-operator → verify → self-evolve with no operator in the loop.
"""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

OBSERVATIONS_REL = ".aios/helpers/observations.jsonl"


def now_iso() -> str:
    return datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds")


ERROR_MARKERS = ("local_llm_call_failed", "could not parse", "error:", "timed out", "traceback")


def check_summarize(inp: str, out: str) -> tuple[bool, str]:
    if len(out) < 20:
        return False, "summary too short / empty"
    if len(out) >= len(inp) and len(inp) > 200:
        return False, "summary not shorter than a long input"
    return True, "non-empty, condensed"


def check_classify(inp: str, out: str) -> tuple[bool, str]:
    u = out.upper()
    if "VISION" in u or "OPERATOR" in u:
        return True, "emitted a valid class tag"
    return False, "no VISION/OPERATOR tag in output"


def check_consolidate(inp: str, out: str) -> tuple[bool, str]:
    u = out.upper()
    hits = sum(1 for m in ("RECURRING SCHEMA", "STALE", "OPEN QUESTION") if m in u)
    if hits >= 2:
        return True, f"{hits}/3 consolidation sections present"
    return False, f"only {hits}/3 consolidation sections"


def check_operator_review(inp: str, out: str) -> tuple[bool, str]:
    u = out.upper()
    if any(t in u for t in ("ROUTINE-REVERSIBLE", "NEEDS-REVIEW", "ESCALATE", "ROUTINE REVERSIBLE", "NEEDS REVIEW")):
        return True, "emitted at least one review tag"
    return False, "no review tag in output"


def check_default(inp: str, out: str) -> tuple[bool, str]:
    if len(out.strip()) < 10:
        return False, "output empty / trivial"
    return True, "non-empty output"


CHECKS = {
    "cap_helper_summarize": check_summarize,
    "cap_helper_classify_vision_level": check_classify,
    "cap_helper_consolidate": check_consolidate,
    "cap_helper_operator_review": check_operator_review,
}


def structural_check(helper_id: str, inp: str, out: str) -> tuple[bool, str]:
    low = out.lower()
    if any(m in low for m in ERROR_MARKERS):
        return False, "output contains an error/failure marker"
    return CHECKS.get(helper_id, check_default)(inp, out)


def load_observations(root: Path) -> list[dict[str, Any]]:
    path = root / OBSERVATIONS_REL
    if not path.exists():
        return []
    rows = []
    for line in path.read_text(encoding="utf-8", errors="replace").splitlines():
        line = line.strip()
        if line:
            try:
                rows.append(json.loads(line))
            except ValueError:
                continue
    return rows


def write_observations(root: Path, rows: list[dict[str, Any]]) -> None:
    (root / OBSERVATIONS_REL).write_text(
        "".join(json.dumps(r, ensure_ascii=False) + "\n" for r in rows), encoding="utf-8")


def cmd_run(root: Path, json_mode: bool) -> int:
    rows = load_observations(root)
    verified_good = verified_bad = skipped = 0
    receipts = []
    for r in rows:
        # only auto-verify v2 records that are still unmarked and have output
        if r.get("schema") != "aios.helper_observation.v2":
            continue
        if r.get("verified") is not None:
            continue
        helper_id = r.get("helper_id", "")
        out = r.get("output_excerpt", "") or ""
        inp = r.get("input_excerpt", "") or ""
        if not r.get("ok", True) or not out:
            r["verified"] = False
            r["verified_at"] = now_iso()
            r["verified_by"] = "auto:aios_verify"
            r["verify_reason"] = "invocation failed or produced no output"
            verified_bad += 1
            continue
        ok, reason = structural_check(helper_id, inp, out)
        r["verified"] = bool(ok)
        r["verified_at"] = now_iso()
        r["verified_by"] = "auto:aios_verify"
        r["verify_reason"] = reason
        if ok:
            verified_good += 1
        else:
            verified_bad += 1
        receipts.append({"invocation_id": r.get("invocation_id"), "helper_id": helper_id,
                          "verified": bool(ok), "reason": reason})
    write_observations(root, rows)

    summary = {
        "schema": "aios.verify.v1",
        "ran_at": now_iso(),
        "method": "deterministic structural checks — not an LLM judging an LLM",
        "verified_good": verified_good,
        "verified_bad": verified_bad,
        "receipts": receipts[-20:],
    }
    if json_mode:
        print(json.dumps(summary, indent=2, ensure_ascii=False))
    else:
        for rc in receipts[-20:]:
            mark = "good" if rc["verified"] else "bad "
            print(f"  [{mark}] {rc['helper_id']}: {rc['reason']}")
        print(f"-- auto-verified: {verified_good} good, {verified_bad} bad")
    return 0


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description="AIOS auto-verification organ")
    p.add_argument("--root", default=".")
    p.add_argument("action", nargs="?", default="run", choices=["run"])
    p.add_argument("--json", action="store_true")
    args = p.parse_args(argv)
    return cmd_run(Path(args.root).resolve(), args.json)


if __name__ == "__main__":
    sys.exit(main())
