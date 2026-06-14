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

def make_provider_sampler(provider: str, adapters: dict[str, Callable[[str], str]],
                          goal: str = ""):
    """Reactive sampler for the turn-loop: ask the provider for the NEXT single move
    given the trajectory so far (one tool call, or done). This is the agent-loop shape
    (react to results), unlike the one-shot planner. Degrades: returns 'done' if the
    provider can't be reached, so the loop ends cleanly instead of fabricating.

    goal: include the active goal in every sampler call so the model has context.
    Without it the model can only see the trajectory shape, not what it's working toward.
    """
    tools = _load("aios_tools")
    # Build human-readable tool menu for the sampler prompt
    _tool_list = tools.list_tools()
    catalog_lines = "\n".join(
        f"  {t['name']} — {t.get('description', t['class'])}"
        for t in _tool_list
    )
    goal_line = f"Goal: {goal[:200]}\n" if goal else ""

    def sampler(history: list[dict]) -> dict:
        tl = _load("aios_turn_loop")
        recent = history[-12:]
        # Track repeated tool usage to steer the model away from loops
        tool_counts: dict[str, int] = {}
        for h in recent:
            for t in h.get("tools", []):
                tool_counts[t] = tool_counts.get(t, 0) + 1
        turn_num = sum(1 for h in recent if h.get("role") == "assistant")

        # Filter out exhausted tools (used ≥2 times) from the catalog.
        exhausted = {t for t, n in tool_counts.items() if n >= 2}
        # Also exhaust any tool whose last result was terminal (no_results/unavailable/
        # not_found/empty) — retrying in the same run won't produce different output.
        _terminal_statuses = {"no_results", "unavailable", "not_found", "empty",
                              "denied", "denied_scope"}
        for h in recent:
            if h.get("role") == "tool":
                result_status = (h.get("result") or {}).get("status", "")
                if result_status in _terminal_statuses:
                    exhausted.add(h.get("tool", ""))
        active_catalog = "\n".join(
            f"  {t['name']} — {t.get('description', t['class'])}"
            for t in _tool_list if t['name'] not in exhausted
        ) or "  (no tools available — emit {\"done\":true})"

        done_hint = ""
        if turn_num >= 3:
            done_hint = 'If the goal is satisfied or cannot be completed, emit {"done":true} now.\n'
        # Steer toward variety: name already-used tools so model picks differently
        used_in_recent = [t for t, n in tool_counts.items() if n >= 1]
        no_repeat_hint = ""
        if used_in_recent:
            no_repeat_hint = (f"Already called: {', '.join(used_in_recent[:4])}. "
                              "Pick a DIFFERENT tool next.\n")
        early_exit_hint = (
            'If this goal can be answered directly from general knowledge '
            '(math, basic code, concepts, how-to) without searching or reading files — '
            'emit {"done":true} immediately on turn 1.\n'
        ) if turn_num == 0 else ""
        prompt = (
            goal_line
            + "You are the AIOS agent turn-loop. Available tools:\n" + active_catalog + "\n"
            + early_exit_hint
            + "STRATEGY: For questions about AIOS, its tools, architecture, or internal state — "
            "call memory.retrieve FIRST to recall stored knowledge before searching the web or reading files.\n"
            + done_hint
            + no_repeat_hint
            + "Trajectory:\n"
            + json.dumps(recent, ensure_ascii=False) + "\n"
            'Emit ONLY JSON: {"tool":"<name>","arguments":{...}} for the next single '
            'action, or {"done":true} when complete. No prose.')
        try:
            # "auto" routes per-turn based on goal complexity; resolve to actual key
            _pkey = _auto_provider(goal) if provider == "auto" else provider
            raw = adapters[_pkey](prompt)
        except Exception:  # noqa: BLE001 — provider unreachable → end loop honestly
            return {"tool_calls": []}
        try:
            m = re.search(r"\{.*\}", raw, re.S)
            obj = json.loads(m.group(0)) if m else {"done": True}
        except (json.JSONDecodeError, AttributeError):
            return {"tool_calls": []}
        if obj.get("done") or not obj.get("tool"):
            return {"tool_calls": []}
        tool_name = str(obj["tool"])
        # Hard block: if model requests an exhausted tool despite filtered catalog, force done
        if tool_name in exhausted:
            return {"tool_calls": []}
        return {"tool_calls": [tl.ToolCall(tool_name, dict(obj.get("arguments", {})))]}

    return sampler


