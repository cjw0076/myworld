#!/usr/bin/env python3
"""Goal-level AIOS evolution planner.

This script is recommendation-only. It reads one active goal plus existing
control-plane evidence and emits the next best contract candidate or a hold
reason. It does not edit child repos or dispatch packets.
"""

from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


SCHEMA_VERSION = "aios.goal_evolution.v1"
PRIVATE_PREFIXES = ("_from_desktop/", "dain/", "minyoung/")
HISTORY_SOURCE_NAMES = {"AGENT_WORKLOG.md", "comms_log.md", "COMPACT_HANDOFF.md"}
INDEX_SOURCE_PATHS = {"docs/AIOS_AGENT_LEDGER.md", "docs/contracts/README.md"}
REFERENCE_SOURCE_PATHS = {
    "docs/AIOS_BUILD_METHOD.md",
    "docs/AIOS_DEFINITION.md",
    "docs/AIOS_NORTHSTAR.md",
    "docs/AIOS_SMART_CONTRACT.md",
    "docs/AIOS_WORK_DISPATCH.md",
    "docs/WORKSTREAMS.md",
}
GOAL_QUALITY_WEIGHTS = {
    "reduce_user_relay": 10,
    "increase_verified_execution": 8,
    "improve_context_reuse": 8,
    "improve_capability_routing": 7,
    "strengthen_stop_conditions": 7,
    "increase_repeatability": 9,
}


@dataclass(frozen=True)
class Goal:
    path: Path
    frontmatter: dict[str, str]
    body: str
    quality_function: list[str]
    anti_cheat_checks: list[str]
    preferred_next: list[str]

    @property
    def goal_id(self) -> str:
        return self.frontmatter.get("goal_id") or self.path.stem

    @property
    def status(self) -> str:
        return self.frontmatter.get("status") or "unknown"

    @property
    def slug(self) -> str:
        return self.frontmatter.get("slug") or self.path.stem


@dataclass(frozen=True)
class RadarRow:
    score: int
    domain: str
    path: str
    signals: dict[str, int]
    candidate_task: str


def now_iso() -> str:
    return datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds")


def parse_frontmatter(text: str) -> tuple[dict[str, str], str]:
    if not text.startswith("---\n"):
        return {}, text
    end = text.find("\n---\n", 4)
    if end == -1:
        return {}, text
    data: dict[str, str] = {}
    for raw in text[4:end].splitlines():
        key, sep, value = raw.partition(":")
        if sep:
            data[key.strip()] = value.strip()
    return data, text[end + 5 :]


def section(body: str, heading: str) -> str:
    match = re.search(rf"^##\s+{re.escape(heading)}\s*$", body, flags=re.MULTILINE)
    if not match:
        return ""
    rest = body[match.end() :]
    next_heading = re.search(r"^##\s+", rest, flags=re.MULTILINE)
    return rest[: next_heading.start()] if next_heading else rest


def bullet_items(text: str) -> list[str]:
    items: list[str] = []
    current: str | None = None
    for raw in text.splitlines():
        stripped = raw.strip()
        if not stripped:
            continue
        if stripped.startswith("- "):
            if current:
                items.append(current)
            current = stripped[2:].strip()
        elif current and raw.startswith((" ", "\t")):
            current = f"{current} {stripped}".strip()
        elif current:
            items.append(current)
            current = None
    if current:
        items.append(current)
    return items


def load_goal(path: Path) -> Goal:
    if not path.exists():
        raise SystemExit(f"goal file not found: {path}")
    text = path.read_text(encoding="utf-8")
    frontmatter, body = parse_frontmatter(text)
    goal = Goal(
        path=path,
        frontmatter=frontmatter,
        body=body,
        quality_function=bullet_items(section(body, "Quality Function")),
        anti_cheat_checks=bullet_items(section(body, "Anti-Cheat Checks")),
        preferred_next=bullet_items(section(body, "Preferred Next Improvements")),
    )
    if not goal.quality_function:
        raise SystemExit("goal lacks Quality Function bullets")
    return goal


def parse_signal_counts(raw: str) -> dict[str, int]:
    counts: dict[str, int] = {}
    for part in raw.strip().strip("`").split(","):
        key, sep, value = part.partition(":")
        if sep and value.strip().isdigit():
            counts[key.strip()] = int(value.strip())
    return counts


def split_table_row(line: str) -> list[str]:
    stripped = line.strip()
    if not stripped.startswith("|") or not stripped.endswith("|"):
        return []
    return [cell.strip() for cell in stripped.strip("|").split("|")]


