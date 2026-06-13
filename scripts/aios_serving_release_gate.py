#!/usr/bin/env python3
"""Assess the ASC-0260 production-serving release slices for AIOS.

This gate is intentionally stricter than the first serving prototype markers.
It checks the owner-bound release slices from ASC-0260 and keeps world readiness
false until the product has user-facing, runtime, memory, routing, observability,
and adversarial-launch evidence.
"""

from __future__ import annotations

import argparse
import json
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Final


SCHEMA_VERSION: Final = "aios.serving_release_gate.v1"
DESIGN_GATE: Final = Path(".aios/serving/design_gate.json")
CONCRETE_VISUAL_TYPES: Final = {"url", "screenshot", "figma", "image", "design_system"}


@dataclass(frozen=True)
class SliceSpec:
    slice_id: str
    title: str
    owner: str
    required_markers: tuple[str, ...]
    partial_markers: tuple[str, ...]
    stop_conditions: tuple[str, ...]
    next_action: str


SLICES: Final = (
    SliceSpec(
        slice_id="product_design_visual_target",
        title="Product Design ideation and concrete visual target",
        owner="myworld/product-design",
        required_markers=("docs/product/AIOS_SERVING_DESIGN_BRIEF.md",),
        partial_markers=(
            "docs/product/AIOS_END_USER_SERVING_INTERFACE_SPEC.md",
            "docs/product/AIOS_SERVING_INTERFACE_ROUTE_MAP.md",
            "scripts/aios_serving_design_gate.py",
        ),
        stop_conditions=("ui_implementation_before_visual_target", "needs_ideation_allows_build"),
        next_action="Product Design ideation, then update .aios/serving/design_gate.json with a concrete visual target",
    ),
    SliceSpec(
        slice_id="serving_ui_prototype",
        title="End-user serving UI prototype",
        owner="myworld",
        required_markers=(
            "apps/serving/index.html",
            "tests/test_aios_serving_e2e.py",
            ".aios/serving/proofs/browser_375.json",
            ".aios/serving/proofs/browser_1280.json",
        ),
        partial_markers=("docs/contracts/ASC-0253-end-user-serving-prototype-scope.md",),
        stop_conditions=("serving_ui_reuses_operator_control_center", "world_readiness_claim_without_browser_proof"),
        next_action="Build and browser-verify separate apps/serving workflow after visual target is accepted",
    ),
    SliceSpec(
        slice_id="runtime_profile",
        title="end_user_serving runtime profile and session boundary",
        owner="myworld/hivemind",
        required_markers=(
            "scripts/aios_serving_session.py",
            "tests/test_aios_serving_session.py",
            "tests/test_aios_dispatch.py",
            "tests/test_aios_round_controller.py",
        ),
        partial_markers=("docs/contracts/ASC-0255-end-user-serving-runtime-session-boundary.md",),
        stop_conditions=("operator_state_exposed_to_user_session", "live_child_execution_without_user_scope"),
        next_action="Prove user/session scoped runtime receipts under end_user_serving",
    ),
    SliceSpec(
        slice_id="hivemind_worker_resume",
        title="Hivemind hosted worker queue/resume",
        owner="hivemind",
        required_markers=(
            "hivemind/hivemind/serving_worker.py",
            "hivemind/tests/test_serving_worker.py",
        ),
        partial_markers=("hivemind/hivemind/cloud_isolation.py",),
        stop_conditions=("duplicate_sensitive_action_on_retry", "cross_user_worker_state_access"),
        next_action="Dispatch owner-bound Hivemind worker queue/resume contract",
    ),
    SliceSpec(
        slice_id="memoryos_user_lifecycle",
        title="MemoryOS per-user memory lifecycle",
        owner="memoryOS",
        required_markers=(
            "memoryOS/memoryos/serving_memory.py",
            "memoryOS/tests/test_serving_memory.py",
        ),
        partial_markers=("memoryOS/memoryos/akashic_ledger.py",),
        stop_conditions=("cross_user_memory_visible", "auto_accept_without_user_review"),
        next_action="Dispatch owner-bound MemoryOS per-user memory lifecycle contract",
    ),
    SliceSpec(
        slice_id="capabilityos_access_routing",
        title="CapabilityOS provider-access/rate/consent routing",
        owner="CapabilityOS",
        required_markers=(
            "CapabilityOS/capabilityos/serving_access.py",
            "CapabilityOS/tests/test_serving_access.py",
        ),
        partial_markers=("CapabilityOS/capabilityos/skillos_registry.py",),
        stop_conditions=("provider_call_without_consent_check", "budget_exceeded_without_refusal_receipt"),
        next_action="Dispatch owner-bound CapabilityOS access/rate/consent routing contract",
    ),
    SliceSpec(
        slice_id="observability_support_redaction",
        title="Observability and support redaction",
        owner="myworld/memoryOS",
        required_markers=(
            "scripts/aios_serving_support.py",
            "tests/test_aios_serving_support.py",
        ),
        partial_markers=("scripts/aios_monitor.py",),
        stop_conditions=("raw_user_content_in_support_view", "operator_audit_exposes_user_memory_body"),
        next_action="Add redacted serving support and incident timeline proof",
    ),
    SliceSpec(
        slice_id="release_readiness_gate",
        title="Production-serving release readiness gate",
        owner="myworld",
        required_markers=(
            "docs/research/AIOS_AGENT_SERVICE_BASELINE_2026-06-13.md",
            "scripts/aios_serving_release_gate.py",
            "tests/test_aios_serving_release_gate.py",
            "scripts/aios_world_readiness.py",
            "tests/test_aios_world_readiness.py",
        ),
        partial_markers=("docs/contracts/ASC-0260-real-user-serving-release-spine.md",),
        stop_conditions=("prototype_claimed_as_world_ready", "infra_markers_sufficient_for_world_ready"),
        next_action="Keep serving release gate wired into world readiness",
    ),
    SliceSpec(
        slice_id="genesis_prelaunch_challenge",
        title="GenesisOS pre-launch adversarial challenge",
        owner="GenesisOS",
        required_markers=(
            "GenesisOS/genesisos/serving_prelaunch.py",
            "GenesisOS/tests/test_serving_prelaunch.py",
            ".aios/serving/proofs/genesis_prelaunch.json",
        ),
        partial_markers=("GenesisOS/genesisos/seci_entropy.py",),
        stop_conditions=("launch_closes_without_adversarial_review", "privacy_risk_unresolved"),
        next_action="Dispatch GenesisOS pre-launch adversarial challenge after release candidate exists",
    ),
)


