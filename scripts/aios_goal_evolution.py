#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path


SCRIPT_DIR = Path(__file__).resolve().parent
if SCRIPT_DIR.as_posix() not in sys.path:
    sys.path.insert(0, SCRIPT_DIR.as_posix())

from aios_goal_plan import build_plan, stop_conditions, write_markdown  # noqa: E402
from aios_goal_sources import Goal  # noqa: E402


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Plan the next AIOS contract from one active goal")
    sub = parser.add_subparsers(dest="cmd", required=True)
    plan = sub.add_parser("plan", help="build a goal evolution plan")
    plan.add_argument("--root", default=Path.cwd().as_posix(), help="myworld root")
    plan.add_argument("--goal", required=True, help="goal markdown file")
    plan.add_argument("--radar", default="docs/AIOS_TASK_RADAR.md", help="task radar markdown")
    plan.add_argument("--write", help="write markdown plan")
    plan.add_argument("--json", action="store_true", help="print JSON")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    root = Path(args.root).resolve()
    goal_path = Path(args.goal)
    if not goal_path.is_absolute():
        goal_path = root / goal_path
    radar_path = Path(args.radar)
    if not radar_path.is_absolute():
        radar_path = root / radar_path
    plan = build_plan(root, goal_path, radar_path)
    if args.write:
        out = Path(args.write)
        write_markdown(root / out if not out.is_absolute() else out, plan)
    if args.json or not args.write:
        print(json.dumps(plan, ensure_ascii=False, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    sys.exit(main())
