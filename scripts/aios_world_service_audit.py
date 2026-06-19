#!/usr/bin/env python3
"""Read-only audit of the broad AIOS world-service objective.

This is not another release gate. It consumes the existing readiness gates and
adds objective-fit caveats, evidence-quality notes, and contract-hygiene flags.
"""

from __future__ import annotations

import argparse
import json
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Final

try:
    from scripts.aios_serving_design_gate import assess as assess_design_gate
    from scripts.aios_serving_release_gate import assess as assess_serving_release
    from scripts.aios_world_readiness import readiness as assess_world_readiness
except ModuleNotFoundError:  # pragma: no cover - direct script execution
    from aios_serving_design_gate import assess as assess_design_gate
    from aios_serving_release_gate import assess as assess_serving_release
    from aios_world_readiness import readiness as assess_world_readiness


SCHEMA_VERSION: Final = "aios.world_service_objective_audit.v1"


@dataclass(frozen=True)
class Requirement:
    requirement_id: str
    title: str
    owner_repos: tuple[str, ...]
    evidence_standard: str
    proof_markers: tuple[str, ...]
    partial_markers: tuple[str, ...]
    weak_markers: tuple[str, ...]
    next_action: str


@dataclass(frozen=True)
class RequirementResult:
    requirement_id: str
    title: str
    owner_repos: tuple[str, ...]
    status: str
    evidence: tuple[str, ...]
    missing_proof: tuple[str, ...]
    evidence_standard: str
    next_action: str


