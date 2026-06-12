#!/usr/bin/env python3
"""ASC-0241 live hosted-run proof.

This proof uses Hive's deterministic provider passthrough prepare path so it
does not require provider credentials. It still exercises the real Hive
artifact path that writes a runtime isolation receipt, then projects safe refs
into MemoryOS Akashic lineage.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

import yaml


ROOT = Path(__file__).resolve().parents[1]
HIVE_ROOT = ROOT / "hivemind"
MEMORY_ROOT = ROOT / "memoryOS"

sys.path.insert(0, str(HIVE_ROOT))
sys.path.insert(0, str(MEMORY_ROOT))

from hivemind.cloud_isolation import load_runtime_isolation_receipt, validate_runtime_isolation_receipt  # noqa: E402
from hivemind.harness import create_run  # noqa: E402
from hivemind.provider_passthrough import provider_passthrough  # noqa: E402
from memoryos.akashic_ledger import append_index, build_index  # noqa: E402


SCHEMA_VERSION = "aios.live_hosted_run_proof.v1"


def relative_or_absolute(root: Path, path: Path) -> str:
    try:
        return path.relative_to(root).as_posix()
    except ValueError:
        return path.as_posix()


def run_proof(hive_root: Path, memory_root: Path, *, write_memory: bool = False) -> dict[str, Any]:
    paths = create_run(hive_root, "ASC-0241 live hosted-run proof", project="AIOS")
    result_path = provider_passthrough(
        hive_root,
        "codex",
        ["exec", "--cd", ".", "--sandbox", "read-only", "inspect"],
        run_id=paths.run_id,
        execute=False,
    )
    provider_result = yaml.safe_load(result_path.read_text(encoding="utf-8")) or {}
    runtime_refs = [ref for ref in provider_result.get("artifacts_created", []) if "runtime_isolation/" in str(ref)]
    if len(runtime_refs) != 1:
        raise RuntimeError(f"expected exactly one runtime isolation receipt, got {runtime_refs}")
    runtime_ref = str(runtime_refs[0])
    runtime_receipt_path = hive_root / runtime_ref
    runtime_receipt = load_runtime_isolation_receipt(runtime_receipt_path)
    runtime_issues = validate_runtime_isolation_receipt(runtime_receipt)
    if runtime_issues:
        raise RuntimeError(f"runtime isolation receipt invalid: {runtime_issues}")

    akashic = build_index(
        {
            "work_id": "ASC-0241",
            "goal": "Live hosted-run proof and Akashic projection",
            "status": "paused",
            "session_ids": [paths.run_id],
            "provider_run_ids": [paths.run_id],
            "tool_call_ids": ["hivemind.provider_passthrough"],
            "verification_refs": [
                "python3 scripts/aios_live_hosted_proof.py --json",
                "python -m pytest tests/test_provider_passthrough.py tests/test_cloud_isolation.py -q",
            ],
            "source_artifact_refs": [
                f"hivemind/{runtime_ref}",
                f"hivemind/{relative_or_absolute(hive_root, result_path)}",
            ],
            "next_action": "wire provider/local execution to write runtime receipts without an explicit proof command",
        }
    )
    akashic_receipt = append_index(memory_root, akashic, dry_run=not write_memory)

    return {
        "schema_version": SCHEMA_VERSION,
        "run_id": paths.run_id,
        "provider_result_ref": f"hivemind/{relative_or_absolute(hive_root, result_path)}",
        "runtime_receipt_ref": f"hivemind/{runtime_ref}",
        "runtime_receipt_status": runtime_receipt.get("status"),
        "runtime_network_policy": runtime_receipt.get("network_policy"),
        "credential_refs_only": runtime_receipt.get("credential_refs") == [],
        "akashic_index_id": akashic.id,
        "akashic_index_ref": f"memoryOS/{akashic_receipt['path']}",
        "akashic_written": akashic_receipt["written"],
        "akashic_dry_run": not write_memory,
        "privacy_receipt": {
            "raw_provider_history_copied": False,
            "credential_values_copied": False,
            "runtime_receipt_issues": runtime_issues,
        },
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Run ASC-0241 live hosted proof")
    parser.add_argument("--hive-root", default=HIVE_ROOT.as_posix())
    parser.add_argument("--memory-root", default=MEMORY_ROOT.as_posix())
    parser.add_argument("--write-memory", action="store_true")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args(argv)
    payload = run_proof(Path(args.hive_root).resolve(), Path(args.memory_root).resolve(), write_memory=args.write_memory)
    if args.json:
        print(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True))
    else:
        print(f"run_id={payload['run_id']}")
        print(f"runtime_receipt={payload['runtime_receipt_ref']} status={payload['runtime_receipt_status']}")
        print(f"akashic_index={payload['akashic_index_id']} dry_run={payload['akashic_dry_run']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
