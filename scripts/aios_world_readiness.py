#!/usr/bin/env python3
"""World-deployment readiness gate for AIOS.

This gate is separate from scripts/aios_completion.py and scripts/aios_readiness.py.
Those prove local self-maintenance and the contract loop. This script checks
whether AIOS has the infrastructure spine for hosted, resumable, isolated,
observable agent-service operation.
"""

from __future__ import annotations

import argparse
import json
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Final


SCHEMA_VERSION: Final = "aios.world_readiness.v1"


@dataclass(frozen=True)
class Axis:
    axis_id: str
    title: str
    owner_repos: tuple[str, ...]
    met_markers: tuple[str, ...]
    partial_markers: tuple[str, ...]
    missing_gap: str
    next_contract: str
    met_policy: str = "any"


@dataclass(frozen=True)
class AxisResult:
    axis_id: str
    title: str
    owner_repos: tuple[str, ...]
    status: str
    evidence: tuple[str, ...]
    gap: str
    next_contract: str


AXES: Final = (
    Axis(
        axis_id="iterative_engine_spine",
        title="Iterative engine spine",
        owner_repos=("myworld", "hivemind"),
        met_markers=("scripts/aios_turn_loop.py", "scripts/aios_agent_turn.py"),
        partial_markers=("scripts/aios_loop.py", "docs/AIOS_ECOSYSTEM_BLUEPRINT.md"),
        missing_gap="model-in-the-loop sample/dispatch/receipt/resample spine is not proven",
        next_contract="ASC-0235",
    ),
    Axis(
        axis_id="durable_work_lineage",
        title="Durable cross-session work lineage",
        owner_repos=("myworld", "memoryOS"),
        met_markers=("scripts/aios_work_lineage.py", "scripts/aios_replay_checkpoint.py", "memoryOS/memoryos/akashic_ledger.py"),
        partial_markers=("scripts/aios_work.py", "scripts/aios_checkpoint.py"),
        missing_gap="work lineage exists only as local pieces, not a replayable cross-device contract",
        next_contract="ASC-0237",
    ),
    Axis(
        axis_id="cloud_execution_isolation",
        title="Cloud-native execution isolation",
        owner_repos=("hivemind",),
        met_markers=("hivemind/hivemind/cloud_isolation.py", "scripts/aios_runtime_isolation.py"),
        partial_markers=("scripts/aios_sandbox.py", "tests/test_aios_sandbox.py"),
        missing_gap="hosted filesystem/process/network/package/quota isolation receipt is not proven",
        next_contract="ASC-0240",
    ),
    Axis(
        axis_id="credential_private_data_boundary",
        title="Credential and private-data boundary",
        owner_repos=("myworld", "CapabilityOS"),
        met_markers=("scripts/aios_credential_broker.py", "docs/contracts/ASC-0236-credential-broker.md"),
        partial_markers=("scripts/aios_vault.py", "tests/test_aios_secret_scan.py"),
        missing_gap="vault exists, but provider credential brokering and denial receipts are not proven",
        next_contract="ASC-0236",
    ),
    Axis(
        axis_id="akashic_observability",
        title="Unified observability and Akashic ledger",
        owner_repos=("memoryOS", "hivemind"),
        met_markers=("scripts/aios_trace_graph.py", "memoryOS/memoryos/akashic_ledger.py"),
        partial_markers=("scripts/aios_multi_substrate.py", "scripts/aios_ingest_session.py"),
        missing_gap="provider runs, tool calls, memory traces, and costs are not one queryable trace graph",
        next_contract="ASC-0237",
    ),
    Axis(
        axis_id="skillos_routing",
        title="CapabilityOS / SkillOS neuromuscular routing",
        owner_repos=("CapabilityOS",),
        met_markers=("CapabilityOS/capabilityos/skillos_registry.py", "scripts/aios_skillos_registry.py"),
        partial_markers=("scripts/aios_boundary_classifier.py", "scripts/aios_provider.py"),
        missing_gap="capabilities are not yet a live risk/cost/success/fallback registry",
        next_contract="ASC-0238",
    ),
    Axis(
        axis_id="genesis_seci_entropy",
        title="Genesis SECI entropy and frozen-knowledge pressure",
        owner_repos=("GenesisOS",),
        met_markers=("GenesisOS/genesisos/seci_entropy.py", "scripts/aios_seci_entropy.py"),
        partial_markers=("scripts/aios_convergence_audit.py", "docs/contracts/ASC-0234-world-deployable-aios-readiness-spine.md"),
        missing_gap="SECI conversion and discomfort injection are not enforced before closeout",
        next_contract="ASC-0239",
    ),
    Axis(
        axis_id="end_user_serving_readiness",
        title="End-user serving interface and runtime",
        owner_repos=("myworld",),
        met_markers=(
            "apps/serving/index.html",
            "scripts/aios_serving_session.py",
            "tests/test_aios_serving_e2e.py",
        ),
        partial_markers=(
            "docs/product/AIOS_END_USER_SERVING_INTERFACE_SPEC.md",
            "docs/product/AIOS_SERVING_INTERFACE_ROUTE_MAP.md",
            "scripts/aios_serving_design_gate.py",
        ),
        missing_gap=(
            "end-user serving surface (apps/serving/), end_user_serving runtime profile, "
            "Product Design gate, and first-workflow browser-test proof are not yet complete"
        ),
        next_contract="ASC-0253",
        met_policy="all",
    ),
)


