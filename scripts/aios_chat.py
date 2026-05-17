#!/usr/bin/env python3
"""Persistent AIOS chat CLI.

This is a thin user-facing wrapper around `aios_chat_router.py`. The router
owns substrate selection, persistence, memory drafts, and cost records.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

import aios_chat_router


SCHEMA_VERSION = "aios.chat.cli.v1"


def canonical_json(data: Any) -> str:
    return json.dumps(data, ensure_ascii=False, indent=2, sort_keys=True)


def list_conversations(root: Path) -> dict[str, Any]:
    base = root / ".aios" / "chat"
    rows = []
    if base.exists():
        for path in sorted(base.iterdir()):
            if not path.is_dir():
                continue
            messages = aios_chat_router.read_jsonl(path / "messages.jsonl")
            cost = aios_chat_router.read_json(path / "cost.json")
            rows.append(
                {
                    "conversation_id": path.name,
                    "messages": len(messages),
                    "total_cost_usd": (cost or {}).get("total_cost_usd") if isinstance(cost, dict) else 0.0,
                    "path": path.relative_to(root).as_posix(),
                }
            )
    return {"schema_version": SCHEMA_VERSION, "status": "ok", "conversations": rows}


def run_repl(root: Path, conversation: str) -> int:
    print(f"AIOS chat conversation={conversation}. Type /exit to quit.")
    while True:
        try:
            message = input("aios> ").strip()
        except EOFError:
            print()
            return 0
        if message in {"/exit", "/quit"}:
            return 0
        if not message:
            continue
        result = aios_chat_router.route_turn(root, message, conversation)
        print(result["response"])


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=Path.cwd())
    parser.add_argument("--conversation", "--resume", dest="conversation", default="default")
    parser.add_argument("--message", help="run a single chat turn instead of opening the REPL")
    parser.add_argument("--list", action="store_true", help="list persisted conversations")
    parser.add_argument("--json", action="store_true")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    root = args.root.resolve()
    if args.list:
        payload = list_conversations(root)
        print(canonical_json(payload) if args.json else "\n".join(row["conversation_id"] for row in payload["conversations"]))
        return 0
    if args.message is not None:
        result = aios_chat_router.route_turn(root, args.message, args.conversation)
        print(canonical_json(result) if args.json else result["response"])
        return 0
    if args.json:
        print(canonical_json({"schema_version": SCHEMA_VERSION, "status": "repl_requires_tty", "conversation_id": args.conversation}))
        return 2
    return run_repl(root, args.conversation)


if __name__ == "__main__":
    raise SystemExit(main())
