#!/usr/bin/env python3
"""Build a local AIOS control-plane snapshot for the static control app."""

from __future__ import annotations

import argparse
import json
import os
import re
import shutil
import subprocess
import sys
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
            }
        )
    counts = Counter(row["status"] for row in rows)
    latest = sorted(rows, key=lambda row: row["id"], reverse=True)[:10]
    return {"counts": dict(counts), "latest": latest, "total": len(rows)}


def first_heading(body: str) -> str:
    for line in body.splitlines():
        if line.startswith("# "):
            return line[2:].strip()
    return ""


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
        rows.append({**entry, "sent": sorted(entry["sent"]), "collected": sorted(entry["collected"])})
    rows.sort(key=lambda row: row.get("timestamp") or "", reverse=True)
    counts = Counter(row["status"] for row in rows)
    return {"counts": dict(counts), "latest": rows[:12], "timeline": timeline[-30:], "total": len(rows)}


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


def load_gate_chair_runtime(root: Path) -> dict[str, Any]:
    pack = read_json(root / ".aios" / "gate" / "founder" / "gate_pack.json")
    active_pack = isinstance(pack, dict) and pack.get("schema_version") == "aios.gate.pack.v1" and pack.get("status") == "active"
    config = load_gate_chair_runtime_config(root)
    candidate_config = load_gate_chair_candidate_config(root)
    config_active = bool(config and config.get("status") == "active")
    env_command = os.environ.get("AIOS_GATE_AGENT_COMMAND", "").strip()
    ollama_path = shutil.which("ollama")
    latest = latest_gate_chair_turn(root)
    if config_active and config.get("mode") == "internal_evidence_synthesizer":
        mode = "internal_evidence_synthesizer"
        state = "internal"
        detail = "chair_runtime.json"
    elif config_active and config.get("mode") == "ollama":
        mode = "ollama" if ollama_path else "internal_evidence_synthesizer"
        state = "external" if ollama_path else "internal"
        model = config.get("model") or "qwen2.5:7b"
        detail = f"chair_runtime.json model={model}" if ollama_path else f"chair_runtime.json requested ollama model={model}; command missing"
    elif config_active and config.get("mode") in PROVIDER_CHAIR_MODES:
        requested = str(config.get("mode"))
        provider_path = shutil.which(requested)
        mode = requested if provider_path else "internal_evidence_synthesizer"
        state = "external" if provider_path else "internal"
        model = config.get("model") or ""
        model_text = f" model={model}" if model else ""
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
    return {
        "enabled": bool(active_pack),
        "state": state if active_pack else "disabled",
        "mode": mode,
        "detail": detail,
        "gate_pack_id": pack.get("id") if isinstance(pack, dict) else "",
        "gate_pack_active": bool(active_pack),
        "runtime_config": config,
        "runtime_config_active": config_active,
        "candidate_config": candidate_config,
        "candidate_config_active": bool(candidate_config),
        "latest_turn": latest,
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


def load_promotions(root: Path) -> dict[str, Any]:
    base = root / ".aios" / "promotions"
    if not base.exists():
        return {"items": [], "total": 0}
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
                "next_action": receipt.get("next_action") or "",
                "execution_started": bool(receipt.get("execution_started")),
                "stop_conditions": receipt.get("stop_conditions") if isinstance(receipt.get("stop_conditions"), list) else [],
                "mtime": receipt_path.stat().st_mtime,
            }
        )
    items.sort(key=lambda row: (row.get("created_at") or "", row.get("mtime") or 0), reverse=True)
    for row in items:
        row.pop("mtime", None)
    return {"items": items[:8], "total": len(items)}


