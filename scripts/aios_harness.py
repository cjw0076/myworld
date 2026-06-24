#!/usr/bin/env python3
"""AIOS Harness — real tool execution wired to the turn loop.

aios_turn_loop.py provides the loop spine and DNA invariants.
This file adds what's missing: a real sampler (ReAct parser → LLM),
a real TOOL_REGISTRY (Bash/Read/Edit/Write/WebSearch), and AkashicRecord
contribution at session end.

Usage:
    aios do "list files in current directory"    # zero-friction shortcut
    aios do "fix the bug in auth.py"             # auto-selects qwen3:8b
    aios harness "task"                          # explicit harness entry
    python aios_harness.py "task" --dry-run      # dry run (no tool execution)

Design principle: works with ANY local LLM via ReAct text parsing —
no function-calling API required.
"""
from __future__ import annotations

import argparse
import importlib.util
import json
import os
import re
import subprocess
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path
from typing import Callable

ROOT    = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "scripts"
OLLAMA  = "http://127.0.0.1:11434"
# (AKASHIC URL moved to aios_memory with the shared contribute_run — Cycle 12/13.)

# ── Lazy import helper ────────────────────────────────────────────────────────

def _load(name: str):
    if str(SCRIPTS) not in sys.path:
        sys.path.insert(0, str(SCRIPTS))
    if name in sys.modules:
        return sys.modules[name]
    p = SCRIPTS / f"{name}.py"
    if not p.exists():
        return None
    spec = importlib.util.spec_from_file_location(name, p)
    m = importlib.util.module_from_spec(spec)
    sys.modules[name] = m
    spec.loader.exec_module(m)
    return m


# ── Bash risk classifier ──────────────────────────────────────────────────────

_HIGH_PATTERNS = re.compile(
    r"rm\s+-rf|sudo\s|curl\s.*\|.*sh|wget.*\|.*sh|chmod\s+777|"
    r"dd\s+if=|mkfs|shutdown|reboot|halt|kill\s+-9|pkill|"
    r">\s*/dev/sd|git\s+push\s+--force",
    re.IGNORECASE,
)
_MED_PATTERNS = re.compile(
    r"rm\s|mv\s|cp\s+-r|chmod|chown|git\s+(reset|clean|checkout\s+--)|"
    r"pip\s+install|npm\s+install|apt\s+|yum\s+|brew\s+",
    re.IGNORECASE,
)

def classify_bash(cmd: str) -> str:
    if _HIGH_PATTERNS.search(cmd):
        return "HIGH"
    if _MED_PATTERNS.search(cmd):
        return "MED"
    return "LOW"


# ── Tool registry & executors ─────────────────────────────────────────────────

def _exec_bash(args: dict) -> tuple[str, str]:
    cmd = args.get("cmd", args.get("command", ""))
    if not cmd:
        return "error", "no cmd provided"
    if _SHELL_META.search(cmd):
        return "error", "unsafe shell syntax blocked (metacharacter or privileged shell)"
    try:
        cwd = str(_safe_path(args.get("cwd", "."))) if args.get("cwd") else str(ROOT)
        r = subprocess.run(
            shlex.split(cmd), capture_output=True, text=True, timeout=30, cwd=cwd,
        )
        out = (r.stdout + r.stderr).strip()
        return ("ok" if r.returncode == 0 else "error"), out[:4000]
    except subprocess.TimeoutExpired:
        return "error", "timeout (30s)"
    except ValueError as e:
        return "error", str(e)
    except Exception as e:
        return "error", str(e)


def _exec_read(args: dict) -> tuple[str, str]:
    path = args.get("path", args.get("file", ""))
    if not path:
        return "error", "no path provided"
    try:
        text = _safe_path(path).read_text(encoding="utf-8", errors="replace")
        lines = text.splitlines()
        return "ok", "\n".join(lines[:200]) + (f"\n[…{len(lines)-200} more lines]" if len(lines) > 200 else "")
    except ValueError as e:
        return "error", str(e)
    except Exception as e:
        return "error", str(e)


