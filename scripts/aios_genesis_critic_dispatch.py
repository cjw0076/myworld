#!/usr/bin/env python3
"""Run GenesisOS prompt-prison critic against open AIOS contracts."""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


SCHEMA_VERSION = "aios.genesis_critic_dispatch.v1"
OPEN_STATUSES = {"proposed", "accepted", "active"}
ESCAPE_REVIEW_HEADING = "## GenesisOS Escape Review"
ESCAPE_REVIEW_REQUIRED_MARKERS = (
    "### Assumptions",
    "Counter branch:",
    "### Plain Language",
    "### Cross-Domain Frame",
    "### Time Horizons",
)
ESCAPE_REVIEW_MIN_WORDS = 50


def now_iso() -> str:
    return datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds")


def parse_frontmatter(path: Path) -> tuple[dict[str, str], str]:
    text = path.read_text(encoding="utf-8")
    if not text.startswith("---\n"):
        return {}, text
    end = text.find("\n---\n", 4)
    if end == -1:
        return {}, text
    raw = text[4:end]
    data: dict[str, str] = {}
    for line in raw.splitlines():
        key, sep, value = line.partition(":")
        if sep:
            data[key.strip()] = value.strip()
    return data, text[end + 5 :]


def import_genesis_critic(root: Path):
    genesis_root = root / "GenesisOS"
    if genesis_root.as_posix() not in sys.path:
        sys.path.insert(0, genesis_root.as_posix())
    from genesisos.critic import Critic  # type: ignore

    return Critic


def iter_contracts(root: Path) -> list[Path]:
    return sorted((root / "docs" / "contracts").glob("ASC-*.md"))


def extract_escape_review(body: str) -> str:
    if ESCAPE_REVIEW_HEADING not in body:
        return ""
    section = body.split(ESCAPE_REVIEW_HEADING, 1)[1]
    return section.split("\n## ", 1)[0]


def escape_review_status(body: str) -> dict[str, Any]:
    section = extract_escape_review(body)
    if not section:
        return {
            "present": False,
            "complete": False,
            "missing_markers": list(ESCAPE_REVIEW_REQUIRED_MARKERS),
            "word_count": 0,
        }
    missing = [marker for marker in ESCAPE_REVIEW_REQUIRED_MARKERS if marker not in section]
    word_count = len(section.split())
    return {
        "present": True,
        "complete": not missing and word_count >= ESCAPE_REVIEW_MIN_WORDS,
        "missing_markers": missing,
        "word_count": word_count,
    }


def build_report(root: Path, *, limit: int | None = None) -> dict[str, Any]:
    root = root.resolve()
    Critic = import_genesis_critic(root)
    critic = Critic()
    scanned: list[dict[str, Any]] = []
    flagged: list[dict[str, Any]] = []
    unreviewed_flagged: list[dict[str, Any]] = []
    reviewed_flagged: list[dict[str, Any]] = []
    paths = iter_contracts(root)
    if limit is not None:
        paths = paths[-limit:]
    for path in paths:
        frontmatter, body = parse_frontmatter(path)
        status = frontmatter.get("status", "")
        if status not in OPEN_STATUSES:
            continue
        payload = critic.detect(text=f"{frontmatter}\n{body}")
        signatures = payload.get("prison_signatures", [])
        row = {
            "path": path.relative_to(root).as_posix(),
            "contract_id": frontmatter.get("contract_id") or path.stem.split("-", 1)[0],
            "status": status,
            "signature_count": len(signatures),
            "escape_review": escape_review_status(body),
        }
        scanned.append(row)
        if signatures:
            flagged_row = {
                **row,
                "confidence": payload.get("confidence"),
                "signatures": signatures,
                "escape_vectors": payload.get("escape_vectors", []),
            }
            flagged.append(flagged_row)
            if flagged_row["escape_review"]["complete"]:
                reviewed_flagged.append(flagged_row)
            else:
                unreviewed_flagged.append(flagged_row)
    return {
        "schema_version": SCHEMA_VERSION,
        "generated_at": now_iso(),
        "authority": "advisory_only",
        "recommendation_only": True,
        "mutation_policy": "no_contract_or_memory_mutation",
        "mutated_files": [],
        "scanned_count": len(scanned),
        "flagged_count": len(flagged),
        "unreviewed_flagged_count": len(unreviewed_flagged),
        "reviewed_flagged_count": len(reviewed_flagged),
        "scanned": scanned,
        "flagged": flagged,
        "unreviewed_flagged": unreviewed_flagged,
        "reviewed_flagged": reviewed_flagged,
    }


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", default=".", help="MyWorld root")
    parser.add_argument("--limit", type=int, default=None, help="limit to most recent N contract files")
    parser.add_argument("--json", action="store_true")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    report = build_report(Path(args.root), limit=args.limit)
    if args.json:
        print(json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True))
    else:
        print(
            f"schema={report['schema_version']} scanned={report['scanned_count']} "
            f"flagged={report['flagged_count']} authority={report['authority']}"
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
