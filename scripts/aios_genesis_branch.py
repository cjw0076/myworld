#!/usr/bin/env python3
"""Fork, list, and collapse GenesisOS multi-universe branches for a goal."""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


SCHEMA_VERSION = "aios.genesis_branch.v1"


def now_iso() -> str:
    return datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds")


def import_genesis_branches(root: Path):
    genesis_root = (root / "GenesisOS").resolve()
    package_dir = genesis_root / "genesisos"
    if genesis_root.as_posix() not in sys.path:
        sys.path.insert(0, genesis_root.as_posix())
    loaded = sys.modules.get("genesisos")
    loaded_paths = [Path(path).resolve() for path in getattr(loaded, "__path__", [])] if loaded else []
    if loaded and package_dir not in loaded_paths:
        for name in list(sys.modules):
            if name == "genesisos" or name.startswith("genesisos."):
                del sys.modules[name]
    from genesisos.branches import collapse, fork, snapshot  # type: ignore

    return fork, snapshot, collapse


def parse_goal_document(path: Path) -> str:
    text = path.read_text(encoding="utf-8")
    if text.startswith("---"):
        end = text.find("\n---", 3)
        if end != -1:
            for line in text[3:end].splitlines():
                key, _, value = line.partition(":")
                if key.strip() == "goal" and value.strip():
                    return value.strip()
            text = text[end + 4 :]
    for line in text.splitlines():
        stripped = line.strip(" #")
        if stripped:
            return stripped
    raise ValueError(f"goal document has no usable text: {path}")


def resolve_goal(goal: str | None, goal_path: str | None) -> tuple[str, str | None]:
    if goal:
        return goal, None
    if goal_path:
        path = Path(goal_path)
        return parse_goal_document(path), str(path)
    raise ValueError("either --goal or --goal-path is required")


def universes_root_for(root: Path, override: str | None = None) -> Path:
    return Path(override) if override else root / ".aios" / "genesis_universes"


def build_report(
    root: Path,
    *,
    action: str,
    goal: str | None = None,
    goal_path: str | None = None,
    n: int = 3,
    winner: str | None = None,
    reason: str | None = None,
    universes_root: str | None = None,
    include_collapsed: bool = False,
) -> dict[str, Any]:
    root = root.resolve()
    fork, snapshot, collapse = import_genesis_branches(root)
    branch_root = universes_root_for(root, universes_root)
    selected_goal, selected_goal_path = resolve_goal(goal, goal_path) if action in {"fork", "collapse"} else (goal, goal_path)

    if action == "fork":
        result = fork(
            selected_goal,
            n=n,
            universes_root=branch_root,
            seeds_root=root / "GenesisOS" / "seeds",
        )
    elif action == "list":
        result = snapshot(universes_root=branch_root, goal=goal, include_collapsed=include_collapsed)
    elif action == "collapse":
        if not winner:
            raise ValueError("--winner is required for collapse")
        if not reason:
            raise ValueError("--reason is required for collapse")
        result = collapse(selected_goal, winner, reason, universes_root=branch_root)
        alive = [branch for branch in result["branches"] if branch["alive"]]
        result["canonical_branch"] = alive[0] if alive else None
        result["canonical_contract_path"] = "pending_operator_promotion"
    else:
        raise ValueError(f"unknown action: {action}")

    return {
        "schema_version": SCHEMA_VERSION,
        "generated_at": now_iso(),
        "authority": "operator_review_required",
        "recommendation_only": True,
        "mutation_policy": "no_contract_or_memory_mutation",
        "action": action,
        "goal_path": selected_goal_path,
        "universes_root": branch_root.relative_to(root).as_posix() if branch_root.is_relative_to(root) else str(branch_root),
        "result": result,
        "mutated_files": [],
        "stop_conditions": [
            "no_contract_creation",
            "no_external_execution",
            "explicit_operator_collapse_required",
        ],
    }


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", default=".", help="MyWorld root")
    sub = parser.add_subparsers(dest="action", required=True)

    fork_cmd = sub.add_parser("fork")
    fork_goal = fork_cmd.add_mutually_exclusive_group(required=True)
    fork_goal.add_argument("--goal")
    fork_goal.add_argument("--goal-path")
    fork_cmd.add_argument("--n", type=int, default=3)
    fork_cmd.add_argument("--universes-root")
    fork_cmd.add_argument("--json", action="store_true")

    list_cmd = sub.add_parser("list")
    list_cmd.add_argument("--goal")
    list_cmd.add_argument("--all", action="store_true")
    list_cmd.add_argument("--universes-root")
    list_cmd.add_argument("--json", action="store_true")

    collapse_cmd = sub.add_parser("collapse")
    collapse_goal = collapse_cmd.add_mutually_exclusive_group(required=True)
    collapse_goal.add_argument("--goal")
    collapse_goal.add_argument("--goal-path")
    collapse_cmd.add_argument("--winner", required=True)
    collapse_cmd.add_argument("--reason", required=True)
    collapse_cmd.add_argument("--universes-root")
    collapse_cmd.add_argument("--json", action="store_true")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    report = build_report(
        Path(args.root),
        action=args.action,
        goal=getattr(args, "goal", None),
        goal_path=getattr(args, "goal_path", None),
        n=getattr(args, "n", 3),
        winner=getattr(args, "winner", None),
        reason=getattr(args, "reason", None),
        universes_root=getattr(args, "universes_root", None),
        include_collapsed=getattr(args, "all", False),
    )
    if getattr(args, "json", False):
        print(json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True))
    else:
        result = report["result"]
        count = len(result.get("branches", []))
        print(f"schema={report['schema_version']} action={report['action']} branches={count}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