def now_iso() -> str:
    return datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds")


def marker_exists(root: Path, marker: str) -> bool:
    return (root / marker).exists()


def present_markers(root: Path, markers: tuple[str, ...]) -> list[str]:
    return [marker for marker in markers if marker_exists(root, marker)]


def load_json(path: Path) -> dict[str, Any] | None:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None
    return data if isinstance(data, dict) else None


def design_gate_state(root: Path) -> dict[str, Any]:
    path = root / DESIGN_GATE
    payload = load_json(path)
    if payload is None:
        return {
            "status": "missing",
            "ready": False,
            "build_allowed": False,
            "visual_target_type": "",
            "visual_target_ref": "",
            "next_product_design_step": "",
            "evidence": [],
            "missing": [DESIGN_GATE.as_posix()],
        }
    visual_type = str(payload.get("visual_target_type") or "")
    visual_ref = str(payload.get("visual_target_ref") or "")
    build_allowed = payload.get("build_allowed") is True
    concrete = visual_type in CONCRETE_VISUAL_TYPES and bool(visual_ref.strip())
    ready = concrete and build_allowed and payload.get("next_product_design_step") == "prototype"
    missing: list[str] = []
    if not concrete:
        missing.append("concrete visual target")
    if not build_allowed:
        missing.append("build_allowed=true")
    return {
        "status": "ready" if ready else "needs_ideation" if visual_type == "needs_ideation" else "incomplete",
        "ready": ready,
        "build_allowed": build_allowed,
        "visual_target_type": visual_type,
        "visual_target_ref": visual_ref,
        "next_product_design_step": payload.get("next_product_design_step"),
        "evidence": [DESIGN_GATE.as_posix()],
        "missing": missing,
    }


def assess_slice(root: Path, spec: SliceSpec) -> dict[str, Any]:
    required = present_markers(root, spec.required_markers)
    partial = present_markers(root, spec.partial_markers)
    missing = [marker for marker in spec.required_markers if marker not in required]
    extra: dict[str, Any] = {}
    if spec.slice_id == "product_design_visual_target":
        gate = design_gate_state(root)
        extra["design_gate"] = gate
        required = list(dict.fromkeys([*gate["evidence"], *required]))
        if not gate["ready"]:
            missing = list(dict.fromkeys([*gate["missing"], *missing]))
    status = "met" if not missing else "partial" if required or partial else "missing"
    return {
        "slice_id": spec.slice_id,
        "title": spec.title,
        "owner": spec.owner,
        "status": status,
        "evidence": list(dict.fromkeys([*partial, *required])),
        "missing": missing,
        "stop_conditions": list(spec.stop_conditions),
        "next_action": "" if status == "met" else spec.next_action,
        **extra,
    }


def assess(root: Path) -> dict[str, Any]:
    slices = [assess_slice(root, spec) for spec in SLICES]
    met_count = sum(1 for item in slices if item["status"] == "met")
    partial_count = sum(1 for item in slices if item["status"] == "partial")
    missing_count = sum(1 for item in slices if item["status"] == "missing")
    ready = met_count == len(slices)
    first_gap = next((item for item in slices if item["status"] != "met"), None)
    return {
        "schema_version": SCHEMA_VERSION,
        "generated_at": now_iso(),
        "ready_for_production_serving": ready,
        "met_count": met_count,
        "partial_count": partial_count,
        "missing_count": missing_count,
        "slice_count": len(slices),
        "next_action": first_gap["next_action"] if first_gap else "maintain serving release evidence",
        "slices": slices,
    }


def cmd_assess(args: argparse.Namespace) -> int:
    payload = assess(Path(args.root).resolve())
    if args.json:
        print(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True))
        return 0
    print(f"serving_release_ready={payload['ready_for_production_serving']}")
    print(f"met={payload['met_count']} partial={payload['partial_count']} missing={payload['missing_count']}")
    if payload["next_action"]:
        print(f"next={payload['next_action']}")
    return 0 if payload["ready_for_production_serving"] else 1


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Assess ASC-0260 production-serving release slices")
    sub = parser.add_subparsers(dest="cmd", required=True)
    assess_cmd = sub.add_parser("assess")
    assess_cmd.add_argument("--root", default=".")
    assess_cmd.add_argument("--json", action="store_true")
    assess_cmd.set_defaults(func=cmd_assess)
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