REQUIREMENTS: Final = (
    Requirement(
        requirement_id="serving_product_surface",
        title="End-user serving product surface",
        owner_repos=("myworld",),
        evidence_standard="Separate serving UI, e2e test, and browser proofs at mobile and desktop sizes.",
        proof_markers=(
            "apps/serving/index.html",
            "tests/test_aios_serving_e2e.py",
            ".aios/serving/proofs/browser_375.json",
            ".aios/serving/proofs/browser_1280.json",
            "scripts/aios_serving_release_gate.py",
        ),
        partial_markers=("docs/product/AIOS_END_USER_SERVING_INTERFACE_SPEC.md",),
        weak_markers=("docs/contracts/ASC-0253-end-user-serving-prototype-scope.md",),
        next_action="Maintain browser proof and serving-release evidence.",
    ),
    Requirement(
        requirement_id="hosting_packaging_preparation",
        title="Hosting and deployment preparation",
        owner_repos=("myworld", "hivemind"),
        evidence_standard="Deploy manifest, clean archive/release smoke, and launcher/tunnel path exist.",
        proof_markers=(
            "docs/AIOS_DEPLOY_MANIFEST.md",
            "docs/contracts/ASC-0243-hosted-backend-selection-and-release-archive-smoke.md",
            "scripts/aios_packaging_proof.py",
            "scripts/aios_release_archive_proof.py",
        ),
        partial_markers=("scripts/aios_launcher.py",),
        weak_markers=("docs/contracts/ASC-0234-world-deployable-aios-readiness-spine.md",),
        next_action="Add live hosted-scale proof only after operator chooses a deployment target.",
    ),
    Requirement(
        requirement_id="live_public_hosting_proof",
        title="Live public hosting and scale proof",
        owner_repos=("myworld", "hivemind"),
        evidence_standard="A public endpoint or hosted worker proof with retention, scale, and rollback notes.",
        proof_markers=(
            ".aios/serving/proofs/public_url.json",
            "docs/deploy/PRODUCTION_HOSTING_RUNBOOK.md",
        ),
        partial_markers=(
            "docs/AIOS_DEPLOY_MANIFEST.md",
            "scripts/aios_launcher.py",
            "scripts/aios_release_archive_proof.py",
        ),
        weak_markers=("docs/contracts/ASC-0243-hosted-backend-selection-and-release-archive-smoke.md",),
        next_action="Create a hosted-scale proof contract when external deployment authority is granted.",
    ),
    Requirement(
        requirement_id="session_resume_lineage",
        title="Session management, pause/resume, and lineage",
        owner_repos=("myworld", "memoryOS", "hivemind"),
        evidence_standard="Serving session, work resume, checkpoint resume, and Akashic lineage all exist.",
        proof_markers=(
            "scripts/aios_serving_session.py",
            "scripts/aios_work.py",
            "scripts/aios_checkpoint.py",
            "memoryOS/memoryos/akashic_ledger.py",
        ),
        partial_markers=("scripts/aios_chat.py", "scripts/aios_chat_router.py"),
        weak_markers=("docs/contracts/ASC-0237-memoryos-akashic-work-lineage-replay-index.md",),
        next_action="Keep provider-state refs separate from MemoryOS accepted memory.",
    ),
    Requirement(
        requirement_id="filesystem_execution_isolation",
        title="Filesystem, process, network, and package isolation",
        owner_repos=("hivemind", "myworld"),
        evidence_standard="Fail-closed sandbox plus hosted runtime and serving worker isolation proofs.",
        proof_markers=(
            "scripts/aios_sandbox.py",
            "tests/test_aios_sandbox.py",
            "hivemind/hivemind/cloud_isolation.py",
            "hivemind/hivemind/serving_worker.py",
        ),
        partial_markers=("docs/contracts/ASC-0240-hive-hosted-runtime-isolation-receipts.md",),
        weak_markers=("docs/contracts/ASC-0249-build-runtime-isolation-boundary.md",),
        next_action="Require isolation receipts before any provider-managed sandbox becomes authoritative.",
    ),
    Requirement(
        requirement_id="credential_vault_boundary",
        title="Credential vault and private-data boundary",
        owner_repos=("myworld", "CapabilityOS"),
        evidence_standard="Credential values stay out of prompts; grants are opaque refs with denial receipts.",
        proof_markers=(
            "scripts/aios_credential_broker.py",
            "scripts/aios_vault.py",
            "CapabilityOS/capabilityos/credential_grant.py",
            "CapabilityOS/capabilityos/serving_access.py",
            "tests/test_aios_secret_scan.py",
        ),
        partial_markers=("scripts/aios_secret_scan.py",),
        weak_markers=("docs/contracts/ASC-0236-credential-broker-boundary.md",),
        next_action="Route provider credential requests through broker/grant refs only.",
    ),
    Requirement(
        requirement_id="user_private_memory_boundary",
        title="User-private memory and support redaction",
        owner_repos=("memoryOS", "myworld"),
        evidence_standard="Per-user memory lifecycle, review gate, and redacted support timeline exist.",
        proof_markers=(
            "memoryOS/memoryos/serving_memory.py",
            "memoryOS/tests/test_serving_memory.py",
            "scripts/aios_serving_support.py",
            "tests/test_aios_serving_support.py",
        ),
        partial_markers=("docs/product/AIOS_END_USER_SERVING_INTERFACE_SPEC.md",),
        weak_markers=("docs/contracts/ASC-0264-memoryos-serving-memory-lifecycle.md",),
        next_action="Keep raw user content out of support/operator projections.",
    ),
    Requirement(
        requirement_id="akashic_observability_web_absorption",
        title="Akashic observability and web-study absorption",
        owner_repos=("memoryOS", "myworld"),
        evidence_standard="Work lineage, trace graph, web receipts, and draft-first study intake exist.",
        proof_markers=(
            "memoryOS/memoryos/akashic_ledger.py",
            "scripts/aios_akashic.py",
            "scripts/aios_web_research_receipt.py",
            "scripts/aios_web_evidence_memory_review.py",
            "memoryOS/memoryos/dream_agora.py",
        ),
        partial_markers=("scripts/aios_ingest_session.py",),
        weak_markers=("docs/contracts/ASC-0272-memoryos-dream-agora-intake.md",),
        next_action="Unify provider traces and web study receipts without accepting raw bodies as memory.",
    ),
    Requirement(
        requirement_id="cli_log_asset_pool",
        title="Privacy-safe CLI log asset pool",
        owner_repos=("memoryOS", "hivemind", "CapabilityOS"),
        evidence_standard="Synthetic CLI logs validate, assetize, re-import idempotently, and never share raw logs.",
        proof_markers=(
            "memoryOS/memoryos/cli_log_asset.py",
            "memoryOS/tests/test_cli_log_asset.py",
        ),
        partial_markers=(),
        weak_markers=("docs/contracts/ASC-0277-memoryos-cli-log-asset-pool-ledger.md",),
        next_action="Accept and dispatch ASC-0277 to MemoryOS when ready.",
    ),
    Requirement(
        requirement_id="seci_context_token_automation",
        title="SECI, context packing, and token optimization",
        owner_repos=("GenesisOS", "memoryOS", "myworld"),
        evidence_standard="SECI entropy, Gate sleep/context pack, and review proposer exist.",
        proof_markers=(
            "scripts/aios_seci_entropy.py",
            "scripts/aios_gate_sleep.py",
            "scripts/aios_memory_review_proposer.py",
        ),
        partial_markers=("scripts/aios_convergence_audit.py",),
        weak_markers=("docs/contracts/ASC-0239-genesis-seci-entropy-closeout-gate.md",),
        next_action="Bind context packs to serving sessions and eval closeouts.",
    ),
    Requirement(
        requirement_id="genesis_entropy_frozen_knowledge",
        title="Frozen-knowledge prevention and discomfort injection",
        owner_repos=("GenesisOS",),
        evidence_standard="Entropy quota, prelaunch challenge, and convergence audit can block unsafe closure.",
        proof_markers=(
            "GenesisOS/genesisos/entropy_quota.py",
            "GenesisOS/genesisos/serving_prelaunch.py",
            "scripts/aios_convergence_audit.py",
        ),
        partial_markers=("GenesisOS/genesisos/smx_branch.py",),
        weak_markers=("docs/contracts/ASC-0275-genesisos-entropy-quota-enforcement.md",),
        next_action="Require discomfort/counter-branch evidence for major closeouts.",
    ),
    Requirement(
        requirement_id="capabilityos_skillos_neuromuscular",
        title="CapabilityOS and SkillOS neuromuscular routing",
        owner_repos=("CapabilityOS", "myworld"),
        evidence_standard="CapabilityOS owns provider/tool/skill route evidence, risk, and fallback state.",
        proof_markers=(
            "CapabilityOS/capabilityos/skillos_registry.py",
            "scripts/aios_skillos_registry.py",
            "CapabilityOS/capabilityos/provider_blindspot.py",
            "CapabilityOS/capabilityos/serving_access.py",
        ),
        partial_markers=("scripts/aios_boundary_classifier.py", "scripts/aios_provider.py"),
        weak_markers=("docs/contracts/ASC-0238-skillos-recommendation-registry.md",),
        next_action="Move SkillOS registry from MyWorld-only script into CapabilityOS when the route is accepted.",
    ),
    Requirement(
        requirement_id="hivemind_parallel_company_execution",
        title="Hivemind parallel company-style execution",
        owner_repos=("hivemind", "myworld"),
        evidence_standard="Watcher, round controller, serving worker, and workflow projection support parallel work.",
        proof_markers=(
            "scripts/aios_child_watcher.sh",
            "scripts/aios_round_controller.py",
            "hivemind/hivemind/serving_worker.py",
            "hivemind/hivemind/workflow_projection.py",
        ),
        partial_markers=("scripts/aios_loop.py",),
        weak_markers=("docs/contracts/ASC-0263-hivemind-serving-worker-resume.md",),
        next_action="Keep long waits outside single agent turns; use watchers and receipts.",
    ),
    Requirement(
        requirement_id="provider_managed_state_absorption",
        title="Provider-managed state absorption",
        owner_repos=("myworld", "hivemind", "memoryOS", "CapabilityOS", "GenesisOS"),
        evidence_standard="Provider response/conversation/sandbox/trace IDs have an AIOS ownership matrix and hardening result.",
        proof_markers=(
            ".aios/outbox/myworld/asc-0278.myworld.result.json",
        ),
        partial_markers=(),
        weak_markers=(
            "docs/contracts/ASC-0278-openai-agent-surface-absorption.md",
            "docs/research/AIOS_OPENAI_AGENT_SURFACE_DELTA_2026-06-19.md",
        ),
        next_action="Accept ASC-0278 and collect Claude's provider-state ownership matrix.",
    ),
)


