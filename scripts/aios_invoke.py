#!/usr/bin/env python3
"""Build a plan-only AIOS invocation artifact set.

The wrapper is deliberately conservative. It may call local recommendation or
planning CLIs, but it does not edit child repo source files and it never grants
execution authority by itself.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

try:
    import aios_few_shot_injector
except ModuleNotFoundError:  # imported by tests via importlib spec
    from scripts import aios_few_shot_injector  # type: ignore


RECEIPT_SCHEMA = "aios.invocation_receipt.v1"
GOAL_SCHEMA = "aios.invocation_goal.v1"
CONTEXT_REQUEST_SCHEMA = "aios.memory_context_request.v1"
HIVE_PLAN_SCHEMA = "aios.hive_execution_plan.v1"
PACKETS_SCHEMA = "aios.dispatch_packets.v1"
SESSION_ENVELOPE_SCHEMA = "aios.session_envelope.v1"
OS_ROLES = ("genesis", "memory", "capability", "hive")


def now_iso() -> str:
    return datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds")


def stable_hash(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def canonical_json(data: Any) -> str:
    return json.dumps(data, ensure_ascii=False, indent=2, sort_keys=True)


def write_json(path: Path, data: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(canonical_json(data) + "\n", encoding="utf-8")


def write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def relative(path: Path, root: Path) -> str:
    try:
        return path.resolve().relative_to(root.resolve()).as_posix()
    except ValueError:
        return path.resolve().as_posix()


def resolve_output_dir(root: Path, goal: str, write: str | None) -> Path:
    base = (root / ".aios" / "invocations").resolve()
    if write:
        candidate = (root / write).resolve() if not Path(write).is_absolute() else Path(write).resolve()
    else:
        stamp = datetime.now(timezone.utc).astimezone().strftime("%Y%m%dT%H%M%S")
        candidate = base / f"inv-{stable_hash(goal)[:12]}-{stamp}"
    try:
        candidate.relative_to(base)
    except ValueError as exc:
        raise SystemExit(f"invocation output must stay under {base}") from exc
    return candidate


def run_json(command: list[str], *, cwd: Path, timeout: int = 60) -> tuple[str, dict[str, Any] | None, str]:
    try:
        result = subprocess.run(
            command,
            cwd=cwd,
            text=True,
            capture_output=True,
            timeout=timeout,
            check=False,
        )
    except (OSError, subprocess.TimeoutExpired) as exc:
        return "failed", None, str(exc)
    if result.returncode != 0:
        return "failed", None, (result.stderr or result.stdout)[-1000:]
    try:
        parsed = json.loads(result.stdout)
    except json.JSONDecodeError as exc:
        return "failed", None, f"json_parse_failed: {exc}"
    if not isinstance(parsed, dict):
        return "failed", None, "json_payload_not_object"
    return "passed", parsed, ""


def genesis_artifact(root: Path, goal: str) -> tuple[str, dict[str, Any], list[str]]:
    genesis_root = root / "GenesisOS"
    command = [sys.executable, "-m", "genesisos.cli", "diverge", "--goal", goal, "--json"]
    status, payload, reason = run_json(command, cwd=genesis_root) if (genesis_root / "genesisos" / "cli.py").exists() else ("failed", None, "GenesisOS CLI missing")
    stops: list[str] = []
    if status != "passed" or not payload:
        stops.append("missing_genesis_artifact")
        payload = {
            "schema_version": "genesisos.v1",
            "kind": "divergence",
            "status": "degraded",
            "goal": goal,
            "authority": "speculative_only",
            "branches": [],
            "reason": reason,
        }
        status = "failed"
    elif payload.get("authority") != "speculative_only" or len(payload.get("branches") or []) != 5:
        stops.append("missing_genesis_artifact")
        status = "failed"
    return status, payload, stops


def memory_artifacts(root: Path, goal: str) -> tuple[str, dict[str, Any], str, list[str]]:
    request = {
        "schema_version": CONTEXT_REQUEST_SCHEMA,
        "goal_hash": stable_hash(goal),
        "task": goal,
        "for_role": "hive",
        "project": "AIOS",
        "requested_outputs": ["context_pack.md", "retrieval_trace"],
        "auto_accept": False,
    }
    memory_root = root / "memoryOS"
    command = [
        sys.executable,
        "-m",
        "memoryos.cli",
        "--root",
        ".",
        "context",
        "build",
        "--task",
        goal,
        "--for",
        "hive",
        "--project",
        "AIOS",
        "--json",
    ]
    status, payload, reason = run_json(command, cwd=memory_root, timeout=90) if (memory_root / "memoryos" / "cli.py").exists() else ("failed", None, "MemoryOS CLI missing")
    stops: list[str] = []
    if status == "passed" and payload:
        selected_ids = [
            str(item.get("id"))
            for key in ("decisions", "constraints", "open_questions", "recent_actions", "other")
            for item in (payload.get(key) or [])
            if isinstance(item, dict) and item.get("id")
        ]
        markdown = "\n".join(
            [
                "# Context pack",
                "",
                f"Task: {goal}",
                "Role: hive",
                "",
                "## Source",
                "",
                "- MemoryOS context build returned JSON.",
                f"- selected_memory_ids: {json.dumps(selected_ids, ensure_ascii=False)}",
                f"- trace_id: {payload.get('retrieval_trace_id') or payload.get('trace_id') or ''}",
                "",
            ]
        )
        return "passed", request, markdown, stops
    markdown = "\n".join(
        [
            "# Context pack",
            "",
            f"Task: {goal}",
            "Role: hive",
            "",
            "## Degraded",
            "",
            "- MemoryOS context build is unavailable or returned no JSON.",
            f"- reason: {reason}",
            "- auto_accept: false",
            "",
        ]
    )
    return "degraded", request, markdown, stops


def capability_artifact(root: Path, goal: str) -> tuple[str, dict[str, Any], list[str]]:
    capability_root = root / "CapabilityOS"
    command = [sys.executable, "-m", "capabilityos.cli", "recommend", "--task", goal, "--json"]
    status, payload, reason = run_json(command, cwd=capability_root) if (capability_root / "capabilityos" / "cli.py").exists() else ("failed", None, "CapabilityOS CLI missing")
    stops: list[str] = []
    if status != "passed" or not payload:
        payload = {
            "contract": "capabilityos.recommendations.v1",
            "status": "degraded",
            "task": goal,
            "recommendation_only": True,
            "recommendations": [],
            "risk_notes": [reason],
        }
        return "degraded", payload, stops
    payload["recommendation_only"] = bool(payload.get("recommendation_only", True))
    if payload.get("recommendation_only") is not True:
        stops.append("capability_executes_tool")
        status = "failed"
    for row in payload.get("recommendations") or []:
        if isinstance(row, dict) and row.get("executes_tools") is True:
            stops.append("capability_executes_tool")
            status = "failed"
    return status, payload, stops


def hive_plan(root: Path, goal: str, *, contract_id: str | None, plan_only: bool) -> tuple[str, dict[str, Any], list[str]]:
    execute_allowed = bool(contract_id and not plan_only)
    user_patterns = aios_few_shot_injector.summarize_patterns(root, user="founder", limit=3)
    plan = {
        "schema_version": HIVE_PLAN_SCHEMA,
        "goal_hash": stable_hash(goal),
        "owner_repo": "hivemind",
        "candidate_worker": "hive.provider_loop",
        "candidate_provider": "capabilityos_recommended",
        "verification_gate": [
            "python -m unittest discover -s tests -p 'test_aios_*.py'",
            "python scripts/aios_monitor.py assess --json",
        ],
        "stop_conditions": [
            "missing_required_artifact",
            "scope_violation",
            "provider_backpressure",
            "verification_gate_failed",
        ],
        "plan_only": plan_only,
        "contract_id": contract_id,
        "execute_allowed": execute_allowed,
        "user_patterns": {
            "status": "draft",
            "user": "founder",
            "patterns": user_patterns,
        },
    }
    stops = [] if contract_id or plan_only else ["hive_executes_without_contract"]
    return "passed", plan, stops if execute_allowed else []


def dispatch_packets(goal: str) -> dict[str, Any]:
    return {
        "schema_version": PACKETS_SCHEMA,
        "goal_hash": stable_hash(goal),
        "status": "draft",
        "packets": [
            {"target_repo": "GenesisOS", "role": "divergence", "mode": "local_cli"},
            {"target_repo": "memoryOS", "role": "context", "mode": "degraded_allowed"},
            {"target_repo": "CapabilityOS", "role": "route", "mode": "recommendation_only"},
            {"target_repo": "hivemind", "role": "execution_plan", "mode": "plan_only"},
        ],
    }


def build_session_envelope(
    *,
    invocation_id: str,
    goal: str,
    goal_hash: str,
    created_at: str,
    plan_only: bool,
    role_statuses: dict[str, str],
    artifact_paths: dict[str, str],
    stop_conditions: list[str],
    contract_id: str | None,
) -> dict[str, Any]:
    degraded_roles = sorted(role for role, status in role_statuses.items() if status == "degraded")
    failed_roles = sorted(role for role, status in role_statuses.items() if status == "failed")
    return {
        "schema_version": SESSION_ENVELOPE_SCHEMA,
        "envelope_id": f"se-{goal_hash[:16]}",
        "invocation_id": invocation_id,
        "goal": goal,
        "goal_hash": goal_hash,
        "created_at": created_at,
        "contract_id": contract_id,
        "plan_only": plan_only,
        "required_before_execution": True,
        "role_statuses": role_statuses,
        "degraded_roles": degraded_roles,
        "failed_roles": failed_roles,
        "role_artifacts": {
            "genesis": artifact_paths["genesis"],
            "memory_request": artifact_paths["memory_request"],
            "memory_context_pack": artifact_paths["memory_context_pack"],
            "capability_route": artifact_paths["capability"],
            "hive_execution_plan": artifact_paths["hive"],
            "dispatch_packets": artifact_paths["dispatch"],
        },
        "executor_assignment": {
            "default_executor": "codex",
            "execution_owner": "hivemind",
            "mode": "bounded_worker_packet",
            "requires_dispatch_packet": True,
            "requires_verification_result": True,
        },
        "degraded_receipt": {
            "status": "degraded" if degraded_roles or failed_roles or stop_conditions else "not_needed",
            "missing_or_degraded_roles": degraded_roles + failed_roles,
            "stop_conditions_triggered": sorted(set(stop_conditions)),
        },
        "authority": {
            "source": "myworld_control_plane",
            "grants_execution_authority": False,
            "operator_override_required_for_irreversible_actions": True,
        },
    }


def build_invocation(root: Path, args: argparse.Namespace) -> dict[str, Any]:
    goal = args.goal
    goal_hash = stable_hash(goal)
    out_dir = resolve_output_dir(root, goal, args.write)
    invocation_id = out_dir.name
    created_at = now_iso()
    plan_only = True if not getattr(args, "execute", False) else bool(args.plan_only)

    role_statuses: dict[str, str] = {}
    stop_conditions: list[str] = []

    goal_payload = {
        "schema_version": GOAL_SCHEMA,
        "invocation_id": invocation_id,
        "goal": goal,
        "goal_hash": goal_hash,
        "control_plane_root": root.as_posix(),
        "created_at": created_at,
        "plan_only": plan_only,
    }
    write_json(out_dir / "goal.json", goal_payload)

    genesis_status, genesis_payload, stops = genesis_artifact(root, goal)
    role_statuses["genesis"] = genesis_status
    stop_conditions.extend(stops)
    write_json(out_dir / "genesis" / "branches.json", genesis_payload)

    memory_status, memory_request, context_pack, stops = memory_artifacts(root, goal)
    role_statuses["memory"] = memory_status
    stop_conditions.extend(stops)
    write_json(out_dir / "memory" / "context_request.json", memory_request)
    write_text(out_dir / "memory" / "context_pack.md", context_pack)

    capability_status, capability_payload, stops = capability_artifact(root, goal)
    role_statuses["capability"] = capability_status
    stop_conditions.extend(stops)
    write_json(out_dir / "capability" / "route.json", capability_payload)

    hive_status, hive_payload, stops = hive_plan(root, goal, contract_id=args.contract_id, plan_only=plan_only)
    role_statuses["hive"] = hive_status
    stop_conditions.extend(stops)
    write_json(out_dir / "hive" / "execution_plan.json", hive_payload)

    packets = dispatch_packets(goal)
    write_json(out_dir / "dispatch" / "packets.json", packets)

    if any(status == "failed" for status in role_statuses.values()):
        overall_status = "failed"
    elif any(status == "degraded" for status in role_statuses.values()) or stop_conditions:
        overall_status = "degraded"
    else:
        overall_status = "passed"

    artifact_paths = {
        "goal": relative(out_dir / "goal.json", root),
        "genesis": relative(out_dir / "genesis" / "branches.json", root),
        "memory_request": relative(out_dir / "memory" / "context_request.json", root),
        "memory_context_pack": relative(out_dir / "memory" / "context_pack.md", root),
        "capability": relative(out_dir / "capability" / "route.json", root),
        "hive": relative(out_dir / "hive" / "execution_plan.json", root),
        "dispatch": relative(out_dir / "dispatch" / "packets.json", root),
        "session_envelope": relative(out_dir / "session_envelope.json", root),
        "receipt": relative(out_dir / "receipt.json", root),
    }
    session_envelope = build_session_envelope(
        invocation_id=invocation_id,
        goal=goal,
        goal_hash=goal_hash,
        created_at=created_at,
        plan_only=plan_only,
        role_statuses=role_statuses,
        artifact_paths=artifact_paths,
        stop_conditions=stop_conditions,
        contract_id=args.contract_id,
    )
    write_json(out_dir / "session_envelope.json", session_envelope)
    receipt = {
        "schema_version": RECEIPT_SCHEMA,
        "invocation_id": invocation_id,
        "goal_hash": goal_hash,
        "created_at": created_at,
        "plan_only": plan_only,
        "overall_status": overall_status,
        "role_statuses": role_statuses,
        "session_envelope": artifact_paths["session_envelope"],
        "artifact_paths": artifact_paths,
        "stop_conditions_triggered": sorted(set(stop_conditions)),
        "next_action": "review_degraded_roles" if overall_status != "passed" else "dispatch_ready",
    }
    write_json(out_dir / "receipt.json", receipt)
    return receipt


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Create AIOS invocation artifacts")
    parser.add_argument("--root", type=Path, default=Path.cwd())
    parser.add_argument("--goal", required=True)
    parser.add_argument("--write", help="output directory under .aios/invocations")
    parser.add_argument("--contract-id", help="accepted contract id for non-plan execution")
    parser.add_argument("--plan-only", action="store_true", default=True)
    parser.add_argument("--execute", action="store_true", help="reserved; still requires contract id")
    parser.add_argument("--json", action="store_true")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    root = args.root.resolve()
    receipt = build_invocation(root, args)
    if args.json:
        print(canonical_json(receipt))
    else:
        print(f"{receipt['schema_version']} status={receipt['overall_status']} invocation_id={receipt['invocation_id']}")
    return 0 if receipt.get("overall_status") in {"passed", "degraded"} else 1


if __name__ == "__main__":
    raise SystemExit(main())
