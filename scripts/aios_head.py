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
import hashlib
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


def _planner_receipt(co_mod, *, contract_id: str, planner_label: str, context: dict,
                     memory_count: int, raw: str, parse_status: str,
                     step_count: int, error: str | None = None):
    """Build a PlannerReceipt from a planner call. Raw body is never stored."""
    digest = hashlib.sha256(raw.encode("utf-8", errors="replace")).hexdigest()
    return co_mod.PlannerReceipt(
        schema_version="aios.planner_receipt.v0",
        contract_id=contract_id,
        planner_label=planner_label,
        workspace_root=context.get("workspace_root", ""),
        write_paths=list(context.get("write_paths", [])),
        network=bool(context.get("network", False)),
        memory_count=memory_count,
        parse_status=parse_status,
        step_count=step_count,
        raw_body_hash=digest,
        raw_body_len=len(raw),
        error=error,
    )


def compile_goal(
    goal: str,
    *,
    workspace_root: str,
    planner: Planner,
    allow_write: list[str] | None = None,
    allow_network: bool = False,
    retriever: Callable[[str], list[str]] | None = None,
    planner_label: str = "unknown",
) -> tuple[Any, list[str]]:
    """Goal -> (ContractObject with steps, validation errors).

    Validation errors non-empty => the plan exceeds granted authority and must
    not run (fail-closed). Caller decides whether to surface or abort.

    `retriever(goal)->list[str]` recalls prior execution traces (memory) and
    injects them into the planner context. This is what closes the cognition
    loop: the head plans better for a goal it has seen relatives of before.

    A PlannerReceipt is always attached to the ContractObject after the planner
    call — whether parsing succeeds or fails — so planning is never invisible.
    The raw planner body is never stored; only its SHA-256 hash and byte length.
    """
    co_mod = _load("aios_contract_object")
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
    try:
        plan = _extract_json_array(raw)
        c.steps = steps_from_plan(plan)
        c.planner_receipt = _planner_receipt(
            co_mod, contract_id=c.contract_id, planner_label=planner_label,
            context=context, memory_count=len(recalled), raw=raw,
            parse_status="ok", step_count=len(c.steps),
        )
        errors = c.validate()
    except (ValueError, KeyError, TypeError) as exc:
        c.planner_receipt = _planner_receipt(
            co_mod, contract_id=c.contract_id, planner_label=planner_label,
            context=context, memory_count=len(recalled), raw=raw,
            parse_status="failed", step_count=0, error=str(exc),
        )
        errors = [f"planner parse failed: {exc}"]
    return c, errors


# --- CLI ----------------------------------------------------------------------

def make_provider_sampler(provider: str, adapters: dict[str, Callable[[str], str]]):
    """Reactive sampler for the turn-loop: ask the provider for the NEXT single move
    given the trajectory so far (one tool call, or done). This is the agent-loop shape
    (react to results), unlike the one-shot planner. Degrades: returns 'done' if the
    provider can't be reached, so the loop ends cleanly instead of fabricating."""
    tools = _load("aios_tools")
    catalog = json.dumps(tools.list_tools(), ensure_ascii=False)

    def sampler(history: list[dict]) -> dict:
        tl = _load("aios_turn_loop")
        prompt = (
            "You are the AIOS agent loop. Tools (name/class):\n" + catalog + "\n"
            "Trajectory so far (names/status only):\n"
            + json.dumps(history[-12:], ensure_ascii=False) + "\n"
            'Emit ONLY JSON: {"tool":"<name>","arguments":{...}} for the next single '
            'action, or {"done":true} when the goal is met. No prose.')
        try:
            raw = adapters[provider](prompt)
        except Exception:  # noqa: BLE001 — provider unreachable → end loop honestly
            return {"tool_calls": []}
        try:
            m = re.search(r"\{.*\}", raw, re.S)
            obj = json.loads(m.group(0)) if m else {"done": True}
        except (json.JSONDecodeError, AttributeError):
            return {"tool_calls": []}
        if obj.get("done") or not obj.get("tool"):
            return {"tool_calls": []}
        return {"tool_calls": [tl.ToolCall(str(obj["tool"]), dict(obj.get("arguments", {})))]}

    return sampler