def now_iso() -> str:
    return datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds")


def marker_exists(root: Path, marker: str) -> bool:
    return (root / marker).exists()


def present_markers(root: Path, markers: tuple[str, ...]) -> tuple[str, ...]:
    return tuple(marker for marker in markers if marker_exists(root, marker))


def assess_axis(root: Path, axis: Axis) -> AxisResult:
    met = present_markers(root, axis.met_markers)
    partial = present_markers(root, axis.partial_markers)
    if axis.met_policy == "all":
        if axis.met_markers and len(met) == len(axis.met_markers):
            status = "met"
            evidence = met
            gap = ""
        elif met or partial:
            status = "partial"
            evidence = tuple(dict.fromkeys((*partial, *met)))
            gap = axis.missing_gap
        else:
            status = "missing"
            evidence = ()
            gap = axis.missing_gap
    elif met:
        status = "met"
        evidence = met
        gap = ""
    elif partial:
        status = "partial"
        evidence = partial
        gap = axis.missing_gap
    else:
        status = "missing"
        evidence = ()
        gap = axis.missing_gap
    return AxisResult(
        axis_id=axis.axis_id,
        title=axis.title,
        owner_repos=axis.owner_repos,
        status=status,
        evidence=evidence,
        gap=gap,
        next_contract=axis.next_contract,
    )


def local_completion_summary(root: Path) -> dict[str, Any]:
    completion = root / "scripts" / "aios_completion.py"
    return {
        "script": "scripts/aios_completion.py",
        "present": completion.exists(),
        "scope": "local self-maintaining completion, not world-deployment readiness",
    }


def readiness(root: Path) -> dict[str, Any]:
    checks = [assess_axis(root, axis) for axis in AXES]
    met_count = sum(1 for check in checks if check.status == "met")
    partial_count = sum(1 for check in checks if check.status == "partial")
    missing_count = sum(1 for check in checks if check.status == "missing")
    ready = met_count == len(checks)
    first_gap = next((check for check in checks if check.status != "met"), None)
    return {
        "schema_version": SCHEMA_VERSION,
        "generated_at": now_iso(),
        "ready_for_world_deployment": ready,
        "met_count": met_count,
        "partial_count": partial_count,
        "missing_count": missing_count,
        "local_completion": local_completion_summary(root),
        "next_action": first_gap.next_contract if first_gap else "maintain world readiness evidence",
        "gaps": [check.gap for check in checks if check.gap],
        "checks": [
            {
                "axis_id": check.axis_id,
                "title": check.title,
                "owner_repos": list(check.owner_repos),
                "status": check.status,
                "evidence": list(check.evidence),
                "gap": check.gap,
                "next_contract": check.next_contract,
            }
            for check in checks
        ],
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Evaluate AIOS world-deployment readiness")
    parser.add_argument("--root", default=".")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args(argv)
    payload = readiness(Path(args.root).resolve())
    if args.json:
        print(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True))
        return 0
    print(f"world_deployment_ready={payload['ready_for_world_deployment']}")
    print(
        f"met={payload['met_count']} partial={payload['partial_count']} "
        f"missing={payload['missing_count']}"
    )
    if payload["gaps"]:
        print(f"next: {payload['next_action']}")
        for gap in payload["gaps"]:
            print(f"- {gap}")
    return 0 if payload["ready_for_world_deployment"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