def _exec_edit(args: dict) -> tuple[str, str]:
    path = args.get("path", "")
    old  = args.get("old", "")
    new  = args.get("new", "")
    if not (path and old):
        return "error", "need path + old + new"
    try:
        p = _safe_path(path)
        text = p.read_text(encoding="utf-8")
        if old not in text:
            return "error", f"old_string not found in {path}"
        p.write_text(text.replace(old, new, 1), encoding="utf-8")
        return "ok", f"replaced 1 occurrence in {path}"
    except ValueError as e:
        return "error", str(e)
    except Exception as e:
        return "error", str(e)


def _exec_write(args: dict) -> tuple[str, str]:
    path    = args.get("path", "") or args.get("file_path", "")
    content = args.get("content", "") or args.get("text", "")
    if not path:
        return "error", "no path provided"
    try:
        p = _safe_path(path)
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(content, encoding="utf-8")
        return "ok", f"wrote {len(content)} chars to {path}"
    except ValueError as e:
        return "error", str(e)
    except Exception as e:
        return "error", str(e)


def _exec_websearch(args: dict) -> tuple[str, str]:
    query = args.get("query", args.get("q", ""))
    if not query:
        return "error", "no query"
    try:
        url = f"https://duckduckgo.com/html/?q={urllib.parse.quote_plus(query)}"
        req = urllib.request.Request(url, headers={"User-Agent": "AIOS-Agent/1.0"})
        with urllib.request.urlopen(req, timeout=10) as r:
            html = r.read().decode("utf-8", errors="replace")
        # Extract result snippets (crude but dependency-free)
        import re as _re
        snippets = _re.findall(r'class="result__snippet"[^>]*>(.*?)</a>', html, _re.S)
        clean = [_re.sub(r"<[^>]+>", "", s).strip() for s in snippets[:5]]
        return "ok", "\n".join(f"- {s}" for s in clean) or "no results"
    except Exception as e:
        return "error", str(e)


def _exec_ouroboros(args: dict) -> tuple[str, str]:
    """Ouroboros spec-first pipeline (absorbed from Q00/ouroboros 0.42.5).

    mode='auto'      — full pipeline (interview→seed→run). runtime='codex'|'claude'
    mode='interview' — interactive Socratic refinement (non-blocking, returns questions)
    mode='qa'        — quality gate verdict for an artifact path or text
    """
    goal    = args.get("goal", args.get("task", args.get("artifact", "")))
    mode    = args.get("mode", "auto")   # auto | interview | qa
    runtime = args.get("runtime", "codex")  # codex by default (LiteLLM-free)
    if not goal:
        return "error", "no goal provided"
    if mode not in ("auto", "interview", "qa"):
        return "error", f"unknown mode {mode!r} — use auto/interview/qa"
    try:
        cmd = [sys.executable, "-m", "ouroboros", mode]
        if mode == "auto":
            cmd += ["--runtime", runtime, goal]
        elif mode == "qa":
            artifact_type = args.get("artifact_type", "document")
            quality_bar   = args.get("quality_bar", "")
            cmd += [goal, "--artifact-type", artifact_type]
            if quality_bar:
                cmd += ["--quality-bar", quality_bar]
        else:
            cmd += [goal]
        r = subprocess.run(cmd, capture_output=True, text=True, timeout=120, cwd=str(ROOT))
        out = (r.stdout + r.stderr).strip()
        status = "ok" if r.returncode == 0 else "error"
        return status, out[:4000]
    except subprocess.TimeoutExpired:
        return "error", "ouroboros timeout (120s)"
    except Exception as e:
        return "error", str(e)