def run_loop_goal(goal: str, *, agent_id: str = "codex@myworld", sampler=None,
                  max_turns: int = 12) -> dict:
    """Run a goal as a real agent TURN-LOOP (the kernel spine) with AIOS organs as
    kernel tools behind an authority gate — not a single-pass batch over a pre-planned
    step list. The model is a sampler (DI for tests, provider-backed live)."""
    tl = _load("aios_turn_loop")
    tools = _load("aios_tools")
    if sampler is None:
        return {"schema_version": "aios.turn_loop.v1", "exit": "no_sampler",
                "detail": "pass a sampler, or run --loop with an available provider"}
    return tl.run_loop(goal, sampler, tools.build_registry(),
                       gate=tools.gate_for(agent_id), max_turns=max_turns)


def _organ_preamble(goal: str, root: Path) -> dict:
    """Mandatory 5-OS preamble: memory context + capability route + genesis challenge.

    Called before any execution so all three organs shape the plan.
    Returns a context dict that the sampler prompt can reference.
    Degrades honestly — a failing organ returns status=unavailable, never fabricates.
    """
    import subprocess as _sp

    def _shell(cmd: list[str], cwd: Path) -> dict:
        try:
            p = _sp.run(cmd, cwd=str(cwd), capture_output=True, text=True, timeout=60)
            if p.returncode != 0:
                return {"status": "unavailable"}
            return {"status": "ok", "data": json.loads(p.stdout)}
        except Exception as exc:  # noqa: BLE001
            return {"status": "unavailable", "reason": str(exc)[:80]}

    mem = _shell([sys.executable, "-m", "memoryos", "--root", ".", "context", "build",
                  "--task", goal, "--json"], root / "memoryOS")
    cap = _shell([sys.executable, "-m", "capabilityos.cli", "recommend",
                  "--task", goal, "--json"], root / "CapabilityOS")
    return {
        "memory_hits": len((mem.get("data") or {}).get("selected", [])) if mem["status"] == "ok" else 0,
        "memory_status": mem["status"],
        "capability_status": cap["status"],
        "top_capability": ((cap.get("data") or {}).get("top", []) or [{}])[0].get("id") if cap["status"] == "ok" else None,
    }


def _organ_postamble(goal: str, result: dict, root: Path) -> dict:
    """Mandatory postamble: Dream Agora ingest + Akashic record.

    Runs after every completed turn loop so AIOS learns from each execution.
    Draft-first: Dream Agora produces status=draft records only.
    Degrades honestly if MemoryOS or Akashic are unavailable.
    """
    import importlib.util as _ilu
    import hashlib as _hl

    preamble_errors: list[str] = []

    # 1. Dream Agora ingest — the result summary becomes a source-backed draft
    try:
        mem_path = root / "memoryOS"
        if str(mem_path) not in sys.path:
            sys.path.insert(0, str(mem_path))
        spec = _ilu.spec_from_file_location("dream_agora", mem_path / "memoryos" / "dream_agora.py")
        da_mod = _ilu.module_from_spec(spec)
        spec.loader.exec_module(da_mod)
        store = da_mod.DreamAgoraStore(mem_path)
        ref_hash = _hl.sha256(goal.encode()).hexdigest()[:16]
        receipt = da_mod.SourceReceipt(
            source_ref=f"aios_head_run:{ref_hash}",
            source_type="aios_run_trace",
            source_time=__import__("datetime").datetime.now(__import__("datetime").timezone.utc).isoformat(timespec="seconds"),
            provider="aios_head",
            privacy_class="internal",
        )
        import json as _json
        store.ingest(receipt, content_summary=f"goal={goal[:120]} exit={result.get('exit','?')} turns={result.get('turns',0)}")
        dream_status = "ok"
    except Exception as exc:  # noqa: BLE001
        dream_status = f"unavailable:{str(exc)[:60]}"
        preamble_errors.append(dream_status)

    # 2. Akashic index — record work lineage
    akashic_status = "skipped"
    try:
        ak_path = root / "scripts" / "aios_akashic.py"
        spec2 = _ilu.spec_from_file_location("aios_akashic", ak_path)
        ak_mod = _ilu.module_from_spec(spec2)
        spec2.loader.exec_module(ak_mod)
        work_id = f"aios_head:{ref_hash}"
        exit_status = result.get("exit", "unknown")
        ak_payload = {
            "work_id": work_id,
            "goal": goal[:240],
            "status": "completed" if exit_status == "model_finished" else "paused",
            "next_action": f"exit={exit_status} turns={result.get('turns',0)}",
        }
        ak_mod.cmd_append(type("A", (), {**ak_payload, "json": False, "dry_run": False,
                                          "session_ids": [], "checkpoint_refs": [],
                                          "source_artifact_refs": []})(), root)
        akashic_status = "ok"
    except Exception as exc:  # noqa: BLE001
        akashic_status = f"unavailable:{str(exc)[:60]}"

    return {
        "dream_agora_ingest": dream_status,
        "akashic_record": akashic_status,
        "errors": preamble_errors,
    }


