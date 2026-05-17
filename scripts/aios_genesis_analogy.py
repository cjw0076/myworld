#!/usr/bin/env python3
"""Write top GenesisOS cross-domain analogies for a contract."""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


SCHEMA_VERSION = "aios.genesis_analogy.v1"


def now_iso() -> str:
    return datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds")


def import_genesis_analogy(root: Path):
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
    from genesisos.analogy import Analogy  # type: ignore

    return Analogy


def find_contract(root: Path, contract_id: str) -> Path:
    contract_id = contract_id.upper()
    matches = sorted((root / "docs" / "contracts").glob(f"{contract_id}-*.md"))
    if not matches:
        raise FileNotFoundError(f"contract not found: {contract_id}")
    return matches[0]


def artifact_id(path: Path, text: str) -> str:
    return f"{path.stem}-{hashlib.sha256(text.encode('utf-8')).hexdigest()[:12]}"


def build_report(
    root: Path,
    *,
    contract_id: str,
    top: int = 3,
    output_root: str | None = None,
    write: bool = True,
) -> dict[str, Any]:
    root = root.resolve()
    source_path = find_contract(root, contract_id)
    text = source_path.read_text(encoding="utf-8")
    Analogy = import_genesis_analogy(root)
    matches = Analogy().match(text, top=top)
    view_id = artifact_id(source_path, text)
    analogy_root = Path(output_root) if output_root else root / ".aios" / "genesis_analogies"
    output_path = analogy_root / f"{view_id}.json"
    report = {
        "schema_version": SCHEMA_VERSION,
        "generated_at": now_iso(),
        "authority": "advisory_only",
        "recommendation_only": True,
        "mutation_policy": "no_source_mutation",
        "contract_id": contract_id.upper(),
        "contract_path": source_path.relative_to(root).as_posix(),
        "artifact_id": view_id,
        "output_path": output_path.as_posix(),
        "matches": matches,
        "mutated_files": [],
        "stop_conditions": [
            "no_source_mutation",
            "no_contract_creation",
            "no_external_execution",
        ],
    }
    if write:
        analogy_root.mkdir(parents=True, exist_ok=True)
        output_path.write_text(json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return report


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", default=".", help="MyWorld root")
    parser.add_argument("--contract-id", required=True)
    parser.add_argument("--top", type=int, default=3)
    parser.add_argument("--output-root")
    parser.add_argument("--no-write", action="store_true")
    parser.add_argument("--json", action="store_true")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    report = build_report(
        Path(args.root),
        contract_id=args.contract_id,
        top=args.top,
        output_root=args.output_root,
        write=not args.no_write,
    )
    if args.json:
        print(json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True))
    else:
        print(
            f"schema={report['schema_version']} contract={report['contract_id']} "
            f"matches={len(report['matches']['matches'])}"
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
