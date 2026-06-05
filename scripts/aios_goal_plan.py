from __future__ import annotations

import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from aios_goal_candidates import build_candidates, recommended_candidate
from aios_goal_sources import Goal, load_goal, parse_radar
from aios_goal_stop_conditions import monitor_blocks_goal


SCHEMA_VERSION = "aios.goal_evolution.v1"


def now_iso() -> str:
    return datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds")


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


def build_plan(root: Path, goal_path: Path, radar_path: Path) -> dict[str, Any]:
    goal = load_goal(goal_path)
    radar_rows = parse_radar(radar_path)
    policy = load_policy(root, radar_path)
    readiness = load_readiness(root)
    monitor = load_monitor(root)
    candidates = build_candidates(root, goal, radar_rows, policy)
    recommendation = recommended_candidate(root, goal, candidates)
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
    if monitor_blocks_goal(monitor):
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