def _exec_omx_skill(args: dict) -> tuple[str, str]:
    """Invoke an OMX skill via the omx CLI (absorbed from oh-my-codex)."""
    skill = args.get("skill", "")
    task  = args.get("task", args.get("goal", ""))
    if not skill:
        return "error", "no skill provided (e.g. ralph, team, autoresearch)"
    if not task:
        return "error", "no task provided"
    try:
        omx_bin = subprocess.run(
            ["which", "omx"], capture_output=True, text=True
        ).stdout.strip() or "omx"
        r = subprocess.run(
            [omx_bin, skill, task],
            capture_output=True, text=True, timeout=300, cwd=str(ROOT),
        )
        out = (r.stdout + r.stderr).strip()
        return ("ok" if r.returncode == 0 else "error"), out[:4000]
    except subprocess.TimeoutExpired:
        return "error", f"omx {skill} timeout (300s)"
    except FileNotFoundError:
        return "error", "omx not found — install via: npm install -g oh-my-codex"
    except Exception as e:
        return "error", str(e)


import shlex
import shutil
import urllib.parse


def _exec_aider(args: dict) -> tuple[str, str]:
    """Aider AI pair-programming substrate (Aider-AI/aider).

    Delegates git-integrated code editing to aider CLI when present.
    Args: {message: str, files?: list[str], yes?: bool}
    Returns not_available if CLI not installed — install with: pip install aider-chat
    """
    if not shutil.which("aider"):
        return "not_available", "aider not installed; run: pip install aider-chat"
    message = args.get("message", args.get("goal", args.get("task", "")))
    if not message:
        return "error", "no message provided"
    files = args.get("files", [])
    cmd = ["aider", "--message", message, "--yes-always", "--no-check-update"]
    if files:
        cmd += list(files)
    try:
        r = subprocess.run(cmd, capture_output=True, text=True, timeout=300, cwd=str(ROOT))
        out = (r.stdout + r.stderr).strip()
        return ("ok" if r.returncode == 0 else "error"), out[:4000]
    except subprocess.TimeoutExpired:
        return "error", "aider timeout (300s)"
    except Exception as e:
        return "error", str(e)


def _exec_sweagent(args: dict) -> tuple[str, str]:
    """SWE-agent issue-fixing substrate (SWE-agent/SWE-agent).

    Autonomous bug-fix agent. Requires SWE-agent installed and a GitHub issue URL or
    problem statement. CLI: python -m sweagent run ...
    Args: {problem: str, repo?: str}
    Returns not_available if sweagent not importable.
    """
    try:
        import importlib.util
        if importlib.util.find_spec("sweagent") is None:
            return "not_available", "sweagent not installed; see github.com/SWE-agent/SWE-agent"
    except Exception:
        return "not_available", "sweagent not installed"
    problem = args.get("problem", args.get("task", args.get("goal", "")))
    if not problem:
        return "error", "no problem statement provided"
    repo = args.get("repo", "")
    cmd = [sys.executable, "-m", "sweagent", "run", "--problem-statement", problem]
    if repo:
        cmd += ["--repo", repo]
    try:
        r = subprocess.run(cmd, capture_output=True, text=True, timeout=600, cwd=str(ROOT))
        out = (r.stdout + r.stderr).strip()
        return ("ok" if r.returncode == 0 else "error"), out[:4000]
    except subprocess.TimeoutExpired:
        return "error", "sweagent timeout (600s)"
    except Exception as e:
        return "error", str(e)


# ── Workspace path guard (Patch 2/3: Codex security review) ──────────────────

def _safe_path(raw: str) -> Path:
    """Resolve path and reject anything outside the workspace root."""
    p = Path(raw or ".").expanduser()
    p = (ROOT / p).resolve() if not p.is_absolute() else p.resolve()
    if p != ROOT and ROOT not in p.parents:
        raise ValueError(f"path outside workspace: {raw!r}")
    return p


# ── Shell metacharacter block (Patch 1/3: Codex security review) ─────────────

_SHELL_META = re.compile(r"[;&|`$<>]|\b(sh|bash|zsh|fish|sudo)\b")

