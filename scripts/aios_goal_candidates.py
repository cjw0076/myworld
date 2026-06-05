from __future__ import annotations

import re
from pathlib import Path
from typing import Any

from aios_goal_source_hygiene import (
    is_closed_contract_source,
    is_history_or_index_source,
    is_private_path,
    is_provider_transcript_source,
)
from aios_goal_sources import Goal, RadarRow, resolve_path
HIVE_RADAR_GAP_PATH = "myworld/hivemind/docs/RADAR_GAP_TRIAGE.md"
HIVE_TODO_PATH = "myworld/hivemind/docs/TODO.md"
HIVE_RADAR_TODO_PATTERNS = (
    ("hive-evaluate", ("hive evaluate", "hive subagents review")),
    ("semantic-verifier", ("semantic verifier", "high-risk runs")),
)
GOAL_QUALITY_WEIGHTS = {
    "reduce_user_relay": 10,
    "increase_verified_execution": 8,
    "improve_context_reuse": 8,
    "improve_capability_routing": 7,
    "strengthen_stop_conditions": 7,
    "increase_repeatability": 9,
}

def normalize_phrase(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", value.lower()).strip("-")


def normalize_words(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", " ", value.lower()).strip()


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


def unchecked_todo_items(path: Path) -> list[str]:
    if not path.exists():
        return []
    items: list[str] = []
    for raw in path.read_text(encoding="utf-8", errors="replace").splitlines():
        stripped = raw.strip()
        if not stripped.startswith("- [ ] "):
            continue
        item = stripped.removeprefix("- [ ] ").strip()
        if item:
            items.append(item)
    return items


def matching_hive_todo(root: Path) -> tuple[str, str] | None:
    todo_path = resolve_path(root, HIVE_TODO_PATH)
    for item in unchecked_todo_items(todo_path):
        words = normalize_words(item)
        for slug, phrases in HIVE_RADAR_TODO_PATTERNS:
            if all(normalize_words(phrase) in words for phrase in phrases):
                return slug, item
    return None


def concrete_hive_radar_candidate(root: Path, base: dict[str, Any]) -> dict[str, Any] | None:
    if base.get("path") != HIVE_RADAR_GAP_PATH:
        return None
    match = matching_hive_todo(root)
    if match:
        slug, item = match
        refined = dict(base)
        refined["path"] = f"{HIVE_TODO_PATH}#{slug}"
        refined["candidate_task"] = item.rstrip(".")
        refined["goal_score"] = int(base.get("goal_score") or 0) + 50
        refined["policy_reason"] = "refined from Hive radar-gap source to concrete unchecked Hive TODO"
        refined["alignment_reasons"] = list(base.get("alignment_reasons") or []) + ["concrete_hive_todo"]
        refined["source_path"] = base.get("path")
        return refined
    return None


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
        if is_provider_transcript_source(root, row.path):
            blocked_reasons.append("provider_transcript_source_requires_triage")
        if row.path == HIVE_RADAR_GAP_PATH and matching_hive_todo(root) is None:
            blocked_reasons.append("stale_hive_radar_gap_source")
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
        name, _, description = item.partition(":")
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


def recommended_candidate(root: Path, goal: Goal, candidates: list[dict[str, Any]]) -> dict[str, Any] | None:
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
            return concrete_hive_radar_candidate(root, candidate) or candidate
    fallback = fallback_preferred_candidate(goal)
    if fallback:
        return fallback
    for candidate in candidates:
        if not candidate["blocked"]:
            return concrete_hive_radar_candidate(root, candidate) or candidate
    return None
