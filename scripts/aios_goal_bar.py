#!/usr/bin/env python3
"""Deterministic natural-language goal bar router for the AIOS control app."""

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


SCHEMA_VERSION = "aios.goal_bar.v1"
MAX_INPUT_CHARS = 4000
DANGEROUS_PATTERNS = (
    r"\brm\s+-[^\n]*r",
    r"\bdd\s+if=",
    r"\bmkfs\b",
    r"\bsudo\b",
    r"\bshutdown\b",
    r"\breboot\b",
    r":\(\)\s*\{",
    r">\s*/dev/sd[a-z]",
)


@dataclass(frozen=True)
class Route:
    intent: str
    argv: list[str]
    cwd: str
    reason: str
    will_execute: bool = True

    @property
    def command(self) -> str:
        return " ".join(shlex.quote(part) for part in self.argv)


def now_iso() -> str:
    return datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds")


def normalize(text: str) -> str:
    return " ".join(text.strip().split())


def contains_any(text: str, terms: tuple[str, ...]) -> bool:
    return any(term in text for term in terms)


def dangerous_reason(text: str) -> str | None:
    lower = text.lower()
    for pattern in DANGEROUS_PATTERNS:
        if re.search(pattern, lower):
            return f"dangerous_pattern:{pattern}"
    return None


def classify(goal: str, root: Path) -> dict[str, Any]:
    text = normalize(goal)
    if not text:
        return envelope(text, Route("empty", [], ".", "goal_missing", will_execute=False), rejected=True)
    if len(text) > MAX_INPUT_CHARS:
        return envelope(text, Route("too_large", [], ".", "goal_too_large", will_execute=False), rejected=True)
    danger = dangerous_reason(text)
    if danger:
        return envelope(text, Route("rejected", [], ".", danger, will_execute=False), rejected=True)

    route = select_route(text, root)
    return envelope(text, route, rejected=False)


def select_route(text: str, root: Path) -> Route:
    lower = text.lower()
    has_list = contains_any(lower, ("어떤", "뭐", "무엇", "list", "what", "show", "status", "상태"))
    mentions_agent = contains_any(lower, ("agent", "agents", "provider", "providers", "모델", "에이전트", "작업자"))
    mentions_contract = contains_any(lower, ("contract", "contracts", "asc", "계약"))
    mentions_monitor = contains_any(lower, ("monitor", "watch", "primitive", "heartbeat", "감시", "모니터"))
    mentions_memory = contains_any(lower, ("memory", "memoryos", "기억", "메모리"))
    mentions_capability = contains_any(lower, ("capability", "capabilityos", "tool", "tools", "도구", "능력"))
    mentions_invoke = contains_any(lower, ("invoke", "run aios", "route", "실행", "라우트", "호출"))
    asks_hive = contains_any(lower, ("ask", "물어", "질문"))

    if has_list and mentions_agent:
        return Route(
            "hive_agents_status",
            [sys.executable, "-m", "hivemind.hive", "agents", "status", "--json"],
            "hivemind",
            "matched agent/provider listing request",
        )
    if has_list and mentions_contract:
        return Route(
            "dispatch_status",
            [sys.executable, "scripts/aios_dispatch.py", "status", "--json"],
            ".",
            "matched contract status request",
        )
    if has_list and mentions_monitor:
        return Route(
            "primitive_monitor_list",
            [sys.executable, "-m", "scripts.aios_primitives", "--json", "monitor", "list"],
            ".",
            "matched monitor/primitive listing request",
        )
    if mentions_memory:
        return Route(
            "memory_drafts_list",
            [sys.executable, "-m", "memoryos.cli", "--root", ".", "drafts", "list", "--json"],
            "memoryOS",
            "matched MemoryOS request",
        )
    if mentions_capability:
        return Route(
            "capability_recommend",
            [sys.executable, "-m", "capabilityos.cli", "recommend", "--task", text, "--json"],
            "CapabilityOS",
            "matched CapabilityOS/tool request",
        )
    if mentions_invoke:
        return Route(
            "aios_invoke_plan",
            [sys.executable, "scripts/aios_invoke.py", "--goal", text, "--plan-only", "--json"],
            ".",
            "matched AIOS invocation request",
        )
    if asks_hive:
        return hive_ask_route(text, "matched explicit ask request")
    return hive_ask_route(text, "default fallback to Hive ask")


def hive_ask_route(text: str, reason: str) -> Route:
    return Route(
        "hive_ask",
        [sys.executable, "-m", "hivemind.hive", "ask", text, "--fast", "--json"],
        "hivemind",
        reason,
    )


def envelope(goal: str, route: Route, *, rejected: bool) -> dict[str, Any]:
    return {
        "schema_version": SCHEMA_VERSION,
        "generated_at": now_iso(),
        "goal": goal,
        "intent": route.intent,
        "classified_command": route.command,
        "cwd": route.cwd,
        "will_execute": bool(route.will_execute and not rejected),
        "reason": route.reason,
        "rejected": rejected,
    }


def execute(root: Path, classified: dict[str, Any], *, timeout: int = 60) -> dict[str, Any]:
    if not classified.get("will_execute"):
        return {**classified, "executed": False, "execution": {"ok": False, "reason": classified.get("reason")}}
    route = select_route(str(classified.get("goal") or ""), root)
    cwd = root / route.cwd
    started = now_iso()
    try:
        result = subprocess.run(
            route.argv,
            cwd=cwd,
            text=True,
            capture_output=True,
            timeout=timeout,
            check=False,
        )
    except subprocess.TimeoutExpired as exc:
        return {
            **classified,
            "executed": True,
            "execution": {
                "ok": False,
                "returncode": 124,
                "timed_out": True,
                "stdout_tail": str(exc.stdout or "")[-4000:],
                "stderr_tail": str(exc.stderr or "")[-1200:],
                "started_at": started,
                "finished_at": now_iso(),
            },
        }
    return {
        **classified,
        "executed": True,
        "execution": {
            "ok": result.returncode == 0,
            "returncode": result.returncode,
            "timed_out": False,
            "stdout_tail": result.stdout[-4000:],
            "stderr_tail": result.stderr[-1200:],
            "started_at": started,
            "finished_at": now_iso(),
        },
    }


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("goal")
    parser.add_argument("--root", default=".")
    parser.add_argument("--execute", action="store_true")
    parser.add_argument("--json", action="store_true")
    parser.add_argument("--timeout", type=int, default=60)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    root = Path(args.root).resolve()
    payload = classify(args.goal, root)
    if args.execute:
        payload = execute(root, payload, timeout=args.timeout)
    if args.json:
        print(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True))
    else:
        print(payload.get("classified_command") or payload.get("reason"))
    return 1 if payload.get("rejected") else 0


if __name__ == "__main__":
    raise SystemExit(main())