def load_memory_draft_review_index(root: Path) -> dict[tuple[str, str], dict[str, Any]]:
    index: dict[tuple[str, str], dict[str, Any]] = {}
    for row in read_jsonl_rows(root / ".aios" / "state" / "memory_draft_reviews.jsonl"):
        source = str(row.get("source_artifact") or "")
        draft_id = str(row.get("draft_id") or "")
        if not source or not draft_id:
            continue
        index[(source, draft_id)] = {
            "request_id": row.get("request_id") or "",
            "request_status": row.get("status") or "sent",
            "review_state": "review_requested",
            "review_result": "",
            "review_result_ref": ((row.get("artifact_paths") or {}).get("return_to") or ""),
            "requested_at": row.get("created_at") or "",
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
        decision = str(review.get("review_decision") or "")
        index[key] = {
            **existing,
            "request_id": review.get("request_id") or payload.get("dispatch_id") or existing.get("request_id") or "",
            "request_status": payload.get("status") or existing.get("request_status") or "unknown",
            "review_state": "review_result_ready" if payload.get("status") == "passed" else "review_result_attention",
            "review_result": decision,
            "review_result_ref": safe_promotion_ref(root, result_path),
            "reviewed_at": payload.get("executed_at") or "",
        }
    return index


def load_chat_memory_draft_queue(root: Path) -> dict[str, Any]:
    base = root / ".aios" / "chat"
    if not base.exists():
        return {"items": [], "total": 0, "counts": {}, "latest_created_at": ""}

    review_index = load_memory_draft_review_index(root)
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
                    "review_result_ref": review_state.get("review_result_ref") or "",
                    "reviewed_at": review_state.get("reviewed_at") or "",
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
                "stop_conditions": payload.get("stop_conditions") or [],
            }
    return {"branches": []}


def load_friction_radar(root: Path, monitor: dict[str, Any] | None) -> dict[str, Any]:
    items: list[dict[str, Any]] = []
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
    hyperedges_path = ontology / "hyperedges.jsonl"
    sources_path = memory / "sources.jsonl"

    object_rows = read_jsonl_rows(objects_path)
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
    selected_trace_count = sum(1 for row in traces if row.get("selected"))

    nodes = count_lines(memory / "processed" / "nodes.jsonl")
    edges = count_lines(ontology / "edges.jsonl")
    memory_objects = len(object_rows) if object_rows else count_lines(objects_path)
    reviews = len(review_rows) if review_rows else count_lines(reviews_path)
    retrieval_traces = len(traces) if traces else count_lines(retrieval_path)
    hyperedges = count_lines(hyperedges_path)
    sources = count_lines(sources_path)

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
        "hyperedges": hyperedges,
        "sources": sources,
        "latest_review_at": latest_review,
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


def load_capability_observatory(root: Path) -> dict[str, Any]:
    listed = run_capabilityos(root, "list", "--json") or {}
    recommended = run_capabilityos(
        root,
        "recommend",
        "--task",
        "visual operating system interface memory search capability route genesis divergence hive execution",
        "--observations-inbox",
        "../.aios/outbox",
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
                "score": row.get("score"),
                "requires_network": bool(row.get("requires_network")),
                "risk": row.get("risk"),
                "observation_count": row.get("observation_count", 0),
            }
        )
    return {
        "status": "active" if capabilities else ("degraded" if (root / "CapabilityOS").exists() else "missing"),
        "capability_cards": len(capabilities),
        "observations": int(summary.get("observations_count") or 0),
        "gaps": int(summary.get("gaps_count") or 0),
        "result_files": int(summary.get("result_files") or 0),
        "observed_capabilities": int(recommended.get("observed_capabilities") or 0),
        "top_routes": top_routes,
        "headline": f"{len(capabilities)} cards, {int(summary.get('observations_count') or 0)} observations, {int(summary.get('gaps_count') or 0)} gaps",
    }


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


def build_snapshot(root: Path) -> dict[str, Any]:
    monitor = load_monitor(root)
    round_state = load_round(root)
    invocations = load_latest_invocations(root)
    contracts = load_contracts(root)
    dispatches = load_dispatches(root)
    genesis_lens = load_genesis_lens(root, invocations)
    installation = load_installation(root, round_state)
    return {
        "schema_version": SCHEMA_VERSION,
        "generated_at": now_iso(),
        "root": root.as_posix(),
        "goals": load_goals(root),
        "contracts": contracts,
        "dispatches": dispatches,
        "repos": load_repos(root),
        "aios_inputs": load_aios_inputs(root),
        "monitor": monitor,
        "installation": installation,
        "round_controller": round_state,
        "stop_lanes": load_stop_lanes(root),
        "invocations": invocations,
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
