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
    "fs.read/list inputs: {path}. "
    "fs.write inputs: {path, content} — IMPORTANT: content must be the FULL actual document body "
    "(never a placeholder like '작성 완료', 'done', 'TBD', '(완료)', or any short summary). "
    "If the content would be long, include it ALL in the content field — do not truncate or summarize. "
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


def _repair_json(candidate: str) -> str:
    """Best-effort repair of common LLM JSON mistakes."""
    # 1. trailing commas: ,} or ,]
    candidate = re.sub(r",\s*([}\]])", r"\1", candidate)
    # 2. unescaped newlines inside string values (replace \n with space approx)
    #    Only outside of escaped sequences — heuristic: non-backslash-preceded newline
    candidate = re.sub(r'(?<!\\)\n', " ", candidate)
    # 3. unescaped tab
    candidate = re.sub(r'(?<!\\)\t', " ", candidate)
    return candidate


def _extract_json_array(text: str) -> list[Any]:
    """Robustly pull the first JSON array out of an LLM response.

    Handles markdown fences and NDJSON-ish noise (qwen3 lesson): scan for the
    first '[' ... matching ']' and json.loads it.
    On parse failure, attempts lightweight JSON repair before giving up.
    """
    text = re.sub(r"```(?:json)?", "", text)
    text = re.sub(r"```", "", text)  # strip any remaining fences
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
                candidate = text[start:i + 1]
                try:
                    return json.loads(candidate)
                except json.JSONDecodeError:
                    repaired = _repair_json(candidate)
                    try:
                        return json.loads(repaired)
                    except json.JSONDecodeError as exc2:
                        raise ValueError(f"planner JSON malformed after repair: {exc2}") from exc2
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


def _load_standards(workspace_root: str) -> str:
    """Load docs/aios-standards.md if present (agent-os inject-standards pattern)."""
    path = Path(workspace_root) / "docs" / "aios-standards.md"
    try:
        text = path.read_text(encoding="utf-8")
        # Truncate to avoid bloating context — first 2000 chars covers all rules
        return text[:2000]
    except OSError:
        return ""