def now_iso() -> str:
    return datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds")


def marker_exists(root: Path, marker: str) -> bool:
    return (root / marker).exists()


def present(root: Path, markers: tuple[str, ...]) -> tuple[str, ...]:
    return tuple(marker for marker in markers if marker_exists(root, marker))


def assess_requirement(root: Path, requirement: Requirement) -> RequirementResult:
    proof = present(root, requirement.proof_markers)
    partial = present(root, requirement.partial_markers)
    weak = present(root, requirement.weak_markers)
    missing_proof = tuple(marker for marker in requirement.proof_markers if marker not in proof)

    if requirement.proof_markers and not missing_proof:
        status = "proven"
    elif proof or partial:
        status = "partial"
    elif weak:
        status = "weak"
    else:
        status = "missing"

    evidence = tuple(dict.fromkeys((*proof, *partial, *weak)))
    return RequirementResult(
        requirement_id=requirement.requirement_id,
        title=requirement.title,
        owner_repos=requirement.owner_repos,
        status=status,
        evidence=evidence,
        missing_proof=missing_proof,
        evidence_standard=requirement.evidence_standard,
        next_action=requirement.next_action,
    )


def existing_gate_summary(root: Path) -> dict[str, Any]:
    design = assess_design_gate(root)
    serving = assess_serving_release(root)
    world = assess_world_readiness(root)
    return {
        "serving_design_gate": {
            "schema_version": design.get("schema_version"),
            "ready": design.get("ready") is True,
            "status": design.get("status"),
            "artifact_path": design.get("artifact_path"),
            "next_action": design.get("next_action"),
        },
        "serving_release_gate": {
            "schema_version": serving.get("schema_version"),
            "ready": serving.get("ready_for_production_serving") is True,
            "met_count": serving.get("met_count"),
            "partial_count": serving.get("partial_count"),
            "missing_count": serving.get("missing_count"),
            "next_action": serving.get("next_action"),
        },
        "world_readiness_gate": {
            "schema_version": world.get("schema_version"),
            "ready": world.get("ready_for_world_deployment") is True,
            "met_count": world.get("met_count"),
            "partial_count": world.get("partial_count"),
            "missing_count": world.get("missing_count"),
            "next_action": world.get("next_action"),
        },
    }