TOOL_REGISTRY: dict[str, dict] = {
    "Bash": {
        "description": "Run a shell command. Args: {cmd: str, cwd?: str}",
        "permission": "workspace",
        "timeout_s":  30,
        "risk_fn":    lambda a: classify_bash(a.get("cmd", "")),
        "executor":   _exec_bash,
    },
    "Read": {
        "description": "Read a file. Args: {path: str}",
        "permission": "read-only",
        "timeout_s":  10,
        "risk_fn":    lambda _: "LOW",
        "executor":   _exec_read,
    },
    "Edit": {
        "description": "Replace text in file. Args: {path: str, old: str, new: str}",
        "permission": "workspace",
        "timeout_s":  10,
        "risk_fn":    lambda _: "MED",
        "executor":   _exec_edit,
    },
    "Write": {
        "description": "Write/overwrite file. Args: {path: str, content: str}",
        "permission": "workspace",
        "timeout_s":  10,
        "risk_fn":    lambda _: "MED",
        "executor":   _exec_write,
    },
    "WebSearch": {
        "description": "Web search. Args: {query: str}",
        "permission": "network",
        "timeout_s":  20,
        "risk_fn":    lambda _: "LOW",
        "executor":   _exec_websearch,
    },
    "Ouroboros": {
        "description": (
            "Spec-first pipeline (Ouroboros 0.42.5 absorbed). "
            "Args: {goal: str, mode?: 'auto'|'interview'|'qa'}"
        ),
        "permission": "network",
        "timeout_s":  120,
        "risk_fn":    lambda _: "LOW",
        "executor":   _exec_ouroboros,
    },
    "OmxSkill": {
        "description": (
            "Run an OMX skill (oh-my-codex). "
            "Args: {skill: str, task: str}  skill ∈ {ralph, team, autoresearch, deep-interview, ...}"
        ),
        "permission": "workspace",
        "timeout_s":  300,
        "risk_fn":    lambda _: "MED",
        "executor":   _exec_omx_skill,
    },
    # ── Substrate tools (hivemind delegation layer) ───────────────────────────
    "Aider": {
        "description": (
            "AI pair-programmer with git integration (Aider-AI/aider). "
            "Args: {message: str, files?: list[str]}. "
            "Returns not_available if aider CLI not installed."
        ),
        "permission": "workspace",
        "timeout_s":  300,
        "risk_fn":    lambda _: "MED",
        "executor":   _exec_aider,
    },
    "SWEAgent": {
        "description": (
            "Autonomous issue-fixing agent (SWE-agent/SWE-agent). "
            "Args: {problem: str, repo?: str}. "
            "Returns not_available if sweagent not installed."
        ),
        "permission": "workspace",
        "timeout_s":  600,
        "risk_fn":    lambda _: "HIGH",
        "executor":   _exec_sweagent,
    },
}

# Alias map: planner uses fs.* naming; harness TOOL_REGISTRY uses Claude-style names.
_TOOL_ALIAS: dict[str, str] = {
    "fs.read":    "Read",
    "fs.write":   "Write",
    "fs.list":    "Bash",     # fs.list → Bash ls equivalent
    "fs.delete":  "Bash",
    "fs.move":    "Bash",
    "web":        "WebSearch",
    "web.search": "WebSearch",
    "web.fetch":  "WebSearch",
    "bash":       "Bash",
    "read":       "Read",
    "write":      "Write",
    "edit":       "Edit",
}


def _resolve_tool_name(name: str) -> str:
    """Normalize planner tool names (fs.read, web, …) to TOOL_REGISTRY keys."""
    return _TOOL_ALIAS.get(name, name)


# ── Gate: auth based on risk ──────────────────────────────────────────────────

def default_gate(name: str, arguments: dict, dry_run: bool = False) -> str:
    name = _resolve_tool_name(name)
    spec = TOOL_REGISTRY.get(name)
    if spec is None:
        return "deny"
    risk = spec["risk_fn"](arguments)
    if dry_run:
        return "deny"
    if risk == "HIGH":
        return "deny"      # never auto-exec high-risk without explicit approval
    return "allow"


