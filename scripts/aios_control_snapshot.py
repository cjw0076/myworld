#!/usr/bin/env python3
"""Build a local AIOS control-plane snapshot for the static control app."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
import urllib.parse
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


SCHEMA_VERSION = "aios.control_snapshot.v1"
REPOS = ("hivemind", "memoryOS", "CapabilityOS")
INSTALL_MARKER = "# AIOS_INSTALLER_MANAGED v=asc-0080"
CHAIR_RUNTIME_SCHEMA = "aios.gate.chair_runtime.v1"
CHAIR_RUNTIME_MODES = {"internal_evidence_synthesizer", "ollama", "claude", "codex", "gemini"}
PROVIDER_CHAIR_MODES = {"claude", "codex", "gemini"}
GATE_CHAIR_DEMOTION_STATUSES = {
    "gate_chair_timeout",
    "gate_chair_exception",
    "provider_access_denied",
    "provider_backpressure",
    "pin_required_noninteractive",
    "empty_output",
    "provider_execution_failed",
}


def now_iso() -> str:
    return datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds")


def stable_hash(value: str) -> str:
    return hashlib.sha1(value.encode("utf-8", "replace")).hexdigest()


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
    marker = f"## {heading}"
    start = body.find(marker)
    if start == -1:
        return ""
    rest = body[start + len(marker) :]
    next_start = rest.find("\n## ")
    return rest[:next_start] if next_start != -1 else rest


def bullet_items(text: str, limit: int = 8) -> list[str]:
    items: list[str] = []
    current: str | None = None
    for raw in text.splitlines():
        stripped = raw.strip()
        if stripped.startswith("- "):
            if current:
                items.append(current)
            current = stripped[2:].strip()
        elif current and raw.startswith((" ", "\t")):
            current = f"{current} {stripped}".strip()
    if current:
        items.append(current)
    return items[:limit]


def read_json(path: Path) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None


def count_lines(path: Path) -> int:
    try:
        with path.open("rb") as handle:
            return sum(1 for _line in handle)
    except OSError:
        return 0


def read_jsonl_rows(path: Path, *, limit: int | None = None) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    try:
        with path.open("r", encoding="utf-8", errors="replace") as handle:
            for raw in handle:
                try:
                    row = json.loads(raw)
                except json.JSONDecodeError:
                    continue
                if isinstance(row, dict):
                    rows.append(row)
                    if limit is not None and len(rows) >= limit:
                        break
    except OSError:
        return []
    return rows


def read_text(path: Path, *, limit: int = 4096) -> str:
    try:
        return path.read_text(encoding="utf-8", errors="replace")[:limit]
    except OSError:
        return ""


def compact_preview(value: Any, *, limit: int = 240) -> str:
    text = " ".join(str(value or "").split())
    return text[:limit]


def is_managed_install_file(path: Path) -> bool:
    return INSTALL_MARKER in read_text(path, limit=600)


def process_alive(pid_path: Path) -> bool:
    raw = read_text(pid_path, limit=64).strip()
    if not raw.isdigit():
        return False
    try:
        os.kill(int(raw), 0)
        return True
    except OSError:
        return False


def systemctl_user_state(service_name: str) -> dict[str, Any]:
    if os.environ.get("AIOS_INSTALL_SKIP_SYSTEMCTL") == "1" or not shutil.which("systemctl"):
        return {"available": False, "reason": "systemctl_unavailable"}

    def check(kind: str) -> dict[str, Any]:
        try:
            result = subprocess.run(
                ["systemctl", "--user", kind, service_name],
                text=True,
                capture_output=True,
                timeout=3,
                check=False,
            )
        except (OSError, subprocess.SubprocessError) as exc:
            return {"status": "failed", "stdout": "", "returncode": 1, "error": str(exc)}
        return {"status": "passed" if result.returncode == 0 else "failed", "stdout": result.stdout.strip(), "returncode": result.returncode}

    enabled = check("is-enabled")
    active = check("is-active")
    return {
        "available": True,
        "enabled": enabled.get("stdout") or "unknown",
        "active": active.get("stdout") or "unknown",
    }


def load_goals(root: Path) -> dict[str, Any]:
    goals: list[dict[str, Any]] = []
    for path in sorted((root / "docs" / "goals").glob("AIOS-GOAL-*.md")):
        text = path.read_text(encoding="utf-8", errors="replace")
        frontmatter, body = parse_frontmatter(text)
        if path.name.endswith("-evolution.md"):
            continue
        goals.append(
            {
                "id": frontmatter.get("goal_id") or path.stem,
                "slug": frontmatter.get("slug") or path.stem,
                "status": frontmatter.get("status") or "unknown",
                "path": path.relative_to(root).as_posix(),
                "north_star": section(body, "North Star").strip().splitlines()[:4],
                "preferred_next": bullet_items(section(body, "Preferred Next Improvements"), limit=6),
                "completed": bullet_items(section(body, "Completed Improvements"), limit=8),
            }
        )
    evolution = read_goal_evolution(root / "docs" / "goals" / "AIOS-GOAL-0001-evolution.md", root)
    return {"items": goals, "active": next((g for g in goals if g["status"] == "active"), goals[0] if goals else None), "evolution": evolution}


def read_goal_evolution(path: Path, root: Path) -> dict[str, Any] | None:
    if not path.exists():
        return None
    text = path.read_text(encoding="utf-8", errors="replace")
    rec = {"path": path.relative_to(root).as_posix(), "recommendation": None, "monitor_health": None, "readiness": None}
    for line in text.splitlines():
        stripped = line.strip()
        if stripped.startswith("- path:"):
            rec["recommendation"] = stripped.partition("`")[2].rpartition("`")[0]
        elif stripped.startswith("- monitor_health:"):
            rec["monitor_health"] = stripped.partition("`")[2].rpartition("`")[0]
        elif stripped.startswith("- readiness:"):
            rec["readiness"] = stripped.partition("`")[2].rpartition("`")[0]
    return rec


def load_contracts(root: Path) -> dict[str, Any]:
    rows: list[dict[str, Any]] = []
    for path in sorted((root / "docs" / "contracts").glob("ASC-*.md")):
        text = path.read_text(encoding="utf-8", errors="replace")
        frontmatter, body = parse_frontmatter(text)
        quality = contract_quality(frontmatter, body)
        rows.append(
            {
                "id": frontmatter.get("contract_id") or path.stem.split("-")[0],
                "slug": frontmatter.get("slug") or path.stem,
                "status": frontmatter.get("status") or "unknown",
                "goal": frontmatter.get("goal") or first_heading(body),
                "created": frontmatter.get("created", ""),
                "accepted": frontmatter.get("accepted", ""),
                "closed": frontmatter.get("closed", ""),
                "path": path.relative_to(root).as_posix(),
                "stop_conditions": bullet_items(section(body, "Stop Conditions"), limit=8),
                "quality_state": quality["state"],
                "quality_warnings": quality["warnings"],
                "review_action": quality["review_action"],
            }
        )
    counts = Counter(row["status"] for row in rows)
    quality_counts = Counter(row["quality_state"] for row in rows)
    latest = sorted(rows, key=lambda row: row["id"], reverse=True)[:10]
    # ASC-0204: compact all-contract list for the contract board projection.
    board_rows = [
        {"id": row["id"], "slug": row["slug"], "status": row["status"],
         "goal": row["goal"], "path": row["path"]}
        for row in rows
    ]
    return {
        "counts": dict(counts),
        "quality_counts": dict(quality_counts),
        "latest": latest,
        "total": len(rows),
        "board_rows": board_rows,
    }


def contract_quality(frontmatter: dict[str, str], body: str) -> dict[str, Any]:
    status = (frontmatter.get("status") or "unknown").strip().lower()
    goal = (frontmatter.get("goal") or "").strip()
    origin = (frontmatter.get("origin") or "").strip().lower()
    body_lower = body.lower()
    warnings: list[str] = []

    if status == "proposed" and "session promotion" in origin:
        if len(goal) < 18:
            warnings.append("goal_too_short_for_contract_acceptance")
        if "signal_coverage: `0.0`" in body_lower or "signal_coverage: 0.0" in body_lower:
            warnings.append("memory_signal_coverage_zero")
        if "pending_or_not_required" in body_lower:
            warnings.append("os_role_evidence_not_narrowed")

    if status == "proposed" and warnings:
        return {
            "state": "weak_proposed",
            "warnings": warnings,
            "review_action": "revise_or_supersede_before_acceptance",
        }
    if status == "proposed":
        return {"state": "review_required", "warnings": [], "review_action": "operator_accept_or_revise"}
    return {"state": status, "warnings": [], "review_action": ""}


def first_heading(body: str) -> str:
    for line in body.splitlines():
        if line.startswith("# "):
            return line[2:].strip()
    return ""


def dispatch_packet_candidates(root: Path, dispatch_id: str, repos: set[str]) -> list[Path]:
    candidates: list[Path] = []
    inbox_root = root / ".aios" / "inbox"
    archive_root = root / ".aios" / "archive" / "inbox"
    for repo in sorted(repos):
        candidates.append(inbox_root / repo / f"{dispatch_id}.{repo}.json")
        candidates.append(archive_root / repo / f"{dispatch_id}.{repo}.json")
    if inbox_root.exists():
        candidates.extend(sorted(inbox_root.glob(f"*/{dispatch_id}.*.json")))
    if archive_root.exists():
        candidates.extend(sorted(archive_root.glob(f"*/{dispatch_id}.*.json")))
    seen: set[Path] = set()
    unique: list[Path] = []
    for path in candidates:
        if path in seen:
            continue
        seen.add(path)
        unique.append(path)
    return unique


def dispatch_memory_context(root: Path, dispatch_id: str, repos: set[str]) -> dict[str, Any]:
    for path in dispatch_packet_candidates(root, dispatch_id, repos):
        payload = read_json(path)
        if not isinstance(payload, dict):
            continue
        envelope = payload.get("session_envelope") if isinstance(payload.get("session_envelope"), dict) else {}
        memory_context = envelope.get("memory_context") if isinstance(envelope.get("memory_context"), dict) else {}
        if not memory_context:
            continue
        try:
            packet_ref = path.relative_to(root).as_posix()
        except ValueError:
            packet_ref = path.as_posix()
        return {
            "packet": packet_ref,
            "session_envelope_ref": envelope.get("ref") or "",
            "retrieval_trace": memory_context.get("retrieval_trace") or "",
            "signal_coverage": memory_context.get("signal_coverage") or "",
            "context_pack": memory_context.get("context_pack") or "",
            "memory_backed": bool(memory_context.get("retrieval_trace") and memory_context.get("signal_coverage")),
        }
    return {}


def load_dispatches(root: Path) -> dict[str, Any]:
    state_path = root / ".aios" / "state" / "dispatches.jsonl"
    events: list[dict[str, Any]] = []
    if state_path.exists():
        for raw in state_path.read_text(encoding="utf-8", errors="replace").splitlines():
            try:
                row = json.loads(raw)
            except json.JSONDecodeError:
                continue
            if isinstance(row, dict):
                events.append(row)
    by_id: dict[str, dict[str, Any]] = {}
    timeline: list[dict[str, Any]] = []
    for row in events:
        dispatch_id = str(row.get("dispatch_id") or "")
        if not dispatch_id:
            continue
        entry = by_id.setdefault(
            dispatch_id,
            {
                "dispatch_id": dispatch_id,
                "contract_id": row.get("contract_id"),
                "goal": row.get("goal"),
                "sent": set(),
                "collected": set(),
                "status": row.get("status") or row.get("event"),
                "reason": row.get("reason", ""),
                "timestamp": row.get("timestamp", ""),
            },
        )
        if row.get("repo") and row.get("event") == "sent":
            entry["sent"].add(row["repo"])
        if row.get("repo") and row.get("event") == "collected":
            entry["collected"].add(row["repo"])
        for key in ("contract_id", "goal", "reason", "timestamp"):
            if row.get(key):
                entry[key] = row[key]
        if row.get("status"):
            entry["status"] = row["status"]
        timeline.append({"dispatch_id": dispatch_id, "event": row.get("event"), "repo": row.get("repo"), "status": row.get("status"), "timestamp": row.get("timestamp")})
    rows = []
    for entry in by_id.values():
        repos = set(entry["sent"]) | set(entry["collected"])
        memory_context = dispatch_memory_context(root, str(entry["dispatch_id"]), repos)
        rows.append({**entry, "sent": sorted(entry["sent"]), "collected": sorted(entry["collected"]), "memory_context": memory_context})
    rows.sort(key=lambda row: row.get("timestamp") or "", reverse=True)
    counts = Counter(row["status"] for row in rows)
    # ASC-0204: per-contract dispatch aggregate, so the contract board can
    # tell an accepted-but-undispatched contract from a dispatched/collected one.
    by_contract: dict[str, dict[str, Any]] = {}
    for row in rows:
        cid = str(row.get("contract_id") or "")
        if not cid:
            continue
        agg = by_contract.setdefault(cid, {"sent": set(), "collected": set(), "statuses": []})
        agg["sent"].update(row.get("sent") or [])
        agg["collected"].update(row.get("collected") or [])
        if row.get("status"):
            agg["statuses"].append(str(row["status"]))
    by_contract = {
        cid: {"sent": sorted(agg["sent"]), "collected": sorted(agg["collected"]), "statuses": agg["statuses"]}
        for cid, agg in by_contract.items()
    }
    return {
        "counts": dict(counts),
        "latest": rows[:12],
        "timeline": timeline[-30:],
        "total": len(rows),
        "by_contract": by_contract,
    }


# ASC-0204 — the six AIOS repo-agents the roster surfaces.
ROSTER_AGENTS: tuple[tuple[str, str], ...] = (
    ("claude@myworld", "myworld"),
    ("codex@myworld", "myworld"),
    ("codex@hivemind", "hivemind"),
    ("codex@memoryOS", "memoryOS"),
    ("codex@CapabilityOS", "CapabilityOS"),
    ("codex@GenesisOS", "GenesisOS"),
)

# Contract-lifecycle kanban columns (vibe-kanban borrow).
CONTRACT_BOARD_COLUMNS: tuple[str, ...] = (
    "proposed", "accepted", "dispatched", "collected", "closed",
)

# Roster event ordering — blocked / needs_input float to the top (cmux
# out-of-band channel: a stuck agent must never need scrolling to find).
ROSTER_EVENT_ORDER: dict[str, int] = {
    "blocked": 0, "needs_input": 1, "working": 2, "idle": 3, "unknown": 4,
}


def _roster_event(*, inbox_count: int, dirty: bool, blocked: bool, needs_input: bool) -> str:
    """Derive an agent's out-of-band event from traceable signals only —
    never invent state (Invariant 8)."""
    if blocked:
        return "blocked"
    if needs_input:
        return "needs_input"
    if inbox_count > 0 or dirty:
        return "working"
    return "idle"


def build_roster(
    root: Path,
    dispatches: dict[str, Any],
    repos_state: dict[str, Any],
) -> dict[str, Any]:
    """ASC-0204 — one card per repo-agent: a one-line status digest and an
    out-of-band event, projected from inbox/outbox counts, git dirtiness, and
    dispatch failure signals. A projection only — no new store."""
    repo_by_name = {str(item.get("repo")): item for item in repos_state.get("items", [])}
    # repos not in load_repos() (myworld itself, GenesisOS) — read git directly.
    extra_repo_state: dict[str, dict[str, Any]] = {}
    for repo, rel in (("myworld", "."), ("GenesisOS", "GenesisOS")):
        if repo not in repo_by_name:
            extra_repo_state[repo] = git_status(root, rel)
    blocked_repos: set[str] = set()
    for row in dispatches.get("latest", []):
        status = str(row.get("status") or "").lower()
        if any(token in status for token in ("fail", "block", "error", "stuck")):
            for repo in list(row.get("sent") or []):
                blocked_repos.add(str(repo))
    agents: list[dict[str, Any]] = []
    for agent, repo in ROSTER_AGENTS:
        rs = repo_by_name.get(repo) or extra_repo_state.get(repo) or {}
        inbox_count = int(rs.get("inbox_count") or 0)
        outbox_count = int(rs.get("outbox_count") or 0)
        dirty = bool(rs.get("dirty"))
        blocked = repo in blocked_repos
        event = _roster_event(inbox_count=inbox_count, dirty=dirty, blocked=blocked, needs_input=False)
        digest = f"{event} · inbox {inbox_count} · outbox {outbox_count}"
        if dirty:
            digest += " · git dirty"
        agents.append({
            "agent": agent,
            "repo": repo,
            "event": event,
            "health": "blocked" if blocked else "ok",
            "inbox_count": inbox_count,
            "outbox_count": outbox_count,
            "dirty": dirty,
            "status_digest": digest,
        })
    agents.sort(key=lambda a: (ROSTER_EVENT_ORDER.get(a["event"], 9), a["agent"]))
    return {
        "agents": agents,
        "blocked_count": sum(1 for a in agents if a["event"] == "blocked"),
        "needs_input_count": sum(1 for a in agents if a["event"] == "needs_input"),
    }


def build_contract_board(
    contract_rows: list[dict[str, Any]],
    dispatches: dict[str, Any],
) -> dict[str, Any]:
    """ASC-0204 — bucket every contract into the five lifecycle columns.
    proposed/closed come from contract status (the source of truth); an
    accepted contract is refined to dispatched/collected by its dispatch
    aggregate. A read projection of the ledger, never a writable board."""
    by_contract = dispatches.get("by_contract") or {}
    columns: dict[str, list[dict[str, Any]]] = {col: [] for col in CONTRACT_BOARD_COLUMNS}
    for row in contract_rows:
        status = str(row.get("status") or "unknown").strip().lower()
        card = {
            "contract_id": row.get("id"),
            "slug": row.get("slug"),
            "title": row.get("goal") or row.get("slug"),
            "status": status,
            "path": row.get("path"),
        }
        if status == "closed":
            column = "closed"
        elif status == "proposed":
            column = "proposed"
        elif status == "accepted":
            agg = by_contract.get(str(row.get("id")))
            if not agg or not agg.get("sent"):
                column = "accepted"
            elif agg.get("collected") and set(agg["collected"]) >= set(agg["sent"]):
                column = "collected"
            else:
                column = "dispatched"
            card["dispatch"] = {
                "sent": (agg or {}).get("sent", []),
                "collected": (agg or {}).get("collected", []),
            }
        else:
            # untraceable status — surface as proposed-for-review, never drop
            column = "proposed"
            card["status"] = "unknown"
        columns[column].append(card)
    return {
        "columns": {col: columns[col] for col in CONTRACT_BOARD_COLUMNS},
        "counts": {col: len(columns[col]) for col in CONTRACT_BOARD_COLUMNS},
        "column_order": list(CONTRACT_BOARD_COLUMNS),
    }


def load_hive_board(root: Path) -> dict[str, Any]:
    runs_root = root / "hivemind" / ".runs"
    if not runs_root.exists():
        return {"status": "inactive", "run_id": "", "message": "Hive run directory is not available"}
    current_path = runs_root / "current"
    current_run = read_text(current_path, limit=200).strip()
    if current_run:
        run_dir = runs_root / current_run
        if not run_dir.is_dir() or not (run_dir / "run_state.json").exists():
            current_run = ""
    if not current_run:
        candidate_dirs = sorted(
            (p for p in runs_root.glob("run_*") if p.is_dir() and (p / "run_state.json").exists()),
            reverse=True,
        )
        current_run = candidate_dirs[0].name if candidate_dirs else ""
    if not current_run:
        return {"status": "idle", "run_id": "", "message": "No Hive run is currently available"}

    run_dir = runs_root / current_run
    state = read_json(run_dir / "run_state.json") or {}
    if not isinstance(state, dict):
        state = {}

    def _agent_status(name: str) -> str:
        for agent in state.get("agents") if isinstance(state.get("agents"), list) else []:
            if not isinstance(agent, dict):
                continue
            if agent.get("name") == name:
                return str(agent.get("status") or "").lower()
        return ""

    def _memory_draft_count(path: Path) -> int:
        payload = read_json(path)
        if not isinstance(payload, dict):
            return 0
        rows = payload.get("memory_drafts")
        if isinstance(rows, list):
            return len(rows)
        if isinstance(rows, int):
            return max(rows, 0)
        return 0

    def _relative_path(rel: str) -> str:
        if rel.startswith(".runs/") or rel.startswith(".runs\\"):
            return rel
        return (run_dir / rel).resolve().relative_to(root.resolve()).as_posix()

    pipeline_spec: list[tuple[str, str, str]] = [
        ("intake", "task.yaml", "task"),
        ("route", "routing_plan.json", "routing_plan"),
        ("context", "context_pack.md", "context_pack"),
        ("deliberate", "agents/claude/planner_result.yaml", "claude_planner"),
        ("handoff", "handoff.yaml", "handoff"),
        ("execute", "agents/codex/executor_result.yaml", "codex_executor"),
        ("verify", "verification.yaml", "verification"),
        ("memory", "memory_drafts.json", "memory_drafts"),
        ("close", "final_report.md", "final_report"),
    ]

    pipeline: list[dict[str, Any]] = []
    for step, file_name, artifact_id in pipeline_spec:
        artifact_path = run_dir / file_name
        exists = artifact_path.exists()
        status = "done" if exists else "pending"
        if step == "verify" and exists:
            status = "pending" if "not_run" in read_text(artifact_path, limit=5000) else "done"
        if step == "memory" and exists:
            status = "done" if _memory_draft_count(artifact_path) > 0 else "empty"
        if step == "close" and exists:
            status = "initial" if "Status: planned" in read_text(artifact_path, limit=5000) else "done"
        pipeline.append(
            {
                "step": step,
                "artifact": artifact_id,
                "path": _relative_path(str(artifact_path.relative_to(root / "hivemind"))),
                "status": status,
            }
        )

    next_action: dict[str, str] = {}
    route_done = next((item for item in pipeline if item["step"] == "route"), {}).get("status") == "done"
    context_done = next((item for item in pipeline if item["step"] == "context"), {}).get("status") == "done"
    deliberate_done = next((item for item in pipeline if item["step"] == "deliberate"), {}).get("status") == "done"
    execute_done = next((item for item in pipeline if item["step"] == "execute"), {}).get("status") == "done"
    verify_done = next((item for item in pipeline if item["step"] == "verify"), {}).get("status") == "done"
    memory_done = next((item for item in pipeline if item["step"] == "memory"), {}).get("status") == "done"
    close_done = next((item for item in pipeline if item["step"] == "close"), {}).get("status") == "done"

    if not route_done:
        next_action = {"command": f'hive run "{state.get("user_request", "")}"', "reason": "route artifact missing"}
    elif _agent_status("local-context-compressor") == "failed":
        next_action = {"command": "hive audit", "reason": "local context worker failed"}
    elif not context_done:
        next_action = {"command": "hive invoke local --role context", "reason": "context artifact not produced"}
    elif not deliberate_done:
        next_action = {"command": "hive invoke claude --role planner", "reason": "planner artifact not prepared"}
    elif not execute_done:
        next_action = {"command": "hive invoke codex --role executor", "reason": "executor artifact not prepared"}
    elif not verify_done:
        next_action = {"command": "hive verify", "reason": "verification missing or not run"}
    elif not memory_done:
        next_action = {"command": "hive make-memory-drafts", "reason": "memory drafts are empty"}
    elif not close_done:
        next_action = {"command": "hive close", "reason": "final report still open"}
    else:
        next_action = {"command": "hive inspect", "reason": "pipeline complete"}

    artifacts: list[dict[str, Any]] = []
    for name, rel_path in (state.get("artifacts") or {}).items():
        if not isinstance(rel_path, str):
            continue
        raw_path = Path(rel_path)
        if raw_path.is_absolute():
            artifact_file = raw_path
        else:
            artifact_file = (root / "hivemind" / rel_path).resolve()
        artifacts.append(
            {
                "name": name,
                "path": rel_path,
                "exists": artifact_file.exists(),
                "status": "ok" if artifact_file.exists() else "missing",
            }
        )

    extra_artifacts = {
        "routing_plan": run_dir / "routing_plan.json",
        "society_plan": run_dir / "society_plan.json",
        "hive_events": run_dir / "hive_events.jsonl",
        "checks_report": run_dir / "checks_report.json",
        "git_diff_report": run_dir / "git_diff_report.json",
        "commit_summary": run_dir / "commit_summary.md",
    }
    existing_names = {item["name"] for item in artifacts}
    for name, path in extra_artifacts.items():
        if name in existing_names:
            continue
        exists = path.exists()
        rel = path.resolve().relative_to((root / "hivemind").resolve()).as_posix() if path.exists() or path.parent.exists() else str(path)
        artifacts.append(
            {
                "name": name,
                "path": rel,
                "exists": exists,
                "status": "ok" if exists else "missing",
            }
        )

    artifacts.sort(key=lambda item: item["name"])

    return {
        "run_id": current_run,
        "status": state.get("status", "unknown"),
        "phase": state.get("phase", ""),
        "project": state.get("project", "Hive Mind"),
        "task": state.get("user_request", ""),
        "agents": state.get("agents") if isinstance(state.get("agents"), list) else [],
        "pipeline": pipeline,
        "artifacts": artifacts,
        "next": next_action,
        "pipeline_done": sum(1 for item in pipeline if item.get("status") == "done"),
        "pipeline_total": len(pipeline),
        "updated_at": state.get("updated_at", ""),
        "latest_event": state.get("latest_event", ""),
    }


def git_status(root: Path, repo: str) -> dict[str, Any]:
    repo_path = root / repo
    if not repo_path.exists():
        return {"repo": repo, "exists": False, "dirty": None, "changes": []}
    try:
        result = subprocess.run(
            ["git", "-C", repo_path.as_posix(), "status", "--short", "--untracked-files=all"],
            text=True,
            capture_output=True,
            timeout=10,
            check=False,
        )
    except (OSError, subprocess.SubprocessError) as exc:
        return {"repo": repo, "exists": True, "dirty": None, "changes": [], "error": str(exc)}
    changes = [line for line in result.stdout.splitlines() if line.strip()]
    return {"repo": repo, "exists": True, "dirty": bool(changes), "changes": changes[:12]}


def load_repos(root: Path) -> dict[str, Any]:
    inbox = root / ".aios" / "inbox"
    outbox = root / ".aios" / "outbox"
    goal_inbox = root / ".aios" / "goal_inbox"
    goal_routes = root / ".aios" / "goal_routes"
    rows = []
    for repo in REPOS:
        rows.append(
            {
                **git_status(root, repo),
                "inbox_count": len(list((inbox / repo).glob("*.json"))) if (inbox / repo).exists() else 0,
                "outbox_count": len(list((outbox / repo).glob("*.json"))) if (outbox / repo).exists() else 0,
                "goal_count": len(list((goal_inbox / repo).glob("*.json"))) if (goal_inbox / repo).exists() else 0,
                "route_count": len(list((goal_routes / repo).glob("*.json"))) if (goal_routes / repo).exists() else 0,
            }
        )
    return {"items": rows}


def load_monitor(root: Path) -> dict[str, Any] | None:
    return read_json(root / ".aios" / "state" / "monitor_assessment.latest.json")


def load_round(root: Path) -> dict[str, Any] | None:
    return read_json(root / ".aios" / "state" / "round_controller.latest.json")


def install_target(path: Path) -> dict[str, Any]:
    return {
        "path": path.as_posix(),
        "exists": path.exists(),
        "managed": is_managed_install_file(path),
    }


def latest_gate_chair_turn(root: Path) -> dict[str, Any] | None:
    rows: list[tuple[float, dict[str, Any], Path]] = []
    for path in (root / ".aios" / "chat").glob("*/gate_chair_turns.jsonl"):
        try:
            mtime = path.stat().st_mtime
        except OSError:
            continue
        for row in read_jsonl_rows(path):
            rows.append((mtime, row, path))
    if not rows:
        return None
    _mtime, row, path = sorted(rows, key=lambda item: item[0], reverse=True)[0]
    meta = row.get("chair_meta") if isinstance(row.get("chair_meta"), dict) else {}
    runtime = meta.get("meta") if isinstance(meta.get("meta"), dict) else {}
    return {
        "path": path.relative_to(root).as_posix(),
        "executed": bool(row.get("executed")),
        "status": meta.get("status") or "unknown",
        "mode": runtime.get("mode"),
        "model": runtime.get("model"),
        "created_at": row.get("created_at", ""),
    }


def load_gate_chair_runtime_config(root: Path) -> dict[str, Any] | None:
    payload = read_json(root / ".aios" / "gate" / "founder" / "chair_runtime.json")
    if not isinstance(payload, dict) or payload.get("schema_version") != CHAIR_RUNTIME_SCHEMA:
        return None
    mode = str(payload.get("mode") or "")
    if mode not in CHAIR_RUNTIME_MODES:
        return None
    return {
        "path": ".aios/gate/founder/chair_runtime.json",
        "status": payload.get("status") or "unknown",
        "mode": mode,
        "model": payload.get("model") or "",
        "updated_at": payload.get("updated_at") or payload.get("created_at") or "",
    }


def load_gate_chair_candidate_config(root: Path) -> dict[str, Any] | None:
    payload = read_json(root / ".aios" / "gate" / "founder" / "chair_candidate_runtime.json")
    if not isinstance(payload, dict) or payload.get("schema_version") != CHAIR_RUNTIME_SCHEMA:
        return None
    mode = str(payload.get("mode") or "")
    if payload.get("status") != "candidate" or mode not in CHAIR_RUNTIME_MODES:
        return None
    return {
        "path": ".aios/gate/founder/chair_candidate_runtime.json",
        "status": payload.get("status") or "unknown",
        "mode": mode,
        "model": payload.get("model") or "",
        "updated_at": payload.get("updated_at") or payload.get("created_at") or "",
        "command_available": payload.get("command_available"),
        "fallback_expected": payload.get("fallback_expected"),
    }


def gate_chair_report_recovers_runtime(root: Path, report: dict[str, Any], mode: str, model: str, ref: Path | str) -> dict[str, Any] | None:
    if not report.get("promotion_ready"):
        return None
    scores = report.get("scores") if isinstance(report.get("scores"), dict) else {}
    try:
        if float(scores.get("current", 0.0)) <= float(scores.get("internal", 0.0)):
            return None
    except (TypeError, ValueError):
        return None
    for mode_report in report.get("modes") or []:
        if not isinstance(mode_report, dict) or mode_report.get("mode") != "current":
            continue
        runtime_modes = {str(item) for item in mode_report.get("runtime_modes") or []}
        if mode not in runtime_modes:
            continue
        runtime_models = {str(item) for item in mode_report.get("runtime_models") or []}
        if model and model not in runtime_models:
            continue
        failed = False
        for run in mode_report.get("runs") or []:
            if not isinstance(run, dict):
                continue
            chair = run.get("gate_chair_status") if isinstance(run.get("gate_chair_status"), dict) else {}
            status = str(chair.get("status") or "")
            if run.get("ok") is False or (status and status not in {"success", "not_attempted"}):
                failed = True
                break
        if failed:
            continue
        ref_text = ref.resolve().relative_to(root.resolve()).as_posix() if isinstance(ref, Path) else str(ref)
        return {
            "recovery_reason": "fresh_eval_beat_internal_baseline",
            "recovery_ref": ref_text,
            "recovery_current_score": scores.get("current"),
            "recovery_internal_score": scores.get("internal"),
        }
    return None


def gate_chair_runtime_demotion(root: Path, mode: str, model: str = "", threshold: int = 2) -> dict[str, Any] | None:
    if mode in {"", "internal_evidence_synthesizer"}:
        return None
    failures: list[dict[str, str]] = []

    def add_failure(status: str, provider: str, found_model: str, ref: Path | str) -> None:
        if len(failures) >= threshold:
            return
        if status not in GATE_CHAIR_DEMOTION_STATUSES or provider != mode:
            return
        if model and found_model not in {"", "unknown", model}:
            return
        ref_text = ref.resolve().relative_to(root.resolve()).as_posix() if isinstance(ref, Path) else str(ref)
        failures.append({"status": status, "ref": ref_text, "model": found_model or model or "unknown"})

    eval_root = root / ".aios" / "evals" / "gate_chair"
    if eval_root.exists():
        for path in sorted(eval_root.glob("*/report.json"), key=lambda item: item.stat().st_mtime, reverse=True)[:80]:
            payload = read_json(path)
            if not isinstance(payload, dict) or payload.get("schema_version") != "aios.gate_chair_eval.v1":
                continue
            if gate_chair_report_recovers_runtime(root, payload, mode, model, path):
                return None
            for mode_report in payload.get("modes") or []:
                if not isinstance(mode_report, dict):
                    continue
                for run in mode_report.get("runs") or []:
                    if not isinstance(run, dict):
                        continue
                    chair = run.get("gate_chair_status") if isinstance(run.get("gate_chair_status"), dict) else {}
                    add_failure(
                        str(chair.get("status") or ""),
                        str(chair.get("mode") or mode_report.get("mode") or ""),
                        str(chair.get("model") or "unknown"),
                        path,
                    )
                    if len(failures) >= threshold:
                        break
                if len(failures) >= threshold:
                    break
            if len(failures) >= threshold:
                break

    chat_root = root / ".aios" / "chat"
    if len(failures) < threshold and chat_root.exists():
        for path in sorted(chat_root.glob("*/gate_chair_turns.jsonl"), key=lambda item: item.stat().st_mtime, reverse=True)[:120]:
            for row in reversed(read_jsonl_rows(path)[-80:]):
                if row.get("schema_version") != "aios.chat.gate_chair_turn.v1":
                    continue
                meta = row.get("chair_meta") if isinstance(row.get("chair_meta"), dict) else {}
                runtime = meta.get("meta") if isinstance(meta.get("meta"), dict) else {}
                add_failure(
                    str(meta.get("status") or ""),
                    str(runtime.get("mode") or ""),
                    str(runtime.get("model") or "unknown"),
                    path,
                )
                if len(failures) >= threshold:
                    break
            if len(failures) >= threshold:
                break

    if len(failures) < threshold:
        return None
    return {
        "reason": "active_runtime_demoted_by_negative_evidence",
        "requested_mode": mode,
        "requested_model": model,
        "failure_count": len(failures),
        "failure_threshold": threshold,
        "failure_statuses": [item["status"] for item in failures],
        "failure_refs": list(dict.fromkeys(item["ref"] for item in failures)),
    }


def gate_chair_runtime_recovery_proof(root: Path, mode: str, model: str = "", threshold: int = 2) -> dict[str, Any] | None:
    if mode in {"", "internal_evidence_synthesizer"}:
        return None
    proof: dict[str, Any] | None = None
    older_failures: list[str] = []
    eval_root = root / ".aios" / "evals" / "gate_chair"
    if not eval_root.exists():
        return None
    for path in sorted(eval_root.glob("*/report.json"), key=lambda item: item.stat().st_mtime, reverse=True)[:80]:
        payload = read_json(path)
        if not isinstance(payload, dict) or payload.get("schema_version") != "aios.gate_chair_eval.v1":
            continue
        if proof is None:
            proof = gate_chair_report_recovers_runtime(root, payload, mode, model, path)
            if proof is not None:
                continue
        if proof is None:
            continue
        for mode_report in payload.get("modes") or []:
            if not isinstance(mode_report, dict):
                continue
            for run in mode_report.get("runs") or []:
                if not isinstance(run, dict):
                    continue
                chair = run.get("gate_chair_status") if isinstance(run.get("gate_chair_status"), dict) else {}
                status = str(chair.get("status") or "")
                provider = str(chair.get("mode") or mode_report.get("mode") or "")
                found_model = str(chair.get("model") or "unknown")
                if status not in GATE_CHAIR_DEMOTION_STATUSES or provider != mode:
                    continue
                if model and found_model not in {"", "unknown", model}:
                    continue
                older_failures.append(path.resolve().relative_to(root.resolve()).as_posix())
                if len(older_failures) >= threshold:
                    return {
                        **proof,
                        "superseded_failure_count": len(older_failures),
                        "superseded_failure_refs": list(dict.fromkeys(older_failures)),
                    }
    return None


def build_gate_chair_runtime_preview(
    mode: str,
    state: str,
    detail: str,
    config: dict[str, Any] | None,
    candidate_config: dict[str, Any] | None,
    latest: dict[str, Any] | None,
    demotion: dict[str, Any] | None,
    recovery_proof: dict[str, Any] | None,
) -> dict[str, Any]:
    nodes: list[dict[str, Any]] = []
    edges: list[dict[str, str]] = []
    seen: set[str] = set()

    def add_node(node_id: str, node_type: str, label: str, node_state: str, x: int, y: int, detail_text: str = "") -> None:
        if node_id in seen:
            return
        seen.add(node_id)
        nodes.append(
            {
                "id": node_id,
                "type": node_type,
                "label": compact_preview(label, limit=30),
                "detail": compact_preview(detail_text or label, limit=140),
                "state": node_state,
                "x": x,
                "y": y,
            }
        )

    if config:
        configured_mode = str(config.get("mode") or "runtime")
        configured_model = str(config.get("model") or "")
        add_node(
            "runtime_config",
            "config",
            configured_mode if not configured_model else f"{configured_mode} {configured_model}",
            "active" if config.get("status") == "active" else "held",
            14,
            34,
            str(config.get("path") or ".aios/gate/founder/chair_runtime.json"),
        )
    if candidate_config:
        candidate_mode = str(candidate_config.get("mode") or "candidate")
        add_node(
            "runtime_candidate",
            "candidate",
            candidate_mode,
            "held",
            14,
            66,
            str(candidate_config.get("path") or ".aios/gate/founder/chair_candidate_runtime.json"),
        )
    add_node(
        "runtime_effective",
        "effective",
        mode,
        "attention" if demotion else ("external" if state == "external" else "internal"),
        46,
        50,
        detail,
    )
    if config:
        edges.append({"from": "runtime_config", "to": "runtime_effective", "kind": "selects"})
    if candidate_config:
        edges.append({"from": "runtime_candidate", "to": "runtime_effective", "kind": "candidate"})
    if latest:
        latest_status = str(latest.get("status") or "latest_turn")
        add_node(
            "runtime_latest_turn",
            "turn",
            latest_status,
            "attention" if latest_status in GATE_CHAIR_DEMOTION_STATUSES else "active",
            82,
            50,
            str(latest.get("turn_id") or latest.get("conversation") or "latest gate chair turn"),
        )
        edges.append({"from": "runtime_effective", "to": "runtime_latest_turn", "kind": "produces"})
    if demotion:
        add_node(
            "runtime_demotion",
            "failure",
            f"{demotion.get('failure_count', 0)} failure(s)",
            "attention",
            46,
            78,
            ", ".join(str(item) for item in (demotion.get("failure_statuses") or [])[:3]),
        )
        edges.append({"from": "runtime_demotion", "to": "runtime_effective", "kind": "demotes"})
    if recovery_proof:
        add_node(
            "runtime_recovery",
            "recovery",
            "recovery proof",
            "active",
            46,
            22,
            str(recovery_proof.get("recovery_ref") or ""),
        )
        edges.append({"from": "runtime_recovery", "to": "runtime_effective", "kind": "recovers"})

    edges = [edge for edge in edges if edge.get("from") in seen and edge.get("to") in seen]
    return {"nodes": nodes, "edges": edges}


def load_gate_chair_runtime(root: Path) -> dict[str, Any]:
    pack = read_json(root / ".aios" / "gate" / "founder" / "gate_pack.json")
    active_pack = isinstance(pack, dict) and pack.get("schema_version") == "aios.gate.pack.v1" and pack.get("status") == "active"
    config = load_gate_chair_runtime_config(root)
    candidate_config = load_gate_chair_candidate_config(root)
    config_active = bool(config and config.get("status") == "active")
    env_command = os.environ.get("AIOS_GATE_AGENT_COMMAND", "").strip()
    ollama_path = shutil.which("ollama")
    latest = latest_gate_chair_turn(root)
    demotion: dict[str, Any] | None = None
    recovery_proof: dict[str, Any] | None = None
    if config_active and config.get("mode") == "internal_evidence_synthesizer":
        mode = "internal_evidence_synthesizer"
        state = "internal"
        detail = "chair_runtime.json"
    elif config_active and config.get("mode") == "ollama":
        model = config.get("model") or "qwen2.5:7b"
        demotion = gate_chair_runtime_demotion(root, "ollama", str(model))
        recovery_proof = None if demotion else gate_chair_runtime_recovery_proof(root, "ollama", str(model))
        if demotion:
            mode = "internal_evidence_synthesizer"
            state = "internal"
            detail = f"chair_runtime.json requested ollama model={model}; demoted by negative evidence"
        else:
            mode = "ollama" if ollama_path else "internal_evidence_synthesizer"
            state = "external" if ollama_path else "internal"
            detail = f"chair_runtime.json model={model}" if ollama_path else f"chair_runtime.json requested ollama model={model}; command missing"
    elif config_active and config.get("mode") in PROVIDER_CHAIR_MODES:
        requested = str(config.get("mode"))
        provider_path = shutil.which(requested)
        model = config.get("model") or ""
        model_text = f" model={model}" if model else ""
        demotion = gate_chair_runtime_demotion(root, requested, str(model))
        recovery_proof = None if demotion else gate_chair_runtime_recovery_proof(root, requested, str(model))
        if demotion:
            mode = "internal_evidence_synthesizer"
            state = "internal"
            detail = f"chair_runtime.json requested {requested}{model_text}; demoted by negative evidence"
        else:
            mode = requested if provider_path else "internal_evidence_synthesizer"
            state = "external" if provider_path else "internal"
            detail = f"chair_runtime.json provider={requested}{model_text}" if provider_path else f"chair_runtime.json requested {requested}; command missing"
    elif env_command:
        mode = "env_command"
        state = "external"
        detail = "AIOS_GATE_AGENT_COMMAND"
    elif ollama_path:
        mode = "ollama"
        state = "external"
        detail = ollama_path
    else:
        mode = "internal_evidence_synthesizer"
        state = "internal"
        detail = "deterministic fallback"
    runtime_preview = build_gate_chair_runtime_preview(
        mode,
        state,
        detail,
        config,
        candidate_config,
        latest,
        demotion,
        recovery_proof,
    )
    return {
        "enabled": bool(active_pack),
        "state": state if active_pack else "disabled",
        "mode": mode,
        "effective_mode": mode,
        "configured_mode": config.get("mode") if config else "",
        "detail": detail,
        "demoted": bool(demotion),
        "demotion": demotion,
        "recovery_proof": recovery_proof,
        "gate_pack_id": pack.get("id") if isinstance(pack, dict) else "",
        "gate_pack_active": bool(active_pack),
        "runtime_config": config,
        "runtime_config_active": config_active,
        "candidate_config": candidate_config,
        "candidate_config_active": bool(candidate_config),
        "latest_turn": latest,
        "runtime_preview": runtime_preview,
    }


def load_installation(root: Path, round_state: dict[str, Any] | None) -> dict[str, Any]:
    home = Path(os.environ.get("HOME") or str(Path.home())).expanduser()
    config_home = Path(os.environ.get("XDG_CONFIG_HOME") or str(home / ".config")).expanduser()
    launcher = home / ".local" / "bin" / "aios"
    service = config_home / "systemd" / "user" / "aios.service"
    desktop = config_home / "autostart" / "aios-control.desktop"
    run_dir = root / ".aios" / "run"
    command_path = shutil.which("aios")
    control_port = read_text(run_dir / "aios_control_app.port", limit=32).strip() or "8765"
    control_running = process_alive(run_dir / "aios_control_app.pid")
    websocket_running = process_alive(run_dir / "aios_control_ws.pid")
    round_running = process_alive(run_dir / "aios_round_controller.pid") or bool((round_state or {}).get("status") == "passed")
    service_state = systemctl_user_state("aios.service")
    targets = {
        "launcher": install_target(launcher),
        "service": install_target(service),
        "desktop": install_target(desktop),
    }
    installed = bool(targets["launcher"]["managed"] and targets["service"]["managed"])
    service_active = service_state.get("active") == "active"
    if service_active and installed:
        status = "installed"
        headline = "AIOS starts in the background."
    elif control_running and round_running:
        status = "running"
        headline = "AIOS is running locally."
    elif installed:
        status = "installed_stopped"
        headline = "AIOS is installed but stopped."
    elif (root / "scripts" / "aios_install.py").exists():
        status = "ready_to_install"
        headline = "AIOS can be installed."
    else:
        status = "missing"
        headline = "Installer not found."
    return {
        "status": status,
        "headline": headline,
        "commands": ["aios install", "aios open", "aios status --json", "aios stop"],
        "command": {
            "available": bool(command_path),
            "path": command_path or "",
            "launcher_installed": targets["launcher"]["managed"],
        },
        "service": {
            "installed": targets["service"]["managed"],
            "active": service_active,
            "enabled": service_state.get("enabled", "unknown"),
            "state": service_state,
        },
        "control_center": {
            "running": control_running,
            "websocket_running": websocket_running,
            "url": f"http://127.0.0.1:{control_port}/",
        },
        "loop": {
            "running": round_running,
            "latest_status": (round_state or {}).get("status") or "unknown",
            "latest_next": ((round_state or {}).get("recommended_next") or {}).get("action", ""),
        },
        "gate_chair": load_gate_chair_runtime(root),
        "targets": targets,
    }


def load_aios_inputs(root: Path) -> dict[str, Any]:
    contracts = sorted((root / "docs" / "contracts").glob("ASC-*.md"), reverse=True)
    trace_ids: list[str] = []
    route_ids: list[str] = []
    run_ids: list[str] = []
    for path in contracts[:8]:
        text = path.read_text(encoding="utf-8", errors="replace")
        trace_ids.extend(unique_tokens(text, "rtrace_"))
        route_ids.extend(unique_tokens(text, "cap_"))
        run_ids.extend(unique_tokens(text, "run_"))
    return {"memory_traces": trace_ids[:6], "capability_routes": route_ids[:8], "hive_runs": run_ids[:6]}


def unique_tokens(text: str, prefix: str) -> list[str]:
    pattern = re.compile(rf"{re.escape(prefix)}[A-Za-z0-9_]+")
    seen: list[str] = []
    for match in pattern.finditer(text):
        token = match.group(0)
        if token not in seen:
            seen.append(token)
    return seen


def load_stop_lanes(root: Path) -> dict[str, Any]:
    lanes: dict[str, list[str]] = defaultdict(list)
    for row in load_contracts(root)["latest"]:
        for stop in row.get("stop_conditions", []):
            lanes[stop].append(row["id"])
    return {"items": [{"name": name, "contracts": contracts[:5]} for name, contracts in sorted(lanes.items())[:12]]}


def safe_artifact_preview(root: Path, artifact_ref: str, *, limit: int = 520) -> dict[str, Any] | None:
    if not artifact_ref:
        return None
    path = root / artifact_ref
    try:
        resolved = path.resolve()
        resolved.relative_to((root / ".aios" / "invocations").resolve())
    except ValueError:
        return None
    if not resolved.is_file() or resolved.stat().st_size > 200_000:
        return None
    raw = resolved.read_text(encoding="utf-8", errors="replace")
    if resolved.suffix == ".json":
        parsed = read_json(resolved)
        if isinstance(parsed, dict):
            preview_source = json.dumps(parsed, ensure_ascii=False, indent=2, sort_keys=True)
        else:
            preview_source = raw
    else:
        preview_source = raw
    text = " ".join(line.strip() for line in preview_source.splitlines() if line.strip())
    return {
        "path": artifact_ref,
        "preview": text[:limit],
        "truncated": len(text) > limit,
    }


def load_latest_invocations(root: Path) -> dict[str, Any]:
    invocations: list[dict[str, Any]] = []
    base = root / ".aios" / "invocations"
    if not base.exists():
        return {"latest": []}
    for receipt_path in base.glob("*/receipt.json"):
        receipt = read_json(receipt_path)
        if not isinstance(receipt, dict):
            continue
        envelope_ref = receipt.get("session_envelope")
        envelope = read_json(root / str(envelope_ref)) if envelope_ref else None
        if not isinstance(envelope, dict):
            envelope = {}
        role_artifacts = envelope.get("role_artifacts") or {}
        artifact_previews = {
            key: preview
            for key, value in role_artifacts.items()
            if isinstance(value, str)
            for preview in [safe_artifact_preview(root, value)]
            if preview
        }
        invocations.append(
            {
                "invocation_id": receipt.get("invocation_id") or receipt_path.parent.name,
                "goal": envelope.get("goal") or receipt.get("goal") or "",
                "created_at": receipt.get("created_at") or envelope.get("created_at") or "",
                "overall_status": receipt.get("overall_status") or "unknown",
                "next_action": receipt.get("next_action") or "",
                "session_envelope": envelope_ref or "",
                "role_statuses": envelope.get("role_statuses") or receipt.get("role_statuses") or {},
                "role_artifacts": role_artifacts,
                "artifact_previews": artifact_previews,
                "executor_assignment": envelope.get("executor_assignment") or {},
                "degraded_receipt": envelope.get("degraded_receipt") or {},
                "mtime": receipt_path.stat().st_mtime,
            }
        )
    invocations.sort(key=lambda row: (row.get("created_at") or "", row.get("mtime") or 0), reverse=True)
    for row in invocations:
        row.pop("mtime", None)
    return {"latest": invocations[:5]}


def safe_promotion_ref(root: Path, path: Path) -> str:
    try:
        return path.resolve().relative_to(root.resolve()).as_posix()
    except ValueError:
        return path.as_posix()


def load_latest_asks(root: Path) -> dict[str, Any]:
    base = root / ".aios" / "asks"
    if not base.exists():
        return {"latest": [], "total": 0}
    rows: list[dict[str, Any]] = []
    for receipt_path in base.glob("*/receipt.json"):
        receipt = read_json(receipt_path)
        if not isinstance(receipt, dict) or receipt.get("schema_version") != "aios.ask.receipt.v1":
            continue
        paths = receipt.get("artifact_paths") if isinstance(receipt.get("artifact_paths"), dict) else {}
        goal_ref = str(paths.get("goal") or "")
        goal_payload = read_json(root / goal_ref) if goal_ref else None
        if not isinstance(goal_payload, dict):
            goal_payload = {}
        materialization = read_json(receipt_path.parent / "materialization.json")
        if not isinstance(materialization, dict) or materialization.get("schema_version") != "aios.ask_contract_materialization.v1":
            materialization = {}
        rows.append(
            {
                "ask_id": receipt.get("ask_id") or receipt_path.parent.name,
                "created_at": receipt.get("created_at") or goal_payload.get("created_at") or "",
                "goal": receipt.get("goal") or goal_payload.get("goal") or "",
                "status": receipt.get("status") or "unknown",
                "invocation_status": receipt.get("invocation_status") or "",
                "next_action": receipt.get("next_action") or "",
                "role_statuses": receipt.get("invocation_role_statuses") if isinstance(receipt.get("invocation_role_statuses"), dict) else {},
                "receipt": safe_promotion_ref(root, receipt_path),
                "goal_ref": goal_ref,
                "instruction": str(paths.get("instruction") or ""),
                "praxis": str(paths.get("praxis") or ""),
                "contract_seed": str(paths.get("contract_seed") or ""),
                "invocation_receipt": str(paths.get("invocation_receipt") or ""),
                "materialized_contract_id": materialization.get("contract_id") or "",
                "materialized_contract": materialization.get("contract_path") or "",
                "materialization_receipt": safe_promotion_ref(root, receipt_path.parent / "materialization.json") if materialization else "",
                "mtime": receipt_path.stat().st_mtime,
            }
        )
    rows.sort(key=lambda row: (row.get("created_at") or "", row.get("mtime") or 0), reverse=True)
    for row in rows:
        row.pop("mtime", None)
    return {"latest": rows[:5], "total": len(rows)}


def offline_user_title(packet: dict[str, Any]) -> str:
    for key in ("question", "task", "summary", "observed", "expected"):
        value = packet.get(key)
        if value:
            return str(value)
    return str(packet.get("packet_type") or "offline user packet")


def offline_user_next_action(packet: dict[str, Any]) -> str:
    packet_type = str(packet.get("packet_type") or "")
    if packet_type == "unknown.frontier.question":
        return "route frontier through GenesisOS/CapabilityOS before guessing"
    if packet_type == "user.offline_task":
        return "wait for bounded user@offline observation"
    if packet_type == "field_observation":
        return "send to MemoryOS draft review"
    if packet_type == "contradiction":
        return "open follow-up contract candidate"
    return "inspect packet"


def load_offline_user_memory_draft_index(root: Path) -> dict[str, dict[str, Any]]:
    draft_path = root / ".aios" / "chat" / "offline-user" / "memory_drafts.json"
    payload = read_json(draft_path)
    drafts = payload.get("memory_drafts") if isinstance(payload, dict) else None
    if not isinstance(drafts, list):
        return {}
    source_artifact = safe_promotion_ref(root, draft_path)
    review_index = load_memory_draft_review_index(root)
    evidence_index = load_memory_review_evidence_index(root)
    rows: dict[str, dict[str, Any]] = {}
    for index, draft in enumerate(drafts):
        if not isinstance(draft, dict):
            continue
        draft_id = str(draft.get("id") or f"offline-user:{index}")
        raw_refs = [str(ref) for ref in draft.get("raw_refs") or [] if isinstance(ref, str)]
        provenance = draft.get("provenance") if isinstance(draft.get("provenance"), dict) else {}
        source_packet = str(provenance.get("source_packet") or "")
        content = " ".join(str(draft.get("content") or "").split())
        for packet_ref in raw_refs + ([source_packet] if source_packet else []):
            if not packet_ref:
                continue
            review = review_index.get((source_artifact, draft_id), {})
            evidence = evidence_index.get((source_artifact, draft_id), {})
            rows[packet_ref] = {
                "memory_draft_title": content[:260],
                "memory_draft_created_at": str(provenance.get("created_at") or ""),
                "memory_draft_next_question": str(provenance.get("next_question") or ""),
                "memory_draft_source": source_artifact,
                "memory_draft_id": draft_id,
                "memory_draft_type": str(draft.get("type") or "memory_draft"),
                "memory_review_state": review.get("review_state") or "operator_review_required",
                "memory_review_result": review.get("review_result") or "",
                "memory_review_request_id": review.get("request_id") or "",
                "memory_review_result_ref": review.get("review_result_ref") or "",
                "evidence_count": int(evidence.get("evidence_count") or 0),
                "latest_evidence_ref": evidence.get("latest_evidence_ref") or "",
                "latest_evidence_note": evidence.get("latest_evidence_note") or "",
                "latest_evidence_artifact": evidence.get("latest_evidence_artifact") or "",
                "latest_evidence_at": evidence.get("latest_evidence_at") or "",
            }
    return rows


def load_offline_user_packets(root: Path) -> dict[str, Any]:
    inbox = root / ".aios" / "inbox" / "memoryOS"
    memory_draft_index = load_offline_user_memory_draft_index(root)
    rows: list[dict[str, Any]] = []
    matched_packet_refs: set[str] = set()
    for packet_path in inbox.glob("*.json") if inbox.exists() else []:
        packet = read_json(packet_path)
        if not isinstance(packet, dict):
            continue
        if packet.get("schema_version") != "aios.offline_user_agent_packet.v1":
            continue
        review_policy = packet.get("review_policy") if isinstance(packet.get("review_policy"), dict) else {}
        packet_ref = safe_promotion_ref(root, packet_path)
        matched_packet_refs.add(packet_ref)
        rows.append(
            {
                "packet_type": packet.get("packet_type") or "unknown",
                "contract_id": packet.get("contract_id") or "",
                "created_at": packet.get("created_at") or "",
                "status": packet.get("status") or "draft",
                "title": offline_user_title(packet),
                "privacy_boundary": packet.get("privacy_boundary") or "",
                "stop_condition": packet.get("stop_condition") or "",
                "next_question": packet.get("next_question") or "",
                "next_action": offline_user_next_action(packet),
                "path": packet_ref,
                "draft_first": review_policy.get("draft_first") is True,
                "auto_accept": review_policy.get("auto_accept") is True,
                "mtime": packet_path.stat().st_mtime,
                **memory_draft_index.get(packet_ref, {}),
            }
        )
    for packet_ref, draft_row in memory_draft_index.items():
        if packet_ref in matched_packet_refs:
            continue
        draft_type = str(draft_row.get("memory_draft_type") or "field_observation")
        if draft_type != "field_observation":
            continue
        rows.append(
            {
                "packet_type": "field_observation",
                "contract_id": "ASC-0210",
                "created_at": draft_row.get("memory_draft_created_at") or "",
                "status": "draft",
                "title": draft_row.get("memory_draft_title") or "offline user field observation",
                "privacy_boundary": "",
                "stop_condition": "",
                "next_question": draft_row.get("memory_draft_next_question") or "",
                "next_action": offline_user_next_action({"packet_type": "field_observation"}),
                "path": draft_row.get("memory_draft_source") or packet_ref,
                "source_packet": packet_ref,
                "draft_first": True,
                "auto_accept": False,
                "mtime": (root / str(draft_row.get("memory_draft_source") or "")).stat().st_mtime
                if (root / str(draft_row.get("memory_draft_source") or "")).exists()
                else 0,
                **draft_row,
            }
        )
    rows.sort(key=lambda row: (row.get("created_at") or "", row.get("mtime") or 0), reverse=True)
    for row in rows:
        row.pop("mtime", None)
    return {"latest": rows[:5], "total": len(rows)}


def next_contract_id(root: Path) -> str:
    highest = 0
    for path in (root / "docs" / "contracts").glob("ASC-*.md"):
        match = re.match(r"ASC-(\d{4})", path.name)
        if match:
            highest = max(highest, int(match.group(1)))
    return f"ASC-{highest + 1:04d}"


def parse_iso(value: Any) -> str:
    return str(value or "")


def visual_focus_url_for(url: str) -> str:
    parsed = urllib.parse.urlsplit(url)
    if not parsed.fragment or "=" in parsed.fragment:
        return ""
    query = urllib.parse.parse_qs(parsed.query, keep_blank_values=True)
    query["visual_focus"] = [parsed.fragment]
    encoded = urllib.parse.urlencode(query, doseq=True)
    return urllib.parse.urlunsplit((parsed.scheme, parsed.netloc, parsed.path, encoded, ""))


def visual_receipt_index(root: Path) -> list[dict[str, Any]]:
    base = root / ".aios" / "visual_verification"
    if not base.exists():
        return []
    rows: list[dict[str, Any]] = []
    for path in base.glob("*/receipt.json"):
        payload = read_json(path)
        if not isinstance(payload, dict) or payload.get("schema_version") != "aios.visual_verification.v1":
            continue
        rows.append(
            {
                "path": safe_promotion_ref(root, path),
                "status": payload.get("status") or "",
                "url": payload.get("url") or "",
                "created_at": parse_iso(payload.get("created_at")),
                "screenshot_path": payload.get("screenshot_path") or "",
                "stop_conditions": payload.get("stop_conditions") if isinstance(payload.get("stop_conditions"), list) else [],
            }
        )
    rows.sort(key=lambda row: row.get("created_at") or "")
    return rows


def visual_promotion_quality(root: Path, receipt: dict[str, Any], visual_rows: list[dict[str, Any]]) -> dict[str, Any]:
    source = receipt.get("source") if isinstance(receipt.get("source"), dict) else {}
    if source.get("kind") != "visual_verification_receipt":
        if receipt.get("materialization_recommended") is False:
            return {
                "quality_state": "needs_revision",
                "quality_reason": ", ".join(str(item) for item in receipt.get("quality_warnings") or []) or "promotion_quality_warning",
                "quality_evidence": "",
            }
        return {"quality_state": "actionable", "quality_reason": "", "quality_evidence": ""}

    source_ref = str(source.get("ref") or "")
    source_receipt = read_json(root / source_ref) if source_ref else {}
    source_url = str(source_receipt.get("url") or "")
    source_created = parse_iso(source_receipt.get("created_at"))
    for row in visual_rows:
        if row.get("status") == "passed" and row.get("url") == source_url and row.get("created_at", "") > source_created:
            return {
                "quality_state": "solved_by_later_receipt",
                "quality_reason": "same visual verification URL passed after this promotion source",
                "quality_evidence": row.get("path") or "",
            }

    focus_url = visual_focus_url_for(source_url)
    if focus_url:
        passed_focus = [row for row in visual_rows if row.get("status") == "passed" and row.get("url") == focus_url]
        if passed_focus:
            evidence = sorted(passed_focus, key=lambda row: row.get("created_at") or "")[-1]
            return {
                "quality_state": "mitigated_by_visual_focus",
                "quality_reason": "hash-scroll visual issue has a passing visual_focus harness receipt",
                "quality_evidence": evidence.get("path") or "",
            }
    return {"quality_state": "actionable_visual_fix", "quality_reason": "latest source visual receipt remains degraded or failed", "quality_evidence": source_ref}


def load_promotions(root: Path) -> dict[str, Any]:
    base = root / ".aios" / "promotions"
    if not base.exists():
        return {"items": [], "total": 0, "next_contract_id": next_contract_id(root)}
    visual_rows = visual_receipt_index(root)
    items: list[dict[str, Any]] = []
    for receipt_path in sorted(base.glob("*/promotion.json")):
        try:
            receipt_path.resolve().relative_to(base.resolve())
        except ValueError:
            continue
        receipt = read_json(receipt_path)
        if not isinstance(receipt, dict) or receipt.get("schema_version") != "aios.session_promotion.v1":
            continue
        paths = receipt.get("artifact_paths") if isinstance(receipt.get("artifact_paths"), dict) else {}
        session_envelope = receipt.get("session_envelope") if isinstance(receipt.get("session_envelope"), dict) else {}
        materialization = read_json(receipt_path.parent / "materialization.json")
        if not isinstance(materialization, dict) or materialization.get("schema_version") != "aios.promotion_contract_materialization.v1":
            materialization = {}
        quality = visual_promotion_quality(root, receipt, visual_rows)
        items.append(
            {
                "promotion_id": receipt.get("promotion_id") or receipt_path.parent.name,
                "status": receipt.get("status") or "unknown",
                "goal": receipt.get("goal") or "",
                "created_at": receipt.get("created_at") or "",
                "session_envelope_ref": session_envelope.get("ref") or "",
                "contract_seed": paths.get("contract_seed") or "",
                "dispatch_preview": paths.get("dispatch_preview") or "",
                "receipt": safe_promotion_ref(root, receipt_path),
                "materialized_contract_id": materialization.get("contract_id") or "",
                "materialized_contract": materialization.get("contract_path") or "",
                "materialization_receipt": safe_promotion_ref(root, receipt_path.parent / "materialization.json") if materialization else "",
                "next_action": receipt.get("next_action") or "",
                "next_contract_id": next_contract_id(root),
                "execution_started": bool(receipt.get("execution_started")),
                "stop_conditions": receipt.get("stop_conditions") if isinstance(receipt.get("stop_conditions"), list) else [],
                "quality_state": quality.get("quality_state") or "actionable",
                "quality_reason": quality.get("quality_reason") or "",
                "quality_evidence": quality.get("quality_evidence") or "",
                "mtime": receipt_path.stat().st_mtime,
            }
        )
    items.sort(key=lambda row: (row.get("created_at") or "", row.get("mtime") or 0), reverse=True)
    for row in items:
        row.pop("mtime", None)
    return {"items": items[:8], "total": len(items), "next_contract_id": next_contract_id(root)}


def load_memory_draft_review_index(root: Path) -> dict[tuple[str, str], dict[str, Any]]:
    index: dict[tuple[str, str], dict[str, Any]] = {}
    def newer_or_equal(candidate: str, existing: dict[str, Any]) -> bool:
        existing_ts = str(existing.get("reviewed_at") or existing.get("requested_at") or "")
        return not existing_ts or str(candidate or "") >= existing_ts

    for row in read_jsonl_rows(root / ".aios" / "state" / "memory_draft_reviews.jsonl"):
        source = str(row.get("source_artifact") or "")
        draft_id = str(row.get("draft_id") or "")
        if not source or not draft_id:
            continue
        key = (source, draft_id)
        requested_at = str(row.get("created_at") or "")
        if not newer_or_equal(requested_at, index.get(key, {})):
            continue
        index[key] = {
            "request_id": row.get("request_id") or "",
            "request_status": row.get("status") or "sent",
            "review_state": "review_requested",
            "review_result": "",
            "review_result_ref": ((row.get("artifact_paths") or {}).get("return_to") or ""),
            "requested_at": requested_at,
        }

    outbox = root / ".aios" / "outbox" / "memoryOS"
    if not outbox.exists():
        return index
    for result_path in outbox.glob("mdrev-*.memoryOS.result.json"):
        payload = read_json(result_path)
        if not isinstance(payload, dict):
            continue
        review = payload.get("review_request") if isinstance(payload.get("review_request"), dict) else {}
        source = str(review.get("source_artifact") or "")
        draft_id = str(review.get("draft_id") or "")
        if not source or not draft_id:
            continue
        key = (source, draft_id)
        existing = index.get(key, {})
        reviewed_at = str(payload.get("executed_at") or "")
        if not newer_or_equal(reviewed_at, existing):
            continue
        decision = str(review.get("review_decision") or "")
        index[key] = {
            **existing,
            "request_id": review.get("request_id") or payload.get("dispatch_id") or existing.get("request_id") or "",
            "request_status": payload.get("status") or existing.get("request_status") or "unknown",
            "review_state": "review_result_ready" if payload.get("status") == "passed" else "review_result_attention",
            "review_result": decision,
            "review_result_ref": safe_promotion_ref(root, result_path),
            "reviewed_at": reviewed_at,
        }
    return index


def memory_review_guidance(decision: str) -> dict[str, str]:
    normalized = str(decision or "").strip()
    if normalized == "needs_more_evidence":
        return {
            "review_reason": "MemoryOS kept this candidate as draft because the evidence is not strong enough for durable memory.",
            "next_evidence": "Add a corroborating artifact, an operator review note, or repeated future turns that point to the same pattern before accepting it.",
        }
    if normalized == "accept":
        return {
            "review_reason": "MemoryOS judged the draft acceptable for the review lifecycle.",
            "next_evidence": "Operator can approve or cite this memory with provenance; no automatic acceptance is implied by the UI.",
        }
    if normalized == "reject":
        return {
            "review_reason": "MemoryOS judged this candidate unsuitable for durable memory.",
            "next_evidence": "Keep the rejection as negative evidence and avoid routing future decisions through this claim.",
        }
    if normalized:
        return {
            "review_reason": f"MemoryOS returned review decision `{normalized}`.",
            "next_evidence": "Open the review result artifact before using this draft as evidence.",
        }
    return {
        "review_reason": "",
        "next_evidence": "",
    }


def load_memory_review_evidence_index(root: Path) -> dict[tuple[str, str], dict[str, Any]]:
    index: dict[tuple[str, str], dict[str, Any]] = {}
    for row in read_jsonl_rows(root / ".aios" / "state" / "memory_review_evidence.jsonl"):
        source = str(row.get("source_artifact") or "")
        draft_id = str(row.get("draft_id") or "")
        if not source or not draft_id:
            continue
        key = (source, draft_id)
        existing = index.setdefault(
            key,
            {
                "evidence_count": 0,
                "latest_evidence_ref": "",
                "latest_evidence_note": "",
                "latest_evidence_artifact": "",
                "latest_evidence_at": "",
            },
        )
        created_at = str(row.get("created_at") or "")
        existing["evidence_count"] = int(existing.get("evidence_count") or 0) + 1
        if created_at >= str(existing.get("latest_evidence_at") or ""):
            paths = row.get("artifact_paths") if isinstance(row.get("artifact_paths"), dict) else {}
            existing["latest_evidence_ref"] = paths.get("evidence") or ""
            existing["latest_evidence_note"] = str(row.get("note") or "")[:220]
            existing["latest_evidence_artifact"] = str(row.get("evidence_artifact") or "")
            existing["latest_evidence_at"] = created_at
    return index


def load_chat_memory_draft_queue(root: Path) -> dict[str, Any]:
    base = root / ".aios" / "chat"
    if not base.exists():
        return {"items": [], "total": 0, "counts": {}, "latest_created_at": ""}

    review_index = load_memory_draft_review_index(root)
    evidence_index = load_memory_review_evidence_index(root)
    items: list[dict[str, Any]] = []
    type_counts: Counter[str] = Counter()
    latest_created_at = ""
    for draft_path in base.glob("*/memory_drafts.json"):
        try:
            resolved = draft_path.resolve()
            resolved.relative_to(base.resolve())
        except ValueError:
            continue
        if not resolved.is_file() or resolved.stat().st_size > 300_000:
            continue
        payload = read_json(resolved)
        drafts = payload.get("memory_drafts") if isinstance(payload, dict) else None
        if not isinstance(drafts, list):
            continue
        conversation_id = draft_path.parent.name
        rel_path = safe_promotion_ref(root, draft_path)
        for index, draft in enumerate(drafts):
            if not isinstance(draft, dict):
                continue
            status = str(draft.get("status") or "draft")
            if status not in {"draft", "proposed", "pending_review"}:
                continue
            provenance = draft.get("provenance") if isinstance(draft.get("provenance"), dict) else {}
            created_at = str(provenance.get("created_at") or "")
            if created_at > latest_created_at:
                latest_created_at = created_at
            draft_type = str(draft.get("type") or "memory_draft")
            type_counts[draft_type] += 1
            content = " ".join(str(draft.get("content") or "").split())
            raw_refs = [str(ref) for ref in draft.get("raw_refs") or [] if isinstance(ref, str)]
            resolved_draft_id = str(draft.get("id") or f"{conversation_id}:{index}")
            review_state = review_index.get((rel_path, resolved_draft_id), {})
            evidence_state = evidence_index.get((rel_path, resolved_draft_id), {})
            guidance = memory_review_guidance(str(review_state.get("review_result") or ""))
            items.append(
                {
                    "draft_id": resolved_draft_id,
                    "conversation_id": str(draft.get("conversation_id") or conversation_id),
                    "type": draft_type,
                    "origin": str(draft.get("origin") or "unknown"),
                    "status": status,
                    "confidence": draft.get("confidence"),
                    "content_preview": content[:260],
                    "truncated": len(content) > 260,
                    "created_at": created_at,
                    "source_artifact": rel_path,
                    "raw_refs": raw_refs[:5],
                    "genesis_ref": str(provenance.get("genesis_ref") or ""),
                    "review_state": review_state.get("review_state") or "operator_review_required",
                    "review_request_id": review_state.get("request_id") or "",
                    "review_result": review_state.get("review_result") or "",
                    "review_reason": review_state.get("review_reason") or guidance["review_reason"],
                    "next_evidence": review_state.get("next_evidence") or guidance["next_evidence"],
                    "review_result_ref": review_state.get("review_result_ref") or "",
                    "reviewed_at": review_state.get("reviewed_at") or "",
                    "evidence_count": evidence_state.get("evidence_count") or 0,
                    "latest_evidence_ref": evidence_state.get("latest_evidence_ref") or "",
                    "latest_evidence_note": evidence_state.get("latest_evidence_note") or "",
                    "latest_evidence_artifact": evidence_state.get("latest_evidence_artifact") or "",
                    "latest_evidence_at": evidence_state.get("latest_evidence_at") or "",
                    "mtime": resolved.stat().st_mtime,
                }
            )

    items.sort(key=lambda row: (row.get("created_at") or "", row.get("mtime") or 0), reverse=True)
    for row in items:
        row.pop("mtime", None)
    return {
        "items": items[:12],
        "total": len(items),
        "counts": dict(type_counts),
        "latest_created_at": latest_created_at,
    }


def load_genesis_lens(root: Path, invocations: dict[str, Any]) -> dict[str, Any]:
    for invocation in invocations.get("latest") or []:
        genesis_ref = (invocation.get("role_artifacts") or {}).get("genesis")
        payload = read_json(root / genesis_ref) if isinstance(genesis_ref, str) else None
        if isinstance(payload, dict) and isinstance(payload.get("branches"), list):
            branches = []
            for branch in payload["branches"][:5]:
                if not isinstance(branch, dict):
                    continue
                branches.append(
                    {
                        "branch_id": branch.get("branch_id"),
                        "type": branch.get("type"),
                        "premise": branch.get("premise"),
                        "what_it_breaks": branch.get("what_it_breaks"),
                        "why_it_might_matter": branch.get("why_it_might_matter"),
                        "contract_seed": branch.get("contract_seed"),
                        "risk": branch.get("risk"),
                    }
                )
            return {
                "source_invocation": invocation.get("invocation_id"),
                "source_artifact": genesis_ref,
                "authority": payload.get("authority") or "speculative_only",
                "branches": branches,
                "worldline_preview": build_genesis_worldline_preview(branches, str(genesis_ref or "")),
                "stop_conditions": payload.get("stop_conditions") or [],
            }
    return {"branches": []}


def build_genesis_worldline_preview(branches: list[dict[str, Any]], source_artifact: str = "") -> dict[str, Any]:
    nodes: list[dict[str, Any]] = []
    edges: list[dict[str, str]] = []
    seen: set[str] = set()

    if source_artifact:
        source_id = f"gen_src_{stable_hash(source_artifact)[:10]}"
        nodes.append(
            {
                "id": source_id,
                "type": "source",
                "label": compact_preview(source_artifact, limit=30),
                "detail": source_artifact,
                "state": "clear",
                "x": 86,
                "y": 50,
            }
        )
        seen.add(source_id)
    else:
        source_id = ""

    branch_total = min(len(branches), 5)
    discomfort_count = 0
    seed_count = 0
    for index, branch in enumerate(branches[:5]):
        if not isinstance(branch, dict):
            continue
        branch_id = str(branch.get("branch_id") or f"branch_{index}")
        branch_node_id = f"gen_branch_{stable_hash(branch_id)[:10]}"
        branch_type = str(branch.get("type") or "branch")
        nodes.append(
            {
                "id": branch_node_id,
                "type": "branch",
                "label": compact_preview(branch_type.replace("_", " "), limit=26),
                "detail": compact_preview(branch.get("premise") or branch_id, limit=120),
                "state": "speculative",
                "x": 46,
                "y": distributed_y(index, branch_total),
            }
        )
        seen.add(branch_node_id)

        discomfort = str(branch.get("what_it_breaks") or branch.get("premise") or "")
        if discomfort:
            discomfort_id = f"gen_discomfort_{stable_hash(discomfort)[:10]}"
            if discomfort_id not in seen:
                nodes.append(
                    {
                        "id": discomfort_id,
                        "type": "discomfort",
                        "label": compact_preview(discomfort, limit=28),
                        "detail": discomfort,
                        "state": "attention",
                        "x": 13,
                        "y": distributed_y(discomfort_count, max(branch_total, 1)),
                    }
                )
                discomfort_count += 1
                seen.add(discomfort_id)
            edges.append({"from": discomfort_id, "to": branch_node_id, "kind": "provokes"})

        seed = str(branch.get("contract_seed") or "")
        if seed:
            seed_id = f"gen_seed_{stable_hash(branch_id + seed)[:10]}"
            nodes.append(
                {
                    "id": seed_id,
                    "type": "seed",
                    "label": compact_preview(seed, limit=28),
                    "detail": seed,
                    "state": "held",
                    "x": 68,
                    "y": distributed_y(seed_count, max(branch_total, 1)),
                }
            )
            seed_count += 1
            seen.add(seed_id)
            edges.append({"from": branch_node_id, "to": seed_id, "kind": "invents"})
            if source_id:
                edges.append({"from": seed_id, "to": source_id, "kind": "evidence"})
        elif source_id:
            edges.append({"from": branch_node_id, "to": source_id, "kind": "evidence"})

    edges = [edge for edge in edges if edge.get("from") in seen and edge.get("to") in seen][:40]
    return {"nodes": nodes[:24], "edges": edges}


def load_friction_radar(root: Path, monitor: dict[str, Any] | None) -> dict[str, Any]:
    items: list[dict[str, Any]] = []
    for row in (monitor or {}).get("findings", [])[:4]:
        if not isinstance(row, dict):
            continue
        alert = row.get("alert") if isinstance(row.get("alert"), dict) else {}
        contracts = []
        if row.get("code") == "genesis_prompt_prison_advisory":
            for sample in (alert.get("sample") or [])[:3]:
                if not isinstance(sample, dict):
                    continue
                contracts.append(
                    {
                        "contract_id": sample.get("contract_id"),
                        "path": sample.get("path"),
                        "status": sample.get("status"),
                        "confidence": sample.get("confidence"),
                        "escape_vectors": [str(value) for value in (sample.get("escape_vectors") or [])[:4]],
                        "signatures": [
                            {
                                "signature": signature.get("signature"),
                                "evidence": signature.get("evidence"),
                                "escape_vector": signature.get("escape_vector"),
                            }
                            for signature in (sample.get("signatures") or [])[:3]
                            if isinstance(signature, dict)
                        ],
                    }
                )
        weak_personas = []
        if row.get("code") == "persona_axis_advisory":
            persona_axis = monitor.get("persona_axis") if isinstance(monitor, dict) else {}
            if isinstance(persona_axis, dict):
                for weak in (persona_axis.get("weak_personas") or [])[:3]:
                    if isinstance(weak, dict):
                        weak_personas.append(
                            {
                                "score_key": weak.get("score_key"),
                                "score": weak.get("score"),
                                "recommendation": weak.get("recommendation"),
                            }
                        )
        related_dispatches = []
        for dispatch in (alert.get("related_dispatches") or [])[:3]:
            if not isinstance(dispatch, dict):
                continue
            related_dispatches.append(
                {
                    "dispatch_id": dispatch.get("dispatch_id"),
                    "contract_id": dispatch.get("contract_id"),
                    "current_contract_status": dispatch.get("current_contract_status"),
                    "latest_status": dispatch.get("latest_status"),
                    "latest_reason": dispatch.get("latest_reason"),
                    "latest_timestamp": dispatch.get("latest_timestamp"),
                }
            )
        items.append(
            {
                "source": "monitor",
                "code": row.get("code"),
                "owner": row.get("owner") or "myworld",
                "severity": row.get("severity") or "info",
                "need": row.get("action") or "review",
                "reason": row.get("reason") or "",
                "alert_entries": [str(entry) for entry in (alert.get("entries") or [])[:5]],
                "contracts": contracts,
                "weak_personas": weak_personas,
                "related_dispatches": related_dispatches,
            }
        )
    if not items:
        for row in (monitor or {}).get("next_actions", [])[:4]:
            if not isinstance(row, dict):
                continue
            items.append(
                {
                    "source": "monitor",
                    "owner": row.get("owner") or "myworld",
                    "severity": row.get("severity") or "info",
                    "need": row.get("action") or "review",
                    "reason": row.get("reason") or "",
                    "alert_entries": [],
                    "contracts": [],
                    "weak_personas": [],
                    "related_dispatches": [],
                }
            )
    if not items:
        items.append(
            {
                "source": "control_center",
                "owner": "myworld",
                "severity": "info",
                "need": "continue_conversation",
                "reason": "Ask AIOS for the next step, or turn the current conversation into governed work.",
                "alert_entries": [],
                "contracts": [],
                "weak_personas": [],
                "related_dispatches": [],
            }
        )
    return {"items": items}


def load_memory_observatory(root: Path) -> dict[str, Any]:
    base = root / "memoryOS"
    memory = base / "memory"
    ontology = base / "ontology"
    objects_path = memory / "objects.jsonl"
    reviews_path = memory / "reviews.jsonl"
    retrieval_path = memory / "retrieval_traces.jsonl"
    graph_control_path = memory / "graph_control_runs.jsonl"
    hyperedges_path = ontology / "hyperedges.jsonl"
    sources_path = memory / "sources.jsonl"

    object_rows = read_jsonl_rows(objects_path)
    objects_by_id = {str(row.get("id")): row for row in object_rows if row.get("id")}
    object_statuses = {str(row.get("id")): str(row.get("status") or "unknown") for row in object_rows if row.get("id")}
    review_rows = read_jsonl_rows(reviews_path)
    latest_review = ""
    for row in review_rows:
        captured_at = str(row.get("captured_at") or "")
        if captured_at > latest_review:
            latest_review = captured_at
        memory_object_id = str(row.get("memory_object_id") or "")
        if memory_object_id and row.get("new_status"):
            object_statuses[memory_object_id] = str(row.get("new_status"))
    status_counts = Counter(object_statuses.values())
    traces = read_jsonl_rows(retrieval_path)
    graph_control_rows = read_jsonl_rows(graph_control_path)
    selected_trace_count = sum(1 for row in traces if row.get("selected"))
    source_rows = read_jsonl_rows(sources_path)
    sources_by_id = {str(row.get("id")): row for row in source_rows if row.get("id")}

    def selected_memory_ids(row: dict[str, Any]) -> list[str]:
        selected = row.get("selected")
        ids: list[str] = []
        if isinstance(selected, list):
            for item in selected:
                if isinstance(item, dict):
                    memory_id = str(item.get("id") or item.get("memory_object_id") or "")
                else:
                    memory_id = str(item or "")
                if memory_id and memory_id not in ids:
                    ids.append(memory_id)
        attrs = row.get("attrs") if isinstance(row.get("attrs"), dict) else {}
        selected_ids = attrs.get("selected_ids") or []
        if isinstance(selected_ids, list):
            for item in selected_ids:
                memory_id = str(item or "")
                if memory_id and memory_id not in ids:
                    ids.append(memory_id)
        return ids

    def selected_payload(row: dict[str, Any]) -> dict[str, dict[str, Any]]:
        payloads: dict[str, dict[str, Any]] = {}
        selected = row.get("selected")
        if isinstance(selected, list):
            for item in selected:
                if not isinstance(item, dict):
                    continue
                memory_id = str(item.get("id") or item.get("memory_object_id") or "")
                if memory_id:
                    payloads[memory_id] = item
        return payloads

    def memory_card(memory_id: str, trace_payload: dict[str, Any] | None = None) -> dict[str, Any]:
        payload = trace_payload or {}
        obj = objects_by_id.get(memory_id, {})
        attrs = obj.get("attrs") if isinstance(obj.get("attrs"), dict) else {}
        source_id = str(payload.get("source_artifact_id") or obj.get("source_artifact_id") or attrs.get("source_artifact_id") or "")
        source = sources_by_id.get(source_id, {})
        raw_refs = [str(ref) for ref in obj.get("raw_refs") or [] if isinstance(ref, str)]
        source_path = str(source.get("path") or (raw_refs[0] if raw_refs else ""))
        return {
            "id": memory_id,
            "status": str(payload.get("status") or obj.get("status") or object_statuses.get(memory_id) or "unknown"),
            "confidence": payload.get("confidence") if payload.get("confidence") is not None else obj.get("confidence"),
            "evidence_state": str(payload.get("evidence_state") or obj.get("evidence_state") or "unknown"),
            "content_preview": compact_preview(obj.get("content") or "(memory object not found)", limit=220),
            "source_artifact_id": source_id,
            "source_path": source_path,
            "source_kind": str(source.get("kind") or ""),
            "review_record_id": str(payload.get("last_review_record_id") or attrs.get("last_review_record_id") or ""),
            "raw_refs": raw_refs[:3],
        }

    recent_traces: list[dict[str, Any]] = []
    for trace in list(reversed(traces))[:5]:
        ids = selected_memory_ids(trace)
        payloads = selected_payload(trace)
        attrs = trace.get("attrs") if isinstance(trace.get("attrs"), dict) else {}
        explain = attrs.get("explain") if isinstance(attrs.get("explain"), dict) else {}
        recent_traces.append(
            {
                "id": str(trace.get("id") or ""),
                "created_at": str(trace.get("created_at") or ""),
                "query": compact_preview(trace.get("query") or trace.get("task"), limit=180),
                "role": str(trace.get("role") or ""),
                "privacy_filter": str(trace.get("privacy_filter") or ""),
                "signal_coverage": trace.get("signal_coverage"),
                "selected_count": len(ids),
                "selected_ids": ids[:10],
                "candidate_counts": explain.get("candidate_counts") if isinstance(explain.get("candidate_counts"), dict) else {},
                "selected_memories": [memory_card(memory_id, payloads.get(memory_id)) for memory_id in ids[:4]],
            }
        )

    def distributed_y(index: int, total: int) -> int:
        if total <= 1:
            return 50
        return int(18 + (index * (64 / max(total - 1, 1))))

    def graph_preview() -> dict[str, Any]:
        graph_nodes: list[dict[str, Any]] = []
        graph_edges: list[dict[str, str]] = []
        seen_nodes: set[str] = set()
        selected_ids: list[str] = []
        trace_ids: list[str] = []

        for trace in recent_traces[:3]:
            trace_id = str(trace.get("id") or "")
            if not trace_id:
                continue
            trace_ids.append(trace_id)
            for memory_id in trace.get("selected_ids") or []:
                memory_id = str(memory_id)
                if memory_id and memory_id not in selected_ids:
                    selected_ids.append(memory_id)
                graph_edges.append({"from": trace_id, "to": memory_id, "kind": "retrieved"})

        if not selected_ids:
            for row in object_rows[:8]:
                memory_id = str(row.get("id") or "")
                if memory_id:
                    selected_ids.append(memory_id)

        selected_ids = selected_ids[:10]
        trace_ids = trace_ids[:3]

        for index, trace_id in enumerate(trace_ids):
            trace = next((row for row in recent_traces if row.get("id") == trace_id), {})
            graph_nodes.append(
                {
                    "id": trace_id,
                    "type": "trace",
                    "label": trace_id.replace("rtrace_", "r:")[:18],
                    "detail": compact_preview(trace.get("query"), limit=90),
                    "x": 13,
                    "y": distributed_y(index, len(trace_ids)),
                }
            )
            seen_nodes.add(trace_id)

        source_ids: list[str] = []
        for index, memory_id in enumerate(selected_ids):
            card = memory_card(memory_id)
            graph_nodes.append(
                {
                    "id": memory_id,
                    "type": "memory",
                    "status": card.get("status"),
                    "label": memory_id.replace("mem_", "m:")[:18],
                    "detail": card.get("content_preview"),
                    "x": 50,
                    "y": distributed_y(index, len(selected_ids)),
                }
            )
            seen_nodes.add(memory_id)
            source_path = str(card.get("source_path") or "")
            if source_path:
                source_id = f"src_{stable_hash(source_path)[:10]}"
                graph_edges.append({"from": memory_id, "to": source_id, "kind": "provenance"})
                if source_id not in source_ids:
                    source_ids.append(source_id)
                    sources_by_id[source_id] = {"path": source_path, "kind": card.get("source_kind") or "artifact"}

        for index, source_id in enumerate(source_ids[:6]):
            source = sources_by_id.get(source_id, {})
            graph_nodes.append(
                {
                    "id": source_id,
                    "type": "source",
                    "label": compact_preview(source.get("path") or source_id, limit=22),
                    "detail": str(source.get("kind") or "source"),
                    "x": 86,
                    "y": distributed_y(index, min(len(source_ids), 6)),
                }
            )
            seen_nodes.add(source_id)

        graph_edges = [
            edge
            for edge in graph_edges
            if edge.get("from") in seen_nodes and edge.get("to") in seen_nodes
        ][:24]
        return {"nodes": graph_nodes[:20], "edges": graph_edges}

    nodes = count_lines(memory / "processed" / "nodes.jsonl")
    edges = count_lines(ontology / "edges.jsonl")
    memory_objects = len(object_rows) if object_rows else count_lines(objects_path)
    reviews = len(review_rows) if review_rows else count_lines(reviews_path)
    retrieval_traces = len(traces) if traces else count_lines(retrieval_path)
    hyperedges = count_lines(hyperedges_path)
    sources = count_lines(sources_path)
    latest_graph_control = graph_control_rows[-1] if graph_control_rows else {}
    graph_control_attrs = latest_graph_control.get("attrs") if isinstance(latest_graph_control.get("attrs"), dict) else {}
    graph_control = {
        "run_count": len(graph_control_rows) if graph_control_rows else count_lines(graph_control_path),
        "latest": {
            "id": str(latest_graph_control.get("id") or ""),
            "status": str(graph_control_attrs.get("status") or latest_graph_control.get("status") or "unknown"),
            "captured_at": str(latest_graph_control.get("captured_at") or ""),
            "bound_ratio": latest_graph_control.get("bound_ratio"),
            "raw_ingest_count": latest_graph_control.get("raw_ingest_count"),
            "reclaimed_count": latest_graph_control.get("reclaimed_count"),
            "queryable_surface_count": latest_graph_control.get("queryable_surface_count"),
            "stop_conditions": list(latest_graph_control.get("stop_conditions") or []),
            "halt_auto_consolidation": bool(latest_graph_control.get("halt_auto_consolidation")),
            "provenance_contract_ids": list(graph_control_attrs.get("provenance_contract_ids") or []),
        } if latest_graph_control else {},
    }

    exists = base.exists()
    return {
        "status": "active" if exists and (nodes or memory_objects or retrieval_traces) else ("present" if exists else "missing"),
        "nodes": nodes,
        "edges": edges,
        "memory_objects": memory_objects,
        "accepted": int(status_counts.get("accepted", 0)),
        "draft": int(status_counts.get("draft", 0)),
        "rejected": int(status_counts.get("rejected", 0)),
        "reviews": reviews,
        "retrieval_traces": retrieval_traces,
        "retrieval_traces_with_selected": selected_trace_count,
        "graph_control": graph_control,
        "hyperedges": hyperedges,
        "sources": sources,
        "latest_review_at": latest_review,
        "recent_traces": recent_traces,
        "graph_preview": graph_preview(),
        "headline": f"{int(status_counts.get('accepted', 0))} accepted / {int(status_counts.get('draft', 0))} draft memories from {nodes:,} graph nodes",
        "signals": [
            {"label": "Knowledge graph", "value": nodes, "unit": "nodes"},
            {"label": "Provenance links", "value": edges, "unit": "edges"},
            {"label": "Reviewed memory", "value": int(status_counts.get("accepted", 0)), "unit": "accepted"},
            {"label": "Retrieval traces", "value": retrieval_traces, "unit": "traces"},
        ],
    }


def run_capabilityos(root: Path, *args: str) -> dict[str, Any] | None:
    repo = root / "CapabilityOS"
    if not repo.exists():
        return None
    try:
        result = subprocess.run(
            [sys.executable, "-m", "capabilityos.cli", *args],
            cwd=repo.as_posix(),
            text=True,
            capture_output=True,
            timeout=10,
            check=False,
        )
    except (OSError, subprocess.SubprocessError):
        return None
    if result.returncode != 0:
        return None
    try:
        payload = json.loads(result.stdout)
    except json.JSONDecodeError:
        return None
    return payload if isinstance(payload, dict) else None


def distributed_y(index: int, total: int) -> int:
    if total <= 1:
        return 50
    return int(18 + (index * (64 / max(total - 1, 1))))


def build_capability_route_preview(
    top_routes: list[dict[str, Any]],
    gap_samples: list[dict[str, Any]],
    provider_routes: list[dict[str, Any]],
) -> dict[str, Any]:
    nodes: list[dict[str, Any]] = []
    edges: list[dict[str, str]] = []
    seen: set[str] = set()

    for index, route in enumerate(top_routes[:5]):
        route_id = str(route.get("id") or f"route_{index}")
        nodes.append(
            {
                "id": route_id,
                "type": "route",
                "label": compact_preview(route.get("name") or route_id, limit=28),
                "detail": f"score {route.get('score')} · risk {route.get('risk')} · {route.get('privacy')}",
                "state": "attention" if route.get("requires_network") or str(route.get("risk")) == "high" else "active",
                "x": 14,
                "y": distributed_y(index, min(len(top_routes), 5)),
            }
        )
        seen.add(route_id)

        for fallback_id in (route.get("fallback_ids") or [])[:2]:
            fallback_id = str(fallback_id)
            if fallback_id and fallback_id not in seen:
                nodes.append(
                    {
                        "id": fallback_id,
                        "type": "fallback",
                        "label": fallback_id.replace("cap_", "")[:26],
                        "detail": "fallback candidate",
                        "state": "held",
                        "x": 48,
                        "y": distributed_y(len([node for node in nodes if node.get("type") == "fallback"]), 8),
                    }
                )
                seen.add(fallback_id)
            if fallback_id:
                edges.append({"from": route_id, "to": fallback_id, "kind": "fallback"})

        for evidence_ref in (route.get("evidence_refs") or [])[:1]:
            evidence_ref = str(evidence_ref)
            if not evidence_ref:
                continue
            evidence_id = f"ev_{stable_hash(evidence_ref)[:10]}"
            if evidence_id not in seen:
                nodes.append(
                    {
                        "id": evidence_id,
                        "type": "evidence",
                        "label": compact_preview(evidence_ref.replace("../", ""), limit=30),
                        "detail": evidence_ref,
                        "state": "clear",
                        "x": 84,
                        "y": distributed_y(len([node for node in nodes if node.get("type") == "evidence"]), 8),
                    }
                )
                seen.add(evidence_id)
            edges.append({"from": route_id, "to": evidence_id, "kind": "evidence"})

    for index, gap in enumerate(gap_samples[:4]):
        evidence_ref = str(gap.get("evidence_ref") or "")
        gap_id = f"gap_{stable_hash(str(gap.get('reason') or '') + evidence_ref)[:10]}"
        nodes.append(
            {
                "id": gap_id,
                "type": "gap",
                "label": compact_preview(gap.get("reason") or "gap", limit=24),
                "detail": compact_preview(gap.get("detail") or evidence_ref, limit=100),
                "state": "attention",
                "x": 48,
                "y": distributed_y(index + 4, 8),
            }
        )
        seen.add(gap_id)
        if evidence_ref:
            evidence_id = f"ev_{stable_hash(evidence_ref)[:10]}"
            if evidence_id in seen:
                edges.append({"from": gap_id, "to": evidence_id, "kind": "blocked_by"})

    for index, provider in enumerate(provider_routes[:4]):
        provider_id = f"provider_{str(provider.get('agent') or index)}"
        try:
            provider_failed = int(provider.get("failed") or 0)
        except (TypeError, ValueError):
            provider_failed = 0
        nodes.append(
            {
                "id": provider_id,
                "type": "provider",
                "label": str(provider.get("agent") or "provider"),
                "detail": f"{provider.get('passed', 0)} passed · {provider.get('failed', 0)} failed",
                "state": "attention" if provider_failed else "active",
                "x": 84,
                "y": distributed_y(index + 4, 8),
            }
        )
        seen.add(provider_id)

    edges = [edge for edge in edges if edge.get("from") in seen and edge.get("to") in seen][:32]
    return {"nodes": nodes[:24], "edges": edges}


def load_capability_observatory(root: Path) -> dict[str, Any]:
    listed = run_capabilityos(root, "list", "--json") or {}
    recommended = run_capabilityos(
        root,
        "recommend",
        "--task",
        "visual operating system interface memory search capability route genesis divergence hive execution web api mcp provider fallback",
        "--observations-inbox",
        "../.aios/outbox",
        "--json",
    ) or {}
    observed = run_capabilityos(root, "observe-results", "--inbox", "../.aios/outbox", "--json") or {}
    provider_route = run_capabilityos(
        root,
        "provider-route",
        "--task",
        "AIOS provider fallback after Claude/Codex/Gemini/local failure",
        "--assigned-agent",
        "claude",
        "--observations-inbox",
        "../.aios/outbox",
        "--json",
    ) or {}
    web_route = run_capabilityos(
        root,
        "web-route",
        "--task",
        "latest provider web design references and current API documentation for AIOS interface",
        "--json",
    ) or {}
    constraint_route = run_capabilityos(
        root,
        "constraint-break",
        "--task",
        "AIOS agents blocked by provider instructions, CLI auth, rate limit, missing GUI/browser",
        "--blocker",
        "provider auth/rate limit/prompt constraints reduce autonomy",
        "--json",
    ) or {}
    capabilities = listed.get("capabilities") if isinstance(listed.get("capabilities"), list) else []
    summary = recommended.get("observation_summary") if isinstance(recommended.get("observation_summary"), dict) else {}
    top_routes = []
    for row in (recommended.get("recommendations") or [])[:5]:
        if not isinstance(row, dict):
            continue
        top_routes.append(
            {
                "id": row.get("id"),
                "name": row.get("name"),
                "kind": row.get("kind"),
                "score": row.get("score"),
                "requires_network": bool(row.get("requires_network")),
                "risk": row.get("risk"),
                "privacy": row.get("privacy"),
                "latency": row.get("latency"),
                "observation_count": row.get("observation_count", 0),
                "reason_codes": [str(item) for item in row.get("reason_codes") or []][:6],
                "risk_notes": [str(item) for item in row.get("risk_notes") or []][:5],
                "fallback_ids": [str(item) for item in row.get("fallback_ids") or []][:4],
                "evidence_refs": [str(item) for item in row.get("evidence_refs") or []][:3],
            }
        )
    mode_rows = capability_source_modes(capabilities)
    gaps = observed.get("gaps") if isinstance(observed.get("gaps"), list) else []
    provider_routes = provider_route.get("routes") if isinstance(provider_route.get("routes"), list) else []
    gap_samples = [
        {
            "reason": str(row.get("reason") or ""),
            "detail": compact_preview(row.get("detail"), limit=120),
            "evidence_ref": str((row.get("evidence_refs") or [""])[0]),
            "status": str(row.get("status") or ""),
        }
        for row in gaps[:6]
        if isinstance(row, dict)
    ]
    provider_route_rows = [
        {
            "agent": row.get("agent"),
            "score": row.get("score"),
            "confidence": row.get("confidence"),
            "observations": row.get("observations"),
            "passed": row.get("passed"),
            "failed": row.get("failed"),
            "timeout": row.get("timeout"),
            "reason_codes": [str(item) for item in row.get("reason_codes") or []][:5],
            "evidence_refs": [str(item) for item in row.get("evidence_refs") or []][:2],
        }
        for row in provider_routes[:4]
        if isinstance(row, dict)
    ]
    return {
        "status": "active" if capabilities else ("degraded" if (root / "CapabilityOS").exists() else "missing"),
        "capability_cards": len(capabilities),
        "observations": int(summary.get("observations_count") or 0),
        "gaps": int(summary.get("gaps_count") or 0),
        "result_files": int(summary.get("result_files") or 0),
        "observed_capabilities": int(recommended.get("observed_capabilities") or 0),
        "top_routes": top_routes,
        "source_modes": mode_rows,
        "gap_samples": gap_samples,
        "provider_routes": provider_route_rows,
        "route_preview": build_capability_route_preview(top_routes, gap_samples, provider_route_rows),
        "web_route": {
            "risk_notes": [str(item) for item in web_route.get("risk_notes") or []][:6],
            "route_steps": [
                {
                    "step": str(row.get("step") or ""),
                    "tool_family": str(row.get("tool_family") or ""),
                    "purpose": compact_preview(row.get("purpose"), limit=120),
                    "evidence_required": [str(item) for item in row.get("evidence_required") or []][:4],
                }
                for row in (web_route.get("route_steps") or [])[:4]
                if isinstance(row, dict)
            ],
            "execution_policy": web_route.get("execution_policy") if isinstance(web_route.get("execution_policy"), dict) else {},
        },
        "constraint_route": {
            "freedom_level": constraint_route.get("freedom_level") or "",
            "permission_questions": [
                {
                    "permission_id": str(row.get("permission_id") or ""),
                    "question": compact_preview(row.get("question"), limit=140),
                    "risk": str(row.get("risk") or ""),
                }
                for row in (constraint_route.get("permission_questions") or [])[:4]
                if isinstance(row, dict)
            ],
            "unblock_options": [
                {
                    "option_id": str(row.get("option_id") or ""),
                    "move": compact_preview(row.get("move"), limit=140),
                    "requires_permission": bool(row.get("requires_permission")),
                }
                for row in (constraint_route.get("unblock_options") or [])[:4]
                if isinstance(row, dict)
            ],
            "stop_conditions": [str(item) for item in constraint_route.get("stop_conditions") or []][:5],
        },
        "headline": f"{len(capabilities)} cards, {int(summary.get('observations_count') or 0)} observations, {int(summary.get('gaps_count') or 0)} gaps",
    }


def capability_mode(card: dict[str, Any]) -> str:
    kind = str(card.get("kind") or "").lower()
    domains = {str(item).lower() for item in card.get("domains") or []}
    privacy = str(card.get("privacy") or "").lower()
    if kind == "mcp" or "mcp" in domains:
        return "MCP"
    if kind == "api" or "api" in domains:
        return "API"
    if bool(card.get("requires_network")) or privacy == "remote" or "web" in domains or "internet" in domains:
        return "Web"
    if "provider" in domains or "llm" in domains or "ollama" in domains or "gemini" in domains or "claude" in domains or "codex" in domains:
        return "Provider/LLM"
    if kind == "skill" or "skill" in domains or "plugin" in domains:
        return "Skill/Plugin"
    if kind in {"workflow", "harness", "router", "catalog", "memory"}:
        return "Local OS"
    return "Other"


def capability_source_modes(capabilities: list[Any]) -> list[dict[str, Any]]:
    buckets: dict[str, dict[str, Any]] = {}
    for item in capabilities:
        if not isinstance(item, dict):
            continue
        mode = capability_mode(item)
        bucket = buckets.setdefault(
            mode,
            {
                "mode": mode,
                "count": 0,
                "network": 0,
                "executes_tools": 0,
                "risk_counts": Counter(),
                "privacy_counts": Counter(),
                "top_capabilities": [],
            },
        )
        bucket["count"] += 1
        if item.get("requires_network"):
            bucket["network"] += 1
        if item.get("executes_tools"):
            bucket["executes_tools"] += 1
        bucket["risk_counts"][str(item.get("risk") or "unknown")] += 1
        bucket["privacy_counts"][str(item.get("privacy") or "unknown")] += 1
        if len(bucket["top_capabilities"]) < 4:
            bucket["top_capabilities"].append(str(item.get("id") or item.get("name") or "capability"))
    order = ["Local OS", "Provider/LLM", "Web", "API", "MCP", "Skill/Plugin", "Other"]
    rows: list[dict[str, Any]] = []
    for mode in order:
        bucket = buckets.get(mode)
        if not bucket:
            continue
        rows.append(
            {
                "mode": mode,
                "count": bucket["count"],
                "network": bucket["network"],
                "executes_tools": bucket["executes_tools"],
                "risk_counts": dict(bucket["risk_counts"]),
                "privacy_counts": dict(bucket["privacy_counts"]),
                "top_capabilities": bucket["top_capabilities"],
            }
        )
    return rows


def load_genesis_observatory(root: Path, genesis_lens: dict[str, Any]) -> dict[str, Any]:
    branches = genesis_lens.get("branches") if isinstance(genesis_lens.get("branches"), list) else []
    branch_types = [str(branch.get("type") or branch.get("branch_id") or "branch") for branch in branches if isinstance(branch, dict)]
    return {
        "status": "active" if branches else ("present" if (root / "GenesisOS").exists() else "missing"),
        "branches": len(branches),
        "branch_types": branch_types[:5],
        "authority": genesis_lens.get("authority") or "speculative_only",
        "source_invocation": genesis_lens.get("source_invocation") or "",
        "headline": f"{len(branches)} speculative worldlines" if branches else "No latest worldline artifact",
    }


def load_hive_observatory(root: Path, invocations: dict[str, Any], dispatches: dict[str, Any]) -> dict[str, Any]:
    latest_invocation = ((invocations.get("latest") or [])[:1] or [{}])[0]
    latest_dispatch = ((dispatches.get("latest") or [])[:1] or [{}])[0]
    hive_board = load_hive_board(root)
    return {
        "status": latest_invocation.get("overall_status") or latest_dispatch.get("status") or "waiting",
        "latest_invocation": latest_invocation.get("invocation_id") or "",
        "latest_goal": latest_invocation.get("goal") or latest_dispatch.get("goal") or "",
        "next_action": latest_invocation.get("next_action") or latest_dispatch.get("reason") or "",
        "dispatch_total": dispatches.get("total") or 0,
        "headline": latest_invocation.get("next_action") or "Waiting for executable session evidence",
        "hive_board": hive_board,
    }


def load_myworld_observatory(root: Path, contracts: dict[str, Any], dispatches: dict[str, Any], monitor: dict[str, Any] | None, round_state: dict[str, Any] | None) -> dict[str, Any]:
    installation = load_installation(root, round_state)
    return {
        "status": (monitor or {}).get("health") or "unknown",
        "contracts": contracts.get("total") or 0,
        "dispatches": dispatches.get("total") or 0,
        "round": (round_state or {}).get("status") or (round_state or {}).get("latest_status") or "unknown",
        "installation": installation.get("status"),
        "headline": f"{contracts.get('total') or 0} contracts / AIOS {installation.get('status')}",
    }


def load_os_observatory(
    root: Path,
    *,
    contracts: dict[str, Any],
    dispatches: dict[str, Any],
    invocations: dict[str, Any],
    genesis_lens: dict[str, Any],
    monitor: dict[str, Any] | None,
    round_state: dict[str, Any] | None,
) -> dict[str, Any]:
    memory = load_memory_observatory(root)
    capability = load_capability_observatory(root)
    genesis = load_genesis_observatory(root, genesis_lens)
    hive = load_hive_observatory(root, invocations, dispatches)
    myworld = load_myworld_observatory(root, contracts, dispatches, monitor, round_state)
    lanes = [
        {"id": "myworld", "label": "MyWorld", "role": "Sovereign control", "status": myworld["status"], "headline": myworld["headline"]},
        {"id": "memory", "label": "MemoryOS", "role": "Knowledge graph", "status": memory["status"], "headline": memory["headline"]},
        {"id": "capability", "label": "CapabilityOS", "role": "Search and route planner", "status": capability["status"], "headline": capability["headline"]},
        {"id": "genesis", "label": "GenesisOS", "role": "Worldline generator", "status": genesis["status"], "headline": genesis["headline"]},
        {"id": "hive", "label": "Hive Mind", "role": "Execution wrapper", "status": hive["status"], "headline": hive["headline"]},
    ]
    return {
        "memory": memory,
        "capability": capability,
        "genesis": genesis,
        "hive": hive,
        "myworld": myworld,
        "lanes": lanes,
    }


def load_workbench(root: Path) -> dict[str, Any]:
    """ASC-0181 Packet D — per-product-repo observed evidence for the workbench view."""
    registry = read_json(root / ".aios" / "workbench" / "registry.json")
    repos_meta = (registry or {}).get("repos", {}) if isinstance(registry, dict) else {}
    processed_dir = root / ".aios" / "processed" / "myworld"
    obs_dir = root / ".aios" / "capability_observations"
    repos: list[dict[str, Any]] = []
    for slug in sorted(repos_meta.keys()):
        recaps = sorted(
            p for p in processed_dir.glob(f"product_recap__{slug}__*.json")
            if not p.name.endswith(".receipt.json")
        ) if processed_dir.exists() else []
        sprint_ids: list[str] = []
        for rc in recaps:
            packet = read_json(rc)
            if isinstance(packet, dict) and packet.get("sprint_id"):
                sprint_ids.append(str(packet["sprint_id"]))
        obs = read_json(obs_dir / f"{slug}_capabilities.json")
        caps = []
        if isinstance(obs, dict):
            for c in obs.get("capabilities", []):
                caps.append({
                    "id": c.get("id"),
                    "observation_count": c.get("observation_count", 0),
                    "observed_sprints": c.get("observed_sprints", []),
                })
        repos.append({
            "repo": slug,
            "kind": repos_meta[slug].get("kind", "product_repo"),
            "registered_at": repos_meta[slug].get("registered_at"),
            "note": repos_meta[slug].get("note", ""),
            "sprints_absorbed": len(sprint_ids),
            "sprint_ids": sprint_ids[-12:],
            "observed_capabilities": caps,
        })
    return {
        "schema": "aios.workbench_snapshot.v1",
        "registered_repo_count": len(repos),
        "repos": repos,
    }


def load_completion(root: Path) -> dict[str, Any]:
    """AIOS completion check for the Control Center — see completion with the eyes."""
    import importlib.util

    spec = importlib.util.spec_from_file_location(
        "aios_completion", (root / "scripts" / "aios_completion.py").as_posix())
    if spec is None or spec.loader is None:
        return {"schema": "aios.completion.v1", "verdict": "completion check unavailable"}
    try:
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        return mod.assess(root)
    except Exception as exc:  # noqa: BLE001
        return {"schema": "aios.completion.v1", "verdict": f"completion check failed: {exc}"}


TRANSCENDENCE_ORIGINS = {
    "aios_discomfort_inject",
    "aios_frontier_question",
    "aios_boundary_probe",
}


def build_frontier_queue(root: Path, *, limit: int = 20) -> dict[str, Any]:
    """Surface ASC-0211 L3 Transcendence Engine drafts queued in
    .aios/inbox/memoryOS/. Anticipatory output — visible *before* a peer
    asks. ASC-0211 L4 condition. Read-only projection."""
    inbox = root / ".aios" / "inbox" / "memoryOS"
    rows: list[dict[str, Any]] = []
    if inbox.exists():
        files = sorted(inbox.glob("*.json"), key=lambda p: p.stat().st_mtime, reverse=True)
        for path in files:
            try:
                packet = json.loads(path.read_text(encoding="utf-8", errors="replace"))
            except Exception:
                continue
            draft = packet.get("draft", {}) or {}
            origin = str(draft.get("origin", ""))
            if origin not in TRANSCENDENCE_ORIGINS:
                continue
            provenance = draft.get("provenance", {}) or {}
            rows.append({
                "request_id": packet.get("request_id"),
                "origin": origin,
                "kind": provenance.get("kind", origin.replace("aios_", "")),
                "content": str(draft.get("content", ""))[:400],
                "target": provenance.get("target_id") or provenance.get("memo") or provenance.get("contract_id"),
                "verdict": provenance.get("audit_verdict"),
                "footprint_score": provenance.get("footprint_score"),
                "domain": provenance.get("domain"),
                "memo_slug": provenance.get("memo_slug"),
                "generated_at": provenance.get("generated_at"),
                "path": path.relative_to(root).as_posix(),
            })
            if len(rows) >= limit:
                break
    counts: dict[str, int] = {}
    for r in rows:
        counts[r["origin"]] = counts.get(r["origin"], 0) + 1
    return {
        "schema_version": "aios.frontier_queue.v1",
        "queued": len(rows),
        "by_origin": counts,
        "drafts": rows,
    }


def build_snapshot(root: Path) -> dict[str, Any]:
    monitor = load_monitor(root)
    round_state = load_round(root)
    invocations = load_latest_invocations(root)
    contracts = load_contracts(root)
    dispatches = load_dispatches(root)
    genesis_lens = load_genesis_lens(root, invocations)
    installation = load_installation(root, round_state)
    repos_state = load_repos(root)
    return {
        "schema_version": SCHEMA_VERSION,
        "generated_at": now_iso(),
        "root": root.as_posix(),
        "goals": load_goals(root),
        "contracts": contracts,
        "dispatches": dispatches,
        "repos": repos_state,
        "roster": build_roster(root, dispatches, repos_state),
        "contract_board": build_contract_board(contracts.get("board_rows", []), dispatches),
        "frontier_queue": build_frontier_queue(root),
        "aios_inputs": load_aios_inputs(root),
        "monitor": monitor,
        "installation": installation,
        "round_controller": round_state,
        "stop_lanes": load_stop_lanes(root),
        "invocations": invocations,
        "asks": load_latest_asks(root),
        "offline_user": load_offline_user_packets(root),
        "promotions": load_promotions(root),
        "memory_draft_queue": load_chat_memory_draft_queue(root),
        "genesis_lens": genesis_lens,
        "os_observatory": load_os_observatory(
            root,
            contracts=contracts,
            dispatches=dispatches,
            invocations=invocations,
            genesis_lens=genesis_lens,
            monitor=monitor,
            round_state=round_state,
        ),
        "friction_radar": load_friction_radar(root, monitor),
        "next_actions": (monitor or {}).get("next_actions", []),
        "workbench": load_workbench(root),
        "completion": load_completion(root),
    }


def write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def write_js(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    body = json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True)
    path.write_text(f"window.AIOS_CONTROL_SNAPSHOT = {body};\n", encoding="utf-8")


def check_app_js(root: Path, path: str) -> dict[str, Any]:
    target = root / path
    if not target.exists():
        return {"ok": False, "path": path, "errors": ["app js not found"]}
    text = target.read_text(encoding="utf-8", errors="replace")
    errors: list[str] = []
    for required in (
        "AIOS_CONTROL_SNAPSHOT",
        "renderContracts",
        "renderDispatches",
        "renderRepos",
        "renderRoster",
        "renderContractBoard",
        "renderRoutes",
        "renderOsObservatory",
        "renderInstallation",
        "renderPromotionQueue",
        "renderMemoryDraftQueue",
    ):
        if required not in text:
            errors.append(f"missing marker: {required}")
    try:
        result = subprocess.run(["node", "--check", target.as_posix()], text=True, capture_output=True, timeout=10, check=False)
    except FileNotFoundError:
        result = None
    except (OSError, subprocess.SubprocessError) as exc:
        errors.append(f"node check failed: {exc}")
        result = None
    if result is not None and result.returncode != 0:
        errors.append(result.stderr.strip() or result.stdout.strip() or "node check failed")
    return {"ok": not errors, "path": path, "errors": errors, "node_checked": result is not None}


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", default=".")
    parser.add_argument("--write-json")
    parser.add_argument("--write-js")
    parser.add_argument("--check-app-js")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args(argv)

    root = Path(args.root).resolve()
    if args.check_app_js:
        result = check_app_js(root, args.check_app_js)
        if args.json:
            print(json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True))
        if not result["ok"]:
            raise SystemExit(1)
        return 0

    snapshot = build_snapshot(root)
    if args.write_json:
        write_json(root / args.write_json, snapshot)
    if args.write_js:
        write_js(root / args.write_js, snapshot)
    if args.json or not (args.write_json or args.write_js):
        print(json.dumps(snapshot, ensure_ascii=False, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
