#!/usr/bin/env python3
"""Draft and validate AIOS production praxis envelopes."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any


SCHEMA_VERSION = "aios.production_praxis.v1"
REQUIRED_SECTIONS = (
    "memory_context",
    "capability_routes",
    "external_resource_check",
    "genesis_reframe",
    "hive_execution_plan",
    "specialist_assignment",
)


def nonempty(value: Any) -> bool:
    if isinstance(value, str):
        return bool(value.strip())
    if isinstance(value, (list, tuple, dict)):
        return bool(value)
    return value is not None


def section_status(section: Any) -> str:
    if isinstance(section, dict):
        return str(section.get("status") or "").strip()
    return ""


def draft_praxis(task: str) -> dict[str, Any]:
    visual_terms = ("visual", "ui", "dashboard", "image", "asset", "design", "screen", "gui", "control app")
    external_terms = ("api", "mcp", "plugin", "provider", "model", "web", "github", "hugging face", "research")
    lower = task.lower()
    visual_needed = any(term in lower for term in visual_terms)
    external_needed = any(term in lower for term in external_terms) or visual_needed
    return {
        "schema_version": SCHEMA_VERSION,
        "task": task,
        "memory_context": {
            "status": "required",
            "owner": "MemoryOS",
            "ask": "Retrieve accepted decisions, prior failures, provenance, and relevant context packs before planning.",
            "evidence_refs": [],
        },
        "capability_routes": {
            "status": "required",
            "owner": "CapabilityOS",
            "ask": "Recommend provider/tool/API/MCP/plugin/local-model routes with risk, privacy, cost, and fallback notes.",
            "routes": [],
        },
        "external_resource_check": {
            "status": "required" if external_needed else "optional_with_reason",
            "ask": "Use MCP/plugin/web/API primary resources when current external behavior or examples matter.",
            "candidate_tools": [
                "GitHub connector for public repo/PR artifacts",
                "Hugging Face connector for models, papers, datasets, Spaces",
                "web search for current primary docs when connector coverage is insufficient",
            ],
            "evidence_refs": [],
        },
        "genesis_reframe": {
            "status": "required",
            "owner": "GenesisOS",
            "frictions": [
                "Name the actual discomfort or missing affordance before implementation.",
                "Produce at least two alternative frames when the founder intent is broad or creative.",
            ],
            "alternative_frames": [],
        },
        "hive_execution_plan": {
            "status": "required",
            "owner": "Hive Mind",
            "ask": "Turn the routed plan into scoped execution and verification receipts.",
            "verification_gate": "",
        },
        "specialist_assignment": [
            {
                "agent": "codex",
                "strength": "code, tests, multimodal inspection, screenshots, asset generation",
                "job": "Own implementation and visual/multimodal verification when needed." if visual_needed else "Own implementation and tests.",
            },
            {
                "agent": "claude",
                "strength": "large codebase topology and architecture critique",
                "job": "Review dependency structure, integration risk, and policy/lifecycle coherence.",
            },
            {
                "agent": "local-llm",
                "strength": "cheap bounded extraction and draft summarization",
                "job": "Draft or extract low-risk intermediate text; never final acceptance without verifier.",
            },
        ],
        "stop_conditions": [
            "memory_context_missing",
            "capability_route_missing",
            "genesis_reframe_missing",
            "external_resource_skipped",
            "specialist_flattening",
            "hive_gate_missing",
        ],
    }


def validate_praxis(payload: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    if payload.get("schema_version") != SCHEMA_VERSION:
        errors.append("schema_version_invalid")
    if not nonempty(payload.get("task")):
        errors.append("task_missing")
    for section in REQUIRED_SECTIONS:
        if section not in payload:
            errors.append(f"{section}_missing")

    memory = payload.get("memory_context")
    if section_status(memory) not in {"used", "required", "unavailable_with_reason"}:
        errors.append("memory_context_status_invalid")
    if isinstance(memory, dict) and section_status(memory) == "used" and not nonempty(memory.get("evidence_refs")):
        errors.append("memory_context_evidence_missing")

    capability = payload.get("capability_routes")
    if section_status(capability) not in {"used", "required", "unavailable_with_reason"}:
        errors.append("capability_route_status_invalid")
    if isinstance(capability, dict) and section_status(capability) == "used" and not nonempty(capability.get("routes")):
        errors.append("capability_routes_missing")

    external = payload.get("external_resource_check")
    if section_status(external) not in {"used", "required", "optional_with_reason", "unavailable_with_reason"}:
        errors.append("external_resource_status_invalid")
    if isinstance(external, dict) and section_status(external) == "used" and not nonempty(external.get("evidence_refs")):
        errors.append("external_resource_evidence_missing")

    genesis = payload.get("genesis_reframe")
    if section_status(genesis) not in {"used", "required", "unavailable_with_reason"}:
        errors.append("genesis_reframe_status_invalid")
    if isinstance(genesis, dict) and section_status(genesis) == "used":
        if not nonempty(genesis.get("frictions")):
            errors.append("genesis_frictions_missing")
        if not nonempty(genesis.get("alternative_frames")):
            errors.append("genesis_alternatives_missing")

    hive = payload.get("hive_execution_plan")
    if section_status(hive) not in {"planned", "used", "required", "unavailable_with_reason"}:
        errors.append("hive_execution_status_invalid")
    if isinstance(hive, dict) and section_status(hive) in {"planned", "used"} and not nonempty(hive.get("verification_gate")):
        errors.append("hive_gate_missing")

    specialists = payload.get("specialist_assignment")
    if not isinstance(specialists, list) or len(specialists) < 2:
        errors.append("specialist_assignment_too_flat")
    elif len({str(item.get("agent")) for item in specialists if isinstance(item, dict) and item.get("agent")}) < 2:
        errors.append("specialist_assignment_too_flat")
    return errors


def cmd_draft(args: argparse.Namespace) -> int:
    payload = draft_praxis(args.task)
    print(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True))
    return 0


def cmd_validate(args: argparse.Namespace) -> int:
    payload = json.loads(Path(args.path).read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError("praxis file must contain a JSON object")
    errors = validate_praxis(payload)
    print(
        json.dumps(
            {
                "schema_version": "aios.production_praxis.validation.v1",
                "ok": not errors,
                "errors": errors,
            },
            ensure_ascii=False,
            indent=2,
            sort_keys=True,
        )
    )
    return 0 if not errors else 1


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="AIOS production praxis gate")
    sub = parser.add_subparsers(dest="cmd", required=True)
    draft = sub.add_parser("draft")
    draft.add_argument("--task", required=True)
    draft.add_argument("--json", action="store_true")
    draft.set_defaults(func=cmd_draft)
    validate = sub.add_parser("validate")
    validate.add_argument("path")
    validate.add_argument("--json", action="store_true")
    validate.set_defaults(func=cmd_validate)
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        return int(args.func(args))
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        print(str(exc), file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
