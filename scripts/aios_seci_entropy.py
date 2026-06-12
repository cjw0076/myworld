#!/usr/bin/env python3
"""SECI entropy gate for AIOS closeout.

Checks whether a synthesis or contract closeout carries the four SECI knowledge
conversion modes plus an entropy/discomfort branch. Advisory only: it blocks
overclaiming in reports, but does not execute GenesisOS work or choose truth.
"""

from __future__ import annotations

import argparse
import json
import re
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Final


SCHEMA_VERSION: Final = "aios.seci_entropy.v1"


@dataclass(frozen=True)
class Requirement:
    key: str
    label: str
    pattern: re.Pattern[str]
    gap: str


REQUIREMENTS: Final = (
    Requirement(
        key="socialization",
        label="Socialization",
        pattern=re.compile(r"\b(socialization|tacit sharing|shared experience|관찰|사회화)\b", re.I),
        gap="missing socialization: no tacit/shared-experience source",
    ),
    Requirement(
        key="externalization",
        label="Externalization",
        pattern=re.compile(r"\b(externalization|tacit to explicit|명시|외재화)\b", re.I),
        gap="missing externalization: tacit knowledge was not made explicit",
    ),
    Requirement(
        key="combination",
        label="Combination",
        pattern=re.compile(r"\b(combination|combine|synthesis|cross[- ]?source|종합|결합)\b", re.I),
        gap="missing combination: explicit sources were not recombined",
    ),
    Requirement(
        key="internalization",
        label="Internalization",
        pattern=re.compile(r"\b(internalization|explicit to tacit|habit|unconscious|내재화|무의식)\b", re.I),
        gap="missing internalization: explicit knowledge did not become a future habit/gate",
    ),
    Requirement(
        key="discomfort",
        label="Discomfort",
        pattern=re.compile(r"\b(discomfort|deficit|dissatisfaction|need|friction|불편|결핍|불만족|필요)\b", re.I),
        gap="missing discomfort: no artificial need/friction was named",
    ),
    Requirement(
        key="counter_branch",
        label="Counter branch",
        pattern=re.compile(r"\b(counter[- ]?branch|alternative|assumption mutation|opposing frame|반대|대안|가정)\b", re.I),
        gap="missing counter branch: no competing frame survived the synthesis",
    ),
)


def now_iso() -> str:
    return datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds")


def read_text(path: Path | None, inline: str | None) -> tuple[str, str]:
    if path is not None:
        return path.read_text(encoding="utf-8", errors="replace"), path.as_posix()
    return inline or "", "inline"


def evaluate(text: str, source: str = "inline") -> dict:
    checks = []
    for req in REQUIREMENTS:
        ok = bool(req.pattern.search(text))
        checks.append(
            {
                "key": req.key,
                "label": req.label,
                "ok": ok,
                "gap": "" if ok else req.gap,
            }
        )
    gaps = [row["gap"] for row in checks if row["gap"]]
    return {
        "schema_version": SCHEMA_VERSION,
        "generated_at": now_iso(),
        "source": source,
        "pass": not gaps,
        "authority": "advisory_only",
        "execution_enabled": False,
        "checks": checks,
        "gaps": gaps,
        "next_action": "closeout may proceed with SECI/entropy receipt" if not gaps else "add missing SECI/entropy evidence before closeout",
        "stop_conditions": [
            "seci_stage_missing",
            "discomfort_missing",
            "counter_branch_missing",
            "genesis_selects_final_truth",
        ],
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Evaluate SECI entropy closeout readiness")
    source = parser.add_mutually_exclusive_group(required=True)
    source.add_argument("--text")
    source.add_argument("--path")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args(argv)
    path = Path(args.path) if args.path else None
    text, source_ref = read_text(path, args.text)
    payload = evaluate(text, source_ref)
    if args.json:
        print(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True))
    else:
        print(f"seci_entropy_pass={payload['pass']}")
        for gap in payload["gaps"]:
            print(f"- {gap}")
    return 0 if payload["pass"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