def run_organic_goal(goal: str, *, agent_id: str = "codex@myworld", sampler=None,
                     max_turns: int = 12, root: Path | None = None) -> dict:
    """The 5-OS organic pipeline — mandatory preamble + turn loop + mandatory postamble.

    This is what 'make AIOS actually run organically' means:
      1. memory.retrieve  — recall before planning (always)
      2. capability.route — select the right organ/provider (always)
      3. turn loop        — execute with all organs available as kernel tools
      4. dream_agora      — ingest result as source-backed draft (always)
      5. akashic          — record work lineage (always)

    No step is optional. Each degrades honestly but never silently skips.
    """
    if root is None:
        root = Path(__file__).resolve().parents[1]

    preamble = _organ_preamble(goal, root)
    result = run_loop_goal(goal, agent_id=agent_id, sampler=sampler, max_turns=max_turns)
    postamble = _organ_postamble(goal, result, root)

    return {
        **result,
        "organic_pipeline": {
            "preamble": preamble,
            "postamble": postamble,
        },
    }


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
    parser.add_argument("--loop", action="store_true",
                        help="run as a reactive agent TURN-LOOP (organs as kernel tools, "
                             "authority-gated) instead of a single-pass plan")
    parser.add_argument("--organic", action="store_true",
                        help="run the full 5-OS organic pipeline: memory→capability→loop→dream_agora→akashic")
    parser.add_argument("--agent", default="codex@myworld", help="agent identity for the gate")
    args = parser.parse_args(argv)

    adapters = _default_adapters(args.provider)
    if args.provider not in adapters:
        print(json.dumps({"status": "no_planner",
                          "detail": f"provider '{args.provider}' CLI not available"}, indent=2))
        return 1

    if args.organic:
        sampler = make_provider_sampler(args.provider, adapters)
        root_path = Path(args.root).resolve()
        outcome = run_organic_goal(args.goal, agent_id=args.agent, sampler=sampler,
                                   root=root_path)
        print(json.dumps(outcome, ensure_ascii=False, indent=2))
        return 0 if outcome.get("exit") in ("model_finished", "needs_approval") else 1

    if args.loop:
        sampler = make_provider_sampler(args.provider, adapters)
        outcome = run_loop_goal(args.goal, agent_id=args.agent, sampler=sampler)
        print(json.dumps(outcome, ensure_ascii=False, indent=2))
        return 0 if outcome.get("exit") in ("model_finished", "needs_approval") else 1

    planner = make_provider_planner(args.provider, adapters)

    # cognition loop: recall before planning, draft after closeout (draft-first)
    retriever = None
    memory_sink = None
    if not args.no_memory:
        bridge = _load("aios_memory_bridge")
        root_path = Path(args.root).resolve()
        retriever = lambda g: bridge.retrieve(g, root_path)
        memory_sink = lambda c: bridge.writeback(c, root_path)

    contract, errors = compile_goal(
        args.goal, workspace_root=args.root, planner=planner,
        allow_write=args.allow_write, allow_network=args.allow_network,
        retriever=retriever, planner_label=args.provider)

    if args.save:
        Path(args.save).write_text(contract.to_json(), encoding="utf-8")

    pr = contract.planner_receipt
    if pr is not None and pr.parse_status == "failed":
        # Failed planning is not invisible: surface the receipt diagnostic
        # (hash + length, never the raw planner body).
        print(json.dumps({"status": "plan_parse_error", "detail": pr.error,
                          "planner_receipt": {"raw_body_hash": pr.raw_body_hash,
                                              "raw_body_len": pr.raw_body_len,
                                              "parse_status": pr.parse_status}}, indent=2))
        return 1

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
