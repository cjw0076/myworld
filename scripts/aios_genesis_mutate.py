#!/usr/bin/env python3
"""Generate GenesisOS assumption-mutation seeds for a MyWorld contract."""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


SCHEMA_VERSION = "aios.genesis_mutate.v1"


def now_iso() -> str:
    return datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds")


def import_genesis_mutator(root: Path):
    genesis_root = root / "GenesisOS"
    if genesis_root.as_posix() not in sys.path:
        sys.path.insert(0, genesis_root.as_posix())
    loaded = sys.modules.get("genesisos")
    loaded_paths = [Path(path).resolve() for path in getattr(loaded, "__path__", [])] if loaded else []
    if loaded and genesis_root.resolve() not in loaded_paths:
        for name in list(sys.modules):
            if name == "genesisos" or name.startswith("genesisos."):
                del sys.modules[name]
    from genesisos.mutator import mutate_record  # type: ignore

    return mutate_record


def find_contract(root: Path, contract_id: str) -> Path:
    contract_id = contract_id.upper()
    matches = sorted((root / "docs" / "contracts").glob(f"{contract_id}-*.md"))
    if not matches:
        direct = root / "docs" / "contracts" / f"{contract_id}.md"
        if direct.exists():
            return direct
        raise FileNotFoundError(f"contract not found: {contract_id}")
    return matches[0]


def batch_name(contract_id: str, contract_path: Path, batch: str | None = None) -> str:
    if batch:
        return batch
    digest = hashlib.sha256(contract_path.read_bytes()).hexdigest()[:12]
    return f"{contract_id.lower()}-{digest}"


def build_report(
    root: Path,
    *,
    contract_id: str,
    batch: str | None = None,
    write: bool = True,
) -> dict[str, Any]:
    root = root.resolve()
    contract_path = find_contract(root, contract_id)
    mutate_record = import_genesis_mutator(root)
    selected_batch = batch_name(contract_id, contract_path, batch=batch)
    seed_inbox = root / ".aios" / "genesis_seed_inbox" / selected_batch
    payload = mutate_record(contract_path, seeds_root=seed_inbox, write=write)
    return {
        "schema_version": SCHEMA_VERSION,
        "generated_at": now_iso(),
        "authority": "operator_review_required",
        "recommendation_only": True,
        "mutation_policy": "no_contract_or_memory_mutation",
        "contract_id": contract_id.upper(),
        "contract_path": contract_path.relative_to(root).as_posix(),
        "seed_inbox": seed_inbox.relative_to(root).as_posix(),
        "batch": selected_batch,
        "source_record_id": payload["source_record_id"],
        "assumption_count": len(payload["assumptions"]),
        "seed_count": len(payload["seeds"]),
        "seeds": payload["seeds"],
        "writes": payload["writes"],
        "mutated_files": [],
        "stop_conditions": [
            "no_source_mutation",
            "no_contract_creation",
            "operator_review_required_before_promotion",
        ],
    }


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", default=".", help="MyWorld root")
    parser.add_argument("--contract-id", required=True, help="contract id such as ASC-0070")
    parser.add_argument("--batch", help="optional seed inbox batch name")
    parser.add_argument("--no-write", action="store_true", help="print seeds without writing .aios inbox files")
    parser.add_argument("--json", action="store_true")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    report = build_report(
        Path(args.root),
        contract_id=args.contract_id,
        batch=args.batch,
        write=not args.no_write,
    )
    if args.json:
        print(json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True))
    else:
        print(
            f"schema={report['schema_version']} contract={report['contract_id']} "
            f"seeds={report['seed_count']} inbox={report['seed_inbox']}"
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
