#!/usr/bin/env python3
"""`aios <goal>` — the goal-first head (missing head piece #1).

This is the entry the kernel audit said was missing: take one natural-language
goal, compile it into a governed ContractObject, then execute it through the
runtime kernel. It ties together the three pieces:

    goal (natural language)
      -> planner (provider adapter)        # aios_adapters.py
      -> ContractObject (governed plan)    # aios_contract_object.py
      -> runtime kernel (syscalls)         # aios_contract_runner.py
      -> receipts + result

Permission model (founder, kernel audit §Permission model):
  - DEFAULT IS READ-ONLY. The head grants read scope over the workspace and
    nothing else. Writes require an explicit --allow-write <path>; network
    requires --allow-network. Private-gated paths are always denied.
  - The plan is validated + authority-checked before any execution. A plan the
    LLM produced that exceeds the granted scope is rejected, not run
    (fail-closed). The model proposes; the contract authorizes.

The planner is dependency-injected. The real planner asks a provider for a JSON
step list; tests pass a fake planner so the head is testable without an LLM.
"""
from __future__ import annotations

import argparse
import importlib.util
import json
import re
import sys
from pathlib import Path
from typing import Any, Callable

_SCRIPT_DIR = Path(__file__).resolve().parent


def _load(name: str):
    if str(_SCRIPT_DIR) not in sys.path:
        sys.path.insert(0, str(_SCRIPT_DIR))
    if name in sys.modules:
        return sys.modules[name]
    spec = importlib.util.spec_from_file_location(name, _SCRIPT_DIR / f"{name}.py")
    m = importlib.util.module_from_spec(spec)
    sys.modules[name] = m
    spec.loader.exec_module(m)
    return m


co = _load("aios_contract_object")
runner = _load("aios_contract_runner")

# Privacy boundary — never grant scope over these (DNA invariant 7).
ALWAYS_DENY = ["_from_desktop/", "dain/", "minyoung/", ".aios/secrets/"]

# The syscalls a plan may use (mirrors the runner dispatch table).
ALLOWED_TOOLS = ["fs.read", "fs.list", "fs.write", "fs.delete", "fs.move", "web"]

PLANNER_SCHEMA_HINT = (
    'Return ONLY a JSON array of steps. Each step: '
    '{"id": "s1", "description": "...", "tool": "<one of '
    + "|".join(ALLOWED_TOOLS) +
    '>", "inputs": {...}, "requires_checkpoint": false}. '
    "fs.read/list inputs: {path}. fs.write inputs: {path, content}. "
    "fs.move inputs: {src, dst}. web inputs: {query} or {url}. "
    "Use absolute paths inside the workspace only. No prose, no markdown fences."
)


# --- plan compilation ---------------------------------------------------------

def build_skeleton(
    goal: str,
    *,
    workspace_root: str,
    allow_write: list[str] | None = None,
    allow_network: bool = False,
) -> Any:
    """Deterministic part: a scoped, step-less ContractObject for `goal`."""
    root = str(Path(workspace_root).resolve())
    fs = co.FilesystemScope(
        read_paths=[root + "/"],
        write_paths=[str(Path(p).resolve()) + "/" for p in (allow_write or [])],
        deny_paths=[root + "/" + d for d in ALWAYS_DENY] + list(ALWAYS_DENY),
    )
    auth = co.AuthorityScope(network=allow_network)
    c = co.ContractObject(
        contract_id=co.new_contract_id("co-head"),
        goal=goal,
        workspace_root=root,
        filesystem_scope=fs,
        authority_scope=auth,
    )
    return c


def _extract_json_array(text: str) -> list[Any]:
    """Robustly pull the first JSON array out of an LLM response.

    Handles markdown fences and NDJSON-ish noise (qwen3 lesson): scan for the
    first '[' ... matching ']' and json.loads it.
    """
    text = re.sub(r"```(?:json)?", "", text)
    start = text.find("[")
    if start == -1:
        raise ValueError("planner returned no JSON array")
    depth = 0
    for i in range(start, len(text)):
        ch = text[i]
        if ch == "[":
            depth += 1
        elif ch == "]":
            depth -= 1
            if depth == 0:
                return json.loads(text[start:i + 1])
    raise ValueError("planner JSON array not closed")


def steps_from_plan(plan: list[dict[str, Any]]) -> list[Any]:
    steps = []
    for i, raw in enumerate(plan):
        steps.append(co.Step(
            id=str(raw.get("id") or f"s{i+1}"),
            description=str(raw.get("description", "")),
            tool=str(raw.get("tool", "")),
            inputs=raw.get("inputs", {}) or {},
            requires_checkpoint=bool(raw.get("requires_checkpoint", False)),
        ))
    return steps


# A planner takes (goal, context) and returns raw planner text (JSON array).
Planner = Callable[[str, dict[str, Any]], str]


def make_provider_planner(provider: str, adapters: dict[str, Callable[[str], str]]) -> Planner:
    """Real planner: ask a provider to emit a JSON step list."""
    def planner(goal: str, context: dict[str, Any]) -> str:
        adapter = adapters[provider]
        recalled = context.get("recalled_memory") or []
        memory_block = ""
        if recalled:
            joined = "\n".join(f"- {m}" for m in recalled[:5])
            memory_block = (
                "\nRelevant prior runs (recalled memory — use to plan better):\n"
                f"{joined}\n"
            )
        prompt = (
            f"You are the AIOS planner. Goal: {goal}\n"
            f"Workspace root: {context['workspace_root']}\n"
            f"Writable paths: {context['write_paths'] or '(none — read-only)'}\n"
            f"Network allowed: {context['network']}\n"
            f"{memory_block}\n"
            f"{PLANNER_SCHEMA_HINT}"
        )
        return adapter(prompt)
    return planner


