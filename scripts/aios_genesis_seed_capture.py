#!/usr/bin/env python3
"""Capture an operator GenesisOS seed from the MyWorld control plane."""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


SCHEMA_VERSION = "aios.genesis_seed_capture.v1"


def now_iso() -> str:
    return datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds")


def import_genesis_library(root: Path):
    genesis_root = (root / "GenesisOS").resolve()
    if not (genesis_root / "genesisos").exists():
        genesis_root = (Path(__file__).resolve().parents[1] / "GenesisOS").resolve()
    package_dir = genesis_root / "genesisos"
    if genesis_root.as_posix() not in sys.path:
        sys.path.insert(0, genesis_root.as_posix())
    loaded = sys.modules.get("genesisos")
    loaded_paths = [Path(path).resolve() for path in getattr(loaded, "__path__", [])] if loaded else []
    if loaded and package_dir not in loaded_paths:
        for name in list(sys.modules):
            if name == "genesisos" or name.startswith("genesisos."):
                del sys.modules[name]
    from genesisos.library import Library, seed_path  # type: ignore

    return Library, seed_path


def load_text(args: argparse.Namespace) -> str:
    if args.inline:
        return args.inline
    return Path(args.text).read_text(encoding="utf-8")


def split_tags(raw: str) -> list[str]:
    return [tag.strip() for tag in raw.split(",") if tag.strip()]


def relative(path: Path, root: Path) -> str:
    try:
        return path.relative_to(root).as_posix()
    except ValueError:
        return path.as_posix()


def build_report(
    root: Path,
    *,
    text: str,
    source: str = "operator",
    tags: list[str] | None = None,
    confidence: float | None = None,
    captured_by: str = "operator",
    seeds_root: str | None = None,
    output_root: str | None = None,
) -> dict[str, Any]:
    root = root.resolve()
    Library, seed_path = import_genesis_library(root)
    target_seeds_root = Path(seeds_root) if seeds_root else root / "GenesisOS" / "seeds"
    library = Library(seeds_root=target_seeds_root)
    seed = library.capture(
        text=text,
        source=source,
        tags=tags or [],
        confidence=confidence,
        captured_by=captured_by,
    )
    persisted_seed = seed_path(seed, target_seeds_root)
    receipt_root = Path(output_root) if output_root else root / ".aios" / "genesis_seed_captures"
    receipt_path = receipt_root / f"{seed.seed_id}.json"
    report = {
        "schema_version": SCHEMA_VERSION,
        "generated_at": now_iso(),
        "authority": "speculative_only",
        "review_required_before_promotion": True,
        "mutation_policy": "append_seed_only",
        "seed": seed.to_json(),
        "seed_path": relative(persisted_seed, root),
        "receipt_path": relative(receipt_path, root),
        "mutated_files": [relative(persisted_seed, root)],
        "stop_conditions": [
            "no_actual_delete",
            "no_in_place_edit",
            "no_silent_drop",
            "requires_myworld_review_before_promotion",
        ],
    }
    receipt_root.mkdir(parents=True, exist_ok=True)
    receipt_path.write_text(json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return report


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", default=".", help="MyWorld root")
    text = parser.add_mutually_exclusive_group(required=True)
    text.add_argument("--text", help="path to seed text")
    text.add_argument("--inline", help="seed text inline")
    parser.add_argument("--source", default="operator", choices=["operator", "mutator", "branches", "analogy", "critic", "external"])
    parser.add_argument("--tags", default="", help="comma-separated tags")
    parser.add_argument("--confidence", type=float)
    parser.add_argument("--captured-by", default="operator")
    parser.add_argument("--seeds-root")
    parser.add_argument("--output-root")
    parser.add_argument("--json", action="store_true")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    report = build_report(
        Path(args.root),
        text=load_text(args),
        source=args.source,
        tags=split_tags(args.tags),
        confidence=args.confidence,
        captured_by=args.captured_by,
        seeds_root=args.seeds_root,
        output_root=args.output_root,
    )
    if args.json:
        print(json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True))
    else:
        print(
            f"schema={report['schema_version']} seed={report['seed']['seed_id']} "
            f"path={report['seed_path']}"
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
