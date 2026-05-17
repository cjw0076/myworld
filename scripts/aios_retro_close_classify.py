#!/usr/bin/env python3
"""Classify existing closed AIOS contracts without reopening them."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from aios_close_condition import evaluate_contract


SCHEMA_VERSION = "aios.retro_close_classify.v1"


def build_report(root: Path) -> dict[str, Any]:
    rows = []
    counts = {"goal_met": 0, "partial": 0, "unmet": 0}
    for path in sorted((root / "docs" / "contracts").glob("ASC-*.md")):
        payload = evaluate_contract(path, root=root)
        if payload.get("status") != "closed":
            continue
        close_type = payload["recommended_close_type"]
        if close_type == "closed_goal_met":
            counts["goal_met"] += 1
        elif close_type == "closed_partial_with_followup":
            counts["partial"] += 1
        else:
            counts["unmet"] += 1
        rows.append(
            {
                "contract_id": payload["contract_id"],
                "path": path.relative_to(root).as_posix(),
                "recommended_close_type": close_type,
                "met": payload["met"],
                "unmet": payload["unmet"],
                "manual": payload["manual"],
            }
        )
    return {
        "schema_version": SCHEMA_VERSION,
        "root": root.as_posix(),
        "total": len(rows),
        "goal_met": counts["goal_met"],
        "partial": counts["partial"],
        "unmet": counts["unmet"],
        "rows": rows,
    }


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Retro-classify closed AIOS contracts")
    parser.add_argument("--root", type=Path, default=Path.cwd())
    parser.add_argument("--json", action="store_true")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    payload = build_report(args.root.resolve())
    if args.json:
        print(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True))
    else:
        print(f"total={payload['total']} goal_met={payload['goal_met']} partial={payload['partial']} unmet={payload['unmet']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