def make_provider_planner(provider: str, adapters: dict[str, Callable[[str], str]]) -> Planner:
    """Real planner: ask a provider to emit a JSON step list."""
    def planner(goal: str, context: dict[str, Any]) -> str:
        adapter = adapters[provider]
        recalled = context.get("recalled_memory") or []
        cap_route = context.get("capability_route") or {}
        memory_block = ""
        if recalled:
            joined = "\n".join(f"- {m}" for m in recalled[:5])
            memory_block = (
                "\nRelevant prior runs (recalled memory — use to plan better):\n"
                f"{joined}\n"
            )
        capability_block = ""
        if cap_route:
            capability_block = (
                "\nCapabilityOS recommendation (recommendation-only; do not bind tools):\n"
                f"{json.dumps(cap_route, ensure_ascii=False)[:1200]}\n"
            )
        standards = _load_standards(context.get("workspace_root", "."))
        standards_block = f"\nAIOS Operating Standards:\n{standards}\n" if standards else ""
        prompt = (
            f"You are the AIOS planner. Goal: {goal}\n"
            f"Workspace root: {context['workspace_root']}\n"
            f"Writable paths: {context['write_paths'] or '(none — read-only)'}\n"
            f"Network allowed: {context['network']}\n"
            f"{memory_block}\n"
            f"{capability_block}"
            f"{standards_block}"
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
    cap_bridge = _load("aios_capabilityos_bridge")
    capability_route = cap_bridge.recommend(goal, Path(workspace_root).resolve())
    c.capability_route = dict(capability_route)
    context = {
        "workspace_root": c.workspace_root,
        "write_paths": c.filesystem_scope.write_paths,
        "network": c.authority_scope.network,
        "recalled_memory": recalled,
        "capability_route": capability_route,
    }
    _MAX_PLAN_RETRIES = 2
    last_exc: Exception | None = None
    raw = ""
    for _attempt in range(_MAX_PLAN_RETRIES):
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
            return c, errors
        except (ValueError, KeyError, TypeError, json.JSONDecodeError) as exc:
            last_exc = exc
            # inject hint on retry
            context = dict(context, _retry_hint=(
                "Previous attempt produced invalid JSON. "
                "Return ONLY a valid JSON array, no prose, no markdown fences."
            ))

    # all retries exhausted
    c.planner_receipt = _planner_receipt(
        co_mod, contract_id=c.contract_id, planner_label=planner_label,
        context=context, memory_count=len(recalled), raw=raw,
        parse_status="failed", step_count=0, error=str(last_exc),
    )
    errors = [f"planner parse failed: {last_exc}"]
    return c, errors


# --- sampler helpers ----------------------------------------------------------

_FS_KEYWORDS = frozenset([
    "list", "find", "read", "write", "create", "delete", "copy", "move",
    "file", "files", "directory", "folder", "path", "파일", "디렉토리",
    "폴더", "읽어", "써줘", "만들어", "삭제", "이동", "복사",
    "ls", "find ", "cat ", "mkdir", "rm ", "cp ", "mv ",
    "scripts/", "docs/", "tests/", ".py", ".md", ".json",
    # write/doc tasks — goal says produce a file/doc, must call a write tool
    "document", "문서", "문서화", "작성", "써", "기록", "저장", "정리",
    "analyze and", "분석하고", "요약하고", "정리하고", "출력해", "출력하",
])

_WRITE_GOAL_KEYWORDS = frozenset([
    "document", "write", "create", "문서화", "작성", "써", "저장", "정리",
    "analyze and", "분석하고", "정리하고",
])


def _goal_needs_filesystem(goal: str) -> bool:
    """Return True when the goal requires actual filesystem inspection.

    Used to suppress the 'early exit on turn 0' hint for goals that must
    call a tool (fs.list, fs.read, etc.) instead of answering from knowledge.
    """
    g = goal.lower()
    return any(kw in g for kw in _FS_KEYWORDS)


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
        # Renewal pillar 1: strip accumulated error traces so the model doesn't
        # self-condition on its own past mistakes (arXiv 2509.09677). Unifies the
        # head path with the harness path — both runners now share the defense.
        recent = tl.decondition_history(history)[-12:]
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
        # Suppress early-exit for filesystem/state goals: they must call a tool first.
        _fs_goal = _goal_needs_filesystem(goal)
        _write_goal = any(kw in goal.lower() for kw in _WRITE_GOAL_KEYWORDS)
        early_exit_hint = (
            '' if _fs_goal else
            'If this goal is PURELY a general-knowledge question '
            '(math, concept explanations, how-to definitions) with NO need to '
            'inspect files, directories, or real-time system state — '
            'emit {"done":true} immediately.\n'
        ) if turn_num == 0 else ""
        # Force tool call for write/document goals: model must not emit done:true
        # without first calling a write/memory tool.
        write_force_hint = ""
        if _write_goal and turn_num == 0:
            write_force_hint = (
                "MANDATORY: this goal requires producing a written artifact. "
                "You MUST call memory.write or a write-capable tool BEFORE emitting done:true. "
                "Do NOT emit done:true on turn 0 for a write/document/analyze-and goal.\n"
            )
        # GenesisOS + CapabilityOS env context from preamble ref
        _pref_data = getattr(sampler, "_preamble_ref", {}) if callable(sampler) else {}
        _escapes = (_pref_data or {}).get("genesis_escape_vectors", [])
        genesis_hint = (
            f"GenesisOS challenge: before answering, consider — {_escapes[0]}\n"
        ) if _escapes and turn_num == 0 else ""
        # Inject environment capability context on turn 0 so model knows what's available
        _env_clis = (_pref_data or {}).get("env_clis", [])
        _env_models = (_pref_data or {}).get("env_ollama_models", [])
        _env_skills = (_pref_data or {}).get("env_skills", [])
        env_hint = ""
        if turn_num == 0 and (_env_clis or _env_models):
            _parts = []
            if _env_clis:
                _parts.append(f"CLIs: {', '.join(_env_clis)}")
            if _env_models:
                _parts.append(f"Local models: {', '.join(_env_models[:4])}")
            if _env_skills:
                _parts.append(f"Skills: {', '.join(_env_skills[:5])}...")
            env_hint = f"Environment: {'; '.join(_parts)}\n"
        prompt = (
            goal_line
            + "You are the AIOS agent turn-loop. Available tools:\n" + active_catalog + "\n"
            + early_exit_hint
            + write_force_hint
            + env_hint
            + "STRATEGY: For questions about AIOS, its tools, architecture, or internal state — "
            "call memory.retrieve FIRST to recall stored knowledge before searching the web or reading files.\n"
            + genesis_hint
            + done_hint
            + no_repeat_hint
            # Renewal pillars 3 & 4 (shared kernel renderer — one format on every path)
            + tl.render_directives(recent)
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

    # Mutable preamble reference — updated by run_organic_goal after preamble runs.
    # Allows sampler to read genesis_escape_vectors injected post-construction.
    sampler._preamble_ref = {}  # type: ignore[attr-defined]
    return sampler


def run_loop_goal(goal: str, *, agent_id: str = "codex@myworld", sampler=None,
                  max_turns: int = 12,
                  turn_sink: Callable[[dict], None] | None = None,
                  constraint_provider=None) -> dict:
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
                       turn_sink=turn_sink, constraint_provider=constraint_provider)


def _cosine(a: list[float], b: list[float]) -> float:
    import math as _math
    dot = sum(x * y for x, y in zip(a, b))
    na = _math.sqrt(sum(x * x for x in a))
    nb = _math.sqrt(sum(x * x for x in b))
    return dot / (na * nb) if na and nb else 0.0


def _semantic_retrieve(goal: str, root: Path, *, top_n: int = 8) -> list[dict]:
    """Return top_n memory objects by cosine similarity to goal embedding.

    Reads objects.jsonl directly (no memoryOS internals touched).
    Embeds lazily: cache miss → Ollama call → write cache entry.
    Graceful degradation: any failure returns []. Results are candidates only (DNA #2).
    """
    import urllib.request as _req, urllib.error as _uerr
    _OLLAMA = "http://localhost:11434/api/embed"
    _MODEL = "nomic-embed-text:latest"
    _CACHE = root / ".aios" / "memory_embed_cache.json"
    _STORE = root / "memoryOS" / "memory" / "objects.jsonl"

    def _embed(text: str) -> list[float] | None:
        body = json.dumps({"model": _MODEL, "input": text}).encode()
        try:
            rq = _req.Request(_OLLAMA, data=body, headers={"Content-Type": "application/json"})
            with _req.urlopen(rq, timeout=10) as r:
                return json.loads(r.read())["embeddings"][0]
        except Exception:  # noqa: BLE001
            return None

    q_vec = _embed(goal)
    if q_vec is None:
        return []

    cache: dict = {}
    if _CACHE.exists():
        try:
            cache = json.loads(_CACHE.read_text(encoding="utf-8"))
        except Exception:  # noqa: BLE001
            cache = {}

    objects: dict[str, dict] = {}
    try:
        for line in _STORE.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if not line:
                continue
            obj = json.loads(line)
            if obj.get("id") and obj.get("content"):
                objects[obj["id"]] = obj
    except Exception:  # noqa: BLE001
        return []

    cache_dirty = False
    for oid, obj in objects.items():
        chash = hashlib.sha256(obj["content"].encode()).hexdigest()[:16]
        entry = cache.get(oid)
        if entry and entry.get("content_hash") == chash:
            continue
        vec = _embed(obj["content"])
        if vec is None:
            return []
        cache[oid] = {"embedding": vec, "content_hash": chash}
        cache_dirty = True

    if cache_dirty:
        try:
            _CACHE.parent.mkdir(parents=True, exist_ok=True)
            _CACHE.write_text(json.dumps(cache, separators=(",", ":")), encoding="utf-8")
        except Exception:  # noqa: BLE001
            pass

    scored: list[tuple[float, dict]] = [
        (_cosine(q_vec, cache[oid]["embedding"]), obj)
        for oid, obj in objects.items()
        if oid in cache
    ]
    scored.sort(key=lambda t: t[0], reverse=True)
    return [obj for _, obj in scored[:top_n]]


def _organ_preamble(goal: str, root: Path) -> dict:
    """Mandatory 5-OS preamble: memory context + capability route + genesis challenge.

    Called before any execution so all three organs shape the plan.
    Returns a context dict that the sampler prompt can reference.
    Degrades honestly — a failing organ returns status=unavailable, never fabricates.
    """
    import subprocess as _sp
    import threading as _th

    def _shell(cmd: list[str], cwd: Path) -> dict:
        try:
            p = _sp.run(cmd, cwd=str(cwd), capture_output=True, text=True, timeout=10)
            if p.returncode != 0:
                return {"status": "unavailable"}
            return {"status": "ok", "data": json.loads(p.stdout)}
        except Exception as exc:  # noqa: BLE001
            return {"status": "unavailable", "reason": str(exc)[:80]}

    # Normalize Korean queries: memoryOS text search is keyword-based, so strip
    # grammatical particles that prevent "AIOS가" from matching "AIOS" in memory text.
    mem_task = _korean_keywords(goal) if any('가' <= c <= '힣' for c in goal) else goal

    # Run all 4 blocking operations in parallel threads — wall-clock = slowest single op,
    # not sum of all. Semantic embed, memoryOS, CapabilityOS, and GenesisOS each get
    # their own thread; results collected via mutable containers after join.
    sem_results: list[dict] = []
    mem_box: list[dict] = [{"status": "unavailable"}]
    cap_box: list[dict] = [{"status": "unavailable"}]
    gen_box: list[dict] = [{"status": "unavailable"}]

    def _run_semantic() -> None:
        sem_results.extend(_semantic_retrieve(goal, root, top_n=8))

    def _run_mem() -> None:
        # Cycle 11 — one memory: the MemoryOS context call now lives in aios_memory
        # (single invocation point). Downstream extraction below is unchanged.
        _mem = _load("aios_memory")
        data = _mem.memoryos_context(mem_task, root)
        mem_box[0] = {"status": "ok", "data": data} if data else {"status": "unavailable"}

    def _run_cap() -> None:
        cap_box[0] = _shell(
            [sys.executable, "-m", "capabilityos.cli", "recommend",
             "--task", goal, "--json"],
            root / "CapabilityOS",
        )

    def _run_gen() -> None:
        gen_box[0] = _shell(
            [sys.executable, "-m", "genesisos.cli", "critic",
             "--text", goal[:200], "--json"],
            root / "GenesisOS",
        )

    threads = [
        _th.Thread(target=_run_semantic, daemon=True),
        _th.Thread(target=_run_mem, daemon=True),
        _th.Thread(target=_run_cap, daemon=True),
        _th.Thread(target=_run_gen, daemon=True),
    ]
    for t in threads:
        t.start()

    # CapabilityOS: load env scan (cached 1h) to inject real environment context
    _env_scan: dict = {}
    _env_scan_path = root / ".aios" / "capability_observations" / "env_scan.json"
    if _env_scan_path.exists():
        import time as _time
        _age = _time.time() - _env_scan_path.stat().st_mtime
        if _age < 3600:  # use cache within 1 hour
            try:
                _env_scan = json.loads(_env_scan_path.read_text())
            except Exception:
                pass
    # If cache is stale or missing, trigger background refresh (non-blocking)
    if not _env_scan:
        import threading as _th2
        _th2.Thread(
            target=lambda: _sp.run(
                [sys.executable, str(root / "scripts" / "aios_capability_scanner.py")],
                capture_output=True, timeout=20
            ), daemon=True
        ).start()

    # Wait for all parallel organ calls (max = longest single subprocess, not sum)
    for t in threads:
        t.join(timeout=12)

    mem = mem_box[0]
    cap = cap_box[0]
    gen = gen_box[0]

    mem_data = (mem.get("data") or {}) if mem["status"] == "ok" else {}
    # context build returns `context_items` (int count) not `selected` (list)
    mem_hit_count = mem_data.get("context_items", 0) or len(mem_data.get("selected", []))

    # GenesisOS: extract escape vectors (assumption challenges) for sampler context
    gen_data = (gen.get("data") or {}) if gen["status"] == "ok" else {}
    gen_escapes = [v.get("escape_vector", v) if isinstance(v, dict) else str(v)
                   for v in (gen_data.get("escape_vectors") or [])][:2]
    gen_prison = [s.get("signature", "") if isinstance(s, dict) else str(s)
                  for s in (gen_data.get("prison_signatures") or [])][:2]

    # Union keyword + semantic results, deduplicate by id
    seen_ids: set[str] = set()
    combined: list[dict] = []
    kw_items = (
        (mem_data.get("decisions") or []) +
        (mem_data.get("constraints") or []) +
        (mem_data.get("other") or [])
    )
    for item in kw_items:
        oid = item.get("id", "")
        if oid and oid not in seen_ids:
            seen_ids.add(oid)
            combined.append({**item, "_source": "keyword"})
    for obj in sem_results:
        oid = obj.get("id", "")
        if oid and oid not in seen_ids:
            seen_ids.add(oid)
            combined.append({**obj, "_source": "semantic"})
    combined.sort(key=lambda x: float(x.get("confidence", 0.5)), reverse=True)

    # GenesisOS active demand: when high-confidence structural flaws are detected,
    # auto-register a demand packet so AIOS can self-improve proactively.
    # This is the "feel discomfort → demand fix" loop (not passive reporting).
    if gen_data and gen_prison:  # any detected prison signature triggers a demand
        try:
            import datetime as _dt, hashlib as _hl
            demand_dir = root / ".aios" / "genesis_demands"
            demand_dir.mkdir(parents=True, exist_ok=True)
            demand_id = "gen-" + _hl.sha256(f"{goal}{gen_prison}".encode()).hexdigest()[:10]
            demand_path = demand_dir / f"{demand_id}.json"
            if not demand_path.exists():  # idempotent — don't duplicate
                demand = {
                    "schema": "aios.genesis_demand.v1",
                    "id": demand_id,
                    "detected_at": _dt.datetime.now(_dt.timezone.utc).isoformat(timespec="seconds"),
                    "trigger_goal": goal[:200],
                    "prison_signatures": gen_prison,
                    "escape_vectors": gen_escapes,
                    "confidence": gen_data.get("confidence", 0),
                    "status": "open",
                    "authority": "genesis_auto",
                }
                demand_path.write_text(json.dumps(demand, ensure_ascii=False, indent=2))
        except Exception:  # noqa: BLE001 — demand registration is best-effort
            pass

    # Build compact env capability summary for sampler injection
    _env_counts = _env_scan.get("counts", {})
    _env_summary = ""
    if _env_counts:
        _env_summary = (
            f"skills={_env_counts.get('skills',0)} "
            f"models={_env_counts.get('ollama_models',0)} "
            f"clis={_env_counts.get('clis',0)} "
            f"mcps={_env_counts.get('mcps',0)}"
        )
    # Key available tools for sampler routing decisions
    _env_clis = [c["name"] for c in _env_scan.get("capabilities", []) if c.get("type") == "cli"]
    _env_models = [c["name"] for c in _env_scan.get("capabilities", [])
                   if c.get("type") == "ollama_model" and "embed" not in c["name"]][:5]
    _env_skills = [c["name"] for c in _env_scan.get("capabilities", [])
                   if c.get("type") == "claude_skill"][:8]

    return {
        "memory_hits": mem_hit_count,
        "memory_accepted": mem_data.get("total_accepted", 0),
        "memory_status": mem["status"],
        "semantic_hits": len(sem_results),
        "hybrid_candidates": combined[:8],  # candidates only — never auto-accepted (DNA #2)
        "capability_status": cap["status"],
        "top_capability": ((cap.get("data") or {}).get("top", []) or [{}])[0].get("id") if cap["status"] == "ok" else None,
        "genesis_status": gen["status"],
        "genesis_escape_vectors": gen_escapes,
        "genesis_prison_signatures": gen_prison,
        "env_capability_summary": _env_summary,
        "env_clis": _env_clis,
        "env_ollama_models": _env_models,
        "env_skills": _env_skills,
        "observed_capabilities": _env_scan.get("total", 0),
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
            status="speculative",
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
        # Synthesis is always a summarization step — the turn loop already did the
        # heavy reasoning with qwen3:8b. Use 1.7b here for fast final-answer generation.
        # Code goals get 8b so the answer itself can contain correct code.
        _is_code_goal = any(kw in goal.lower() for kw in (
            "코드", "구현", "함수", "알고리즘", "code", "implement", "function", "algorithm", "class"))
        _synth_model = "qwen3:8b" if _is_code_goal else "qwen3:1.7b"
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

    # Use preamble hybrid_candidates instead of re-running memoryos subprocess.
    # preamble already ran memoryos context build + semantic search; reuse it here
    # to avoid adding 0.5-3s subprocess overhead per synthesis call.
    mem_snippets: list[str] = []
    _candidates = (preamble or {}).get("hybrid_candidates") or []
    seen_contents: set[str] = set()
    for item in _candidates[:8]:
        content = str(item.get("content", ""))[:120].strip()
        if content and content not in seen_contents:
            seen_contents.add(content)
            origin = item.get("origin", item.get("type", "memory"))
            mem_snippets.append(f"[{origin}] {content}")

    if mem_snippets:
        mem_context = "Memory context:\n" + "\n".join(f"  • {s}" for s in mem_snippets)
    else:
        mem_context = f"Memory hits: {(preamble or {}).get('memory_hits', 0)}."

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
    cap_bridge = _load("aios_capabilityos_bridge")
    preamble["capability_recommendation"] = cap_bridge.recommend(goal, root)
    preamble["capability_status"] = "ok"
    preamble["top_capability"] = preamble["capability_recommendation"].get("provider_hint")

    # Domain tool shortcut: if CapabilityOS routes to a cap_tool_* card, execute
    # via domain.run without burning sampler turns. cap_bridge returns "recommended_tools"
    # (list of IDs); also check preamble["top_capability"] for CLI-sourced routing.
    # Falls through to sampler loop on any failure or non-domain routing.
    tools_mod = _load("aios_tools")
    _cap_rec = preamble.get("capability_recommendation", {})
    _recommended = _cap_rec.get("recommended_tools") or []
    _top_cap_id = (
        next((t for t in _recommended if str(t).startswith("cap_tool_")), None)
        or (preamble.get("top_capability") or "")
    )
    if str(_top_cap_id).startswith("cap_tool_"):
        _domain_result = tools_mod._h_domain_run({"task": goal})
        if _domain_result.get("status") == "ok":
            _result = {
                "exit": "model_finished",
                "turns": 1,
                "tool_calls": 1,
                "trajectory": [{"turn": 1, "tool": "domain.run",
                                "status": "ok", "result": _domain_result}],
                "final_answer": json.dumps(
                    _domain_result.get("result", _domain_result), ensure_ascii=False),
            }
            _postamble = _organ_postamble(goal, _result, root, run_id=run_id)
            return {**_result, "run_id": run_id,
                    "organic_pipeline": {"preamble": preamble, "postamble": _postamble,
                                         "domain_shortcut": True,
                                         "routed_to": _top_cap_id}}

    # Inject preamble context into sampler's genesis_hint if sampler supports it.
    # Sampler may expose a _preamble_ref dict updated after construction.
    _pref = getattr(sampler, "_preamble_ref", None)
    if isinstance(_pref, dict):
        _pref.update(preamble)

    # Pillar 4: re-surface long-range constraints during the loop. Reuse the
    # preamble's already-retrieved memory (zero extra cost) — no new subprocess.
    _pre_constraints = [
        str(c.get("content", "")).strip()[:300]
        for c in (preamble.get("hybrid_candidates") or [])[:3]
        if isinstance(c, dict) and c.get("content")
    ]

    def _constraint_provider(_goal, _trajectory):
        return _pre_constraints

    result = run_loop_goal(goal, agent_id=agent_id, sampler=sampler, max_turns=max_turns,
                           turn_sink=run_log.sink,
                           constraint_provider=_constraint_provider if _pre_constraints else None)
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
    # Cycle 7 — one capability spine: the long/short judgment comes from the shared
    # classify_horizon (same as the harness), mapped here to the head's rest tiers.
    routing = _load("aios_routing")
    has_code_hint = any(kw in goal.lower() for kw in
                        ("코드", "code", "파일", "file", "script", "함수", "function",
                         "버그", "bug", "error", "읽어", "read", "fetch", "url"))
    if routing.classify_horizon(goal) == "long" or has_code_hint:
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


def _load_task_file(path: str) -> dict:
    """Load a task from a JSON or YAML-style JSON file.

    Accepted fields:
      goal (str, required)
      provider (str)
      allow_write (list[str])
      allow_network (bool)
      loop (bool)
      agent (str)
      max_turns (int)

    Pure stdlib — no yaml/toml dependency. The file must be valid JSON.
    Example:
      {"goal": "list all .py files in scripts/", "provider": "ollama_rest", "loop": true}
    """
    try:
        text = Path(path).read_text(encoding="utf-8")
        data = json.loads(text)
        if not isinstance(data, dict):
            raise ValueError("task file must be a JSON object")
        if "goal" not in data:
            raise ValueError("task file must have a 'goal' field")
        return data
    except (OSError, json.JSONDecodeError, ValueError) as exc:
        raise SystemExit(f"aios head --from-file: {exc}") from exc


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="aios <goal> — goal-first head")
    parser.add_argument("goal", nargs="?", default=None, help="natural-language goal")
    parser.add_argument("--from-file", metavar="TASK_JSON",
                        help="read goal and run options from a JSON file (CC6 formal input)")
    parser.add_argument("--root", default=".", help="workspace root (default: cwd)")
    parser.add_argument("--provider", default=None,
                        help="planner provider (claude/codex/gemini/ollama_local/auto). "
                             "default: auto-route via role_router")
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
    parser.add_argument("--max-turns", type=int, default=12, help="max agent turns (default: 12)")
    args = parser.parse_args(argv)

    # CC6: load goal + options from JSON file if --from-file is given
    if args.from_file:
        task = _load_task_file(args.from_file)
        args.goal = task["goal"]
        if "provider" in task:
            args.provider = task["provider"]
        if "allow_write" in task:
            args.allow_write = list(task["allow_write"])
        if task.get("allow_network"):
            args.allow_network = True
        if task.get("loop"):
            args.loop = True
        if task.get("organic"):
            args.organic = True
        if "agent" in task:
            args.agent = task["agent"]
        if "max_turns" in task:
            args.max_turns = int(task["max_turns"])
    elif args.goal is None:
        parser.error("goal is required (positional argument or --from-file TASK_JSON)")

    # Auto-route provider via role_router when --provider is not set
    routed_role = None
    if args.provider is None or args.provider == "auto":
        try:
            rr = _load("aios_role_router")
            route_result = rr.route(args.goal)
            args.provider = route_result.provider
            routed_role = route_result.role
        except Exception:
            args.provider = "claude"
    adapters = _default_adapters(args.provider)
    if args.provider not in adapters:
        print(json.dumps({"status": "no_planner",
                          "detail": f"provider '{args.provider}' CLI not available"}, indent=2))
        return 1

    if args.organic:
        sampler = make_provider_sampler(args.provider, adapters, goal=args.goal)
        root_path = Path(args.root).resolve()
        outcome = run_organic_goal(args.goal, agent_id=args.agent, sampler=sampler,
                                   root=root_path, max_turns=args.max_turns)
        print(json.dumps(outcome, ensure_ascii=False, indent=2))
        return 0 if outcome.get("exit") in ("model_finished", "needs_approval") else 1

    if args.loop:
        # --loop always runs organically — RunLog + postamble wired by default
        sampler = make_provider_sampler(args.provider, adapters, goal=args.goal)
        root_path = Path(args.root).resolve()
        outcome = run_organic_goal(args.goal, agent_id=args.agent, sampler=sampler,
                                   root=root_path, max_turns=args.max_turns)
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
