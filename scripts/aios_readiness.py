#!/usr/bin/env python3
"""AIOS readiness gate based on docs/AIOS_DEFINITION.md."""

from __future__ import annotations

import argparse
import json
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


LEVEL_NAMES = {
    0: "L0 described",
    1: "L1 contractable",
    2: "L2 dispatchable",
    3: "L3 executable",
    4: "L4 verifiable",
    5: "L5 learnable",
    6: "L6 repeatable",
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
            rows.append({"event": "invalid_jsonl", "raw": line[:120]})
    return rows


def result_packets(root: Path) -> list[dict[str, Any]]:
    packets: list[dict[str, Any]] = []
    for path in sorted((root / ".aios/outbox").glob("*/*.json")):
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            payload = {"status": "invalid_json", "path": path.as_posix()}
        payload["_path"] = path.relative_to(root).as_posix()
        packets.append(payload)
    return packets


def contract_statuses(root: Path) -> dict[str, str]:
    statuses: dict[str, str] = {}
    for path in sorted((root / "docs/contracts").glob("ASC-*.md")):
        fm = parse_frontmatter(path)
        contract_id = fm.get("contract_id") or path.stem.split("-", 1)[0]
        statuses[contract_id] = fm.get("status", "unknown")
    return statuses


def pending_packets(root: Path) -> list[str]:
    pending: list[str] = []
    for packet in sorted((root / ".aios/inbox").glob("*/*.json")):
        repo = packet.parent.name
        try:
            payload = json.loads(packet.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            pending.append(packet.relative_to(root).as_posix())
            continue
        return_to = payload.get("return_to") or f".aios/outbox/{repo}/{payload.get('dispatch_id')}.{repo}.result.json"
        if not (root / str(return_to)).exists():
            pending.append(packet.relative_to(root).as_posix())
    return pending


def build_checks(root: Path) -> list[Check]:
    statuses = contract_statuses(root)
    events = load_jsonl(root / ".aios/state/dispatches.jsonl")
    results = result_packets(root)
    closed = {cid for cid, status in statuses.items() if status == "closed"}
    sent_repos = {str(event.get("repo")) for event in events if event.get("event") == "sent"}
    collected_repos = {str(event.get("repo")) for event in events if event.get("event") == "collected"}
    passed_results = [row for row in results if row.get("status") in {"passed", "done"}]
    pending = pending_packets(root)

    return [
        Check(
            0,
            (root / "docs/AIOS_DEFINITION.md").exists(),
            "docs/AIOS_DEFINITION.md exists",
            "AIOS strict definition is missing",
            "create docs/AIOS_DEFINITION.md",
        ),
        Check(
            1,
            bool(statuses),
            f"{len(statuses)} smart contracts found",
            "no AIOS smart contracts found",
            "draft ASC-0001 or equivalent contract",
        ),
        Check(
            2,
            bool(sent_repos),
            f"dispatch sent events exist for repos: {sorted(sent_repos)}",
            "no sent dispatch events found",
            "run scripts/aios_loop.py once --apply --json for an accepted contract",
        ),
        Check(
            3,
            bool(collected_repos) and bool(results),
            f"result packets collected for repos: {sorted(collected_repos)}",
            "no collected child result packets found",
            "wake a child repo agent or watcher and collect its outbox result",
        ),
        Check(
            4,
            bool(passed_results),
            f"{len(passed_results)} result packets report passed/done",
            "no passing verification result packet found",
            "run the contract verification gate and write a result packet",
        ),
        Check(
            5,
            {"memoryOS", "CapabilityOS", "hivemind"}.issubset(sent_repos | collected_repos)
            and {"ASC-0001", "ASC-0002", "ASC-0005"}.issubset(closed),
            "MemoryOS, CapabilityOS, and Hive evidence exists in closed contracts",
            "memory/capability/execution evidence is incomplete",
            "close contracts covering MemoryOS context, CapabilityOS recommendation, and Hive execution",
        ),
        Check(
            6,
            not pending
            and {"ASC-0001", "ASC-0002", "ASC-0003", "ASC-0004", "ASC-0005", "ASC-0006"}.issubset(closed)
            and (root / "scripts/aios_child_watcher.sh").exists()
            and (root / "scripts/aios_pingpong.sh").exists(),
            "all core contracts closed, no pending packets, watcher scripts present",
            f"repeatable completion is not proven; pending={pending}, closed={sorted(closed)}",
            "close ASC-0006 after readiness verification or resolve pending packets",
        ),
    ]


def readiness(root: Path) -> dict[str, Any]:
    checks = build_checks(root)
    passed = [check.level for check in checks if check.ok]
    level = max(passed) if passed else -1
    first_gap = next((check for check in checks if not check.ok), None)
    return {
        "schema_version": "aios.readiness.v1",
        "generated_at": now_iso(),
        "level": level,
        "level_name": LEVEL_NAMES.get(level, "below L0"),
        "ready": level >= 6,
        "evidence": [check.evidence for check in checks if check.ok],
        "gaps": [check.gap for check in checks if not check.ok],
        "next_action": first_gap.next_action if first_gap else "write docs/AIOS_NORTHSTAR_READY.md",
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
    parser = argparse.ArgumentParser(description="Evaluate AIOS readiness level")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args(argv)
    data = readiness(Path.cwd().resolve())
    if args.json:
        print(json.dumps(data, ensure_ascii=False, indent=2, sort_keys=True))
    else:
        print(f"{data['level_name']} ready={data['ready']}")
        if data["gaps"]:
            print(f"next: {data['next_action']}")
            for gap in data["gaps"]:
                print(f"- {gap}")
    return 0 if data["ready"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
