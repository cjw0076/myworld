#!/usr/bin/env python3
"""ASC-0211 L3 routine #1 — Convergence Audit.

Scans recently closed contracts and accepted memories for *footprint
consensus* vs *real challenge*. Goal: detect when AIOS converged because
the two peer agents (user + claude/codex) just agreed too easily, vs.
because the proposition survived real adversarial review.

This routine produces *advisory signals only* (DNA invariant 1 +
draft-first). It never auto-flags anything as invalid. It just gives the
peers a score they can choose to challenge or ignore.

Output schema: aios.convergence_audit.v1
"""
from __future__ import annotations

import argparse
import datetime as _dt
import json
import re
import sys
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parent.parent
CONTRACTS = REPO_ROOT / "docs" / "contracts"


CHALLENGE_SIGNALS: list[tuple[str, re.Pattern[str], int]] = [
    # (signal_name, regex, weight)
    ("genesis_review",      re.compile(r"## Genesis Escape Review", re.M), 3),
    ("adversarial_review",  re.compile(r"adversarial review|hive[ -]debate", re.I), 2),
    ("memory_citation",     re.compile(r"\bmem_[a-f0-9]{8,}|trace_id[: =]", re.I), 2),
    ("external_evidence",   re.compile(r"https?://|arxiv|github\.com", re.I), 1),
    ("supersede_history",   re.compile(r"superseded_by|withdrawn_reason", re.I), 2),
    ("named_exit",          re.compile(r"## Named Exit|닫는 증거", re.I), 1),
    ("stop_conditions",     re.compile(r"## Stop[_ ]?Conditions?", re.M), 2),
    ("verification_gate",   re.compile(r"## Verification Gate|verify[: ]", re.I), 2),
    ("frontier_reference",  re.compile(r"frontier|prompt[ -]prison|cross-domain", re.I), 1),
    ("co_authored_by_peer", re.compile(r"Co-Authored-By", re.I), 0),  # informational
]

FOOTPRINT_SIGNALS: list[tuple[str, re.Pattern[str], int]] = [
    # signals that suggest *accepted without challenge*
    ("auto_close_4min",  re.compile(r"accepted: (.+?)\nclosed: (.+?)\n", re.M), 0),  # special-cased below
    ("no_evidence_refs", re.compile(r"evidence_refs?\s*[:=]\s*\[\s*\]", re.I), 1),
    ("frame_echo",       re.compile(r"per founder|founder said|founder.*명시", re.I), 1),
    ("self_endorsement", re.compile(r"closeout_authority:.+claude@", re.I), 1),
]


def _split_frontmatter(text: str) -> tuple[dict[str, str], str]:
    """Return (frontmatter_dict, body). Frontmatter is parsed as flat key: value
    (no nested YAML support — sufficient for our contracts)."""
    fm: dict[str, str] = {}
    if not text.startswith("---"):
        return fm, text
    parts = text.split("---", 2)
    if len(parts) < 3:
        return fm, text
    fm_block = parts[1]
    body = parts[2]
    cur_key = None
    cur_lines: list[str] = []
    for line in fm_block.splitlines():
        m = re.match(r"^([a-zA-Z_][\w_]*):\s*(.*)$", line)
        if m:
            if cur_key is not None:
                fm[cur_key] = "\n".join(cur_lines).strip()
            cur_key = m.group(1)
            cur_lines = [m.group(2)]
        else:
            cur_lines.append(line)
    if cur_key is not None:
        fm[cur_key] = "\n".join(cur_lines).strip()
    return fm, body


def _parse_ts(s: str | None) -> _dt.datetime | None:
    if not s:
        return None
    s = s.strip().rstrip("KST").strip()
    for fmt in (
        "%Y-%m-%dT%H:%M:%S%z",
        "%Y-%m-%dT%H:%M:%S",
        "%Y-%m-%d %H:%M",
        "%Y-%m-%d",
    ):
        try:
            return _dt.datetime.strptime(s.split(" by ")[0], fmt)
        except ValueError:
            continue
    return None


