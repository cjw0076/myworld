#!/usr/bin/env python3
"""File-based AIOS dispatch control-plane CLI.

This script only writes myworld control-plane packets under `.aios/`. It does
not execute child repo work and does not edit child repo files.
"""

from __future__ import annotations

import argparse
import json
import re
import shlex
import subprocess
import sys
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from aios_action_policy import evaluate_action


REPOS = ("myworld", "hivemind", "memoryOS", "CapabilityOS")
STATE_DIR = Path(".aios/state")
STATE_LOG = STATE_DIR / "dispatches.jsonl"
INBOX_DIR = Path(".aios/inbox")
OUTBOX_DIR = Path(".aios/outbox")
LOG_DIR = Path(".aios/logs")
TERMINAL_STATES = ("released", "held", "retried", "escalated")
STATE_COMMANDS = {
    "release": "released",
    "hold": "held",
    "retry": "retried",
    "escalate": "escalated",
}
SHELL_META = (";", "&&", "||", "|", "`", "$(", ">", "<")


@dataclass(frozen=True)
class Contract:
    path: Path
    frontmatter: dict[str, str]
    body: str
    repos: list[str]
    allowed_files: list[str]
    forbidden_files: list[str]

    @property
    def contract_id(self) -> str:
        return self.frontmatter.get("contract_id") or self.path.stem.split("-", 1)[0]

    @property
    def status(self) -> str:
        return self.frontmatter.get("status") or "unknown"

    @property
    def goal(self) -> str:
        return self.frontmatter.get("goal") or ""


def now_iso() -> str:
    return datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds")


def repo_root() -> Path:
    return Path.cwd().resolve()


def ensure_layout(root: Path) -> None:
    (root / STATE_DIR).mkdir(parents=True, exist_ok=True)
    (root / LOG_DIR).mkdir(parents=True, exist_ok=True)
    for repo in REPOS:
        (root / INBOX_DIR / repo).mkdir(parents=True, exist_ok=True)
        (root / OUTBOX_DIR / repo).mkdir(parents=True, exist_ok=True)


def parse_frontmatter(text: str) -> tuple[dict[str, str], str]:
    if not text.startswith("---\n"):
        return {}, text
    end = text.find("\n---\n", 4)
    if end == -1:
        return {}, text
    raw = text[4:end]
    body = text[end + 5 :]
    data: dict[str, str] = {}
    current_key: str | None = None
    for line in raw.splitlines():
        if not line.strip():
            continue
        if line.startswith((" ", "\t")) and current_key:
            data[current_key] = f"{data[current_key]} {line.strip()}".strip()
            continue
        key, sep, value = line.partition(":")
        if sep:
            current_key = key.strip()
            data[current_key] = value.strip()
    return data, body


def extract_bullet_list(body: str, label: str) -> list[str]:
    lines = body.splitlines()
    values: list[str] = []
    collecting = False
    for line in lines:
        stripped = line.strip()
        if stripped == f"{label}:":
            collecting = True
            continue
        if not collecting:
            continue
        if not stripped:
            if values:
                break
            continue
        if stripped.startswith("- "):
            values.append(stripped[2:].strip().strip("`"))
            continue
        if values:
            break
    return values


def read_contract(path: Path) -> Contract:
    if not path.exists():
        raise SystemExit(f"contract not found: {path}")
    text = path.read_text(encoding="utf-8")
    frontmatter, body = parse_frontmatter(text)
    repos = extract_bullet_list(body, "repos")
    allowed_files = extract_bullet_list(body, "allowed_files")
    forbidden_files = extract_bullet_list(body, "forbidden_files")
    return Contract(
        path=path,
        frontmatter=frontmatter,
        body=body,
        repos=repos,
        allowed_files=allowed_files,
        forbidden_files=forbidden_files,
    )


def append_event(root: Path, event: dict[str, Any]) -> None:
    ensure_layout(root)
    event = {"timestamp": now_iso(), **event}
    with (root / STATE_LOG).open("a", encoding="utf-8") as fh:
        fh.write(json.dumps(event, ensure_ascii=False, sort_keys=True) + "\n")


def load_events(root: Path) -> list[dict[str, Any]]:
    path = root / STATE_LOG
    if not path.exists():
        return []
    events = []
    for line in path.read_text(encoding="utf-8").splitlines():
        if line.strip():
            events.append(json.loads(line))
    return events


def latest_dispatch_id(root: Path) -> str | None:
    for event in reversed(load_events(root)):
        dispatch_id = event.get("dispatch_id")
        if dispatch_id:
            return str(dispatch_id)
    return None


def dispatch_created(root: Path, dispatch_id: str) -> dict[str, Any] | None:
    for event in reversed(load_events(root)):
        if event.get("dispatch_id") == dispatch_id and event.get("event") == "created":
            return event
    return None