def run_loop_goal(goal: str, *, agent_id: str = "codex@myworld", sampler=None,
                  max_turns: int = 12,
                  turn_sink: Callable[[dict], None] | None = None) -> dict:
    """Run a goal as a real agent TURN-LOOP (the kernel spine) with AIOS organs as
    kernel tools behind an authority gate — not a single-pass batch over a pre-planned
    step list. The model is a sampler (DI for tests, provider-backed live)."""
    tl = _load("aios_turn_loop")
    tools = _load("aios_tools")
    if sampler is None:
        return {"schema_version": "aios.turn_loop.v1", "exit": "no_sampler",
                "detail": "pass a sampler, or run --loop with an available provider"}
    return tl.run_loop(goal, sampler, tools.build_registry(),
                       gate=tools.gate_for(agent_id), max_turns=max_turns,
                       turn_sink=turn_sink)


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

    # Normalize Korean queries: memoryOS text search is keyword-based, so strip
    # grammatical particles that prevent "AIOS가" from matching "AIOS" in memory text.
    mem_task = _korean_keywords(goal) if any('가' <= c <= '힣' for c in goal) else goal
    mem = _shell([sys.executable, "-m", "memoryos", "--root", ".", "context", "build",
                  "--task", mem_task, "--json"], root / "memoryOS")
    cap = _shell([sys.executable, "-m", "capabilityos.cli", "recommend",
                  "--task", goal, "--json"], root / "CapabilityOS")
    mem_data = (mem.get("data") or {}) if mem["status"] == "ok" else {}
    # context build returns `context_items` (int count) not `selected` (list)
    mem_hit_count = mem_data.get("context_items", 0) or len(mem_data.get("selected", []))
    return {
        "memory_hits": mem_hit_count,
        "memory_accepted": mem_data.get("total_accepted", 0),
        "memory_status": mem["status"],
        "capability_status": cap["status"],
        "top_capability": ((cap.get("data") or {}).get("top", []) or [{}])[0].get("id") if cap["status"] == "ok" else None,
    }


def _organ_postamble(goal: str, result: dict, root: Path, *, run_id: str | None = None) -> dict:
    """Mandatory postamble: MemoryOS run import + Akashic record.

    Runs after every completed turn loop so AIOS learns from each execution.
    Draft-first: memoryos import-run creates status=draft MemoryObject records.
    Degrades honestly if MemoryOS or Akashic are unavailable.
    """
    import importlib.util as _ilu
    import hashlib as _hl
    import subprocess as _sp

    preamble_errors: list[str] = []

    # 1. MemoryOS run import — write the run as draft MemoryObjects to the real graph.
    #    Uses make_memory_object + GraphStore directly (avoid import-run format mismatch:
    #    import-run expects .runs/<id>/run_state.json; RunLog writes .aios/runs/<id>.jsonl).
    ref_hash = _hl.sha256(f"{goal}{run_id or ''}".encode()).hexdigest()[:16]
    dream_status = "skipped"
    try:
        mem_path = root / "memoryOS"
        if str(mem_path) not in sys.path:
            sys.path.insert(0, str(mem_path))
        from memoryos.schema import make_memory_object  # noqa: PLC0415
        from memoryos.store import GraphStore  # noqa: PLC0415
        exit_status = result.get("exit", "unknown")
        turns = result.get("turns", 0)
        tool_calls_count = result.get("tool_calls", 0)
        final_answer = str(result.get("final_answer") or result.get("answer") or "")[:300]
        # Only record executions that used multiple turns or had interesting exits.
        # Single-turn model_finished (trivial synthesis) → skip to avoid memory noise.
        _is_significant = (turns > 1 or tool_calls_count >= 2
                           or exit_status not in ("model_finished", "unknown"))
        if not _is_significant:
            dream_status = f"skipped:trivial(turns={turns},tools={tool_calls_count},exit={exit_status})"
            return {"dream_agora_ingest": dream_status, "akashic_record": "skipped", "errors": []}
        content = (
            f"Goal: {goal[:200]}\n"
            f"Exit: {exit_status}  Turns: {turns}\n"
            + (f"Result: {final_answer}\n" if final_answer else "")
            + (f"run_id: {run_id}" if run_id else "")
        ).strip()
        mo = make_memory_object(
            memory_type="observation",
            content=content,
            origin="aios_head_organic",
            project="aios_execution",
            raw_refs=[f"run:{run_id}" if run_id else f"goal_hash:{ref_hash}"],
            confidence=0.6,
            status="draft",
        )
        store = GraphStore(mem_path)
        written, skipped = store.append_memory_objects([mo])
        dream_status = f"ok:written={written},skipped={skipped}"
    except Exception as exc:  # noqa: BLE001
        dream_status = f"unavailable:{str(exc)[:80]}"
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