# ── ReAct sampler ─────────────────────────────────────────────────────────────

_TOOL_LIST = "\n".join(
    f"  {name}: {spec['description']}"
    for name, spec in TOOL_REGISTRY.items()
)

_REACT_SYSTEM = """You are a task-executing AI agent. You MUST call tools — never describe what you would do without calling one.

Available tools:
{tools}

RULES — follow exactly:
1. Always start with Thought then Action. NEVER output prose alone.
2. Use Action to call a tool. Use Final Answer ONLY when the task is fully done.
3. For file creation tasks, use Bash with: echo or printf or cat > path.

FORMAT (use EXACTLY):

Thought: <brief plan>
Action: <ToolName>
Action Input: {{"key": "value"}}

OR when done:

Final Answer: <outcome>

EXAMPLES:
User: list files in /tmp
Thought: I need ls.
Action: Bash
Action Input: {{"cmd": "ls /tmp"}}

User: create /tmp/out.txt with content hello
Thought: I will use echo to create the file.
Action: Bash
Action Input: {{"cmd": "echo 'hello' > /tmp/out.txt"}}

DO NOT describe actions without calling them. ALWAYS call a tool first."""

_ACTION_RE = re.compile(r"\bAction:\s*([A-Za-z][A-Za-z0-9_]*)", re.MULTILINE)
_ARG_RE    = re.compile(r"Action Input:\s*```(?:json)?\s*(\{.*?\})\s*```|Action Input:\s*(\{.*?\})",
                        re.DOTALL | re.IGNORECASE)
_FINAL_RE  = re.compile(r"Final Answer:", re.IGNORECASE)
_JSON_BLOCK = re.compile(r"```(?:json)?\s*(\{.*?\})\s*```", re.DOTALL)


def _parse_react(text: str) -> list[tuple[str, dict]] | None:
    """Parse ReAct output. Returns [(tool, args)] or None (done/text-only)."""
    if _FINAL_RE.search(text):
        return None

    m_action = _ACTION_RE.search(text)
    if not m_action:
        # Fallback: detect JSON tool_calls block from function-calling models
        # {"name": "Bash", "arguments": {"cmd": "ls"}}
        try:
            jb = _JSON_BLOCK.search(text)
            if jb:
                obj = json.loads(jb.group(1))
                if "name" in obj and obj["name"] in TOOL_REGISTRY:
                    return [(obj["name"], obj.get("arguments", obj.get("parameters", {})))]
        except Exception:
            pass
        return None

    tool = _resolve_tool_name(m_action.group(1))
    if tool not in TOOL_REGISTRY:
        # Model hallucinated a tool name — treat as done
        return None

    # Extract JSON args (handle both raw and markdown-fenced)
    args: dict = {}
    m_args = _ARG_RE.search(text)
    if m_args:
        raw = m_args.group(1) or m_args.group(2) or ""
        try:
            args = json.loads(raw)
        except json.JSONDecodeError:
            # Last resort: key=value extraction
            for pair in re.findall(r'"(\w+)"\s*:\s*"([^"]*)"', raw):
                args[pair[0]] = pair[1]
    return [(tool, args)]


# ── Renewal pillar 2 + Cycle 7: horizon routing via the one capability spine ────
# The classifier + model selection live in aios_routing (single source of truth,
# shared with aios_head). Re-exported here so existing references keep working.
from aios_routing import (  # noqa: E402
    classify_horizon, select_model_by_horizon,
    LONG_HORIZON_MODELS as _LONG_HORIZON_MODELS,
    SHORT_HORIZON_MODELS as _SHORT_HORIZON_MODELS,
)