def latest_dispatch_event(root: Path, dispatch_id: str) -> dict[str, Any] | None:
    for event in reversed(load_events(root)):
        if event.get("dispatch_id") == dispatch_id:
            return event
    return None


def latest_packet(root: Path, repo: str) -> Path | None:
    packets = sorted((root / INBOX_DIR / repo).glob("*.json"), key=lambda path: path.stat().st_mtime)
    return packets[-1] if packets else None


def default_dispatch_id(contract: Contract) -> str:
    safe = re.sub(r"[^a-z0-9]+", "-", contract.contract_id.lower()).strip("-")
    return safe or contract.path.stem


def contains_term(text: str, term: str) -> bool:
    escaped = re.escape(term.lower()).replace(r"\ ", r"\s+")
    return bool(re.search(rf"(?<![a-z0-9_-]){escaped}(?![a-z0-9_-])", text))


def contains_any_term(text: str, terms: tuple[str, ...]) -> bool:
    return any(contains_term(text, term) for term in terms)


def action_policy_input(contract: Contract, dispatch_id: str, repo: str, agent: str) -> dict[str, Any]:
    text = f"{contract.goal}\n{contract.body}".lower()
    public_communication = contains_any_term(text, ("public communication", "public statement", "on behalf"))
    legal_or_safety_impact = contains_any_term(text, ("legal", "medical", "financial", "employment", "safety"))
    uses_credentials = contains_any_term(text, ("credential", "token", "secret", "login"))
    paid_or_costly = contains_any_term(text, ("paid api", "paid", "spend", "billing", "purchase"))
    irreversible = contains_any_term(text, ("irreversible", "delete production", "destructive"))
    real_world_authority = contains_any_term(text, ("real-world authority", "legal authority", "public authority"))
    sends_private_data = contains_any_term(
        text,
        (
            "send private data",
            "sends private data",
            "upload private data",
            "publish private data",
            "send personal data",
            "upload personal data",
            "raw private export publish",
        ),
    )
    external_effect = contains_any_term(
        text,
        (
            "external system",
            "internet search",
            "browse internet",
            "network call",
            "remote api",
            "deploy",
            "paid",
            "credential",
        ),
    )
    return {
        "action_type": "dispatch_packet",
        "target_repo": repo,
        "authority": "accepted_contract" if contract.status in {"accepted", "closed"} else "unaccepted_contract",
        "risk": "high" if any((public_communication, legal_or_safety_impact, paid_or_costly, irreversible, real_world_authority)) else "low",
        "privacy": "remote" if external_effect or sends_private_data else "local",
        "cost": "paid" if paid_or_costly else "free",
        "has_contract": contract.status in {"accepted", "closed"},
        "evidence_refs": [contract.path.as_posix()],
        "human_approved": contract.frontmatter.get("human_approved", "").lower() == "true",
        "irreversible": irreversible,
        "external_effect": external_effect,
        "uses_credentials": uses_credentials,
        "public_communication": public_communication,
        "legal_or_safety_impact": legal_or_safety_impact,
        "real_world_authority": real_world_authority,
        "sends_private_data": sends_private_data,
        "repos": contract.repos,
        "allowed_files": contract.allowed_files,
        "forbidden_files": contract.forbidden_files,
        "dispatch_id": dispatch_id,
        "agent": agent,
    }


def evaluate_dispatch_policy(contract: Contract, dispatch_id: str, repo: str, agent: str) -> dict[str, Any]:
    action = action_policy_input(contract, dispatch_id, repo, agent)
    result = evaluate_action(action).to_json(action)
    return {
        "schema_version": result["schema_version"],
        "decision": result["decision"],
        "allowed_to_execute": result["allowed_to_execute"],
        "required_checkpoint": result["required_checkpoint"],
        "reason_codes": result["reason_codes"],
    }


def append_policy_block(root: Path, contract: Contract, dispatch_id: str, repo: str, agent: str, policy: dict[str, Any]) -> dict[str, Any]:
    decision = str(policy.get("decision"))
    event = "escalated" if decision == "escalate" else "held" if decision == "hold" else "stopped"
    status = event
    append_event(
        root,
        {
            "event": event,
            "dispatch_id": dispatch_id,
            "contract_id": contract.contract_id,
            "repo": repo,
            "agent": agent,
            "reason": f"action_policy_{decision}",
            "policy": policy,
            "status": status,
        },
    )
    return {
        "ok": False,
        "dispatch_id": dispatch_id,
        "repo": repo,
        "status": status,
        "policy": policy,
    }


def repo_aliases(repo: str) -> set[str]:
    aliases = {
        "hivemind": {"hivemind", "hive mind", "hive_mind", "hive"},
        "memoryOS": {"memoryos", "memory os", "memory_os"},
        "CapabilityOS": {"capabilityos", "capability os", "capability_os"},
        "myworld": {"myworld", "my world", "control plane"},
    }
    return aliases.get(repo, {repo.lower()})


