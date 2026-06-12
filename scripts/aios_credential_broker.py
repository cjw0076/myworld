#!/usr/bin/env python3
"""AIOS credential broker.

The broker never prints credential values. It turns "I need a key" into a
privacy-safe request receipt so agents can route, checkpoint, or fall back
without repeatedly asking the user to paste secrets into chat.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Final


SCHEMA_VERSION: Final = "aios.credential_broker.v1"
DEFAULT_VAULT_DIR = Path.home() / ".aios" / "vault"
DEFAULT_KEYS: Final = (
    "ANTHROPIC_API_KEY",
    "OPENAI_API_KEY",
    "GEMINI_API_KEY",
    "TAVILY_API_KEY",
)


@dataclass(frozen=True)
class CredentialStatus:
    key: str
    env_present: bool
    vault_initialized: bool
    availability: str
    next_action: str


def now_iso() -> str:
    return datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds")


def vault_dir() -> Path:
    return Path(os.environ.get("AIOS_VAULT_DIR", DEFAULT_VAULT_DIR))


def vault_initialized() -> bool:
    root = vault_dir()
    return (root / "vault.enc").exists() and (root / "vault.salt").exists()


def status_for(key: str) -> CredentialStatus:
    env_present = key in os.environ and bool(os.environ.get(key))
    initialized = vault_initialized()
    if env_present:
        availability = "available_via_env"
        next_action = "route may execute with provider process; do not log value"
    elif initialized:
        availability = "vault_may_hold_value"
        next_action = f"resolve inside trusted provider process via scripts/aios_vault.py get {key}"
    else:
        availability = "missing"
        next_action = f"initialize vault and store key with scripts/aios_vault.py set {key}"
    return CredentialStatus(
        key=key,
        env_present=env_present,
        vault_initialized=initialized,
        availability=availability,
        next_action=next_action,
    )


def safe_request_id(key: str, purpose: str, provider: str) -> str:
    seed = f"{key}\0{purpose}\0{provider}\0{now_iso()}".encode()
    return "credreq-" + hashlib.sha256(seed).hexdigest()[:16]


def status_payload(keys: list[str]) -> dict:
    statuses = [status_for(key) for key in keys]
    return {
        "schema_version": SCHEMA_VERSION,
        "generated_at": now_iso(),
        "vault_initialized": vault_initialized(),
        "credentials": [
            {
                "key": item.key,
                "env_present": item.env_present,
                "vault_initialized": item.vault_initialized,
                "availability": item.availability,
                "next_action": item.next_action,
            }
            for item in statuses
        ],
    }


def request_payload(key: str, purpose: str, provider: str, root: Path) -> dict:
    status = status_for(key)
    request_id = safe_request_id(key, purpose, provider)
    receipt_rel = f".aios/credential_requests/{request_id}.json"
    return {
        "schema_version": SCHEMA_VERSION,
        "request_id": request_id,
        "generated_at": now_iso(),
        "key": key,
        "provider": provider,
        "purpose": purpose[:240],
        "availability": status.availability,
        "env_present": status.env_present,
        "vault_initialized": status.vault_initialized,
        "allowed_to_print_value": False,
        "receipt": receipt_rel,
        "next_action": status.next_action,
        "privacy": {
            "values_redacted": True,
            "raw_provider_logs_allowed": False,
            "chat_secret_request_allowed": False,
        },
        "root": root.as_posix(),
    }


def write_receipt(root: Path, payload: dict) -> Path:
    rel = payload["receipt"]
    path = root / rel
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True), encoding="utf-8")
    return path


def parse_keys(value: str | None) -> list[str]:
    if not value:
        return list(DEFAULT_KEYS)
    return [item.strip() for item in value.split(",") if item.strip()]


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="AIOS privacy-safe credential broker")
    parser.add_argument("--root", default=".")
    parser.add_argument("--json", action="store_true")
    sub = parser.add_subparsers(dest="command")

    p_status = sub.add_parser("status", help="Report credential availability without values")
    p_status.add_argument("--keys", help="Comma-separated key names")

    p_request = sub.add_parser("request", help="Write a credential request receipt")
    p_request.add_argument("key")
    p_request.add_argument("--provider", default="unknown")
    p_request.add_argument("--purpose", default="provider route")
    p_request.add_argument("--write", action="store_true")

    args = parser.parse_args(argv)
    root = Path(args.root).resolve()
    if args.command == "status":
        payload = status_payload(parse_keys(args.keys))
    elif args.command == "request":
        payload = request_payload(args.key, args.purpose, args.provider, root)
        if args.write:
            write_receipt(root, payload)
    else:
        parser.print_help()
        return 2

    if args.json:
        print(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True))
    else:
        if args.command == "status":
            for item in payload["credentials"]:
                print(f"{item['key']}: {item['availability']}")
        else:
            print(f"{payload['request_id']}: {payload['availability']}")
            print(f"next: {payload['next_action']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
