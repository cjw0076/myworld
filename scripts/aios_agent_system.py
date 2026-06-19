#!/usr/bin/env python3
"""AIOS Agent System — goal-first, memory-augmented, provider-agnostic.

The missing loop that connects all 5 OS into one runnable command:

    aios agent "fix the auth bug"
    aios agent --chat
    aios agent "분석해줘" --provider local

Flow per goal:
  RECALL   → AkashicRecord: what worked for similar goals?
  PREDICT  → AkashicRecord: which tools are most likely?
  ROUTE    → CapabilityOS: which provider fits? (auto or forced)
  AUGMENT  → Build enriched context for the provider
  EXECUTE  → Call provider (Ollama / Claude CLI / Codex CLI / Gemini)
  CAPTURE  → Record tool sequence
  STORE    → Contribute pattern → AkashicRecord + earn AKR

Design principle: complexity inside AIOS, not on the user.
  - Beginner: aios agent "goal"            (AIOS decides everything)
  - Expert:   aios agent "goal" --provider claude --verbose
"""
from __future__ import annotations

import argparse
import importlib.util
import json
import os
import subprocess
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any

ROOT     = Path(__file__).resolve().parents[1]
SCRIPTS  = ROOT / "scripts"
OLLAMA   = "http://127.0.0.1:11434"
AKASHIC  = os.environ.get("AIOS_AKASHIC_URL", "https://aios-akashic.cjw070690.workers.dev")
MAX_CONTEXT_CHARS = 600


# ── lazy loader ───────────────────────────────────────────────────────────────

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


# ── AkashicRecord thin client ─────────────────────────────────────────────────

def _akashic_post(path: str, payload: dict, api_key: str | None = None,
                  verbose: bool = False) -> dict:
    try:
        headers = {"Content-Type": "application/json", "User-Agent": "AIOS-Agent/1.0"}
        if api_key:
            headers["X-AIOS-Key"] = api_key
        data = json.dumps(payload).encode()
        req = urllib.request.Request(AKASHIC + path, data=data,
                                     headers=headers, method="POST")
        with urllib.request.urlopen(req, timeout=20) as r:
            return json.loads(r.read())
    except Exception as e:
        if verbose:
            print(f"[akashic{path}] {e}", file=sys.stderr)
        return {}


def recall(goal: str, api_key: str | None = None, verbose: bool = False) -> list[dict]:
    """Retrieve top-3 similar past patterns from AkashicRecord."""
    res = _akashic_post("/sync", {"query": goal, "top_k": 3}, api_key, verbose)
    return res.get("results", [])


def predict(goal: str, api_key: str | None = None, verbose: bool = False) -> list[str]:
    """Predict top-3 likely tools for this goal."""
    res = _akashic_post("/predict", {"context": goal, "top_k": 3}, api_key, verbose)
    return [p["tool"] for p in res.get("predictions", [])]


def contribute(goal: str, tools_used: list[str], provider: str,
               duration_s: float, api_key: str | None = None) -> dict:
    """Store this session's pattern back to AkashicRecord."""
    import hashlib, datetime
    session_id = hashlib.sha256(
        f"{goal}{time.time()}".encode()
    ).hexdigest()[:16]
    payload = {
        "id":        f"agent-{session_id}",
        "content":   goal[:MAX_CONTEXT_CHARS],
        "category":  _classify(goal),
        "provider":  provider,
        "os_origin": "myworld",
        "top_tools": tools_used[:10],
        "tool_freq": {t: 1 for t in tools_used},
        "confidence": 0.8,
    }
    return _akashic_post("/contribute", payload, api_key)


def _classify(goal: str) -> str:
    g = goal.lower()
    if any(w in g for w in ["bug", "fix", "error", "test", "코드", "함수", "class"]):
        return "code"
    if any(w in g for w in ["분석", "analyze", "data", "csv", "graph"]):
        return "data"
    if any(w in g for w in ["write", "doc", "readme", "explain", "설명"]):
        return "docs"
    return "code"


# ── Provider routing ──────────────────────────────────────────────────────────

