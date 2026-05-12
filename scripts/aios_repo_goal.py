#!/usr/bin/env python3
"""Repo-originated goal intake for the AIOS control plane.

This CLI is recommendation-only. It lets a lower repo submit a goal/friction
packet to myworld and lets myworld create a deterministic route packet. It does
not dispatch, execute providers, edit child repos, or accept memory.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from dataclasses import dataclass
from datetime import datetime, timezone
from hashlib import sha256
from pathlib import Path
from typing import Any


GOAL_SCHEMA = "aios.repo_goal.v1"
ROUTE_SCHEMA = "aios.repo_goal_route.v1"
ALLOWED_REPOS = ("myworld", "hivemind", "memoryOS", "CapabilityOS", "uri")
ALLOWED_KINDS = ("goal", "friction", "blocker", "improvement", "observation")
SECRET_PATTERNS = (
    re.compile(r"\bsk-[A-Za-z0-9_-]{12,}"),
    re.compile(r"BEGIN (?:RSA |OPENSSH |EC |)PRIVATE KEY"),
    re.compile(r"(?i)\b(password|secret|token)\s*=\s*\S+"),
)
RAW_PATH_PATTERNS = (
    re.compile(r"(^|[\s/])(raw_exports?|exports?)/", re.IGNORECASE),
    re.compile(r"(^|[\s/])\.env($|[\s./])", re.IGNORECASE),
)


@dataclass(frozen=True)
class RepoGoal:
    goal_id: str
    source_repo: str
    kind: str
    goal: str
    summary: str
    evidence_refs: list[str]
    priority: str
    created_at: str


def now_iso() -> str:
    return datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds")


def stable_suffix(*parts: str) -> str:
    return sha256("\n".join(parts).encode("utf-8")).hexdigest()[:12]


def validate_repo(repo: str) -> None:
    if repo not in ALLOWED_REPOS:
        allowed = ", ".join(ALLOWED_REPOS)
        raise SystemExit(f"repo not allowed: {repo}; allowed: {allowed}")


def validate_public_text(label: str, value: str) -> None:
    for pattern in SECRET_PATTERNS:
        if pattern.search(value):
            raise SystemExit(f"{label} contains secret-like content")
    for pattern in RAW_PATH_PATTERNS:
        if pattern.search(value):
            raise SystemExit(f"{label} contains forbidden raw/private path")


def validate_refs(refs: list[str]) -> None:
    for ref in refs:
        validate_public_text("evidence ref", ref)
        if Path(ref).is_absolute():
            raise SystemExit("evidence ref must be relative or an artifact id")


def parse_refs(values: list[str] | None) -> list[str]:
    refs: list[str] = []
    for value in values or []:
        for part in value.split(","):
            stripped = part.strip()
            if stripped:
                refs.append(stripped)
    validate_refs(refs)
    return refs


def goal_from_args(args: argparse.Namespace) -> RepoGoal:
    validate_repo(args.repo)
    if args.kind not in ALLOWED_KINDS:
        raise SystemExit(f"kind not allowed: {args.kind}")
    validate_public_text("goal", args.goal)
    validate_public_text("summary", args.summary or "")
    refs = parse_refs(args.evidence_ref)
    created_at = now_iso()
    goal_id = f"rg_{created_at.replace(':', '').replace('-', '').split('+')[0]}_{stable_suffix(args.repo, args.goal, args.summary or '')}"
    return RepoGoal(
        goal_id=goal_id,
        source_repo=args.repo,
        kind=args.kind,
        goal=args.goal,
        summary=args.summary or "",
        evidence_refs=refs,
        priority=args.priority,
        created_at=created_at,
    )


def goal_to_json(goal: RepoGoal) -> dict[str, Any]:
    return {
        "schema_version": GOAL_SCHEMA,
        "goal_id": goal.goal_id,
        "source_repo": goal.source_repo,
        "kind": goal.kind,
        "goal": goal.goal,
        "summary": goal.summary,
        "evidence_refs": goal.evidence_refs,
        "priority": goal.priority,
        "created_at": goal.created_at,
        "status": "pending_route",
    }


def write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def load_goal_packet(path: Path) -> dict[str, Any]:
    data = json.loads(path.read_text(encoding="utf-8"))
    if data.get("schema_version") != GOAL_SCHEMA:
        raise SystemExit(f"unsupported goal schema in {path}: {data.get('schema_version')}")
    validate_repo(str(data.get("source_repo") or ""))
    validate_public_text("goal", str(data.get("goal") or ""))
    validate_public_text("summary", str(data.get("summary") or ""))
    validate_refs([str(ref) for ref in data.get("evidence_refs") or []])
    return data


def latest_pending_goal(root: Path, repo: str) -> tuple[Path, dict[str, Any]]:
    inbox = root / ".aios" / "goal_inbox" / repo
    packets = sorted(inbox.glob("*.json"))
    for path in reversed(packets):
        data = load_goal_packet(path)
        if data.get("status") == "pending_route":
            return path, data
    raise SystemExit(f"no pending repo goal packet for {repo}")


def recommended_slug(goal: dict[str, Any]) -> str:
    text = f"{goal.get('kind', '')} {goal.get('goal', '')} {goal.get('summary', '')}".lower()
    if "visual" in text or "ui" in text or "dashboard" in text:
        return "visual_control_application"
    if "install" in text or "mcp" in text or "tool" in text or "api" in text:
        return "capability_provisioning_binding_plan"
    if "memory" in text or "context" in text or "provenance" in text:
        return "memory_feedback_or_provenance_followup"
    if "hive" in text or "execute" in text or "watcher" in text:
        return "hive_execution_loop_followup"
    return "self_resonant_repo_loop_followup"


def build_route(goal: dict[str, Any]) -> dict[str, Any]:
    source_repo = str(goal["source_repo"])
    route_id = f"route_{goal['goal_id']}_{stable_suffix(source_repo, goal['goal'], goal.get('summary', ''))}"
    stop_conditions = [
        "sensitive_source_content_in_goal",
        "unknown_source_repo",
        "route_executes_work",
        "memory_auto_accept",
        "capability_binding_without_review",
        "missing_verification_hint",
    ]
    return {
        "schema_version": ROUTE_SCHEMA,
        "route_id": route_id,
        "goal_id": goal["goal_id"],
        "source_repo": source_repo,
        "kind": goal.get("kind", "goal"),
        "goal": goal["goal"],
        "summary": goal.get("summary", ""),
        "evidence_refs": goal.get("evidence_refs", []),
        "priority": goal.get("priority", "normal"),
        "recommended_contract_slug": recommended_slug(goal),
        "memoryos": {
            "task": f"Build accepted context for {source_repo} goal {goal['goal_id']}.",
            "required_context": [
                "accepted prior decisions",
                "related dispatch/result receipts",
                "open review or provenance questions",
            ],
            "trace_required": True,
        },
        "capabilityos": {
            "task": f"Recommend local-first capabilities and fallbacks for {source_repo} goal {goal['goal_id']}.",
            "recommended_routes": [
                "cap_hivemind_execution_harness",
                "cap_memoryos_context_build",
                "cap_capabilityos_recommendation",
            ],
            "risk_notes": ["recommendation_only", "no_network_by_default", "no_tool_binding_without_contract"],
        },
        "hivemind": {
            "task": f"Plan executable work packet for {source_repo} goal {goal['goal_id']} after MemoryOS and CapabilityOS inputs exist.",
            "execution_owner": source_repo if source_repo in {"hivemind", "memoryOS", "CapabilityOS"} else "contract_assigned_repo",
            "verification_hint": "Use the owning repo's existing tests or a contract-specific dry-run gate.",
        },
        "stop_conditions": stop_conditions,
        "next_action": "draft_or_update_aios_smart_contract",
        "created_at": now_iso(),
    }


def command_submit(args: argparse.Namespace) -> int:
    root = Path(args.root).resolve()
    goal = goal_from_args(args)
    payload = goal_to_json(goal)
    if not args.dry_run:
        path = root / ".aios" / "goal_inbox" / goal.source_repo / f"{goal.goal_id}.json"
        write_json(path, payload)
        payload["path"] = path.relative_to(root).as_posix()
    if args.json:
        print(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True))
    else:
        print(f"{goal.goal_id} {goal.source_repo} {goal.kind}")
    return 0


def command_route(args: argparse.Namespace) -> int:
    root = Path(args.root).resolve()
    validate_repo(args.repo)
    source_path: Path | None = None
    if args.goal:
        validate_public_text("goal", args.goal)
        validate_public_text("summary", args.summary or "")
        packet = goal_to_json(
            RepoGoal(
                goal_id=f"rg_dry_{stable_suffix(args.repo, args.goal, args.summary or '')}",
                source_repo=args.repo,
                kind=args.kind,
                goal=args.goal,
                summary=args.summary or "",
                evidence_refs=parse_refs(args.evidence_ref),
                priority=args.priority,
                created_at=now_iso(),
            )
        )
    elif args.goal_file:
        source_path = Path(args.goal_file)
        packet = load_goal_packet(source_path)
    else:
        source_path, packet = latest_pending_goal(root, args.repo)

    route = build_route(packet)
    if source_path is not None:
        route["source_goal_path"] = source_path.relative_to(root).as_posix() if source_path.is_relative_to(root) else source_path.as_posix()
    if not args.dry_run:
        path = root / ".aios" / "goal_routes" / args.repo / f"{route['route_id']}.json"
        write_json(path, route)
        route["path"] = path.relative_to(root).as_posix()
    if args.json:
        print(json.dumps(route, ensure_ascii=False, indent=2, sort_keys=True))
    else:
        print(f"{route['route_id']} {route['recommended_contract_slug']}")
    return 0


def command_status(args: argparse.Namespace) -> int:
    root = Path(args.root).resolve()
    repos = [args.repo] if args.repo != "all" else list(ALLOWED_REPOS)
    status = {"schema_version": "aios.repo_goal_status.v1", "repos": {}, "root": root.as_posix()}
    for repo in repos:
        validate_repo(repo)
        inbox = root / ".aios" / "goal_inbox" / repo
        routes = root / ".aios" / "goal_routes" / repo
        status["repos"][repo] = {
            "pending_goals": len(list(inbox.glob("*.json"))) if inbox.exists() else 0,
            "routes": len(list(routes.glob("*.json"))) if routes.exists() else 0,
        }
    if args.json:
        print(json.dumps(status, ensure_ascii=False, indent=2, sort_keys=True))
    else:
        for repo, data in status["repos"].items():
            print(f"{repo} pending_goals={data['pending_goals']} routes={data['routes']}")
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", default=".", help="myworld root")
    sub = parser.add_subparsers(dest="command", required=True)

    submit = sub.add_parser("submit", help="submit a repo-originated AIOS goal")
    submit.add_argument("--repo", required=True)
    submit.add_argument("--kind", default="goal", choices=ALLOWED_KINDS)
    submit.add_argument("--goal", required=True)
    submit.add_argument("--summary", default="")
    submit.add_argument("--evidence-ref", action="append")
    submit.add_argument("--priority", default="normal", choices=("low", "normal", "high"))
    submit.add_argument("--dry-run", action="store_true")
    submit.add_argument("--json", action="store_true")
    submit.set_defaults(func=command_submit)

    route = sub.add_parser("route", help="create a route packet for a repo goal")
    route.add_argument("--repo", required=True)
    route.add_argument("--goal")
    route.add_argument("--goal-file")
    route.add_argument("--kind", default="goal", choices=ALLOWED_KINDS)
    route.add_argument("--summary", default="")
    route.add_argument("--evidence-ref", action="append")
    route.add_argument("--priority", default="normal", choices=("low", "normal", "high"))
    route.add_argument("--dry-run", action="store_true")
    route.add_argument("--json", action="store_true")
    route.set_defaults(func=command_route)

    status = sub.add_parser("status", help="summarize repo-goal inbox/route counts")
    status.add_argument("--repo", default="all")
    status.add_argument("--json", action="store_true")
    status.set_defaults(func=command_status)
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    return int(args.func(args))


if __name__ == "__main__":
    raise SystemExit(main())