# ── Renewal pillar 4 + Cycle 9: long-range constraint re-surfacing ─────────────
# Catastrophic forgetting is the design-level 27.5% of long-horizon failures
# (arXiv 2604.11978). Constraints retrieved at the start fade as the trajectory
# grows; this provider re-surfaces them. Retrieval now goes through the one memory
# path (aios_memory.retrieve: MemoryOS first, local keyword fallback) — cached once.
def make_memory_constraint_provider(root: Path):
    cache: dict = {"loaded": False, "constraints": []}

    def provider(goal: str, trajectory: list) -> list:
        if not cache["loaded"]:
            cache["loaded"] = True  # one query per run; best-effort, never blocks
            try:
                import aios_memory   # noqa: PLC0415
                import aios_routing  # noqa: PLC0415
                # Runtime = sparse activation: scope recall to the task's domain
                # partition (full-ledger sweep is reserved for sleep/train).
                domain = aios_routing.classify_domain(goal)
                cache["constraints"] = aios_memory.retrieve(goal, root, limit=3, domain=domain)
            except Exception:  # noqa: BLE001
                pass
        return [c for c in cache["constraints"] if c]

    return provider


def make_llm_sampler(goal: str, base_url: str | None = None,
                     model: str | None = None, api_key: str = "none",
                     provider: str | None = None) -> Callable:
    """Return a sampler function that calls local LLM and parses ReAct output.

    `goal` is passed in so the first-turn prompt includes the actual task
    (aios_turn_loop stores only kind='goal' in history — no content).

    provider: 'ollama' (default), 'claude', 'codex', 'gemini', or any key
    understood by aios_agent_system. When Ollama is unavailable, pass
    provider='claude' to fall through to the Claude CLI headless path.
    """
    _agent = _load("aios_agent_system")
    tool_desc = "\n".join(f"  {n}: {s['description']}" for n, s in TOOL_REGISTRY.items())
    system_prompt = _REACT_SYSTEM.format(tools=tool_desc)
    first_turn = True

    # Resolve a dispatch CHAIN at construction time: routed provider first, then
    # local ollama as a backstop. Local-first churn survival (substrate_router
    # philosophy): if the routed CLI provider (codex/claude/gemini) is unusable in
    # this environment it returns junk fast, which used to be silently treated as
    # "model finished" — a 0-tool no-op masquerading as success. The ollama
    # backstop keeps the organism actually running on the always-on local model.
    _chain: list[tuple[str, Callable]] = []
    if _agent:
        _runners = getattr(_agent, "_RUNNERS", None)
        if _runners is None:
            # Build minimal runners map from known functions
            _runners = {
                "ollama":  getattr(_agent, "_run_ollama", None),
                "claude":  getattr(_agent, "_run_claude", None),
                "codex":   getattr(_agent, "_run_codex",  None),
                "gemini":  getattr(_agent, "_run_gemini", None),
            }
        _ollama_run = _runners.get("ollama") or getattr(_agent, "_run_ollama", None)
        if provider and provider in _runners and _runners[provider]:
            _chain.append((provider, _runners[provider]))
        elif base_url:
            _chain.append(("openai_compat", lambda p: _agent._openai_compat(
                base_url, model or "local-model", p, api_key=api_key)))
        # Always backstop with local ollama unless it is already the primary.
        if _ollama_run and not any(n == "ollama" for n, _ in _chain):
            _chain.append(("ollama", _ollama_run))

    def sampler(history: list[dict]) -> dict:
        nonlocal first_turn

        # Renewal pillar 1: strip accumulated error traces before they reach the
        # model, so it doesn't self-condition on its own past mistakes (2509.09677).
        history = _load("aios_turn_loop").decondition_history(history)

        # Build conversation text
        parts = [system_prompt, ""]
        is_first = first_turn
        first_turn = False

        for h in history:
            role = h.get("role", "")
            if role == "user":
                # turn_loop stores no content; inject real goal on first turn
                task_text = goal if is_first else h.get("content", "")
                parts.append(f"User: {task_text}")
            elif role == "assistant":
                used = h.get("tools", [])
                parts.append(f"Assistant: (turn {h.get('turn','?')}, called: {used})")
            elif role == "tool":
                result = h.get("result", {})
                out_snippet = str(result.get("output", result.get("status", "?")))[:300]
                parts.append(f"Observation ({h.get('tool','?')}): {out_snippet}")
        # Renewal pillars 3 & 4 via the shared kernel renderer (one format, every path)
        _directives = _load("aios_turn_loop").render_directives(history)
        if _directives:
            parts.append(_directives.rstrip())

        parts.append("Assistant:")
        prompt = "\n".join(parts)

        # Try each substrate in the chain until one yields a usable move.
        if not _chain:
            raise RuntimeError("no LLM dispatch configured; pass --provider or --base-url")
        # Has the organism done any real work yet? On turn 0 an unparseable reply
        # means the provider is unusable → fall back. On later turns a no-action
        # reply is a genuine finish → don't loop substrates.
        prior_calls = sum(len(h.get("tools", [])) for h in history if h.get("role") == "assistant")
        tl = _load("aios_turn_loop")
        last_err = None
        for i, (_name, _dispatch) in enumerate(_chain):
            is_last = i == len(_chain) - 1
            try:
                text, _ = _dispatch(prompt)
            except Exception as e:  # noqa: BLE001 — try the next substrate
                last_err = f"{_name}: {e}"
                continue
            if not text or not text.strip():
                last_err = f"{_name}: empty output"
                continue
            parsed = _parse_react(text)
            if parsed is not None:
                return {"tool_calls": [tl.ToolCall(name=n, arguments=a) for (n, a) in parsed]}
            # parsed is None: a genuine finish (explicit final marker, or work already
            # done, or last substrate) — otherwise turn-0 junk → fall back.
            if _FINAL_RE.search(text) or prior_calls > 0 or is_last:
                return {"tool_calls": []}
            last_err = f"{_name}: unparseable turn-0 output → falling back"
        # ponytail: all substrates dead on turn 0 → honest no-op; rare (local ollama
        # almost always answers). Add a louder error exit only if this is ever hit.
        return {"tool_calls": []}

    return sampler


