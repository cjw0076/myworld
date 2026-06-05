#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from dataclasses import dataclass
from enum import StrEnum
from typing import Final, assert_never


SCHEMA_VERSION: Final = "aios.boundary_classifier.v1"


class Layer(StrEnum):
    KERNEL = "kernel_primitive"
    EXECUTION = "execution_substrate"
    CAPABILITY = "capability_plugin_route"
    MEMORY = "memory_knowledge_route"
    GENESIS = "genesis_challenge"
    CLARIFICATION = "contract_clarification"


@dataclass(frozen=True, slots=True)
class BoundaryDecision:
    layer: Layer
    owner_repo: str
    substrate_level: str
    surface_type: str
    knowledge_scope: str
    authority: str
    required_receipts: tuple[str, ...]
    stop_conditions: tuple[str, ...]
    next_contract_kind: str


@dataclass(frozen=True, slots=True)
class SignalSet:
    kernel: tuple[str, ...]
    execution: tuple[str, ...]
    capability: tuple[str, ...]
    memory: tuple[str, ...]
    genesis: tuple[str, ...]


SIGNALS: Final = SignalSet(
    kernel=(
        "authority",
        "rollback",
        "syscall",
        "scope check",
        "receipt integrity",
        "privacy",
        "credential boundary",
        "filesystem",
        "sandbox",
    ),
    execution=(
        "process",
        "pid",
        "daemon",
        "daemonize",
        "watcher",
        "scheduler",
        "provider process",
        "long-running",
        "survival",
        "stop receipt",
        "local llm background",
    ),
    capability=(
        "tool",
        "plugin",
        "mcp",
        "api",
        "skill",
        "package",
        "provider choice",
        "fallback",
        "install",
        "browser automation",
    ),
    memory=(
        "research",
        "latest",
        "primary",
        "web",
        "docs",
        "paper",
        "benchmark",
        "history",
        "memory",
        "private context",
        "external knowledge",
        "provider api behavior",
    ),
    genesis=(
        "ambiguous",
        "assumption",
        "assumptions",
        "mutate",
        "counter branch",
        "counter branches",
        "semantic",
        "frame",
        "reframe",
        "final state",
        "prompt-prison",
    ),
)

DECISIONS: Final[dict[Layer, BoundaryDecision]] = {
    Layer.KERNEL: BoundaryDecision(
        layer=Layer.KERNEL,
        owner_repo="myworld",
        substrate_level="primitive",
        surface_type="contract",
        knowledge_scope="local_only",
        authority="execute_with_receipt",
        required_receipts=("policy_gate_receipt", "syscall_receipt", "rollback_receipt"),
        stop_conditions=("kernel_scope_creep", "raw_private_evidence_leak"),
        next_contract_kind="kernel_primitive_contract",
    ),
    Layer.EXECUTION: BoundaryDecision(
        layer=Layer.EXECUTION,
        owner_repo="hivemind",
        substrate_level="runtime",
        surface_type="direct_hive_execution",
        knowledge_scope="local_only",
        authority="execute_with_receipt",
        required_receipts=("run_receipt", "verification_receipt", "stop_or_degraded_receipt"),
        stop_conditions=("provider_truth_without_verifier", "fallback_executes_without_contract"),
        next_contract_kind="hive_execution_contract",
    ),
    Layer.CAPABILITY: BoundaryDecision(
        layer=Layer.CAPABILITY,
        owner_repo="CapabilityOS",
        substrate_level="none",
        surface_type="plugin",
        knowledge_scope="local_only",
        authority="recommendation_only",
        required_receipts=("capability_route", "fallback_plan", "risk_notes"),
        stop_conditions=("plugin_executes_without_contract", "capabilityos_executes_tool"),
        next_contract_kind="capability_route_contract",
    ),
    Layer.MEMORY: BoundaryDecision(
        layer=Layer.MEMORY,
        owner_repo="memoryOS",
        substrate_level="none",
        surface_type="contract",
        knowledge_scope="web_primary_sources",
        authority="speculative_only",
        required_receipts=("source_evidence_receipt", "retrieval_trace", "memory_draft_if_durable"),
        stop_conditions=("memory_auto_accepts_research", "raw_private_evidence_leak"),
        next_contract_kind="knowledge_evidence_contract",
    ),
    Layer.GENESIS: BoundaryDecision(
        layer=Layer.GENESIS,
        owner_repo="GenesisOS",
        substrate_level="none",
        surface_type="contract",
        knowledge_scope="local_only",
        authority="speculative_only",
        required_receipts=("genesis_branch_set", "assumption_mutations", "semantic_alignment_notes"),
        stop_conditions=("provider_truth_without_verifier", "child_repo_implementation_without_dispatch"),
        next_contract_kind="genesis_challenge_contract",
    ),
    Layer.CLARIFICATION: BoundaryDecision(
        layer=Layer.CLARIFICATION,
        owner_repo="myworld",
        substrate_level="none",
        surface_type="contract",
        knowledge_scope="local_only",
        authority="speculative_only",
        required_receipts=("operator_checkpoint", "scope_decision"),
        stop_conditions=("scope_ambiguous", "contract_ambiguous"),
        next_contract_kind="clarification_contract",
    ),
}


