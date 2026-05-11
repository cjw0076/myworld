#!/usr/bin/env python3
"""Bounded AIOS control-plane loop.

The loop makes MyWorld autonomous at the control-plane layer:

- discover contracts
- create dispatch records for accepted contracts
- send repo-specific packets
- collect result packets
- report monitor-style alerts and next actions

It deliberately does not run child repo work. Child repo agents/watchers remain
responsible for consuming inbox packets and writing outbox results.
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

from aios_dispatch import extract_must_produce, extract_verification_commands


REPOS = ("myworld", "hivemind", "memoryOS", "CapabilityOS")
STATE_DIR = Path(".aios/state")
DISPATCH_LOG = STATE_DIR / "dispatches.jsonl"
LOOP_LOG = STATE_DIR / "loop.jsonl"
INBOX_DIR = Path(".aios/inbox")
OUTBOX_DIR = Path(".aios/outbox")


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
    def dispatch_id(self) -> str:
        return re.sub(r"[^a-z0-9]+", "-", self.contract_id.lower()).strip("-")

    @property
    def status(self) -> str:
        return self.frontmatter.get("status") or "unknown"

    @property
    def goal(self) -> str:
        return self.frontmatter.get("goal") or ""


def now_iso() -> str:
    return datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds")


def ensure_layout(root: Path) -> None:
    (root / STATE_DIR).mkdir(parents=True, exist_ok=True)
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
    text = path.read_text(encoding="utf-8")
    frontmatter, body = parse_frontmatter(text)
    return Contract(
        path=path,
        frontmatter=frontmatter,
        body=body,
        repos=extract_bullet_list(body, "repos"),
        allowed_files=extract_bullet_list(body, "allowed_files"),
        forbidden_files=extract_bullet_list(body, "forbidden_files"),
    )


def list_contracts(root: Path) -> list[Contract]:
    return [read_contract(path) for path in sorted((root / "docs/contracts").glob("ASC-*.md"))]


def load_events(root: Path) -> list[dict[str, Any]]:
    path = root / DISPATCH_LOG
    if not path.exists():
        return []
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def append_dispatch_event(root: Path, event: dict[str, Any]) -> None:
    ensure_layout(root)
    event = {"timestamp": now_iso(), **event}
    with (root / DISPATCH_LOG).open("a", encoding="utf-8") as fh:
        fh.write(json.dumps(event, ensure_ascii=False, sort_keys=True) + "\n")


def append_loop_event(root: Path, event: dict[str, Any]) -> None:
    ensure_layout(root)
    event = {"timestamp": now_iso(), **event}
    with (root / LOOP_LOG).open("a", encoding="utf-8") as fh:
        fh.write(json.dumps(event, ensure_ascii=False, sort_keys=True) + "\n")


def dispatch_state(events: list[dict[str, Any]], dispatch_id: str) -> dict[str, Any]:
    state = {"created": False, "sent": set(), "collected": set(), "stopped": False}
    for event in events:
        if event.get("dispatch_id") != dispatch_id:
            continue
        if event.get("event") == "created":
            state["created"] = True
        elif event.get("event") == "sent":
            state["sent"].add(str(event.get("repo")))
        elif event.get("event") == "collected":
            state["collected"].add(str(event.get("repo")))
        elif event.get("event") == "stopped":
            state["stopped"] = True
    return state


def build_packet(root: Path, contract: Contract, repo: str, agent: str = "codex") -> dict[str, Any]:
    verification_commands = [
        {"cwd": command["cwd"], "command": command["line"]}
        for command in extract_verification_commands(contract, repo, root)
    ]
    return {
        "schema_version": "aios.dispatch.v1",
        "result_schema_version": "aios.dispatch.result.v1",
        "dispatch_id": contract.dispatch_id,
        "contract_id": contract.contract_id,
        "contract_path": contract.path.relative_to(root).as_posix(),
        "contract_status": contract.status,
        "target_repo": repo,
        "agent": agent,
        "goal": contract.goal,
        "created_at": now_iso(),
        "status": "sent",
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
            contract.path.relative_to(root).as_posix(),
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
        "return_to": f".aios/outbox/{repo}/{contract.dispatch_id}.{repo}.result.json",
        "stop_conditions": [
            "scope_violation",
            "privacy_violation",
            "missing_required_artifact",
            "test_gate_failed",
            "ownership_conflict",
            "contract_ambiguous",
        ],
    }


def create_dispatch(root: Path, contract: Contract) -> dict[str, Any]:
    append_dispatch_event(
        root,
        {
            "event": "created",
            "dispatch_id": contract.dispatch_id,
            "contract_id": contract.contract_id,
            "contract_path": contract.path.relative_to(root).as_posix(),
            "contract_status": contract.status,
            "goal": contract.goal,
            "repos": contract.repos,
            "allowed_files": contract.allowed_files,
            "forbidden_files": contract.forbidden_files,
            "status": "created",
        },
    )
    return {"action": "create_dispatch", "dispatch_id": contract.dispatch_id, "contract_id": contract.contract_id}


def send_packet(root: Path, contract: Contract, repo: str) -> dict[str, Any]:
    packet = build_packet(root, contract, repo)
    path = root / INBOX_DIR / repo / f"{contract.dispatch_id}.{repo}.json"
    path.write_text(json.dumps(packet, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    append_dispatch_event(
        root,
        {
            "event": "sent",
            "dispatch_id": contract.dispatch_id,
            "contract_id": contract.contract_id,
            "repo": repo,
            "agent": packet["agent"],
            "packet": path.relative_to(root).as_posix(),
            "status": "sent",
        },
    )
    return {
        "action": "send_packet",
        "dispatch_id": contract.dispatch_id,
        "contract_id": contract.contract_id,
        "repo": repo,
        "packet": path.relative_to(root).as_posix(),
    }


def collect_results(root: Path, events: list[dict[str, Any]]) -> list[dict[str, Any]]:
    collected: list[dict[str, Any]] = []
    already = {
        (str(event.get("repo")), str(event.get("result")))
        for event in events
        if event.get("event") == "collected"
    }
    for repo in REPOS:
        for path in sorted((root / OUTBOX_DIR / repo).glob("*.json")):
            rel = path.relative_to(root).as_posix()
            if (repo, rel) in already:
                continue
            try:
                payload = json.loads(path.read_text(encoding="utf-8"))
            except json.JSONDecodeError as exc:
                payload = {"dispatch_id": path.stem.split(".", 1)[0], "status": "invalid_json", "error": str(exc)}
            dispatch_id = str(payload.get("dispatch_id") or path.stem.split(".", 1)[0])
            append_dispatch_event(
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
            collected.append({"action": "collect_result", "dispatch_id": dispatch_id, "repo": repo, "result": rel})
    return collected


def plan_once(root: Path, *, apply: bool) -> dict[str, Any]:
    ensure_layout(root)
    before_events = load_events(root)
    actions: list[dict[str, Any]] = []
    observations: list[dict[str, Any]] = []

    if apply:
        actions.extend(collect_results(root, before_events))
    else:
        already_collected = {
            (str(event.get("repo")), str(event.get("result")))
            for event in before_events
            if event.get("event") == "collected"
        }
        for repo in REPOS:
            for path in sorted((root / OUTBOX_DIR / repo).glob("*.json")):
                rel = path.relative_to(root).as_posix()
                if (repo, rel) not in already_collected:
                    actions.append({"action": "would_collect_result", "repo": repo, "result": rel})

    events = load_events(root)
    for contract in list_contracts(root):
        state = dispatch_state(events, contract.dispatch_id)
        if contract.status == "proposed":
            observations.append(
                {
                    "contract_id": contract.contract_id,
                    "status": contract.status,
                    "next": "operator_accept_revise_or_cancel",
                }
            )
            continue
        if contract.status == "closed":
            observations.append({"contract_id": contract.contract_id, "status": "closed", "next": "archive_or_next_contract"})
            continue
        if contract.status != "accepted":
            observations.append({"contract_id": contract.contract_id, "status": contract.status, "next": "checkpoint_unknown_status"})
            continue

        target_repos = contract.repos or []
        if not target_repos:
            observations.append(
                {
                    "contract_id": contract.contract_id,
                    "status": contract.status,
                    "next": "checkpoint_missing_repos",
                }
            )
            continue

        if not state["created"]:
            action = {"action": "would_create_dispatch", "dispatch_id": contract.dispatch_id, "contract_id": contract.contract_id}
            if apply:
                action = create_dispatch(root, contract)
                events = load_events(root)
                state = dispatch_state(events, contract.dispatch_id)
            actions.append(action)

        invalid_repos = [repo for repo in target_repos if repo not in REPOS]
        if invalid_repos:
            observations.append({"contract_id": contract.contract_id, "next": "checkpoint_invalid_repos", "repos": invalid_repos})
            continue
        for repo in target_repos:
            if repo in state["sent"]:
                continue
            action = {
                "action": "would_send_packet",
                "dispatch_id": contract.dispatch_id,
                "contract_id": contract.contract_id,
                "repo": repo,
            }
            if apply:
                action = send_packet(root, contract, repo)
                events = load_events(root)
                state = dispatch_state(events, contract.dispatch_id)
            actions.append(action)

        pending = sorted(set(target_repos) - set(state["collected"]))
        next_action = "await_results" if pending else "ready_for_closeout"
        observations.append(
            {
                "contract_id": contract.contract_id,
                "status": contract.status,
                "dispatch_id": contract.dispatch_id,
                "pending_results": pending,
                "next": next_action,
            }
        )

    snapshot = {
        "schema_version": "aios.loop.v1",
        "generated_at": now_iso(),
        "mode": "apply" if apply else "plan",
        "actions": actions,
        "observations": observations,
    }
    append_loop_event(root, snapshot)
    return snapshot


def cmd_once(args: argparse.Namespace) -> int:
    root = Path.cwd().resolve()
    data = plan_once(root, apply=args.apply)
    if args.json:
        print(json.dumps(data, ensure_ascii=False, indent=2, sort_keys=True))
    else:
        print(f"mode={data['mode']} actions={len(data['actions'])} observations={len(data['observations'])}")
        for action in data["actions"]:
            print(f"- {action['action']}: {action}")
        for observation in data["observations"]:
            print(f"- observe: {observation}")
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Run one bounded AIOS control-plane loop")
    sub = parser.add_subparsers(dest="cmd", required=True)
    once = sub.add_parser("once", help="plan or apply one control-plane loop iteration")
    once.add_argument("--apply", action="store_true", help="write dispatch/collect state")
    once.add_argument("--json", action="store_true")
    once.set_defaults(func=cmd_once)
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    return int(args.func(args))


if __name__ == "__main__":
    sys.exit(main())