def contract_status(root: Path, rel: str) -> str:
    path = root / rel
    try:
        text = path.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return "missing"
    if not text.startswith("---\n"):
        return "unknown"
    end = text.find("\n---\n", 4)
    if end == -1:
        return "unknown"
    for line in text[4:end].splitlines():
        key, _, value = line.partition(":")
        if key.strip() == "status":
            return value.strip() or "unknown"
    return "unknown"


def contract_hygiene(root: Path, gates: dict[str, Any]) -> list[dict[str, str]]:
    notes: list[dict[str, str]] = []
    asc0253 = contract_status(root, "docs/contracts/ASC-0253-end-user-serving-prototype-scope.md")
    if gates["serving_release_gate"]["ready"] and asc0253 == "proposed":
        notes.append(
            {
                "contract_id": "ASC-0253",
                "status": asc0253,
                "severity": "hygiene",
                "note": "Serving UI evidence exists while the prototype-scope contract remains proposed.",
            }
        )
    asc0234 = contract_status(root, "docs/contracts/ASC-0234-world-deployable-aios-readiness-spine.md")
    if gates["world_readiness_gate"]["ready"] and asc0234 == "proposed":
        notes.append(
            {
                "contract_id": "ASC-0234",
                "status": asc0234,
                "severity": "hygiene",
                "note": "World-readiness follow-on gates are green while the original readiness-spine contract remains proposed.",
            }
        )
    return notes