# ── Registry builder ──────────────────────────────────────────────────────────

def build_registry(allowed: list[str] | None = None, dry_run: bool = False):
    tl = _load("aios_turn_loop")
    reg = tl.Registry()
    for name, spec in TOOL_REGISTRY.items():
        if allowed and name not in allowed:
            continue
        def _make_handler(s=spec, n=name, dr=dry_run):
            def handler(args: dict):
                risk = s["risk_fn"](args)
                if dr or risk == "HIGH":
                    return {"status": "dry_run_blocked", "risk": risk}
                status, out = s["executor"](args)
                return {"status": status, "output": out[:2000], "risk": risk}
            return handler
        reg.register(name, _make_handler())
    return reg


# ── AkashicRecord contribution ────────────────────────────────────────────────

def _contribute_outcome(goal: str, outcome: dict, api_key: str | None) -> None:
    # Cycle 12 — one ledger write path: delegate to aios_memory.contribute_run
    # (shared with the head, so every run on every path becomes a star).
    import aios_memory  # noqa: PLC0415
    aios_memory.contribute_run(goal, outcome, api_key=api_key, source="aios-harness")


# ── CLI ───────────────────────────────────────────────────────────────────────

def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(
        prog="aios harness",
        description="AIOS Harness — run a task with real tool execution.\n"
                    "Examples:\n"
                    "  aios harness 'list files in current directory'\n"
                    "  aios harness 'fix bug in auth.py' --dry-run\n"
                    "  aios harness 'search for X' --tools Read,WebSearch",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    p.add_argument("task", help="Task to execute")
    p.add_argument("--dry-run", action="store_true",
                   help="Plan only — show what tools would be called, don't execute")
    p.add_argument("--tools", default=None,
                   help="Comma-separated allowed tools (default: all)")
    p.add_argument("--base-url", default=None, metavar="URL",
                   help="OpenAI-compatible endpoint (default: Ollama)")
    p.add_argument("--model", default=None)
    p.add_argument("--max-turns", type=int, default=12)
    p.add_argument("--provider", default=None,
                   choices=["ollama", "claude", "codex", "gemini"],
                   help="LLM provider (default: ollama). Use 'claude' when Ollama is unavailable.")
    p.add_argument("--api-key", default=None,
                   help="AKR key for contribution (or AIOS_API_KEY)")
    p.add_argument("--verbose", "-v", action="store_true")
    p.add_argument("--json", dest="as_json", action="store_true")
    args = p.parse_args(argv)

    api_key = args.api_key or os.environ.get("AIOS_API_KEY") or _load_saved_key()
    allowed = [t.strip() for t in args.tools.split(",")] if args.tools else None

    # Auto-route provider via role_router when --provider not specified
    resolved_provider = args.provider
    routed_role = None
    if resolved_provider is None:
        try:
            rr = _load("aios_role_router")
            route_result = rr.route(args.task)
            resolved_provider = route_result.provider
            routed_role = route_result.role
        except Exception:
            pass  # fall back to sampler default

    tl     = _load("aios_turn_loop")
    ts, rs, sid, log_path = tl.make_event_log_sink()
    reg    = build_registry(allowed, dry_run=args.dry_run)

    # Renewal pillar 2: when no model is pinned and we're on a local endpoint,
    # route by task horizon — long/multi-step tasks to a reasoning model.
    _base_url = args.base_url or os.environ.get("OPENAI_COMPAT_URL")
    _horizon = None
    if args.model is None and _base_url:
        _horizon = classify_horizon(args.task)
        args.model = select_model_by_horizon(args.task, _base_url)

    sampler = make_llm_sampler(
        goal=args.task,
        base_url=_base_url,
        model=args.model,
        provider=resolved_provider,
    )
    gate = lambda name, arguments: default_gate(name, arguments, dry_run=args.dry_run)

    if args.verbose:
        print(f"✦ aios task={args.task[:80]!r}  dry_run={args.dry_run}  log={log_path}")
        print(f"✦ aios tools={list(TOOL_REGISTRY.keys()) if not allowed else allowed}")
        if _horizon:
            print(f"✦ aios horizon={_horizon} → model={args.model}")
        if routed_role:
            print(f"✦ aios role_router → role={routed_role}  provider={resolved_provider}")

    # Pillar 4: re-surface long-range constraints from MemoryOS during the run.
    _constraint_provider = (make_memory_constraint_provider(ROOT)
                            if (ROOT / "memoryOS").exists() else None)

    t0 = time.time()
    outcome = tl.run_loop(
        args.task, sampler, reg,
        gate=gate,
        max_turns=args.max_turns,
        turn_sink=ts,
        record_sink=rs,
        session_id=sid,
        constraint_provider=_constraint_provider,
    )
    outcome["wall_s"] = round(time.time() - t0, 2)

    # Contribute to AkashicRecord (non-blocking, best-effort)
    if not args.dry_run:
        _contribute_outcome(args.task, outcome, api_key)

    if args.as_json:
        print(json.dumps(outcome, ensure_ascii=False, indent=2))
    else:
        exit_r = outcome.get("exit", "?")
        turns  = outcome.get("turns", 0)
        calls  = outcome.get("tool_calls", 0)
        tools  = outcome.get("tool_sequence", [])
        print(f"exit={exit_r}  turns={turns}  tool_calls={calls}  time={outcome['wall_s']}s")
        if tools:
            print(f"tools used: {' → '.join(tools)}")
        if args.dry_run:
            print("[dry-run: no tools were actually executed]")
        print(f"log: {log_path}")

    return 0 if outcome.get("exit") in ("model_finished", "max_turns") else 1


def _load_saved_key() -> str | None:
    cfg = Path.home() / ".aios" / "config.json"
    if cfg.exists():
        try:
            return json.loads(cfg.read_text()).get("api_key") or None
        except Exception:
            pass
    return None


if __name__ == "__main__":
    sys.exit(main())
