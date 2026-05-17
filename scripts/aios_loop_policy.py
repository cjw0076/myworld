#!/usr/bin/env python3
"""Rule-based AIOS loop policy.

The policy ranks task-radar candidates and explains whether the operator loop
should accept, hold, or reject each candidate. It is advisory only: it never
changes contract status and never writes dispatch packets.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


SCHEMA_VERSION = "aios.loop_policy.v1"
DEFAULT_CAPACITY = 4
OPEN_STATUSES = {"accepted", "active", "pending"}
OPERATOR_ONLY_PREFIXES = ("_from_desktop/", "dain/", "minyoung/")
DOMAIN_PRIORITY = {
    "myworld": 0,
    "hivemind": 1,
    "memoryOS": 2,
    "CapabilityOS": 3,
}
DECISION_LIMIT = 100
VERIFIER_WAIT_SECONDS = 15 * 60
VERIFIER_WARN_SECONDS = 60 * 60


@dataclass(frozen=True)
class RadarCandidate:
    candidate_id: str
    score: int
    domain: str
    path: str
    signals: dict[str, int]
    candidate_task: str


@dataclass(frozen=True)
class OpenContract:
    contract_id: str
    path: str
    status: str
    issuer: str
    accepted_at: float
    wait_seconds: int
    priority_reason: str


def now_iso() -> str:
    return datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds")


def parse_signal_counts(raw: str) -> dict[str, int]:
    raw = raw.strip().strip("`")
    if not raw:
        return {}
    counts: dict[str, int] = {}
    for part in raw.split(","):
        key, sep, value = part.partition(":")
        if sep and value.strip().isdigit():
            counts[key.strip()] = int(value.strip())
    return counts


def split_table_row(line: str) -> list[str]:
    stripped = line.strip()
    if not stripped.startswith("|") or not stripped.endswith("|"):
        return []
    return [cell.strip() for cell in stripped.strip("|").split("|")]


def parse_task_radar(path: Path, limit: int = DECISION_LIMIT) -> list[RadarCandidate]:
    if not path.exists():
        raise SystemExit(f"radar not found: {path}")
    candidates: list[RadarCandidate] = []
    in_table = False
    for line in path.read_text(encoding="utf-8").splitlines():
        cells = split_table_row(line)
        if not cells:
            if in_table and candidates:
                break
            continue
        if cells[:5] == ["Score", "Domain", "Path", "Signals", "Candidate Task"]:
            in_table = True
            continue
        if not in_table or cells[0].startswith("---"):
            continue
        if len(cells) < 5:
            continue
        score_text = cells[0].strip()
        if not score_text.isdigit():
            continue
        path_text = cells[2].strip().strip("`")
        candidates.append(
            RadarCandidate(
                candidate_id=f"radar-{len(candidates) + 1:03d}",
                score=int(score_text),
                domain=cells[1],
                path=path_text,
                signals=parse_signal_counts(cells[3]),
                candidate_task=cells[4],
            )
        )
        if len(candidates) >= limit:
            break
    return sorted(candidates, key=sort_key)


def parse_frontmatter(path: Path) -> dict[str, str]:
    text = path.read_text(encoding="utf-8")
    if not text.startswith("---\n"):
        return {}
    end = text.find("\n---\n", 4)
    if end == -1:
        return {}
    data: dict[str, str] = {}
    for raw in text[4:end].splitlines():
        key, sep, value = raw.partition(":")
        if sep:
            data[key.strip()] = value.strip()
    return data


def classify_issuer(frontmatter: dict[str, str]) -> str:
    authority = " ".join(
        str(frontmatter.get(key, ""))
        for key in ("acceptance_authority", "accepted", "origin", "proposed_by")
    ).lower()
    if "founder explicit go" in authority or "founder go" in authority:
        return "founder_go"
    if "verifier" in authority or "claude as verifier" in authority:
        return "verifier"
    if "round_controller" in authority or "autodraft" in authority or "codex_auto" in authority:
        return "codex_auto"
    if "codex" in authority:
        return "codex_auto"
    if "operator" in authority or "claude@myworld" in authority:
        return "operator"
    return "operator"


def accepted_timestamp(path: Path, frontmatter: dict[str, str]) -> float:
    epoch = frontmatter.get("accepted_epoch") or frontmatter.get("accepted_at_epoch")
    if epoch:
        try:
            return float(epoch)
        except ValueError:
            pass
    accepted = frontmatter.get("accepted", "")
    match = re.search(r"(\d{4}-\d{2}-\d{2})(?:[ T](\d{2}:\d{2}(?::\d{2})?))?", accepted)
    if match:
        time_part = match.group(2) or "00:00:00"
        if len(time_part) == 5:
            time_part += ":00"
        try:
            return datetime.fromisoformat(f"{match.group(1)}T{time_part}").replace(tzinfo=timezone.utc).timestamp()
        except ValueError:
            pass
    try:
        return path.stat().st_mtime
    except OSError:
        return datetime.now(timezone.utc).timestamp()


def priority_reason_for(issuer: str, wait_seconds: int) -> str:
    if issuer == "founder_go":
        return "founder_go_immediate"
    if issuer == "verifier" and wait_seconds >= VERIFIER_WAIT_SECONDS:
        return "verifier_wait_threshold_met"
    if issuer == "verifier":
        return "verifier_waiting_below_threshold"
    if issuer == "codex_auto":
        return "codex_auto_fifo"
    return "operator_fifo"


def open_contracts(root: Path, now_ts: float | None = None) -> list[OpenContract]:
    now_value = now_ts if now_ts is not None else datetime.now(timezone.utc).timestamp()
    contracts: list[OpenContract] = []
    for path in sorted((root / "docs" / "contracts").glob("ASC-*.md")):
        frontmatter = parse_frontmatter(path)
        status = frontmatter.get("status", "")
        if status not in OPEN_STATUSES:
            continue
        accepted_at = accepted_timestamp(path, frontmatter)
        wait_seconds = max(0, int(now_value - accepted_at))
        issuer = classify_issuer(frontmatter)
        contract_id = frontmatter.get("contract_id") or path.stem.split("-", 1)[0]
        contracts.append(
            OpenContract(
                contract_id=contract_id,
                path=path.relative_to(root).as_posix() if path.is_relative_to(root) else path.as_posix(),
                status=status,
                issuer=issuer,
                accepted_at=accepted_at,
                wait_seconds=wait_seconds,
                priority_reason=priority_reason_for(issuer, wait_seconds),
            )
        )
    return contracts


def contract_priority(contract: OpenContract) -> tuple[int, float, str]:
    if contract.issuer == "founder_go":
        group = 0
    elif contract.issuer == "verifier" and contract.wait_seconds >= VERIFIER_WAIT_SECONDS:
        group = 1
    elif contract.issuer in {"operator", "codex_auto"}:
        group = 2
    else:
        group = 3
    return (group, contract.accepted_at, contract.contract_id)


def serialize_open_contract(contract: OpenContract) -> dict[str, Any]:
    return {
        "contract_id": contract.contract_id,
        "path": contract.path,
        "status": contract.status,
        "issuer": contract.issuer,
        "wait_seconds": contract.wait_seconds,
        "priority_reason": contract.priority_reason,
    }


def open_contract_count(root: Path) -> int:
    return len(open_contracts(root))


def sort_key(candidate: RadarCandidate) -> tuple[int, int, str]:
    return (
        -candidate.score,
        DOMAIN_PRIORITY.get(candidate.domain, 99),
        candidate.path,
    )


def is_operator_only_path(path: str) -> bool:
    return path.startswith(OPERATOR_ONLY_PREFIXES) or any(f"/{part}/" in f"/{path}" for part in ("dain", "minyoung"))


def resolve_candidate_path(root: Path, candidate_path: str) -> Path:
    path = Path(candidate_path)
    if path.is_absolute():
        return path
    parts = path.parts
    if parts and parts[0] == root.name:
        return root.parent / path
    if parts and parts[0] == "myworld":
        return root.joinpath(*parts[1:])
    return root / path


def closed_contract_source(root: Path, candidate: RadarCandidate) -> bool:
    path = resolve_candidate_path(root, candidate.path)
    if not path.name.startswith("ASC-") or path.suffix != ".md":
        return False
    if "contracts" not in path.parts:
        return False
    if not path.exists():
        return False
    return parse_frontmatter(path).get("status") in {"closed", "superseded"}


def semantic_verdict(candidate: RadarCandidate) -> str:
    if is_operator_only_path(candidate.path):
        return "ambiguous"
    if candidate.domain not in {"myworld", "hivemind", "memoryOS", "CapabilityOS"}:
        return "out_of_scope"
    if candidate.signals.get("capabilityos", 0) >= 8 and candidate.domain != "CapabilityOS":
        return "needs_capability"
    if candidate.signals.get("gap", 0) >= 8 or candidate.signals.get("blocker", 0) >= 6:
        return "needs_context"
    return "executable"


def decide(root: Path, candidate: RadarCandidate, open_count: int, capacity: int) -> tuple[str, str, str]:
    if closed_contract_source(root, candidate):
        return "reject_closed_contract_reference", "closed_contract_reference", "source is already a closed contract evidence document"
    verdict = semantic_verdict(candidate)
    if is_operator_only_path(candidate.path):
        return "hold_for_operator", verdict, "operator-gated privacy or founder archive path"
    if verdict == "out_of_scope":
        return "reject_out_of_scope", verdict, "candidate is outside AIOS-owned repos"
    if verdict == "needs_capability":
        return "hold_for_capability", verdict, "capability gap signal must route through CapabilityOS first"
    if verdict in {"needs_context", "ambiguous"}:
        return "hold_for_operator", verdict, "candidate needs context or operator judgment before acceptance"
    if open_count >= capacity:
        return "hold_for_capacity", verdict, f"open contract count {open_count} is at capacity {capacity}"
    return "accept_now", verdict, "executable candidate and loop capacity is available"


def build_policy(root: Path, radar: Path, capacity: int, limit: int) -> dict[str, Any]:
    candidates = parse_task_radar(radar, limit=min(limit, DECISION_LIMIT))
    open_items = open_contracts(root)
    open_count = len(open_items)
    ordered_open = sorted(open_items, key=contract_priority)
    verifier_waits = [item.wait_seconds for item in open_items if item.issuer == "verifier"]
    verifier_starvation_seconds = max(verifier_waits) if verifier_waits else 0
    priority_inversion_detected = any(
        item.issuer == "verifier" and item.wait_seconds >= VERIFIER_WAIT_SECONDS for item in open_items
    ) and any(item.issuer == "codex_auto" for item in open_items)
    decisions = []
    for candidate in candidates:
        decision, verdict, reason = decide(root, candidate, open_count, capacity)
        decisions.append(
            {
                "contract_candidate_id": candidate.candidate_id,
                "decision": decision,
                "semantic_verdict": verdict,
                "reason": reason,
                "issuer": "radar_candidate",
                "ordering_reason": "radar_score_domain_path",
                "score": candidate.score,
                "sources": [
                    {
                        "path": candidate.path,
                        "domain": candidate.domain,
                        "signals": candidate.signals,
                    }
                ],
            }
        )
    return {
        "schema_version": SCHEMA_VERSION,
        "generated_at": now_iso(),
        "capacity": capacity,
        "open_contract_count": open_count,
        "verifier_starvation_seconds": verifier_starvation_seconds,
        "priority_inversion_detected": priority_inversion_detected,
        "open_contract_order": [serialize_open_contract(item) for item in ordered_open],
        "warnings": [
            {
                "code": "verifier_starvation",
                "severity": "warn",
                "seconds": verifier_starvation_seconds,
            }
        ]
        if verifier_starvation_seconds > VERIFIER_WARN_SECONDS
        else [],
        "decision_limit": min(limit, DECISION_LIMIT),
        "operator_only_prefixes": list(OPERATOR_ONLY_PREFIXES),
        "decisions": decisions,
    }


def write_markdown(path: Path, policy: dict[str, Any]) -> None:
    lines = [
        "# AIOS Loop Policy Snapshot",
        "",
        f"- generated_at: `{policy['generated_at']}`",
        f"- open_contract_count: `{policy['open_contract_count']}`",
        f"- capacity: `{policy['capacity']}`",
        f"- verifier_starvation_seconds: `{policy['verifier_starvation_seconds']}`",
        f"- priority_inversion_detected: `{policy['priority_inversion_detected']}`",
        "",
        "## Open Contract Order",
        "",
        "| Contract | Issuer | Wait Seconds | Reason |",
        "| --- | --- | ---: | --- |",
    ]
    for contract in policy.get("open_contract_order", [])[:20]:
        lines.append(
            f"| {contract['contract_id']} | {contract['issuer']} | {contract['wait_seconds']} | {contract['priority_reason']} |"
        )
    lines.extend(
        [
            "",
            "## Radar Decisions",
            "",
            "| Decision | Verdict | Issuer | Score | Source | Reason |",
            "| --- | --- | --- | ---: | --- | --- |",
        ]
    )
    for decision in policy["decisions"]:
        source = decision["sources"][0]
        lines.append(
            f"| {decision['decision']} | {decision['semantic_verdict']} | {decision['issuer']} | {decision['score']} | `{source['path']}` | {decision['reason']} |"
        )
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Rank AIOS task-radar candidates with an advisory policy")
    parser.add_argument("--root", default=Path.cwd().as_posix(), help="myworld root")
    parser.add_argument("--radar", default="docs/AIOS_TASK_RADAR.md", help="task radar markdown path")
    parser.add_argument("--capacity", type=int, default=DEFAULT_CAPACITY)
    parser.add_argument("--limit", type=int, default=40)
    parser.add_argument("--write", help="write markdown policy snapshot")
    parser.add_argument("--json", action="store_true", help="print JSON")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    root = Path(args.root).resolve()
    if args.capacity < 0:
        print("capacity must be non-negative", file=sys.stderr)
        return 2
    radar = Path(args.radar)
    if not radar.is_absolute():
        radar = root / radar
    policy = build_policy(root, radar, args.capacity, args.limit)
    if args.write:
        write_markdown(Path(args.write), policy)
    if args.json or not args.write:
        print(json.dumps(policy, ensure_ascii=False, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    sys.exit(main())