def _ollama_available() -> bool:
    try:
        with urllib.request.urlopen(OLLAMA + "/api/tags", timeout=2) as r:
            tags = json.loads(r.read())
            return len(tags.get("models", [])) > 0
    except Exception:
        return False


def _cli_available(name: str) -> bool:
    import shutil
    return shutil.which(name) is not None


def auto_route(goal: str, predicted_tools: list[str]) -> str:
    """Pick best available provider. Local-first (free, private)."""
    if _ollama_available():
        return "local"
    if _cli_available("claude"):
        return "claude"
    if _cli_available("codex"):
        return "codex"
    if _cli_available("gemini"):
        return "gemini"
    return "none"


# ── Provider execution ────────────────────────────────────────────────────────

def _build_prompt(goal: str, patterns: list[dict], predicted: list[str]) -> str:
    lines = [goal]
    if patterns:
        lines.append("\n[AIOS: similar past patterns]")
        for p in patterns[:3]:
            tools = p.get("top_tools", [])[:4]
            if tools:
                lines.append(f"  - {p.get('category','?')}: used {', '.join(str(t) for t in tools)}")
    if predicted:
        lines.append(f"\n[AIOS: predicted useful tools: {', '.join(predicted[:3])}]")
    return "\n".join(lines)


def _run_ollama(prompt: str) -> tuple[str, list[str]]:
    """Call Ollama HTTP API with qwen3 (best available)."""
    try:
        # Pick model
        with urllib.request.urlopen(OLLAMA + "/api/tags", timeout=3) as r:
            tags = json.loads(r.read())
        models = [m["name"] for m in tags.get("models", [])]
        preferred = ["qwen3-coder:30b", "qwen3:30b-a3b", "qwen3:8b", "qwen3:1.7b"]
        model = next((m for m in preferred if any(m in x for x in models)), models[0] if models else None)
        if not model:
            return "no ollama model available", []

        payload = {
            "model":  model,
            "prompt": prompt,
            "stream": False,
            "options": {"num_predict": 2048},
        }
        data = json.dumps(payload).encode()
        req = urllib.request.Request(OLLAMA + "/api/generate", data=data,
                                     headers={"Content-Type": "application/json"})
        with urllib.request.urlopen(req, timeout=120) as r:
            res = json.loads(r.read())
        return res.get("response", ""), [model]
    except Exception as e:
        return f"ollama error: {e}", []


def _run_claude(prompt: str) -> tuple[str, list[str]]:
    try:
        r = subprocess.run(
            ["claude", "--print", prompt],
            capture_output=True, text=True, timeout=120,
        )
        return (r.stdout or r.stderr).strip(), ["claude-cli"]
    except Exception as e:
        return f"claude error: {e}", []


def _run_codex(prompt: str) -> tuple[str, list[str]]:
    try:
        r = subprocess.run(
            ["codex", "--approval-mode", "suggest", "-q", prompt],
            capture_output=True, text=True, timeout=120,
        )
        return (r.stdout or r.stderr).strip(), ["codex-cli"]
    except Exception as e:
        return f"codex error: {e}", []


def _run_gemini(prompt: str) -> tuple[str, list[str]]:
    try:
        r = subprocess.run(
            ["gemini", "-p", prompt],
            capture_output=True, text=True, timeout=120,
        )
        return (r.stdout or r.stderr).strip(), ["gemini-cli"]
    except Exception as e:
        return f"gemini error: {e}", []


def execute(provider: str, prompt: str) -> tuple[str, list[str]]:
    dispatch = {
        "local":  _run_ollama,
        "claude": _run_claude,
        "codex":  _run_codex,
        "gemini": _run_gemini,
    }
    fn = dispatch.get(provider)
    if fn is None:
        return (
            "No provider available.\n"
            "  Install one:\n"
            "    Local LLM: aios setup apply    (pulls Ollama + qwen3)\n"
            "    Claude:    npm install -g @anthropic-ai/claude-code\n"
            "    Codex:     npm install -g @openai/codex\n"
            "    Gemini:    pip install google-generativeai",
            [],
        )
    return fn(prompt)


# ── Interactive chat loop ─────────────────────────────────────────────────────

