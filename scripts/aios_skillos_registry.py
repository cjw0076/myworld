#!/usr/bin/env python3
"""AIOS SkillOS registry.

Recommendation-only registry for local AIOS skills, scripts, and provider
surfaces. It does not execute tools; it emits capability cards with risk,
owner, evidence, and fallback hints so Hive can later execute under contract.
"""

from __future__ import annotations

import argparse
import json
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Final


SCHEMA_VERSION: Final = "aios.skillos_registry.v1"


@dataclass(frozen=True)
class SkillCard:
    id: str
    name: str
    owner_repo: str
    surface_type: str
    risk: str
    domains: tuple[str, ...]
    actions: tuple[str, ...]
    evidence_refs: tuple[str, ...]
    fallback_ids: tuple[str, ...] = ()


CORE_CARDS: Final = (
    SkillCard(
        id="skill_world_readiness_gate",
        name="World readiness gate",
        owner_repo="myworld",
        surface_type="cli",
        risk="low",
        domains=("readiness", "infrastructure", "deployment"),
        actions=("assess", "report", "gap"),
        evidence_refs=("scripts/aios_world_readiness.py", "docs/contracts/ASC-0235-world-deployment-readiness-cli.md"),
    ),
    SkillCard(
        id="skill_credential_broker",
        name="Credential broker",
        owner_repo="myworld",
        surface_type="cli",
        risk="medium",
        domains=("credential", "vault", "privacy", "provider"),
        actions=("status", "request", "receipt"),
        evidence_refs=("scripts/aios_credential_broker.py", "docs/contracts/ASC-0236-credential-broker-boundary.md"),
    ),
    SkillCard(
        id="skill_multi_substrate_review",
        name="Multi-substrate review",
        owner_repo="hivemind",
        surface_type="provider_route",
        risk="medium",
        domains=("provider", "hivemind", "synthesis", "fallback"),
        actions=("fanout", "synthesize", "compare"),
        evidence_refs=("scripts/aios_multi_substrate.py", "scripts/aios_provider.py"),
        fallback_ids=("skill_credential_broker",),
    ),
    SkillCard(
        id="skill_akashic_ingest",
        name="Akashic ingest",
        owner_repo="memoryOS",
        surface_type="memory_route",
        risk="medium",
        domains=("memory", "akashic", "session", "provenance"),
        actions=("ingest", "trace", "draft"),
        evidence_refs=("scripts/aios_ingest_session.py", "scripts/aios_work.py", "scripts/aios_checkpoint.py"),
    ),
    SkillCard(
        id="skill_entropy_audit",
        name="Entropy and convergence audit",
        owner_repo="GenesisOS",
        surface_type="challenge_route",
        risk="low",
        domains=("genesis", "entropy", "seci", "convergence"),
        actions=("audit", "challenge", "branch"),
        evidence_refs=("scripts/aios_convergence_audit.py", "docs/contracts/ASC-0234-world-deployable-aios-readiness-spine.md"),
    ),
    SkillCard(
        id="skill_capability_catalog",
        name="CapabilityOS catalog bridge",
        owner_repo="CapabilityOS",
        surface_type="capability_route",
        risk="low",
        domains=("capability", "skill", "routing", "fallback"),
        actions=("recommend", "audit", "observe"),
        evidence_refs=("CapabilityOS/capabilityos/catalog.py", "CapabilityOS/capabilityos/cli.py"),
    ),
)


def now_iso() -> str:
    return datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds")


def exists_all(root: Path, refs: tuple[str, ...]) -> bool:
    return all((root / ref).exists() for ref in refs)


def card_status(root: Path, card: SkillCard) -> str:
    return "available" if exists_all(root, card.evidence_refs) else "partial"


def registry(root: Path) -> dict:
    cards = []
    for card in CORE_CARDS:
        data = asdict(card)
        data["domains"] = list(card.domains)
        data["actions"] = list(card.actions)
        data["evidence_refs"] = list(card.evidence_refs)
        data["fallback_ids"] = list(card.fallback_ids)
        data["status"] = card_status(root, card)
        data["authority"] = "recommendation_only"
        data["execution_enabled"] = False
        cards.append(data)
    return {
        "schema_version": SCHEMA_VERSION,
        "generated_at": now_iso(),
        "recommendation_only": True,
        "execution_enabled": False,
        "cards": cards,
    }


def score(card: dict, task: str) -> int:
    text = " ".join(
        [card["id"], card["name"], *card["domains"], *card["actions"]]
    ).lower()
    return sum(1 for token in task.lower().split() if token.strip(".,:;") in text)


def recommend(root: Path, task: str, limit: int) -> dict:
    payload = registry(root)
    ranked = []
    for card in payload["cards"]:
        item = dict(card)
        item["score"] = score(card, task)
        ranked.append(item)
    ranked.sort(key=lambda item: (-item["score"], item["risk"], item["id"]))
    return {
        "schema_version": SCHEMA_VERSION,
        "generated_at": payload["generated_at"],
        "recommendation_only": True,
        "execution_enabled": False,
        "task": task,
        "recommendations": ranked[:limit],
        "stop_conditions": (
            "skillos_executes_tool",
            "capabilityos_executes_tool",
            "provider_truth_without_verifier",
        ),
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="AIOS SkillOS recommendation-only registry")
    parser.add_argument("--root", default=".")
    parser.add_argument("--json", action="store_true")
    sub = parser.add_subparsers(dest="command")
    sub.add_parser("list", help="List SkillOS cards")
    rec = sub.add_parser("recommend", help="Recommend SkillOS cards for a task")
    rec.add_argument("--task", required=True)
    rec.add_argument("--limit", type=int, default=3)
    args = parser.parse_args(argv)
    root = Path(args.root).resolve()
    if args.command == "list":
        payload = registry(root)
    elif args.command == "recommend":
        payload = recommend(root, args.task, args.limit)
    else:
        parser.print_help()
        return 2
    if args.json:
        print(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True))
    else:
        rows = payload.get("cards") or payload.get("recommendations") or []
        for row in rows:
            print(f"{row['id']}: {row.get('status', 'recommended')} risk={row['risk']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
