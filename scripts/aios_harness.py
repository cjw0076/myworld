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
AKASHIC = os.environ.get("AIOS_AKASHIC_URL", "https://aios-akashic.cjw070690.workers.dev")

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
import urllib.parse

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
}


# ── Gate: auth based on risk ──────────────────────────────────────────────────

def default_gate(name: str, arguments: dict, dry_run: bool = False) -> str:
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

    tool = m_action.group(1)
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

    # Resolve the dispatch function once at sampler-construction time
    _dispatch = None
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
        if provider and provider in _runners and _runners[provider]:
            _dispatch = _runners[provider]
        elif base_url:
            _dispatch = lambda p: _agent._openai_compat(
                base_url, model or "local-model", p, api_key=api_key)
        else:
            _dispatch = getattr(_agent, "_run_ollama", None)

    def sampler(history: list[dict]) -> dict:
        nonlocal first_turn

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

        parts.append("Assistant:")
        prompt = "\n".join(parts)

        # Call LLM via resolved dispatch (Patch 3/3: fail hard on LLM error)
        if not _dispatch:
            raise RuntimeError("no LLM dispatch configured; pass --provider or --base-url")
        try:
            text, _ = _dispatch(prompt)
        except Exception as e:
            raise RuntimeError(f"LLM dispatch failed: {e}") from e
        if not text.strip():
            raise RuntimeError("LLM dispatch returned empty output")

        # Parse
        parsed = _parse_react(text)
        if parsed is None:
            return {"tool_calls": []}
        tl = _load("aios_turn_loop")
        calls = [tl.ToolCall(name=n, arguments=a) for (n, a) in parsed]
        return {"tool_calls": calls}

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
    tools = outcome.get("tool_sequence", [])
    if not tools:
        return
    payload = {
        "id":       f"harness-{outcome.get('exit','?')[:4]}-{int(time.time())}",
        "content":  goal[:400],
        "category": "code",
        "provider": "aios-harness",
        "os_origin": "myworld",
        "top_tools": tools[:10],
        "tool_freq": {t: tools.count(t) for t in set(tools)},
        "confidence": 0.9 if outcome.get("exit") == "model_finished" else 0.6,
        "loop_type": outcome.get("loop_type", "unknown"),
    }
    headers = {"Content-Type": "application/json", "User-Agent": "AIOS-Agent/1.0"}
    if api_key:
        headers["X-AIOS-Key"] = api_key
    try:
        data = json.dumps(payload).encode()
        req = urllib.request.Request(
            AKASHIC + "/contribute", data=data, headers=headers, method="POST"
        )
        urllib.request.urlopen(req, timeout=10)
    except Exception:
        pass


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
    sampler = make_llm_sampler(
        goal=args.task,
        base_url=args.base_url or os.environ.get("OPENAI_COMPAT_URL"),
        model=args.model,
        provider=resolved_provider,
    )
    gate = lambda name, arguments: default_gate(name, arguments, dry_run=args.dry_run)

    if args.verbose:
        print(f"[harness] task={args.task[:80]!r}  dry_run={args.dry_run}  log={log_path}")
        print(f"[harness] tools={list(TOOL_REGISTRY.keys()) if not allowed else allowed}")
        if routed_role:
            print(f"[harness] role_router → role={routed_role}  provider={resolved_provider}")

    t0 = time.time()
    outcome = tl.run_loop(
        args.task, sampler, reg,
        gate=gate,
        max_turns=args.max_turns,
        turn_sink=ts,
        record_sink=rs,
        session_id=sid,
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
