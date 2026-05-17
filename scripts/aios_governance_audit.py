#!/usr/bin/env python3
"""Audit AIOS contract governance evidence."""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path
from statistics import mean
from typing import Any

try:
    from aios_dna_lint import dna_citations, requires_dna
except ModuleNotFoundError:
    from scripts.aios_dna_lint import dna_citations, requires_dna


SCHEMA_VERSION = "aios.governance_audit.v1"
SCORE_KEYS = (
    "closure_evidence",
    "verification_evidence",
    "dna_citation",
    "hive_verdict_citation",
    "dogfood_evidence",
    "cross_repo_evidence",
)
CHILD_REPOS = ("hivemind", "memoryOS", "CapabilityOS", "GenesisOS")
VISION_TERMS = ("dna", "governance", "sovereign", "constitution", "vision", "founder reframe", "government")
VERIFICATION_TERMS = ("python ", "pytest", "unittest", "bash ", "verification passed", "dispatch result", ".aios/outbox", "status=passed")
DOGFOOD_TERMS = ("dogfood", "smoke", "dispatch result", "memoryos draft", "live api", "result packet", "verified")


def parse_frontmatter(text: str) -> tuple[dict[str, str], str]:
    if not text.startswith("---\n"):
        return {}, text
    end = text.find("\n---\n", 4)
    if end == -1:
        return {}, text
    data: dict[str, str] = {}
    current_key: str | None = None
    for raw in text[4:end].splitlines():
        if not raw.strip():
            continue
        if raw.startswith((" ", "\t")) and current_key:
            data[current_key] = f"{data[current_key]} {raw.strip()}".strip()
            continue
        key, sep, value = raw.partition(":")
        if sep:
            current_key = key.strip()
            data[current_key] = value.strip().strip('"')
    return data, text[end + 5 :]


def section(body: str, heading: str) -> str:
    match = re.search(rf"^##\s+{re.escape(heading)}\s*$", body, flags=re.MULTILINE)
    if not match:
        return ""
    rest = body[match.end() :]
    next_heading = re.search(r"^##\s+", rest, flags=re.MULTILINE)
    return rest[: next_heading.start()] if next_heading else rest


def scope_repos(body: str) -> list[str]:
    scope = section(body, "Scope")
    repos: list[str] = []
    for repo in ("myworld", *CHILD_REPOS):
        if re.search(rf"\b{re.escape(repo)}\b", scope):
            repos.append(repo)
    return repos


def has_nonempty_receipts(receipts: str) -> bool:
    stripped = receipts.strip()
    return bool(stripped) and stripped.lower() not in {"pending.", "pending"}


def is_vision_level(frontmatter: dict[str, str], body: str) -> bool:
    lower = f"{frontmatter.get('goal', '')}\n{body}".lower()
    return any(term in lower for term in VISION_TERMS)


def contains_any(text: str, terms: tuple[str, ...]) -> bool:
    lower = text.lower()
    return any(term in lower for term in terms)


def cross_repo_score(repos: list[str], receipts: str) -> tuple[int, str]:
    child_repos = [repo for repo in repos if repo != "myworld"]
    if not child_repos:
        return 1, "not_required"
    missing = [repo for repo in child_repos if repo not in receipts]
    if missing:
        return 0, f"missing_repo_evidence:{','.join(missing)}"
    return 1, "all_scoped_repos_evidenced"


def audit_contract(path: Path) -> dict[str, Any]:
    text = path.read_text(encoding="utf-8", errors="replace")
    frontmatter, body = parse_frontmatter(text)
    receipts = section(body, "Receipts")
    repos = scope_repos(body)
    dna_required, dna_reasons = requires_dna(frontmatter, body)
    citations = dna_citations(text)
    hive_required = is_vision_level(frontmatter, body)
    cross_score, cross_reason = cross_repo_score(repos, receipts)
    scores = {
        "closure_evidence": int(frontmatter.get("status") == "closed" and has_nonempty_receipts(receipts)),
        "verification_evidence": int(contains_any(receipts, VERIFICATION_TERMS)),
        "dna_citation": int((not dna_required) or bool(citations)),
        "hive_verdict_citation": int((not hive_required) or ("ASC-0084" in text or "aios_dna_debate" in text)),
        "dogfood_evidence": int(contains_any(receipts, DOGFOOD_TERMS)),
        "cross_repo_evidence": cross_score,
    }
    score = mean(scores.values())
    return {
        "contract_id": frontmatter.get("contract_id") or path.stem.split("-", 1)[0],
        "path": path.as_posix(),
        "status": frontmatter.get("status") or "unknown",
        "repos": repos,
        "scores": scores,
        "governance_score": round(score, 4),
        "citations": citations,
        "dna_required": dna_required,
        "dna_reasons": dna_reasons,
        "hive_verdict_required": hive_required,
        "cross_repo_reason": cross_reason,
    }