def _organ_synthesis(goal: str, result: dict, preamble: dict | None = None,
                      root: "Path | None" = None, prior_context: str = "") -> str:
    """Synthesis step: after the turn loop, generate a concise final answer.

    Uses ollama_rest (fast, local) so this never adds frontier API latency.
    Falls back gracefully if ollama is unavailable.

    Retrieves actual memory snippets (names only, never content blobs per DNA #7)
    to give the synthesizer material to answer from.
    """
    adapters_mod = _load("aios_adapters")
    _ollama_ok = adapters_mod._ollama_rest_available()
    _gemini_ok = adapters_mod._gemini_rest_available()
    _anthropic_ok = adapters_mod._anthropic_rest_available()
    if not _ollama_ok and not _gemini_ok and not _anthropic_ok:
        return ("사용 가능한 AI 제공자가 없습니다. 아래 중 하나를 설정하세요:\n"
                "  • 로컬 모델(무료): `aios setup apply` 후 `aios serve` 재시작\n"
                "  • Google Gemini(무료): 환경 변수 `GEMINI_API_KEY` 설정\n"
                "  • Anthropic Claude: 환경 변수 `ANTHROPIC_API_KEY` 설정\n\n"
                "No provider available. Choose one:\n"
                "  • Local models (free): run `aios setup apply`, then restart `aios serve`\n"
                "  • Google Gemini (free tier): set GEMINI_API_KEY\n"
                "  • Anthropic Claude: set ANTHROPIC_API_KEY")
    if _ollama_ok:
        # Fast path (exit=fast_path) or short conversational goals → 1.7b (0.2s/call)
        # Code/complex goals or organic loop results → 8b (smarter, 2-5s/call)
        _is_fast_exit = result.get("exit") == "fast_path"
        _is_code_goal = any(kw in goal.lower() for kw in (
            "코드", "구현", "함수", "알고리즘", "code", "implement", "function", "algorithm", "class"))
        _synth_model = "qwen3:1.7b" if (_is_fast_exit and not _is_code_goal) else "qwen3:8b"
        adapter = adapters_mod.make_ollama_rest_adapter(model=_synth_model, timeout=60)
    elif _gemini_ok:
        # Gemini REST — free tier (1500 req/day), no billing required
        adapter = adapters_mod.make_gemini_rest_adapter(timeout=60)
    else:
        # Anthropic REST — paid, but high quality
        adapter = adapters_mod.make_anthropic_rest_adapter(timeout=60)

    traj = result.get("trajectory", [])
    exit_status = result.get("exit", "unknown")
    turns = result.get("turns", 0)

    # Collect tool result summaries from trajectory (compact, never content blobs)
    traj_lines: list[str] = []
    for t in traj:
        line = f"  turn {t.get('turn')}: {t.get('tool', '?')} → {t.get('status', '?')}"
        res = t.get("result", {})
        if res:
            # Show key metadata fields compactly
            meta = {k: v for k, v in res.items() if k not in ("snippet", "top")}
            parts = [f"{k}={v}" for k, v in list(meta.items())[:4]]
            if parts:
                line += f" ({', '.join(parts)})"
            # Show snippet/top/abstract separately if present (most informative content)
            snippet = str(res.get("snippet", "") or res.get("top", "") or res.get("abstract", ""))[:200].strip()
            if snippet:
                line += f"\n    content: {snippet}"
        traj_lines.append(line)
    traj_summary = "\n".join(traj_lines) or "  (no tool calls)"

    # Retrieve actual memory content for synthesis (decisions, feedback — names+summaries only)
    mem_snippets: list[str] = []
    if root is not None:
        try:
            import subprocess as _sp
            # Build auxiliary English queries (boosts Korean goals + adds semantic anchors)
            tool_names_used = [t.get("tool", "") for t in traj if t.get("tool")]
            aux_tool_query = " ".join(dict.fromkeys(tool_names_used))
            queries = [goal]
            is_korean = any('가' <= c <= '힣' for c in goal)
            # Semantic anchor: detect goal intent and add precise English keyword query
            _gl = goal.lower()
            _aios_self = any(kw in _gl for kw in ("뭐야", "뭔가요", "무엇", "소개", "설명", "어떻게 작동", "what is", "how does"))
            _tool_query = any(kw in _gl for kw in ("도구", "tool", "기능", "feature", "명령", "command"))
            _install_q = any(kw in _gl for kw in ("install", "설치", "setup", "curl", "how to"))
            # install intent always gets a dedicated first query (before other anchors fill the budget)
            if _install_q:
                queries.insert(0, "AIOS install curl setup one-line command aios serve")
            if _aios_self:
                queries.append("AIOS 5-OS architecture myworld hivemind memoryOS organic pipeline")
                if not _install_q:
                    queries.append("AIOS serving UI localhost install DNA invariants")
            elif _tool_query or aux_tool_query:
                queries.append(f"AIOS {aux_tool_query}" if aux_tool_query else "AIOS 12 kernel tools")
            elif is_korean and aux_tool_query:
                queries.append(f"AIOS {aux_tool_query}")
            seen_contents: set[str] = set()
            for q in queries:
                p = _sp.run(
                    [sys.executable, "-m", "memoryos", "--root", ".", "context", "build",
                     "--task", q, "--json"],
                    cwd=str(root / "memoryOS"), capture_output=True, text=True, timeout=20,
                )
                if p.returncode != 0:
                    continue
                data = json.loads(p.stdout)
                for item in (data.get("decisions") or [])[:5]:
                    content = str(item.get("content", ""))[:120].strip()
                    if content and content not in seen_contents:
                        seen_contents.add(content)
                        mem_snippets.append(f"[decision] {content}")
                        if len(mem_snippets) >= 8:
                            break
                for item in (data.get("constraints") or [])[:2]:
                    content = str(item.get("content", ""))[:80].strip()
                    if content and content not in seen_contents:
                        seen_contents.add(content)
                        mem_snippets.append(f"[constraint] {content}")
                if len(mem_snippets) >= 8:
                    break
        except Exception:  # noqa: BLE001
            pass

    if mem_snippets:
        mem_context = "Memory context:\n" + "\n".join(f"  • {s}" for s in mem_snippets)
    else:
        mem_context = f"Memory hits: {(preamble or {}).get('memory_hits', 0)} (names not available)."

    # Detect goal language — use Korean response if goal is Korean
    is_korean = any('가' <= c <= '힣' for c in goal)
    lang_hint = "한국어로 답하세요. " if is_korean else ""

    prior_section = f"{prior_context.strip()}\n\n" if prior_context.strip() else ""
    _code_hint = any(kw in goal.lower() for kw in (
        "코드", "구현", "작성", "code", "implement", "write", "function", "def ", "class "))
    synthesis_prompt = (
        f"{prior_section}"
        f"Goal: {goal}\n\n"
        f"{mem_context}\n\n"
        f"Agent loop ({turns} turns, exit={exit_status}):\n{traj_summary}\n\n"
        f"{lang_hint}"
        "Write a concise, direct answer to the goal. "
        + ("Use fenced markdown code blocks (```lang) for any code. " if _code_hint else "")
        + "Use only the tool results and prior conversation as evidence — "
        "the Memory context is background hints, use it only when clearly relevant to the goal. "
        "NEVER mention 'memory context', 'provided data', internal system names (ASC-*, contracts), "
        "or any internal system details in your answer. "
        "For real-time information (weather, prices, news, live data): if the tool results do not "
        "contain it, say you could not retrieve it rather than guessing. "
        "For general knowledge (code, concepts, how-to): you may answer from your knowledge. "
        "Keep prose responses to 1-3 sentences unless more detail is needed."
    )
    try:
        raw = adapter(synthesis_prompt)
        # Code responses may be longer; cap at 1500 to avoid context bloat
        limit = 1500 if _code_hint else 800
        return raw.strip()[:limit]
    except Exception as exc:  # noqa: BLE001
        return f"synthesis unavailable: {str(exc)[:60]}"