def normalize_label(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", " ", value.lower()).strip()


def repo_matches_label(repo: str, label: str) -> bool:
    normalized = normalize_label(label)
    return normalized in repo_aliases(repo)


def bullet_lines(text: str) -> list[str]:
    values: list[str] = []
    current: str | None = None
    for raw in text.splitlines():
        line = raw.rstrip()
        stripped = line.strip()
        if not stripped:
            continue
        if stripped.startswith("- "):
            if current:
                values.append(current)
            current = stripped[2:].strip().strip("`")
        elif current and raw.startswith((" ", "\t")):
            current = f"{current} {stripped}".strip()
        elif current:
            values.append(current)
            current = None
    if current:
        values.append(current)
    return values


def section_after_any_heading(body: str, headings: list[str]) -> str:
    for heading in headings:
        section = section_after_heading(body, heading)
        if section:
            return section
    return ""


def extract_must_produce(contract: Contract, repo: str) -> list[str]:
    section = section_after_any_heading(contract.body, ["Per-OS Responsibility", "Responsibilities"])
    if not section:
        return []

    # Legacy shape: "### Hive Mind" followed by "must_produce:" bullets.
    for match in re.finditer(r"^###\s+(.+?)\s*$", section, flags=re.MULTILINE):
        label = match.group(1).strip()
        start = match.end()
        next_match = re.search(r"^###\s+", section[start:], flags=re.MULTILINE)
        block = section[start : start + next_match.start()] if next_match else section[start:]
        if not repo_matches_label(repo, label):
            continue
        marker = re.search(r"^must_produce:\s*$", block, flags=re.MULTILINE)
        return bullet_lines(block[marker.end() :] if marker else block)

    # Compact shape: "- **capabilityos.must_produce**: item, item, ..."
    for raw in section.splitlines():
        stripped = raw.strip()
        match = re.match(r"-\s+\*\*(.+?)\.must_produce\*\*:\s*(.+)", stripped, flags=re.IGNORECASE)
        if match and repo_matches_label(repo, match.group(1)):
            return [match.group(2).strip()]
    return []


def cmd_create(args: argparse.Namespace) -> int:
    root = repo_root()
    contract = read_contract(Path(args.contract))
    dispatch_id = args.dispatch_id or default_dispatch_id(contract)
    if dispatch_created(root, dispatch_id) and not args.force:
        raise SystemExit(f"dispatch already exists: {dispatch_id} (use --force to append another create event)")
    ensure_layout(root)
    append_event(
        root,
        {
            "event": "created",
            "dispatch_id": dispatch_id,
            "contract_id": contract.contract_id,
            "contract_path": contract.path.as_posix(),
            "contract_status": contract.status,
            "goal": contract.goal,
            "repos": contract.repos,
            "allowed_files": contract.allowed_files,
            "forbidden_files": contract.forbidden_files,
            "status": "created",
        },
    )
    print(json.dumps({"ok": True, "dispatch_id": dispatch_id, "status": "created"}, ensure_ascii=False))
    return 0


def build_packet(contract: Contract, dispatch_id: str, repo: str, agent: str, policy: dict[str, Any] | None = None) -> dict[str, Any]:
    verification_commands = [
        {"cwd": command["cwd"], "command": command["line"]}
        for command in extract_verification_commands(contract, repo, repo_root())
    ]
    return {
        "schema_version": "aios.dispatch.v1",
        "result_schema_version": "aios.dispatch.result.v1",
        "dispatch_id": dispatch_id,
        "contract_id": contract.contract_id,
        "contract_path": contract.path.as_posix(),
        "contract_status": contract.status,
        "target_repo": repo,
        "agent": agent,
        "goal": contract.goal,
        "created_at": now_iso(),
        "status": "sent",
        "action_policy": policy or evaluate_dispatch_policy(contract, dispatch_id, repo, agent),
        "control_plane": {
            "root": "myworld",
            "rule": "myworld issues packets; child repo agent executes in the owning repo",
        },
        "scope": {
            "repos": contract.repos,
            "allowed_files": contract.allowed_files,
            "forbidden_files": contract.forbidden_files,
        },
        "required_reading": [
            "AGENTS.md",
            "docs/AIOS_NORTHSTAR.md",
            "docs/AIOS_AGENT_PROTOCOL.md",
            "docs/AIOS_SMART_CONTRACT.md",
            "docs/AIOS_WORK_DISPATCH.md",
            "docs/AIOS_BUILD_METHOD.md",
            contract.path.as_posix(),
        ],
        "must_produce": extract_must_produce(contract, repo),
        "verification_commands": verification_commands,
        "result_contract": {
            "schema_version": "aios.dispatch.result.v1",
            "required_fields": [
                "target_repo",
                "dispatch_id",
                "contract_id",
                "status",
                "evidence",
                "stop_conditions_triggered",
            ],
        },
        "return_to": f".aios/outbox/{repo}/{dispatch_id}.{repo}.result.json",
        "stop_conditions": [
            "scope_violation",
            "privacy_violation",
            "missing_required_artifact",
            "test_gate_failed",
            "ownership_conflict",
            "contract_ambiguous",
        ],
    }


def cmd_send(args: argparse.Namespace) -> int:
    root = repo_root()
    dispatch_id = args.dispatch_id or latest_dispatch_id(root)
    if not dispatch_id:
        raise SystemExit("no dispatch found; run create first or pass --dispatch-id")
    created = dispatch_created(root, dispatch_id)
    if not created:
        raise SystemExit(f"dispatch not found: {dispatch_id}")
    contract = read_contract(Path(str(created["contract_path"])))
    repo = args.repo
    if repo not in REPOS:
        raise SystemExit(f"unsupported repo: {repo}")
    if contract.repos and repo not in contract.repos:
        raise SystemExit(f"{repo} is not in contract scope: {', '.join(contract.repos)}")
    if contract.status not in {"accepted", "closed"} and not args.allow_proposed:
        raise SystemExit(
            f"contract {contract.contract_id} is {contract.status}; operator acceptance required before send"
        )
    ensure_layout(root)
    policy = (
        {
            "schema_version": "aios.action_policy.v1",
            "decision": "allow",
            "allowed_to_execute": True,
            "required_checkpoint": False,
            "reason_codes": ["allow_proposed_test_bypass"],
        }
        if args.allow_proposed
        else evaluate_dispatch_policy(contract, dispatch_id, repo, args.agent)
    )
    if policy["decision"] != "allow":
        blocked = append_policy_block(root, contract, dispatch_id, repo, args.agent, policy)
        print(json.dumps(blocked, ensure_ascii=False, indent=2, sort_keys=True))
        return 1
    packet = build_packet(contract, dispatch_id, repo, args.agent, policy=policy)
    packet_path = root / INBOX_DIR / repo / f"{dispatch_id}.{repo}.json"
    if packet_path.exists() and not args.force:
        raise SystemExit(f"packet already exists: {packet_path} (use --force to overwrite)")
    packet_path.write_text(json.dumps(packet, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    append_event(
        root,
        {
            "event": "sent",
            "dispatch_id": dispatch_id,
            "contract_id": contract.contract_id,
            "repo": repo,
            "agent": args.agent,
            "packet": packet_path.relative_to(root).as_posix(),
            "status": "sent",
        },
    )
    print(
        json.dumps(
            {
                "ok": True,
                "dispatch_id": dispatch_id,
                "repo": repo,
                "packet": packet_path.relative_to(root).as_posix(),
                "return_to": packet["return_to"],
            },
            ensure_ascii=False,
        )
    )
    return 0


def summarize(root: Path) -> dict[str, Any]:
    events = load_events(root)
    dispatches: dict[str, dict[str, Any]] = {}
    for event in events:
        dispatch_id = event.get("dispatch_id")
        if not dispatch_id:
            continue
        row = dispatches.setdefault(str(dispatch_id), {"dispatch_id": dispatch_id, "events": 0, "sent": [], "collected": []})
        row["events"] += 1
        if event.get("event") == "created":
            row.update(
                {
                    "contract_id": event.get("contract_id"),
                    "contract_path": event.get("contract_path"),
                    "contract_status": event.get("contract_status"),
                    "goal": event.get("goal"),
                    "status": event.get("status"),
                }
            )
        elif event.get("event") == "sent":
            row["sent"].append(event.get("repo"))
            row["status"] = "sent"
        elif event.get("event") == "collected":
            row["collected"].append(event.get("repo"))
            row["status"] = "collected"
        elif event.get("event") in {"running", "watched"}:
            row["status"] = event.get("status")
            row["repo"] = event.get("repo")
        elif event.get("event") in TERMINAL_STATES:
            row["status"] = event.get("event")
            row["reason"] = event.get("reason")
        elif event.get("event") == "stopped":
            row["status"] = "stopped"
            row["reason"] = event.get("reason")
    inbox_counts = {repo: len(list((root / INBOX_DIR / repo).glob("*.json"))) for repo in REPOS}
    outbox_counts = {repo: len(list((root / OUTBOX_DIR / repo).glob("*.json"))) for repo in REPOS}
    return {"dispatches": list(dispatches.values()), "inbox": inbox_counts, "outbox": outbox_counts}


def cmd_status(args: argparse.Namespace) -> int:
    root = repo_root()
    data = summarize(root)
    if args.json:
        print(json.dumps(data, ensure_ascii=False, indent=2, sort_keys=True))
        return 0
    if not data["dispatches"]:
        print("No dispatches.")
        return 0
    for row in data["dispatches"]:
        sent = ",".join(str(repo) for repo in row.get("sent") or []) or "-"
        collected = ",".join(str(repo) for repo in row.get("collected") or []) or "-"
        print(f"{row['dispatch_id']}: {row.get('status', 'unknown')} contract={row.get('contract_id')} sent={sent} collected={collected}")
    print(f"inbox={data['inbox']} outbox={data['outbox']}")
    return 0


def cmd_collect(args: argparse.Namespace) -> int:
    root = repo_root()
    ensure_layout(root)
    repos = [args.repo] if args.repo else list(REPOS)
    already = {
        (str(event.get("repo")), str(event.get("result")))
        for event in load_events(root)
        if event.get("event") == "collected"
    }
    collected = []
    for repo in repos:
        for path in sorted((root / OUTBOX_DIR / repo).glob("*.json")):
            rel = path.relative_to(root).as_posix()
            if (repo, rel) in already:
                continue
            try:
                payload = json.loads(path.read_text(encoding="utf-8"))
            except json.JSONDecodeError as exc:
                raise SystemExit(f"invalid result JSON: {rel}: {exc}") from exc
            expected_dispatch_id = path.name.removesuffix(f".{repo}.result.json")
            errors = validate_result_packet(payload, repo, expected_dispatch_id)
            if errors:
                raise SystemExit(f"malformed result packet: {rel}: {', '.join(errors)}")
            dispatch_id = str(payload.get("dispatch_id") or path.stem.split(".", 1)[0])
            append_event(
                root,
                {
                    "event": "collected",
                    "dispatch_id": dispatch_id,
                    "repo": repo,
                    "result": rel,
                    "result_status": payload.get("status"),
                    "status": "collected",
                },
            )
            already.add((repo, rel))
            collected.append({"repo": repo, "path": rel, "status": payload.get("status")})
    print(json.dumps({"ok": True, "collected": collected}, ensure_ascii=False, indent=2, sort_keys=True))
    return 0


def validate_result_packet(payload: dict[str, Any], repo: str, expected_dispatch_id: str | None = None) -> list[str]:
    if payload.get("schema_version") != "aios.dispatch.result.v1":
        return []
    required = ["target_repo", "dispatch_id", "contract_id", "status", "evidence", "stop_conditions_triggered"]
    errors = [f"missing {field}" for field in required if field not in payload]
    if payload.get("target_repo") != repo:
        errors.append(f"target_repo {payload.get('target_repo')} != {repo}")
    if expected_dispatch_id and payload.get("dispatch_id") != expected_dispatch_id:
        errors.append(f"dispatch_id {payload.get('dispatch_id')} != {expected_dispatch_id}")
    if not isinstance(payload.get("evidence"), list):
        errors.append("evidence must be a list")
    if not isinstance(payload.get("stop_conditions_triggered"), list):
        errors.append("stop_conditions_triggered must be a list")
    return errors


def append_transition(root: Path, dispatch_id: str, state: str, reason: str) -> None:
    append_event(
        root,
        {
            "event": state,
            "dispatch_id": dispatch_id,
            "reason": reason,
            "status": state,
        },
    )


def maybe_write_closeout_memory(root: Path, dispatch_id: str, reason: str, disabled: bool = False) -> dict[str, Any]:
    if disabled:
        result = {"ok": True, "skipped": True, "reason": "disabled_by_flag"}
        append_event(root, {"event": "memory_writeback", "dispatch_id": dispatch_id, **result})
        return result
    created = dispatch_created(root, dispatch_id)
    if not created:
        result = {"ok": False, "skipped": True, "reason": "missing_created_event"}
        append_event(root, {"event": "memory_writeback", "dispatch_id": dispatch_id, **result})
        return result
    try:
        contract = read_contract(Path(str(created["contract_path"])))
    except (OSError, SystemExit) as exc:
        result = {"ok": False, "skipped": True, "reason": f"contract_unreadable:{exc}"}
        append_event(root, {"event": "memory_writeback", "dispatch_id": dispatch_id, **result})
        return result
    if contract.status != "closed":
        result = {
            "ok": True,
            "skipped": True,
            "reason": f"contract_status_{contract.status}",
            "contract_id": contract.contract_id,
        }
        append_event(root, {"event": "memory_writeback", "dispatch_id": dispatch_id, **result})
        return result
    emitter = root / "scripts" / "aios_contract_to_memory.py"
    memoryos_dir = root / "memoryOS"
    if not emitter.exists() or not memoryos_dir.exists():
        result = {
            "ok": True,
            "skipped": True,
            "reason": "memoryos_or_emitter_missing",
            "contract_id": contract.contract_id,
        }
        append_event(root, {"event": "memory_writeback", "dispatch_id": dispatch_id, **result})
        return result
    emit = subprocess.run(
        [
            sys.executable,
            emitter.as_posix(),
            "emit",
            "--root",
            root.as_posix(),
            "--contract",
            contract.contract_id,
            "--closed-by",
            "aios_dispatch.release",
            "--json",
        ],
        check=False,
        capture_output=True,
        text=True,
    )
    if emit.returncode != 0:
        result = {"ok": False, "skipped": True, "reason": "emit_failed", "stderr": emit.stderr[-500:]}
        append_event(root, {"event": "memory_writeback", "dispatch_id": dispatch_id, "contract_id": contract.contract_id, **result})
        return result
    ingest = subprocess.run(
        [sys.executable, "-m", "memoryos.cli", "--root", memoryos_dir.as_posix(), "ingest-contract-closeout", "--json"],
        input=emit.stdout,
        cwd=memoryos_dir,
        check=False,
        capture_output=True,
        text=True,
    )
    if ingest.returncode != 0:
        result = {"ok": False, "skipped": True, "reason": "ingest_failed", "stderr": ingest.stderr[-500:]}
        append_event(root, {"event": "memory_writeback", "dispatch_id": dispatch_id, "contract_id": contract.contract_id, **result})
        return result
    try:
        payload = json.loads(ingest.stdout)
    except json.JSONDecodeError:
        payload = {}
    result = {
        "ok": True,
        "skipped": False,
        "contract_id": contract.contract_id,
        "draft_id": payload.get("draft_id"),
        "written": payload.get("written"),
        "reason": reason,
    }
    append_event(root, {"event": "memory_writeback", "dispatch_id": dispatch_id, **result})
    return result


def recover_escalated_release(root: Path, dispatch_id: str, reason: str) -> dict[str, Any] | None:
    last_event = latest_dispatch_event(root, dispatch_id)
    if not last_event or last_event.get("event") != "escalated":
        return None
    created = dispatch_created(root, dispatch_id)
    if not created:
        append_event(
            root,
            {
                "event": "release_recovery_failed",
                "dispatch_id": dispatch_id,
                "reason": "missing_created_event",
                "status": "released",
            },
        )
        return {"ok": False, "reason": "missing_created_event"}

    repo = str(last_event.get("repo") or "")
    agent = str(last_event.get("agent") or "codex")
    if repo not in REPOS:
        append_event(
            root,
            {
                "event": "release_recovery_failed",
                "dispatch_id": dispatch_id,
                "reason": f"unsupported_repo:{repo}",
                "status": "released",
            },
        )
        return {"ok": False, "reason": f"unsupported_repo:{repo}"}

    try:
        contract = read_contract(Path(str(created["contract_path"])))
        if contract.repos and repo not in contract.repos:
            raise ValueError(f"{repo} is not in contract scope: {', '.join(contract.repos)}")
        if contract.status not in {"accepted", "closed"}:
            raise ValueError(f"contract {contract.contract_id} is {contract.status}")
        packet_path = root / INBOX_DIR / repo / f"{dispatch_id}.{repo}.json"
        if packet_path.exists():
            return {"ok": True, "skipped": True, "reason": "packet_already_exists", "repo": repo}
        policy = {
            "schema_version": "aios.action_policy.v1",
            "decision": "allow",
            "allowed_to_execute": True,
            "required_checkpoint": False,
            "reason_codes": ["operator_override_after_escalation"],
            "operator_override": True,
            "override_reason": reason,
            "previous_policy": last_event.get("policy"),
        }
        packet = build_packet(contract, dispatch_id, repo, agent, policy=policy)
        packet["operator_override"] = True
        packet["override_reason"] = reason
        packet_path.write_text(json.dumps(packet, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    except (OSError, KeyError, ValueError) as exc:
        append_event(
            root,
            {
                "event": "release_recovery_failed",
                "dispatch_id": dispatch_id,
                "repo": repo,
                "agent": agent,
                "reason": str(exc),
                "status": "released",
            },
        )
        return {"ok": False, "reason": str(exc), "repo": repo}

    append_event(
        root,
        {
            "event": "dispatch.recovery",
            "dispatch_id": dispatch_id,
            "contract_id": contract.contract_id,
            "repo": repo,
            "agent": agent,
            "packet": packet_path.relative_to(root).as_posix(),
            "reason": reason,
            "operator_override": True,
            "status": "sent",
        },
    )
    append_event(
        root,
        {
            "event": "sent",
            "dispatch_id": dispatch_id,
            "contract_id": contract.contract_id,
            "repo": repo,
            "agent": agent,
            "packet": packet_path.relative_to(root).as_posix(),
            "status": "sent",
        },
    )
    return {"ok": True, "repo": repo, "packet": packet_path.relative_to(root).as_posix()}


def cmd_transition(args: argparse.Namespace) -> int:
    root = repo_root()
    dispatch_id = args.dispatch_id or latest_dispatch_id(root)
    if not dispatch_id:
        raise SystemExit("no dispatch found; pass --dispatch-id")
    recovery = recover_escalated_release(root, dispatch_id, args.reason) if args.state == "released" else None
    append_transition(root, dispatch_id, args.state, args.reason)
    memory_writeback = None
    if args.state == "released":
        memory_writeback = maybe_write_closeout_memory(
            root,
            dispatch_id,
            args.reason,
            disabled=getattr(args, "no_memory_write", False),
        )
    print(json.dumps(
        {
            "ok": True,
            "dispatch_id": dispatch_id,
            "status": args.state,
            "recovery": recovery,
            "memory_writeback": memory_writeback,
        },
        ensure_ascii=False,
    ))
    return 0


def cmd_stop(args: argparse.Namespace) -> int:
    root = repo_root()
    dispatch_id = args.dispatch_id or latest_dispatch_id(root)
    if not dispatch_id:
        raise SystemExit("no dispatch found; pass --dispatch-id")
    append_event(
        root,
        {
            "event": "stopped",
            "dispatch_id": dispatch_id,
            "reason": args.reason,
            "status": "stopped",
        },
    )
    print(json.dumps({"ok": True, "dispatch_id": dispatch_id, "status": "stopped"}, ensure_ascii=False))
    return 0


def section_after_heading(body: str, heading: str) -> str:
    match = re.search(rf"^##\s+{re.escape(heading)}\s*$", body, flags=re.MULTILINE)
    if not match:
        return ""
    rest = body[match.end() :]
    next_heading = re.search(r"^##\s+", rest, flags=re.MULTILINE)
    return rest[: next_heading.start()] if next_heading else rest


def bash_blocks(text: str) -> list[str]:
    return re.findall(r"```bash\n(.*?)```", text, flags=re.DOTALL)


def repo_matches_cwd(repo: str, cwd: Path | None, root: Path) -> bool:
    if repo == "myworld":
        return cwd is None or cwd.resolve() == root.resolve() or cwd.name == "myworld"
    return cwd is not None and repo in cwd.parts


def safe_argv(command: str) -> list[str]:
    if any(token in command for token in SHELL_META):
        raise ValueError(f"unsafe shell token in command: {command}")
    argv = shlex.split(command)
    if not argv:
        raise ValueError("empty command")
    executable = Path(argv[0]).name
    if executable not in {"python", "python3", "pytest", "bash", "sleep"}:
        raise ValueError(f"unsupported executable in verification command: {argv[0]}")
    return argv


def extract_verification_commands(contract: Contract, repo: str, root: Path) -> list[dict[str, Any]]:
    gate = section_after_heading(contract.body, "Verification Gate")
    if not gate:
        return []
    gate = gate.split("Operational smoke equivalent:", 1)[0]
    commands: list[dict[str, Any]] = []
    cwd: Path | None = None
    for block in bash_blocks(gate):
        for raw_line in block.splitlines():
            line = raw_line.strip()
            if not line or line.startswith("#"):
                continue
            if line.startswith("cd "):
                target = shlex.split(line)[1]
                cwd = Path(target).expanduser()
                if not cwd.is_absolute():
                    cwd = (root / cwd).resolve()
                continue
            if not repo_matches_cwd(repo, cwd, root):
                continue
            argv = safe_argv(line)
            commands.append({"argv": argv, "cwd": (cwd or root).as_posix(), "line": line})
    return commands


def bounded_lines(text: str, limit: int = 20) -> list[str]:
    lines = text.splitlines()
    if len(lines) <= limit * 2:
        return lines
    return lines[:limit] + ["..."] + lines[-limit:]


def cmd_watch(args: argparse.Namespace) -> int:
    if not args.once:
        raise SystemExit("watch V1 is on-demand only; pass --once")
    root = repo_root()
    ensure_layout(root)
    packet_path = (
        root / INBOX_DIR / args.repo / f"{args.dispatch_id}.{args.repo}.json"
        if args.dispatch_id
        else latest_packet(root, args.repo)
    )
    if not packet_path or not packet_path.exists():
        raise SystemExit(f"packet not found for repo {args.repo}")
    packet = json.loads(packet_path.read_text(encoding="utf-8"))
    dispatch_id = str(packet["dispatch_id"])
    contract = read_contract(Path(str(packet["contract_path"])))
    preflight_stop_conditions: list[str] = []
    try:
        commands = extract_verification_commands(contract, args.repo, root)
    except ValueError as exc:
        commands = []
        preflight_stop_conditions.append("arbitrary_command_execution")
        preflight_error = str(exc)
    else:
        preflight_error = ""
    append_event(
        root,
        {
            "event": "running",
            "dispatch_id": dispatch_id,
            "contract_id": contract.contract_id,
            "repo": args.repo,
            "packet": packet_path.relative_to(root).as_posix(),
            "status": "running",
        },
    )

    log_path = root / LOG_DIR / f"{dispatch_id}.{args.repo}.log"
    evidence: list[dict[str, Any]] = []
    full_log: list[str] = []
    stop_conditions: list[str] = list(preflight_stop_conditions)
    status = "passed"
    if preflight_error:
        status = "held"
        full_log.append(preflight_error)
    elif not commands:
        status = "held"
        stop_conditions.append("missing_verification_command")

    for command in commands:
        completed = subprocess.run(
            command["argv"],
            cwd=command["cwd"],
            text=True,
            capture_output=True,
        )
        full_log.extend(
            [
                f"$ cd {command['cwd']}",
                f"$ {command['line']}",
                f"[exit {completed.returncode}]",
                completed.stdout,
                completed.stderr,
            ]
        )
        evidence.append(
            {
                "cwd": command["cwd"],
                "command": command["line"],
                "returncode": completed.returncode,
                "stdout_summary": bounded_lines(completed.stdout),
                "stderr_summary": bounded_lines(completed.stderr),
            }
        )
        if completed.returncode != 0:
            status = "failed"
            stop_conditions.append("test_gate_failed")
            break

    log_path.write_text("\n".join(full_log), encoding="utf-8")
    result = {
        "schema_version": "aios.dispatch.result.v1",
        "target_repo": args.repo,
        "dispatch_id": dispatch_id,
        "contract_id": contract.contract_id,
        "status": status,
        "executed_at": now_iso(),
        "agent_assigned": packet.get("agent"),
        "agent_executed": "aios_dispatch.watch",
        "executed_reason": "verification_gate",
        "packet": packet_path.relative_to(root).as_posix(),
        "evidence": evidence,
        "log_path": log_path.relative_to(root).as_posix(),
        "stop_conditions_triggered": stop_conditions,
    }
    result_path = root / OUTBOX_DIR / args.repo / f"{dispatch_id}.{args.repo}.result.json"
    result_path.write_text(json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    append_event(
        root,
        {
            "event": "watched",
            "dispatch_id": dispatch_id,
            "contract_id": contract.contract_id,
            "repo": args.repo,
            "result": result_path.relative_to(root).as_posix(),
            "result_status": status,
            "status": status,
        },
    )
    print(json.dumps({"ok": status == "passed", "dispatch_id": dispatch_id, "repo": args.repo, "status": status, "result": result_path.relative_to(root).as_posix()}, ensure_ascii=False))
    return 0 if status == "passed" else 1


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="AIOS control-plane dispatch CLI")
    sub = parser.add_subparsers(dest="cmd", required=True)

    create = sub.add_parser("create", help="create a dispatch from a smart contract")
    create.add_argument("contract")
    create.add_argument("--dispatch-id")
    create.add_argument("--force", action="store_true")
    create.set_defaults(func=cmd_create)

    send = sub.add_parser("send", help="write a work packet to a child repo inbox")
    send.add_argument("--repo", required=True, choices=REPOS)
    send.add_argument("--agent", default="codex")
    send.add_argument("--dispatch-id")
    send.add_argument("--allow-proposed", action="store_true", help="testing only; bypass accepted-contract guard")
    send.add_argument("--force", action="store_true")
    send.set_defaults(func=cmd_send)

    status = sub.add_parser("status", help="show dispatch state")
    status.add_argument("--json", action="store_true")
    status.set_defaults(func=cmd_status)

    collect = sub.add_parser("collect", help="collect result packets from outboxes")
    collect.add_argument("--repo", choices=REPOS)
    collect.set_defaults(func=cmd_collect)

    stop = sub.add_parser("stop", help="mark a dispatch stopped")
    stop.add_argument("--dispatch-id")
    stop.add_argument("--reason", default="operator_checkpoint")
    stop.set_defaults(func=cmd_stop)

    for command_name, state in STATE_COMMANDS.items():
        transition = sub.add_parser(command_name, help=f"mark a dispatch {state}")
        transition.add_argument("--dispatch-id")
        transition.add_argument("--reason", default=f"operator_{state}")
        if command_name == "release":
            transition.add_argument("--no-memory-write", action="store_true", help="skip closed-contract MemoryOS draft writeback")
        transition.set_defaults(func=cmd_transition, state=state)

    watch = sub.add_parser("watch", help="run one packet's verification gate and write a result packet")
    watch.add_argument("--repo", required=True, choices=REPOS)
    watch.add_argument("--dispatch-id")
    watch.add_argument("--once", action="store_true")
    watch.set_defaults(func=cmd_watch)
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        return int(args.func(args))
    except BrokenPipeError:
        return 1


if __name__ == "__main__":
    sys.exit(main())