def health_color(score: float) -> str:
    if score < 0.5:
        return "red"
    if score < 0.75:
        return "yellow"
    return "green"


def build_audit(root: Path, pattern: str) -> dict[str, Any]:
    paths = sorted(root.glob(pattern))
    rows = [audit_contract(path) for path in paths if path.is_file()]
    recent = rows[-20:]
    low_recent = [row for row in recent if row["governance_score"] < 0.5]
    aggregate_score = round(mean(row["governance_score"] for row in rows), 4) if rows else 0.0
    counts = {
        key: sum(int(row["scores"][key]) for row in rows)
        for key in SCORE_KEYS
    }
    aggregate = {
        "contract_count": len(rows),
        "governance_score": aggregate_score,
        "health_color": health_color(aggregate_score),
        "score_counts": counts,
        "score_rates": {key: round(counts[key] / len(rows), 4) if rows else 0.0 for key in SCORE_KEYS},
        "governance_theater": len(recent) >= 20 and len(low_recent) > len(recent) / 2,
        "recent_low_score_count": len(low_recent),
        "recent_window": len(recent),
    }
    return {
        "schema_version": SCHEMA_VERSION,
        "root": root.as_posix(),
        "pattern": pattern,
        "aggregate": aggregate,
        "per_contract": rows,
    }


def render_markdown(audit: dict[str, Any]) -> str:
    aggregate = audit["aggregate"]
    lines = [
        "# AIOS Governance Audit",
        "",
        "This report is generated by `scripts/aios_governance_audit.py`.",
        "",
        "## Baseline",
        "",
        f"- contracts: `{aggregate['contract_count']}`",
        f"- governance_score: `{aggregate['governance_score']}`",
        f"- health_color: `{aggregate['health_color']}`",
        f"- governance_theater: `{aggregate['governance_theater']}`",
        "",
        "## Score Rates",
        "",
    ]
    for key, rate in aggregate["score_rates"].items():
        lines.append(f"- {key}: `{rate}`")
    lines.extend(["", "## Lowest Contracts", ""])
    lowest = sorted(audit["per_contract"], key=lambda row: (row["governance_score"], row["contract_id"]))[:20]
    for row in lowest:
        zeroes = [key for key, value in row["scores"].items() if not value]
        lines.append(f"- `{row['contract_id']}` score `{row['governance_score']}` missing `{', '.join(zeroes) or 'none'}`")
    lines.extend(["", "## Rubric", ""])
    lines.extend(
        [
            "- closure_evidence: closed contract with non-empty receipts",
            "- verification_evidence: receipts cite concrete commands, artifacts, or passed results",
            "- dna_citation: required contracts cite at least one DNA invariant",
            "- hive_verdict_citation: vision-level contracts cite ASC-0084 or Hive DNA debate artifacts",
            "- dogfood_evidence: receipts show AIOS used its own loop or output",
            "- cross_repo_evidence: cross-repo contracts show evidence for each child repo in scope",
        ]
    )
    return "\n".join(lines) + "\n"


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=Path.cwd())
    parser.add_argument("--glob", default="docs/contracts/ASC-*.md")
    parser.add_argument("--write")
    parser.add_argument("--json", action="store_true")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    root = args.root.resolve()
    audit = build_audit(root, args.glob)
    if args.write:
        output = root / args.write
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(render_markdown(audit), encoding="utf-8")
    if args.json or not args.write:
        print(json.dumps(audit, ensure_ascii=False, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
