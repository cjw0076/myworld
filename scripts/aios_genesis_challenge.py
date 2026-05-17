#!/usr/bin/env python3
"""Run the GenesisOS pre-close challenge for a contract."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path


def import_challenge(root: Path):
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
    from genesisos.challenge import run  # type: ignore

    return run


def build_report(root: Path, contract_id: str) -> dict:
    root = root.resolve()
    run = import_challenge(root)
    return run(contract_id, myworld_root=root)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", default=".", help="MyWorld root")
    parser.add_argument("--contract-id", required=True)
    parser.add_argument("--json", action="store_true")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    report = build_report(Path(args.root), args.contract_id)
    if args.json:
        print(json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True))
    else:
        print(
            f"contract={report['contract_id']} risk={report['risk_level']} "
            f"soft_block={report['soft_block']} recommendation={report['recommendation']}"
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