def run_organic_goal(goal: str, *, agent_id: str = "codex@myworld", sampler=None,
                     max_turns: int = 12, root: Path | None = None) -> dict:
    """The 5-OS organic pipeline — mandatory preamble + turn loop + mandatory postamble.

    This is what 'make AIOS actually run organically' means:
      1. memory.retrieve  — recall before planning (always)
      2. capability.route — select the right organ/provider (always)
      3. turn loop        — execute with all organs available as kernel tools; persisted via RunLog
      4. memoryos import-run — ingest run as MemoryObject drafts in the real graph (always)
      5. akashic          — record work lineage (always)

    No step is optional. Each degrades honestly but never silently skips.
    The learning loop: run → RunLog → import-run → context build → next preamble recalls it.
    """
    import datetime as _dt

    if root is None:
        root = Path(__file__).resolve().parents[1]

    # Create a RunLog to persist the turn-loop to .aios/runs/ so memoryos import-run can read it.
    run_id = f"organic-{_dt.datetime.now(_dt.timezone.utc).strftime('%Y%m%dT%H%M%S')}"
    rl = _load("aios_run_log")
    run_log = rl.RunLog(run_id=run_id, agent=agent_id, runs_dir=root / ".aios" / "runs")
    run_log.open(ts=_dt.datetime.now(_dt.timezone.utc).isoformat(timespec="seconds"))

    preamble = _organ_preamble(goal, root)
    result = run_loop_goal(goal, agent_id=agent_id, sampler=sampler, max_turns=max_turns,
                           turn_sink=run_log.sink)
    postamble = _organ_postamble(goal, result, root, run_id=run_id)

    return {
        **result,
        "run_id": run_id,
        "organic_pipeline": {
            "preamble": preamble,
            "postamble": postamble,
        },
    }


