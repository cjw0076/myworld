#!/usr/bin/env python3
"""AIOS agent identity registry.

The registry is machine-local by default (`~/.aios/agents.json`) and mirrored
into the workspace docs so future agents can inspect known identities without
trusting chat history.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


SCHEMA_VERSION = "aios.agent_registry.v1"
ID_PATTERN = re.compile(r"^[A-Za-z0-9_.@-]+$")
DOC_PATH = Path("docs/AIOS_AGENTS_REGISTRY.md")


def now_iso() -> str:
    return datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds")


def registry_home() -> Path:
    configured = os.environ.get("AIOS_AGENT_HOME")
    if configured:
        return Path(configured).expanduser()
    return Path.home() / ".aios"


def registry_path() -> Path:
    return registry_home() / "agents.json"


def empty_registry() -> dict[str, Any]:
    return {"schema_version": SCHEMA_VERSION, "agents": {}, "updated_at": now_iso()}


def load_registry() -> dict[str, Any]:
    path = registry_path()
    if not path.exists():
        return empty_registry()
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError("registry root must be a JSON object")
    agents = payload.get("agents")
    if not isinstance(agents, dict):
        payload["agents"] = {}
    payload.setdefault("schema_version", SCHEMA_VERSION)
    payload.setdefault("updated_at", now_iso())
    return payload


def save_registry(payload: dict[str, Any]) -> None:
    path = registry_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    payload["schema_version"] = SCHEMA_VERSION
    payload["updated_at"] = now_iso()
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def parse_capabilities(raw: str) -> list[str]:
    values = [item.strip() for item in raw.split(",") if item.strip()]
    return sorted(dict.fromkeys(values))


def validate_agent_id(agent_id: str) -> None:
    if not agent_id or not ID_PATTERN.match(agent_id):
        raise ValueError("agent id must use letters, numbers, underscore, dash, dot, or @")


def register_agent(args: argparse.Namespace) -> dict[str, Any]:
    agent_id = args.id.strip()
    validate_agent_id(agent_id)
    capabilities = parse_capabilities(args.capabilities)
    if not capabilities:
        raise ValueError("at least one capability is required")
    payload = load_registry()
    agents = payload.setdefault("agents", {})
    entry = {
        "agent_id": agent_id,
        "substrate": args.substrate.strip(),
        "capabilities": capabilities,
        "public_key_seed": args.public_key_seed,
        "registered_at": agents.get(agent_id, {}).get("registered_at") or now_iso(),
        "registered_by": args.registered_by,
        "updated_at": now_iso(),
    }
    agents[agent_id] = entry
    save_registry(payload)
    write_docs(Path(args.root).resolve(), payload)
    return {"ok": True, "agent": entry, "registry": registry_path().as_posix(), "doc": (Path(args.root) / DOC_PATH).as_posix()}


def list_agents(args: argparse.Namespace) -> dict[str, Any]:
    payload = load_registry()
    agents = sorted(payload.get("agents", {}).values(), key=lambda item: item.get("agent_id", ""))
    return {"schema_version": SCHEMA_VERSION, "registry": registry_path().as_posix(), "agents": agents}


def verify_agent(args: argparse.Namespace) -> dict[str, Any]:
    agent_id = args.agent_id.strip()
    payload = load_registry()
    entry = payload.get("agents", {}).get(agent_id)
    return {
        "schema_version": SCHEMA_VERSION,
        "agent_id": agent_id,
        "valid": bool(entry),
        "entry": entry,
        "reason": "registered" if entry else "unknown_agent",
    }


def current_agent(args: argparse.Namespace) -> dict[str, Any]:
    explicit = os.environ.get("AIOS_AGENT_ID")
    if explicit:
        agent_id = explicit
    elif os.environ.get("CLAUDECODE") or os.environ.get("CLAUDE_CODE"):
        agent_id = "claude@myworld"
    else:
        agent_id = "codex@myworld"
    payload = verify_agent(argparse.Namespace(agent_id=agent_id))
    payload["inferred"] = True
    payload["substrate_hint"] = "env" if explicit else "codex_cli"
    return payload


def write_docs(root: Path, payload: dict[str, Any]) -> None:
    docs_path = root / DOC_PATH
    docs_path.parent.mkdir(parents=True, exist_ok=True)
    agents = sorted(payload.get("agents", {}).values(), key=lambda item: item.get("agent_id", ""))
    lines = [
        "# AIOS Agents Registry",
        "",
        "Machine-local source: `~/.aios/agents.json` or `$AIOS_AGENT_HOME/agents.json`.",
        "",
        "| Agent ID | Substrate | Capabilities | Registered By |",
        "| --- | --- | --- | --- |",
    ]
    for agent in agents:
        lines.append(
            "| {agent_id} | {substrate} | {capabilities} | {registered_by} |".format(
                agent_id=agent.get("agent_id", ""),
                substrate=agent.get("substrate", ""),
                capabilities=", ".join(agent.get("capabilities") or []),
                registered_by=agent.get("registered_by") or "",
            )
        )
    docs_path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def print_payload(args: argparse.Namespace, payload: dict[str, Any]) -> None:
    if args.json:
        print(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True))
    elif "valid" in payload:
        print(f"{payload['agent_id']} valid={str(payload['valid']).lower()} reason={payload['reason']}")
    elif "agents" in payload:
        for agent in payload["agents"]:
            print(agent["agent_id"])
    else:
        print(payload.get("agent", {}).get("agent_id") or "ok")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", default=".")
    sub = parser.add_subparsers(dest="command", required=True)

    register = sub.add_parser("register")
    register.add_argument("--id", required=True)
    register.add_argument("--substrate", required=True)
    register.add_argument("--capabilities", required=True)
    register.add_argument("--public-key-seed")
    register.add_argument("--registered-by", default="self-bootstrap")
    register.add_argument("--json", action="store_true")
    register.set_defaults(func=register_agent)

    list_cmd = sub.add_parser("list")
    list_cmd.add_argument("--json", action="store_true")
    list_cmd.set_defaults(func=list_agents)

    verify = sub.add_parser("verify")
    verify.add_argument("agent_id")
    verify.add_argument("--json", action="store_true")
    verify.set_defaults(func=verify_agent)

    current = sub.add_parser("current")
    current.add_argument("--json", action="store_true")
    current.set_defaults(func=current_agent)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        payload = args.func(args)
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        print(str(exc), file=sys.stderr)
        return 2
    print_payload(args, payload)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