def audit_contract(path: Path) -> dict[str, Any]:
    path = path.resolve()
    text = path.read_text(encoding="utf-8", errors="replace")
    fm, body = _split_frontmatter(text)

    challenge_hits: dict[str, int] = {}
    challenge_score = 0
    for name, rx, weight in CHALLENGE_SIGNALS:
        matches = rx.findall(text)
        if matches:
            challenge_hits[name] = len(matches)
            challenge_score += weight

    footprint_hits: dict[str, int] = {}
    footprint_score = 0
    for name, rx, weight in FOOTPRINT_SIGNALS:
        if name == "auto_close_4min":
            continue
        m = rx.findall(text)
        if m:
            footprint_hits[name] = len(m)
            footprint_score += weight

    accepted_ts = _parse_ts(fm.get("accepted"))
    closed_ts = _parse_ts(fm.get("closed"))
    duration_seconds = None
    if accepted_ts and closed_ts:
        try:
            duration_seconds = (closed_ts - accepted_ts).total_seconds()
        except Exception:
            duration_seconds = None
        if duration_seconds is not None and 0 <= duration_seconds < 600:
            # accepted -> closed in under 10 minutes is a soft footprint signal
            footprint_hits["auto_close_under_10min"] = 1
            footprint_score += 2

    # Heuristic verdict — *advisory only*.
    if challenge_score >= 6 and footprint_score <= 2:
        verdict = "real_challenge"
    elif challenge_score <= 2 and footprint_score >= 3:
        verdict = "footprint_consensus"
    elif challenge_score >= 4 and footprint_score <= 4:
        verdict = "mixed"
    else:
        verdict = "indeterminate"

    try:
        rel_path = path.relative_to(REPO_ROOT).as_posix()
    except ValueError:
        rel_path = path.as_posix()
    return {
        "contract_id": fm.get("contract_id"),
        "path": rel_path,
        "status": fm.get("status"),
        "slug": fm.get("slug"),
        "challenge_score": challenge_score,
        "challenge_hits": challenge_hits,
        "footprint_score": footprint_score,
        "footprint_hits": footprint_hits,
        "duration_accepted_to_closed_s": duration_seconds,
        "verdict": verdict,
    }


def audit_recent_closed(n: int = 10) -> list[dict[str, Any]]:
    closed = [
        p for p in sorted(CONTRACTS.glob("ASC-*.md"))
        if "^status: closed" in p.read_text(encoding="utf-8", errors="replace")
        or "status: closed" in p.read_text(encoding="utf-8", errors="replace")[:400]
    ]
    closed = closed[-n:]
    return [audit_contract(p) for p in closed]


def audit_paths(paths: list[Path]) -> list[dict[str, Any]]:
    return [audit_contract(p) for p in paths]


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description="ASC-0211 L3 — Convergence Audit")
    p.add_argument("targets", nargs="*", help="contract file paths (default: recent closed)")
    p.add_argument("--recent", type=int, default=10,
                   help="when no targets, audit the N most recent closed contracts")
    p.add_argument("--json", action="store_true")
    p.add_argument("--verdict-only", action="store_true",
                   help="print only id + verdict per line (compact)")
    args = p.parse_args(argv)

    if args.targets:
        rows = audit_paths([Path(t) for t in args.targets])
    else:
        rows = audit_recent_closed(args.recent)

    if args.json:
        out = {
            "schema_version": "aios.convergence_audit.v1",
            "generated_at": _dt.datetime.now(_dt.timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z"),
            "count": len(rows),
            "rows": rows,
        }
        print(json.dumps(out, indent=2, ensure_ascii=False))
    elif args.verdict_only:
        for r in rows:
            print(f"{r['contract_id']:9}  {r['verdict']:20}  ch={r['challenge_score']:>2}  fp={r['footprint_score']:>2}  {r['slug']}")
    else:
        for r in rows:
            print(f"\n=== {r['contract_id']} ({r['verdict']}) ===")
            print(f"  path: {r['path']}")
            print(f"  challenge_score: {r['challenge_score']}  ({', '.join(r['challenge_hits'].keys())})")
            print(f"  footprint_score: {r['footprint_score']}  ({', '.join(r['footprint_hits'].keys())})")
            if r["duration_accepted_to_closed_s"] is not None:
                print(f"  duration: {r['duration_accepted_to_closed_s']:.0f}s")
    return 0


if __name__ == "__main__":
    sys.exit(main())