def count_matches(question: str, needles: tuple[str, ...]) -> int:
    lowered = question.lower()
    return sum(1 for needle in needles if needle in lowered)


def classify(question: str) -> tuple[BoundaryDecision, tuple[str, ...]]:
    if asks_for_multi_model_review(question):
        return DECISIONS[Layer.CAPABILITY], ()
    scores = {
        Layer.KERNEL: count_matches(question, SIGNALS.kernel),
        Layer.EXECUTION: count_matches(question, SIGNALS.execution),
        Layer.CAPABILITY: count_matches(question, SIGNALS.capability),
        Layer.MEMORY: count_matches(question, SIGNALS.memory),
        Layer.GENESIS: count_matches(question, SIGNALS.genesis),
    }
    priority = (Layer.KERNEL, Layer.EXECUTION, Layer.GENESIS, Layer.CAPABILITY, Layer.MEMORY)
    selected = max(priority, key=lambda layer: (scores[layer], -priority.index(layer)))
    if scores[selected] == 0:
        selected = Layer.CLARIFICATION
    decision = DECISIONS[selected]
    matched = matched_signals(question, selected)
    return decision, matched


def matched_signals(question: str, layer: Layer) -> tuple[str, ...]:
    lowered = question.lower()
    match layer:
        case Layer.KERNEL:
            needles = SIGNALS.kernel
        case Layer.EXECUTION:
            needles = SIGNALS.execution
        case Layer.CAPABILITY:
            needles = SIGNALS.capability
        case Layer.MEMORY:
            needles = SIGNALS.memory
        case Layer.GENESIS:
            needles = SIGNALS.genesis
        case Layer.CLARIFICATION:
            needles = ()
        case unreachable:
            assert_never(unreachable)
    return tuple(needle for needle in needles if needle in lowered)


def payload(question: str) -> dict[str, str | list[str]]:
    decision, matched = classify(question)
    knowledge_scope = decision.knowledge_scope
    if asks_for_multi_model_review(question):
        knowledge_scope = "multi_model_review"
    return {
        "schema_version": SCHEMA_VERSION,
        "question": question,
        "layer": decision.layer.value,
        "owner_repo": decision.owner_repo,
        "substrate_level": decision.substrate_level,
        "surface_type": surface_type_for(decision, question),
        "knowledge_scope": knowledge_scope,
        "authority": decision.authority,
        "required_receipts": list(decision.required_receipts),
        "stop_conditions": list(decision.stop_conditions),
        "matched_signals": list(matched),
        "next_contract_kind": decision.next_contract_kind,
    }


def surface_type_for(decision: BoundaryDecision, question: str) -> str:
    match decision.layer:
        case Layer.CAPABILITY if "mcp" in question.lower():
            return "mcp"
        case Layer.KERNEL | Layer.EXECUTION | Layer.CAPABILITY | Layer.MEMORY | Layer.GENESIS | Layer.CLARIFICATION:
            return decision.surface_type
        case unreachable:
            assert_never(unreachable)


def asks_for_multi_model_review(question: str) -> bool:
    lowered = question.lower()
    model_names = ("claude", "gemini", "codex", "local llm", "all available knowledge")
    return sum(1 for name in model_names if name in lowered) >= 2


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Classify AIOS substrate/surface/knowledge boundary.")
    parser.add_argument("--question", required=True, help="Natural-language boundary question to classify.")
    parser.add_argument("--json", action="store_true", help="Emit JSON. Text output is used otherwise.")
    return parser


def main() -> int:
    args = build_parser().parse_args()
    data = payload(str(args.question))
    if args.json:
        print(json.dumps(data, ensure_ascii=False, indent=2))
    else:
        print(f"{data['layer']} owner={data['owner_repo']} authority={data['authority']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