def parse_radar(path: Path) -> list[RadarRow]:
    if not path.exists():
        return []
    rows: list[RadarRow] = []
    in_table = False
    for line in path.read_text(encoding="utf-8").splitlines():
        cells = split_table_row(line)
        if not cells:
            if in_table and rows:
                break
            continue
        if cells[:5] == ["Score", "Domain", "Path", "Signals", "Candidate Task"]:
            in_table = True
            continue
        if not in_table or cells[0].startswith("---") or len(cells) < 5:
            continue
        if not cells[0].isdigit():
            continue
        rows.append(
            RadarRow(
                score=int(cells[0]),
                domain=cells[1],
                path=cells[2].strip("`"),
                signals=parse_signal_counts(cells[3]),
                candidate_task=cells[4],
            )
        )
    return rows


def load_json_command(root: Path, argv: list[str]) -> dict[str, Any]:
    try:
        result = subprocess.run(argv, cwd=root, text=True, capture_output=True, timeout=30, check=False)
    except (OSError, subprocess.SubprocessError) as exc:
        return {"error": str(exc)}
    if result.returncode != 0:
        return {"error": result.stderr.strip() or result.stdout.strip(), "returncode": result.returncode}
    try:
        return json.loads(result.stdout)
    except json.JSONDecodeError as exc:
        return {"error": f"invalid json: {exc}", "returncode": result.returncode}


def load_policy(root: Path, radar: Path) -> dict[str, Any]:
    script = Path(__file__).resolve().parent / "aios_loop_policy.py"
    return load_json_command(root, [sys.executable, script.as_posix(), "--root", root.as_posix(), "--radar", radar.as_posix(), "--json"])


def load_readiness(root: Path) -> dict[str, Any]:
    script = Path(__file__).resolve().parent / "aios_readiness.py"
    return load_json_command(root, [sys.executable, script.as_posix(), "--json"])


def load_monitor(root: Path) -> dict[str, Any]:
    script = Path(__file__).resolve().parent / "aios_monitor.py"
    return load_json_command(root, [sys.executable, script.as_posix(), "assess", "--json"])


def is_private_path(path: str) -> bool:
    return path.startswith(PRIVATE_PREFIXES) or any(f"/{part}/" in f"/{path}" for part in ("dain", "minyoung"))


def resolve_path(root: Path, raw: str) -> Path:
    path = Path(raw)
    if path.is_absolute():
        return path
    parts = path.parts
    if parts and parts[0] == root.name:
        return root.parent / path
    if parts and parts[0] == "myworld":
        return root.joinpath(*parts[1:])
    return root / path


def contract_status(path: Path) -> str | None:
    if not path.exists() or not path.name.startswith("ASC-"):
        return None
    frontmatter, _ = parse_frontmatter(path.read_text(encoding="utf-8", errors="replace"))
    return frontmatter.get("status")


def is_closed_contract_source(root: Path, raw_path: str) -> bool:
    path = resolve_path(root, raw_path)
    return "contracts" in path.parts and contract_status(path) in {"closed", "superseded"}


def is_history_or_index_source(root: Path, raw_path: str) -> str | None:
    path = resolve_path(root, raw_path)
    if path.name in HISTORY_SOURCE_NAMES:
        return "history_source_requires_triage"
    try:
        rel = path.relative_to(root).as_posix()
    except ValueError:
        rel = raw_path
    if rel in INDEX_SOURCE_PATHS:
        return "index_source_requires_triage"
    if rel in REFERENCE_SOURCE_PATHS:
        return "reference_source_requires_contract"
    return None