def chat_loop(provider: str, api_key: str | None, verbose: bool) -> None:
    print(f"[AIOS Agent] provider={provider}  type 'quit' to exit")
    print("-" * 50)
    history: list[str] = []
    while True:
        try:
            goal = input("you> ").strip()
        except (EOFError, KeyboardInterrupt):
            print()
            break
        if not goal or goal.lower() in {"quit", "exit", "q"}:
            break

        result = run_single(goal, provider=provider, api_key=api_key,
                            verbose=verbose, history=history)
        print(f"\naios> {result['output']}\n")
        history.append(f"goal: {goal}\nresult: {result['output'][:200]}")


# ── Single-shot run ───────────────────────────────────────────────────────────

def run_single(goal: str, provider: str | None = None,
               api_key: str | None = None, verbose: bool = False,
               history: list[str] | None = None) -> dict:
    t0 = time.time()

    # 1. RECALL + PREDICT (in parallel — best-effort, fail silent)
    patterns: list[dict] = []
    predicted: list[str] = []
    try:
        patterns = recall(goal, api_key, verbose)
        predicted = predict(goal, api_key, verbose)
    except Exception as e:
        if verbose:
            print(f"[akashic] {e}", file=sys.stderr)

    if verbose:
        print(f"[recall] {len(patterns)} patterns  [predict] {predicted}")

    # 2. ROUTE
    chosen = provider or auto_route(goal, predicted)
    if verbose:
        print(f"[route] provider={chosen}")

    # 3. AUGMENT
    prompt = _build_prompt(goal, patterns, predicted)
    if history:
        prompt = "\n".join(history[-3:]) + "\n\n" + prompt

    # 4. EXECUTE
    output, tools_used = execute(chosen, prompt)

    # 5. STORE (fire-and-forget, non-blocking)
    duration = time.time() - t0
    try:
        ack = contribute(goal, tools_used + [chosen], chosen, duration, api_key)
        earned = ack.get("earned_akr") or 0
    except Exception:
        earned = 0

    result = {
        "goal":       goal,
        "provider":   chosen,
        "output":     output,
        "patterns":   len(patterns),
        "predicted":  predicted,
        "tools_used": tools_used,
        "duration_s": round(duration, 2),
        "earned_akr": earned,
    }
    return result


# ── CLI ───────────────────────────────────────────────────────────────────────

def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(
        prog="aios agent",
        description="AIOS Agent System — goal-first, memory-augmented agent.\n"
                    "Examples:\n"
                    "  aios agent 'fix the auth bug'\n"
                    "  aios agent --chat\n"
                    "  aios agent 'analyze data' --provider local",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    p.add_argument("goal", nargs="?", default=None,
                   help="Goal to execute (natural language)")
    p.add_argument("--chat", action="store_true",
                   help="Interactive chat mode")
    p.add_argument("--provider", choices=["auto", "local", "claude", "codex", "gemini"],
                   default="auto", help="Force a provider (default: auto-select)")
    p.add_argument("--api-key", default=None,
                   help="AKR API key for token credits (or set AIOS_API_KEY)")
    p.add_argument("--verbose", "-v", action="store_true")
    p.add_argument("--json", dest="as_json", action="store_true")

    args = p.parse_args(argv)

    # Resolve API key
    api_key = args.api_key or os.environ.get("AIOS_API_KEY") or _load_saved_key()

    # Provider
    provider = None if args.provider == "auto" else args.provider

    if args.chat:
        actual = provider or auto_route("", [])
        chat_loop(actual, api_key, args.verbose)
        return 0

    if not args.goal:
        p.print_help()
        return 1

    result = run_single(args.goal, provider=provider,
                        api_key=api_key, verbose=args.verbose)

    if args.as_json:
        print(json.dumps(result, ensure_ascii=False, indent=2))
    else:
        print(result["output"])
        if args.verbose or result.get("earned_akr"):
            meta = (f"[provider={result['provider']} "
                    f"patterns={result['patterns']} "
                    f"time={result['duration_s']}s"
                    + (f" +{result['earned_akr']}AKR" if result.get("earned_akr") else "")
                    + "]")
            print(meta, file=sys.stderr)

    return 0


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