def evidence_quality_notes(root: Path) -> list[dict[str, str]]:
    notes: list[dict[str, str]] = []
    if (root / ".aios/serving/proofs/browser_375.json").exists() and (root / ".aios/serving/proofs/browser_1280.json").exists():
        notes.append(
            {
                "kind": "browser_proof",
                "severity": "caveat",
                "note": "Browser proofs are receipts under .aios; inspect them before treating them as full visual screenshots.",
            }
        )
    if (root / ".aios/serving/proofs/genesis_prelaunch.json").exists():
        notes.append(
            {
                "kind": "genesis_prelaunch",
                "severity": "caveat",
                "note": "Genesis prelaunch proof can preserve warnings even when the release gate is green.",
            }
        )
    if (root / "docs/contracts/ASC-0277-memoryos-cli-log-asset-pool-ledger.md").exists():
        notes.append(
            {
                "kind": "memory_asset_pool",
                "severity": "open_gap",
                "note": "ASC-0277 is a proposed CLI log asset pool contract; it is not implementation proof.",
            }
        )
    if (root / "docs/contracts/ASC-0278-openai-agent-surface-absorption.md").exists():
        notes.append(
            {
                "kind": "provider_state_absorption",
                "severity": "open_gap",
                "note": "ASC-0278 is a proposed provider-state absorption contract until its hardening result is collected.",
            }
        )
    return notes


def audit(root: Path) -> dict[str, Any]:
    rows = [assess_requirement(root, requirement) for requirement in REQUIREMENTS]
    gates = existing_gate_summary(root)
    counts = {status: sum(1 for row in rows if row.status == status) for status in ("proven", "partial", "weak", "missing")}
    gaps = [
        {
            "requirement_id": row.requirement_id,
            "status": row.status,
            "missing_proof": list(row.missing_proof),
            "next_action": row.next_action,
        }
        for row in rows
        if row.status != "proven"
    ]
    hygiene = contract_hygiene(root, gates)
    quality_notes = evidence_quality_notes(root)
    return {
        "schema_version": SCHEMA_VERSION,
        "generated_at": now_iso(),
        "audit_type": "read_only_objective_fit",
        "existing_gates": gates,
        "completion_claim_supported": not gaps and not hygiene,
        "ready_for_goal_completion": not gaps and not hygiene,
        "requirement_count": len(rows),
        "counts": counts,
        "requirements": [
            {
                "requirement_id": row.requirement_id,
                "title": row.title,
                "owner_repos": list(row.owner_repos),
                "status": row.status,
                "evidence": list(row.evidence),
                "missing_proof": list(row.missing_proof),
                "evidence_standard": row.evidence_standard,
                "next_action": row.next_action,
            }
            for row in rows
        ],
        "gaps": gaps,
        "evidence_quality_notes": quality_notes,
        "contract_hygiene": hygiene,
        "next_action": gaps[0]["next_action"] if gaps else "maintain objective evidence",
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Audit AIOS world-service objective coverage")
    parser.add_argument("--root", default=".")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args(argv)

    payload = audit(Path(args.root).resolve())
    if args.json:
        print(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True))
        return 0

    print(f"world_service_goal_complete={payload['completion_claim_supported']}")
    print(
        " ".join(
            f"{name}={payload['counts'][name]}"
            for name in ("proven", "partial", "weak", "missing")
        )
    )
    if payload["gaps"]:
        print(f"next: {payload['next_action']}")
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