def normalize_phrase(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", value.lower()).strip("-")


def preferred_key(item: str) -> str:
    return normalize_phrase(item.partition(":")[0])


def doc_contains_preferred(root: Path, row: RadarRow, goal: Goal) -> bool:
    path = resolve_path(root, row.path)
    if (
        not path.exists()
        or is_closed_contract_source(root, row.path)
        or is_private_path(row.path)
        or is_history_or_index_source(root, row.path)
    ):
        return False
    try:
        text = normalize_phrase(path.read_text(encoding="utf-8", errors="replace"))
    except OSError:
        return False
    return any(key and key in text for key in (preferred_key(item) for item in goal.preferred_next))


def goal_alignment(root: Path, goal: Goal, row: RadarRow, policy_decision: str) -> tuple[int, list[str]]:
    score = row.score
    reasons: list[str] = []
    text = normalize_phrase(f"{row.path} {row.candidate_task}")
    for key, weight in GOAL_QUALITY_WEIGHTS.items():
        if key.replace("_", " ") in text or key in text:
            score += weight
            reasons.append(key)
    if "source-read" in text or "source_read" in text or "source read" in text:
        score += 30
        reasons.append("reduces_user_context_relay")
        reasons.append("improves_context_reuse")
    if "watcher" in text:
        score += 20
        reasons.append("increases_repeatability")
        reasons.append("increases_verified_execution")
    if row.signals.get("verify", 0):
        score += min(row.signals["verify"], 6)
        reasons.append("verification_signal")
    if row.signals.get("capabilityos", 0) >= 8:
        score -= 15
        reasons.append("capability_dependency")
    if policy_decision == "accept_now":
        score += 10
        reasons.append("policy_accept_now")
    for item in goal.preferred_next:
        key = preferred_key(item)
        if key and key in text:
            score += 80
            reasons.append("goal_preferred_next")
    if doc_contains_preferred(root, row, goal):
        score += 200
        reasons.append("goal_preferred_doc_signal")
    return score, reasons


def policy_by_path(policy: dict[str, Any]) -> dict[str, dict[str, Any]]:
    result = {}
    for decision in policy.get("decisions") or []:
        sources = decision.get("sources") or []
        if sources:
            result[str(sources[0].get("path"))] = decision
    return result


def build_candidates(root: Path, goal: Goal, radar_rows: list[RadarRow], policy: dict[str, Any]) -> list[dict[str, Any]]:
    decisions = policy_by_path(policy)
    candidates: list[dict[str, Any]] = []
    for row in radar_rows:
        decision = decisions.get(row.path, {})
        policy_decision = decision.get("decision") or "unknown"
        hold_reason = decision.get("reason") or ""
        blocked_reasons: list[str] = []
        if is_closed_contract_source(root, row.path):
            blocked_reasons.append("closed_contract_source")
        if is_private_path(row.path):
            blocked_reasons.append("private_or_operator_gated_path")
        history_reason = is_history_or_index_source(root, row.path)
        if history_reason:
            blocked_reasons.append(history_reason)
        if policy_decision.startswith("hold_") or policy_decision.startswith("reject_"):
            blocked_reasons.append(policy_decision)
        aligned_score, reasons = goal_alignment(root, goal, row, policy_decision)
        candidates.append(
            {
                "path": row.path,
                "domain": row.domain,
                "radar_score": row.score,
                "goal_score": aligned_score,
                "policy_decision": policy_decision,
                "policy_reason": hold_reason,
                "candidate_task": row.candidate_task,
                "signals": row.signals,
                "alignment_reasons": reasons,
                "blocked": bool(blocked_reasons),
                "blocked_reasons": blocked_reasons,
            }
        )
    candidates.sort(key=lambda item: (-int(item["goal_score"]), item["path"]))
    return candidates


def fallback_preferred_candidate(goal: Goal) -> dict[str, Any] | None:
    for item in goal.preferred_next:
        name, sep, description = item.partition(":")
        slug = name.strip()
        if not slug:
            continue
        return {
            "path": f"goal:{slug}",
            "domain": "myworld",
            "radar_score": 0,
            "goal_score": 100,
            "policy_decision": "goal_preferred",
            "policy_reason": "listed in active goal Preferred Next Improvements",
            "candidate_task": description.strip() or slug.replace("_", " "),
            "signals": {},
            "alignment_reasons": ["goal_preferred_next"],
            "blocked": False,
            "blocked_reasons": [],
        }
    return None


def recommended_candidate(goal: Goal, candidates: list[dict[str, Any]]) -> dict[str, Any] | None:
    preferred_reason_prefixes = (
        "goal_preferred",
        "reduce_",
        "increase_",
        "improve_",
        "strengthen_",
        "reduces_",
        "increases_",
        "improves_",
        "strengthens_",
    )
    for candidate in candidates:
        if not candidate["blocked"] and any(
            str(reason).startswith(preferred_reason_prefixes)
            for reason in candidate.get("alignment_reasons") or []
        ):
            return candidate
    fallback = fallback_preferred_candidate(goal)
    if fallback:
        return fallback
    for candidate in candidates:
        if not candidate["blocked"]:
            return candidate
    return None


def build_plan(root: Path, goal_path: Path, radar_path: Path) -> dict[str, Any]:
    goal = load_goal(goal_path)
    radar_rows = parse_radar(radar_path)
    policy = load_policy(root, radar_path)
    readiness = load_readiness(root)
    monitor = load_monitor(root)
    candidates = build_candidates(root, goal, radar_rows, policy)
    recommendation = recommended_candidate(goal, candidates)
    return {
        "schema_version": SCHEMA_VERSION,
        "generated_at": now_iso(),
        "goal": {
            "goal_id": goal.goal_id,
            "slug": goal.slug,
            "status": goal.status,
            "path": goal.path.as_posix(),
            "quality_function": goal.quality_function,
            "anti_cheat_checks": goal.anti_cheat_checks,
        },
        "evidence": {
            "monitor_health": monitor.get("health"),
            "monitor_findings": len(monitor.get("findings") or []),
            "readiness_level": readiness.get("level"),
            "readiness_level_name": readiness.get("level_name"),
            "policy_generated_at": policy.get("generated_at"),
            "policy_decision_count": len(policy.get("decisions") or []),
            "radar_candidate_count": len(radar_rows),
        },
        "recommendation": recommendation,
        "top_candidates": candidates[:10],
        "stop_conditions": stop_conditions(goal, monitor, readiness, recommendation),
    }


def stop_conditions(goal: Goal, monitor: dict[str, Any], readiness: dict[str, Any], recommendation: dict[str, Any] | None) -> list[str]:
    stops: list[str] = []
    if goal.status != "active":
        stops.append("goal_not_active")
    if not goal.quality_function:
        stops.append("no_quality_function")
    if monitor.get("health") not in {None, "clear"}:
        stops.append("monitor_not_clear")
    if readiness.get("ready") is False:
        stops.append("readiness_not_ready")
    if recommendation is None:
        stops.append("no_recommendation")
    elif recommendation.get("blocked"):
        stops.append("recommended_candidate_blocked")
    return stops


def write_markdown(path: Path, plan: dict[str, Any]) -> None:
    goal = plan["goal"]
    rec = plan.get("recommendation") or {}
    lines = [
        "# AIOS Goal Evolution Plan",
        "",
        f"- generated_at: `{plan['generated_at']}`",
        f"- goal_id: `{goal['goal_id']}`",
        f"- goal_status: `{goal['status']}`",
        f"- monitor_health: `{plan['evidence'].get('monitor_health')}`",
        f"- readiness: `{plan['evidence'].get('readiness_level_name')}`",
        "",
        "## Recommendation",
        "",
        f"- path: `{rec.get('path')}`",
        f"- domain: `{rec.get('domain')}`",
        f"- goal_score: `{rec.get('goal_score')}`",
        f"- policy_decision: `{rec.get('policy_decision')}`",
        f"- task: {rec.get('candidate_task')}",
        f"- alignment_reasons: `{', '.join(rec.get('alignment_reasons') or [])}`",
        f"- blocked_reasons: `{', '.join(rec.get('blocked_reasons') or [])}`",
        "",
        "## Top Candidates",
        "",
        "| Goal Score | Domain | Path | Policy | Blocked |",
        "| ---: | --- | --- | --- | --- |",
    ]
    for candidate in plan.get("top_candidates") or []:
        lines.append(
            f"| {candidate['goal_score']} | {candidate['domain']} | `{candidate['path']}` | {candidate['policy_decision']} | {candidate['blocked']} |"
        )
    lines.extend(["", "## Stop Conditions", ""])
    stops = plan.get("stop_conditions") or []
    if stops:
        for stop in stops:
            lines.append(f"- {stop}")
    else:
        lines.append("- none")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Plan the next AIOS contract from one active goal")
    sub = parser.add_subparsers(dest="cmd", required=True)
    plan = sub.add_parser("plan", help="build a goal evolution plan")
    plan.add_argument("--root", default=Path.cwd().as_posix(), help="myworld root")
    plan.add_argument("--goal", required=True, help="goal markdown file")
    plan.add_argument("--radar", default="docs/AIOS_TASK_RADAR.md", help="task radar markdown")
    plan.add_argument("--write", help="write markdown plan")
    plan.add_argument("--json", action="store_true", help="print JSON")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    root = Path(args.root).resolve()
    goal_path = Path(args.goal)
    if not goal_path.is_absolute():
        goal_path = root / goal_path
    radar_path = Path(args.radar)
    if not radar_path.is_absolute():
        radar_path = root / radar_path
    plan = build_plan(root, goal_path, radar_path)
    if args.write:
        write_markdown(root / args.write if not Path(args.write).is_absolute() else Path(args.write), plan)
    if args.json or not args.write:
        print(json.dumps(plan, ensure_ascii=False, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    sys.exit(main())