def _korean_keywords(text: str) -> str:
    """Strip Korean grammatical suffixes so keywords match memory text.

    Korean particles/endings commonly attached to nouns: 가, 이, 은, 는, 을, 를,
    에, 에서, 의, 과, 와, 로, 으로, 도, 만, 까지, 부터.
    Verb endings stripped: 해요, 해, 했다, 한다, 인가요, 뭔가요.
    Returns space-joined root keywords (best-effort, not full NLP).
    """
    _SUFFIXES = [
        "에서", "이에요", "인가요", "뭔가요", "했다", "한다", "해요", "해서",
        "해요", "했어", "하나요", "하는", "까지", "부터", "으로", "만큼",
        "에게", "으로", "이라", "라서", "해서", "에도", "에서", "이라",
        "이다", "하다", "이란", "라는", "가요", "나요", "네요",
        "해", "가", "이", "은", "는", "을", "를", "에", "의", "과", "와",
        "로", "도", "만",
    ]
    _STOP_WORDS = {"어떻게", "무엇", "왜", "언제", "어디", "누가", "얼마나",
                   "그리고", "하지만", "그런데", "또한", "그래서", "따라서"}
    tokens = text.split()
    keywords = []
    for tok in tokens:
        tok_l = tok.lower()
        if tok_l in _STOP_WORDS:
            continue
        root = tok_l
        for suf in sorted(_SUFFIXES, key=len, reverse=True):
            if root.endswith(suf) and len(root) > len(suf) + 1:
                root = root[: -len(suf)]
                break
        if len(root) >= 2:
            keywords.append(root)
    return " ".join(dict.fromkeys(keywords))


def _auto_provider(goal: str) -> str:
    """Choose the best available provider based on goal complexity.

    Simple/short goals → qwen3:1.7b via ollama_rest (fast, ~0.2s/turn)
    Complex/long/code goals → qwen3:8b via ollama_rest (smarter, ~2-5s/turn)
    Always falls back to ollama_rest if either model is missing.
    """
    adapters_mod = _load("aios_adapters")
    if not adapters_mod._ollama_rest_available():
        if adapters_mod._gemini_rest_available():
            return "gemini_rest"
        if adapters_mod._anthropic_rest_available():
            return "anthropic_rest"
        return "ollama_rest"   # will be handled as unavailable downstream
    # Complexity heuristics
    word_count = len(goal.split())
    has_code_hint = any(kw in goal.lower() for kw in
                        ("코드", "code", "파일", "file", "script", "함수", "function",
                         "버그", "bug", "error", "읽어", "read", "fetch", "url"))
    # Korean: space-split underestimates complexity (fewer tokens than English equivalent)
    # Use char count as secondary signal — 25+ chars in Korean ≈ 20+ English words
    has_korean = any('가' <= c <= '힣' for c in goal)
    char_threshold = 15 if has_korean else 120
    if word_count > 20 or len(goal) > char_threshold or has_code_hint:
        return "ollama_rest_8b"
    return "ollama_rest"


def _default_adapters(authorized_provider: str) -> dict[str, Callable[[str], str]]:
    adapters_mod = _load("aios_adapters")
    if authorized_provider == "auto":
        # Ollama (fast local) → Gemini REST (free cloud) → Anthropic REST (paid cloud)
        providers = ["ollama_rest", "ollama_rest_8b", "gemini_rest", "anthropic_rest"]
        return adapters_mod.build_adapters(providers=providers)
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
        # --loop always runs organically — RunLog + postamble wired by default
        sampler = make_provider_sampler(args.provider, adapters)
        root_path = Path(args.root).resolve()
        outcome = run_organic_goal(args.goal, agent_id=args.agent, sampler=sampler,
                                   root=root_path)
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
