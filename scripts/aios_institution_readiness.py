#!/usr/bin/env python3
"""Post-L6 AIOS governance readiness evaluator."""

from __future__ import annotations

import argparse
import json
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


SCHEMA_VERSION = "aios.institution_readiness.v1"
LEVEL_NAMES = {
    6: "L6 repeatable AIOS loop",
    7: "L7 accountable authority",
    8: "L8 resource and capability governance",
    9: "L9 organizational governance",
    10: "L10 sovereign-scale simulation readiness",
}


@dataclass(frozen=True)
class Check:
    level: int
    ok: bool
    evidence: str
    gap: str
    next_action: str


def now_iso() -> str:
    return datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds")


def parse_frontmatter(path: Path) -> dict[str, str]:
    if not path.exists():
        return {}
    text = path.read_text(encoding="utf-8", errors="replace")
    if not text.startswith("---\n"):
        return {}
    end = text.find("\n---\n", 4)
    if end == -1:
        return {}
    data: dict[str, str] = {}
    for line in text[4:end].splitlines():
        key, sep, value = line.partition(":")
        if sep:
            data[key.strip()] = value.strip()
    return data


def load_jsonl(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    rows: list[dict[str, Any]] = []
    for line in path.read_text(encoding="utf-8", errors="replace").splitlines():
        if not line.strip():
            continue
        try:
            rows.append(json.loads(line))
        except json.JSONDecodeError:
            rows.append({"event": "invalid_jsonl"})
    return rows


def contract_statuses(root: Path) -> dict[str, str]:
    statuses: dict[str, str] = {}
    for path in sorted((root / "docs/contracts").glob("ASC-*.md")):
        fm = parse_frontmatter(path)
        contract_id = fm.get("contract_id") or path.stem.split("-", 1)[0]
        statuses[contract_id] = fm.get("status", "unknown")
    return statuses


def result_packets(root: Path) -> list[dict[str, Any]]:
    packets: list[dict[str, Any]] = []
    for path in sorted((root / ".aios/outbox").glob("*/*.json")):
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            payload = {"status": "invalid_json"}
        payload["_path"] = path.relative_to(root).as_posix()
        packets.append(payload)
    return packets


def text_contains(path: Path, terms: list[str]) -> bool:
    if not path.exists():
        return False
    text = path.read_text(encoding="utf-8", errors="replace").lower()
    return all(term.lower() in text for term in terms)


def build_checks(root: Path) -> list[Check]:
    statuses = contract_statuses(root)
    closed = {contract_id for contract_id, status in statuses.items() if status == "closed"}
    dispatch_events = load_jsonl(root / ".aios/state/dispatches.jsonl")
    sent_repos = {str(event.get("repo")) for event in dispatch_events if event.get("event") == "sent"}
    collected_repos = {str(event.get("repo")) for event in dispatch_events if event.get("event") == "collected"}
    packets = result_packets(root)
    passed_packets = [packet for packet in packets if packet.get("status") in {"passed", "done"}]
    ledger = root / "docs/AIOS_AGENT_LEDGER.md"
    governance_model = root / "docs/AIOS_GOVERNANCE_MODEL.md"
    goal = root / "docs/goals/AIOS-GOAL-0001-make-something-great.md"
    web_evidence = root / "docs/evidence/ASC-0031-web-evidence.json"

    return [
        Check(
            6,
            {"ASC-0001", "ASC-0002", "ASC-0003", "ASC-0004", "ASC-0005", "ASC-0006"}.issubset(closed)
            and bool(passed_packets),
            "core L6 contracts and passed result packets exist",
            "base AIOS L6 repeatability is not established",
            "close core AIOS repeatability contracts before governance readiness",
        ),
        Check(
            7,
            text_contains(governance_model, ["authority", "checkpoint", "audit"])
            and text_contains(goal, ["strengthen_governance", "human checkpoints"])
            and ledger.exists(),
            "governance model, goal authority rules, and ledger exist",
            "accountable authority model is incomplete",
            "define authority, checkpoints, and audit ledger rules",
        ),
        Check(
            8,
            {"ASC-0030", "ASC-0031"}.issubset(closed)
            and web_evidence.exists()
            and text_contains(governance_model, ["resource", "risk class", "fallback route"]),
            "web/capability route evidence and resource governance rules exist",
            "resource and capability governance evidence is incomplete",
            "close capability route and evidence contracts with resource rules",
        ),
        Check(
            9,
            {"hivemind", "memoryOS", "CapabilityOS"}.issubset(sent_repos | collected_repos)
            and text_contains(root / "docs/WORKSTREAMS.md", ["codex", "claude", "hive mind", "memoryos", "capabilityos"]),
            "cross-repo workstreams and OS handoff evidence exist",
            "organizational multi-workstream governance is incomplete",
            "record role ownership and cross-repo handoff evidence",
        ),
        Check(
            10,
            text_contains(governance_model, ["legal/safety checkpoints", "does not claim real-world legal sovereignty"])
            and "ASC-0033" in closed,
            "sovereign-scale simulation rules are closed by ASC-0033",
            "sovereign-scale simulation readiness is not yet closed",
            "close ASC-0033 with explicit legal/safety and anti-overclaim rules",
        ),
    ]


def readiness(root: Path) -> dict[str, Any]:
    checks = build_checks(root)
    level = 5
    for check in checks:
        if check.ok:
            level = max(level, check.level)
        else:
            break
    return {
        "schema_version": SCHEMA_VERSION,
        "generated_at": now_iso(),
        "level": level,
        "level_name": LEVEL_NAMES.get(level, "below governance readiness"),
        "ready_for_real_world_authority": False,
        "sovereignty_claimed": False,
        "next_action": next((check.next_action for check in checks if not check.ok), "maintain governance evidence and open next capability contract"),
        "evidence": [check.evidence for check in checks if check.ok],
        "gaps": [check.gap for check in checks if not check.ok],
        "checks": [
            {
                "level": check.level,
                "level_name": LEVEL_NAMES[check.level],
                "ok": check.ok,
                "evidence": check.evidence,
                "gap": check.gap,
                "next_action": check.next_action,
            }
            for check in checks
        ],
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Evaluate post-L6 AIOS governance readiness")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args(argv)
    data = readiness(Path.cwd().resolve())
    if args.json:
        print(json.dumps(data, ensure_ascii=False, indent=2, sort_keys=True))
    else:
        print(f"{data['level_name']} real_world_authority={data['ready_for_real_world_authority']}")
        if data["gaps"]:
            print(f"next: {data['next_action']}")
            for gap in data["gaps"]:
                print(f"- {gap}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