def compile_goal(
    goal: str,
    *,
    workspace_root: str,
    planner: Planner,
    allow_write: list[str] | None = None,
    allow_network: bool = False,
    retriever: Callable[[str], list[str]] | None = None,
) -> tuple[Any, list[str]]:
    """Goal -> (ContractObject with steps, validation errors).

    Validation errors non-empty => the plan exceeds granted authority and must
    not run (fail-closed). Caller decides whether to surface or abort.

    `retriever(goal)->list[str]` recalls prior execution traces (memory) and
    injects them into the planner context. This is what closes the cognition
    loop: the head plans better for a goal it has seen relatives of before.
    """
    c = build_skeleton(goal, workspace_root=workspace_root,
                       allow_write=allow_write, allow_network=allow_network)
    recalled = retriever(goal) if retriever else []
    c.memory_inputs = list(recalled)
    context = {
        "workspace_root": c.workspace_root,
        "write_paths": c.filesystem_scope.write_paths,
        "network": c.authority_scope.network,
        "recalled_memory": recalled,
    }
    raw = planner(goal, context)
    plan = _extract_json_array(raw)
    c.steps = steps_from_plan(plan)
    errors = c.validate()
    return c, errors


# --- CLI ----------------------------------------------------------------------

def _default_adapters(authorized_provider: str) -> dict[str, Callable[[str], str]]:
    adapters_mod = _load("aios_adapters")
    return adapters_mod.build_adapters(providers=[authorized_provider])


def default_fetcher(inputs: dict[str, Any]) -> str:
    """Minimal live web substrate: plain GET for {url}. {query} needs a search
    provider and is not wired here (kernel takes the offline named-exit)."""
    url = inputs.get("url")
    if not url:
        raise ValueError("default_fetcher only supports {url}; {query} needs a search provider")
    import urllib.request
    req = urllib.request.Request(url, headers={"User-Agent": "aios-head/0"})
    with urllib.request.urlopen(req, timeout=30) as resp:  # noqa: S310 — url is contract-scoped
        return resp.read(1_000_000).decode("utf-8", errors="replace")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="aios <goal> — goal-first head")
    parser.add_argument("goal", help="natural-language goal")
    parser.add_argument("--root", default=".", help="workspace root (default: cwd)")
    parser.add_argument("--provider", default="claude",
                        help="planner provider (claude/codex/gemini/ollama_local)")
    parser.add_argument("--allow-write", action="append", default=[],
                        help="grant write scope over a path (repeatable). default: read-only")
    parser.add_argument("--allow-network", action="store_true")
    parser.add_argument("--plan-only", action="store_true",
                        help="compile + validate the plan, do not execute")
    parser.add_argument("--approve-checkpoints", action="store_true")
    parser.add_argument("--save", help="write the resulting contract json to this path")
    parser.add_argument("--no-memory", action="store_true",
                        help="disable the cognition loop (no recall before, no draft after)")
    args = parser.parse_args(argv)

    adapters = _default_adapters(args.provider)
    if args.provider not in adapters:
        print(json.dumps({"status": "no_planner",
                          "detail": f"provider '{args.provider}' CLI not available"}, indent=2))
        return 1
    planner = make_provider_planner(args.provider, adapters)

    # cognition loop: recall before planning, draft after closeout (draft-first)
    retriever = None
    memory_sink = None
    if not args.no_memory:
        bridge = _load("aios_memory_bridge")
        root_path = Path(args.root).resolve()
        retriever = lambda g: bridge.retrieve(g, root_path)
        memory_sink = lambda c: bridge.writeback(c, root_path)

    try:
        contract, errors = compile_goal(
            args.goal, workspace_root=args.root, planner=planner,
            allow_write=args.allow_write, allow_network=args.allow_network,
            retriever=retriever)
    except ValueError as exc:
        print(json.dumps({"status": "plan_parse_error", "detail": str(exc)}, indent=2))
        return 1

    if args.save:
        Path(args.save).write_text(contract.to_json(), encoding="utf-8")

    if errors:
        print(json.dumps({"status": "plan_rejected", "reason": "exceeds granted authority",
                          "errors": errors,
                          "steps": [(s.id, s.tool) for s in contract.steps]}, indent=2))
        return 1

    if args.plan_only:
        print(json.dumps({"status": "plan_ok",
                          "steps": [{"id": s.id, "tool": s.tool, "desc": s.description}
                                    for s in contract.steps]}, indent=2))
        return 0

    fetcher = default_fetcher if args.allow_network else None
    summary = runner.run_contract(contract, adapters=adapters, fetcher=fetcher,
                                  memory_sink=memory_sink,
                                  approve_checkpoints=args.approve_checkpoints)
    if args.save:
        Path(args.save).write_text(contract.to_json(), encoding="utf-8")
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    return 0 if summary.get("status") in ("closed", "waiting_user") else 1


if __name__ == "__main__":
    raise SystemExit(main())
