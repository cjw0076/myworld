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
import re
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


def _safe_summary(category: str, tools=None, loop_type: str | None = None) -> str:
    """Privacy gate (DNA #7 / P0) — delegates to the canonical implementation in
    aios_capture_args so every global call site shares ONE definition. Only structural
    metadata leaves the device for the global corpus, never the raw goal/prompt/output."""
    try:
        import aios_capture_args as _CAP  # noqa: PLC0415
        return _CAP.safe_summary(category, tools, loop_type)
    except Exception:  # noqa: BLE001
        parts = [f"category:{category}"]
        if tools:
            parts.append("tools:" + ",".join(str(t) for t in list(tools)[:10]))
        if loop_type:
            parts.append(f"pattern:{loop_type}")
        return " ".join(parts)


def recall(goal: str, api_key: str | None = None, verbose: bool = False) -> list[dict]:
    """Retrieve top-3 similar patterns from the GLOBAL AkashicRecord using a structural
    query only (never the raw goal). For semantic recall, use the local vault."""
    res = _akashic_post("/sync", {"query": _safe_summary(_classify(goal)), "top_k": 3}, api_key, verbose)
    return res.get("results", [])


def predict(goal: str, api_key: str | None = None, verbose: bool = False) -> list[str]:
    """Predict top-3 likely tools for this goal (structural query only — no raw goal)."""
    res = _akashic_post("/predict", {"context": _safe_summary(_classify(goal)), "top_k": 8}, api_key, verbose)
    raw = [p["tool"] for p in res.get("predictions", [])]
    # Filter out garbage tool names (model IDs, truncated strings, nonsense suffixes)
    valid = [t for t in raw if _valid_tool_name(t)]
    return valid[:3]


_KNOWN_TOOLS = {
    "Bash", "Read", "Edit", "Write", "WebSearch", "WebFetch", "Agent",
    "Task", "Skill", "Browse", "Search",
}
_VALID_CLI = {
    "ls", "find", "grep", "cat", "echo", "mkdir", "rm", "cp", "mv",
    "git", "curl", "wget", "python", "python3", "pip", "npm", "make",
    "docker", "kubectl", "ssh", "df", "du", "ps", "kill", "sed", "awk",
    "sort", "head", "tail", "wc", "diff", "tar", "zip", "unzip", "chmod",
    "env", "export", "cd", "pwd", "which", "test",
}
# Only these colon prefixes are meaningful in AIOS context
_VALID_PREFIXES = {"bash", "note", "web", "memory", "cap", "aios", "read", "edit", "write"}


def _valid_tool_name(name: str) -> bool:
    if not isinstance(name, str) or not name:
        return False
    # Exact AIOS tool names
    if name in _KNOWN_TOOLS:
        return True
    # agentbank / aios_ prefix format: "bash:cmd", "note:slug", etc.
    if ":" in name:
        prefix, suffix = name.split(":", 1)
        if prefix not in _VALID_PREFIXES:
            return False  # reject sql:*, go:*, take:*, unknown:*
        if not re.match(r'^[a-z0-9_/-]{1,20}$', suffix):
            return False
        # Bash suffix must be a known CLI command
        if prefix == "bash" and suffix not in _VALID_CLI:
            return False
        return True
    # aios_ prefixed internal tools
    if name.startswith("aios_") and re.match(r'^aios_[a-z0-9_]{2,30}$', name):
        return True
    # Reject model names and short unknowns
    return False


def contribute(goal: str, tools_used: list[str], provider: str,
               duration_s: float, api_key: str | None = None) -> dict:
    """Store this session's pattern back to AkashicRecord."""
    import hashlib, datetime
    session_id = hashlib.sha256(
        f"{goal}{time.time()}".encode()
    ).hexdigest()[:16]
    category = _classify(goal)
    payload = {
        "id":        f"agent-{session_id}",
        # P0 privacy fix: structural summary ONLY — the raw goal never leaves the device.
        "content":   _safe_summary(category, tools_used),
        "category":  category,
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


def _lm_studio_available() -> bool:
    try:
        base = os.environ.get("LM_STUDIO_URL", "http://127.0.0.1:1234")
        with urllib.request.urlopen(base + "/v1/models", timeout=2) as r:
            return len(json.loads(r.read()).get("data", [])) > 0
    except Exception:
        return False


def _vllm_available() -> bool:
    try:
        base = os.environ.get("VLLM_URL", "http://127.0.0.1:8000")
        with urllib.request.urlopen(base + "/v1/models", timeout=2) as r:
            return True
    except Exception:
        return False


def _cli_available(name: str) -> bool:
    import shutil
    return shutil.which(name) is not None


def auto_route(goal: str, predicted_tools: list[str]) -> str:
    """Pick best available provider. Local-first (free, private)."""
    if _ollama_available():
        return "local"
    if _lm_studio_available():
        return "lm-studio"
    if _vllm_available():
        return "vllm"
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


def _openai_compat(base_url: str, model: str, prompt: str,
                    api_key: str = "none", timeout: int = 120) -> tuple[str, list[str]]:
    """OpenAI-compatible /v1/chat/completions — works with any server that speaks it.

    Covers: Ollama (/v1), vLLM, LM Studio, Jan.ai, llama.cpp server,
    Hugging Face TGI, Codestral, any OpenAI-API-compatible endpoint.
    """
    payload = {
        "model":    model,
        "messages": [{"role": "user", "content": prompt}],
        "stream":   False,
        "max_tokens": 2048,
    }
    data = json.dumps(payload).encode()
    headers = {
        "Content-Type":  "application/json",
        "Authorization": f"Bearer {api_key}",
    }
    req = urllib.request.Request(
        base_url.rstrip("/") + "/v1/chat/completions",
        data=data, headers=headers,
    )
    with urllib.request.urlopen(req, timeout=timeout) as r:
        res = json.loads(r.read())
    text = res["choices"][0]["message"]["content"]
    return text, [model]


def _list_ollama_models() -> list[str]:
    """Return available Ollama model names via /api/tags."""
    try:
        with urllib.request.urlopen(OLLAMA + "/api/tags", timeout=3) as r:
            return [m["name"] for m in json.loads(r.read()).get("models", [])]
    except Exception:
        return []


# Preferred model priority — coder models first, fallback to general
_PREFERRED_MODELS = [
    "qwen3-coder:30b",
    "deepseek-coder-v2:16b",
    "codestral:22b",
    "starcoder2:15b",
    "qwen3:30b-a3b",
    "qwen3:8b",
    "llama3.1:8b",
    "mistral:7b",
    "phi3:mini",
]


def _best_local_model(available: list[str]) -> str | None:
    """Pick the highest-priority model from what's installed."""
    for pref in _PREFERRED_MODELS:
        if any(pref in m or m in pref for m in available):
            return next(m for m in available if pref in m or m in pref)
    return available[0] if available else None


def _run_ollama(prompt: str) -> tuple[str, list[str]]:
    """Call local Ollama — auto-picks best available model."""
    try:
        models = _list_ollama_models()
        model = _best_local_model(models)
        if not model:
            return "no ollama model available — run: ollama pull qwen3:8b", []
        # Ollama supports OpenAI-compatible /v1 endpoint (v0.1.24+)
        try:
            return _openai_compat(OLLAMA, model, prompt)
        except Exception:
            # Fallback to Ollama native /api/generate
            payload = {"model": model, "prompt": prompt,
                       "stream": False, "options": {"num_predict": 2048}}
            req = urllib.request.Request(
                OLLAMA + "/api/generate",
                data=json.dumps(payload).encode(),
                headers={"Content-Type": "application/json"},
            )
            with urllib.request.urlopen(req, timeout=120) as r:
                return json.loads(r.read()).get("response", ""), [model]
    except Exception as e:
        return f"ollama error: {e}", []


def _run_lm_studio(prompt: str) -> tuple[str, list[str]]:
    """LM Studio (default port 1234) — OpenAI-compatible."""
    try:
        base = os.environ.get("LM_STUDIO_URL", "http://127.0.0.1:1234")
        # GET /v1/models to find available model
        with urllib.request.urlopen(base + "/v1/models", timeout=3) as r:
            models = json.loads(r.read()).get("data", [])
        model = models[0]["id"] if models else "local-model"
        return _openai_compat(base, model, prompt)
    except Exception as e:
        return f"lm-studio error: {e}", []


def _run_vllm(prompt: str) -> tuple[str, list[str]]:
    """vLLM server — OpenAI-compatible. Set VLLM_URL env var."""
    try:
        base  = os.environ.get("VLLM_URL", "http://127.0.0.1:8000")
        model = os.environ.get("VLLM_MODEL", "default")
        return _openai_compat(base, model, prompt)
    except Exception as e:
        return f"vllm error: {e}", []


def _run_custom_openai(prompt: str) -> tuple[str, list[str]]:
    """Any OpenAI-compatible endpoint. Set OPENAI_COMPAT_URL + OPENAI_COMPAT_MODEL."""
    try:
        base  = os.environ.get("OPENAI_COMPAT_URL", "")
        model = os.environ.get("OPENAI_COMPAT_MODEL", "gpt-4o-mini")
        key   = os.environ.get("OPENAI_COMPAT_KEY", "none")
        if not base:
            return "set OPENAI_COMPAT_URL to use custom endpoint", []
        return _openai_compat(base, model, prompt, api_key=key)
    except Exception as e:
        return f"openai-compat error: {e}", []


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


def execute(provider: str, prompt: str,
            base_url: str | None = None, model: str | None = None,
            api_key_compat: str | None = None) -> tuple[str, list[str]]:
    """Dispatch to provider. base_url/model override for any OpenAI-compat endpoint."""
    # Direct custom endpoint (--base-url wins over everything)
    if base_url:
        m = model or os.environ.get("OPENAI_COMPAT_MODEL", "local-model")
        k = api_key_compat or os.environ.get("OPENAI_COMPAT_KEY", "none")
        try:
            return _openai_compat(base_url, m, prompt, api_key=k)
        except Exception as e:
            return f"custom endpoint error ({base_url}): {e}", []

    dispatch = {
        "local":      _run_ollama,
        "lm-studio":  _run_lm_studio,
        "vllm":       _run_vllm,
        "openai":     _run_custom_openai,
        "claude":     _run_claude,
        "codex":      _run_codex,
        "gemini":     _run_gemini,
    }
    fn = dispatch.get(provider)
    if fn is None:
        return (
            "No provider available.\n"
            "  Options:\n"
            "    --provider local          (Ollama — ollama.ai)\n"
            "    --provider lm-studio      (LM Studio — lmstudio.ai)\n"
            "    --provider vllm           (vLLM — VLLM_URL env)\n"
            "    --base-url http://...     (any OpenAI-compat endpoint)\n"
            "    --provider claude|codex|gemini\n"
            "  Quick install: aios setup apply",
            [],
        )
    return fn(prompt)


# ── Interactive chat loop ─────────────────────────────────────────────────────

def chat_loop(provider: str, api_key: str | None, verbose: bool,
              base_url: str | None = None, model: str | None = None,
              api_key_compat: str | None = None) -> None:
    desc = base_url or provider
    print(f"[AIOS Agent] provider={desc}  type 'quit' to exit")
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
                            verbose=verbose, history=history,
                            base_url=base_url, model=model,
                            api_key_compat=api_key_compat)
        print(f"\naios> {result['output']}\n")
        history.append(f"goal: {goal}\nresult: {result['output'][:200]}")


# ── Single-shot run ───────────────────────────────────────────────────────────

def run_single(goal: str, provider: str | None = None,
               api_key: str | None = None, verbose: bool = False,
               history: list[str] | None = None,
               base_url: str | None = None, model: str | None = None,
               api_key_compat: str | None = None) -> dict:
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

    # 2. ROUTE (base_url bypasses routing entirely)
    if base_url:
        chosen = f"custom:{base_url.split('/')[2]}"
    else:
        chosen = provider or auto_route(goal, predicted)
    if verbose:
        print(f"[route] provider={chosen}")

    # 3. AUGMENT
    prompt = _build_prompt(goal, patterns, predicted)
    if history:
        prompt = "\n".join(history[-3:]) + "\n\n" + prompt

    # 4. EXECUTE
    output, tools_used = execute(
        chosen, prompt,
        base_url=base_url, model=model, api_key_compat=api_key_compat,
    )

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
    p.add_argument("--execute", action="store_true",
                   help="Execute mode: routes through aios_harness for real tool calls "
                        "(Bash/Read/Edit/Write). Advisory mode (default) just returns text.")
    p.add_argument("--provider",
                   choices=["auto", "local", "lm-studio", "vllm", "openai",
                            "claude", "codex", "gemini"],
                   default="auto",
                   help="Force a provider (default: auto-select)")
    p.add_argument("--base-url", default=None, metavar="URL",
                   help="Any OpenAI-compatible endpoint, e.g. http://localhost:8080 "
                        "(llama.cpp / Jan.ai / anything with /v1/chat/completions)")
    p.add_argument("--model", default=None, metavar="MODEL",
                   help="Model name to pass to --base-url or --provider vllm/openai")
    p.add_argument("--compat-key", default=None, metavar="KEY",
                   help="Bearer token for --base-url (default: 'none')")
    p.add_argument("--api-key", default=None,
                   help="AKR API key for token credits (or set AIOS_API_KEY)")
    p.add_argument("--verbose", "-v", action="store_true")
    p.add_argument("--json", dest="as_json", action="store_true")

    args = p.parse_args(argv)

    # Resolve API key
    api_key = args.api_key or os.environ.get("AIOS_API_KEY") or _load_saved_key()

    # Provider
    provider = None if args.provider == "auto" else args.provider
    base_url = args.base_url or os.environ.get("OPENAI_COMPAT_URL") or None
    model    = args.model or None
    compat_k = args.compat_key or os.environ.get("OPENAI_COMPAT_KEY") or None

    if args.chat:
        actual = provider or auto_route("", [])
        chat_loop(actual, api_key, args.verbose,
                  base_url=base_url, model=model, api_key_compat=compat_k)
        return 0

    if not args.goal:
        p.print_help()
        return 1

    # Execute mode: RECALL + PREDICT first, then pass predicted tools to harness
    if args.execute:
        # Step 1: AkashicRecord — recall similar patterns + predict tools
        predicted_tools: list[str] = []
        if args.verbose:
            print("[execute] querying AkashicRecord for tool predictions...", file=sys.stderr)
        try:
            predicted_tools = predict(args.goal, api_key, args.verbose)
        except Exception as e:
            if args.verbose:
                print(f"[execute] predict failed: {e}", file=sys.stderr)

        # Step 2: Map predicted tool names to TOOL_REGISTRY names
        _HARNESS_TOOLS = {"Bash", "Read", "Edit", "Write", "WebSearch"}
        _PREDICT_MAP   = {
            "bash": "Bash", "bash:": "Bash",
            "edit": "Edit", "read": "Read", "write": "Write",
            "websearch": "WebSearch", "webfetch": "WebSearch",
        }
        resolved: list[str] = []
        for t in predicted_tools:
            tl = t.lower().split(":")[0]
            mapped = _PREDICT_MAP.get(tl)
            if mapped:
                resolved.append(mapped)
            elif t in _HARNESS_TOOLS:
                resolved.append(t)
        # Always include Bash as fallback; deduplicate preserving order
        resolved = list(dict.fromkeys(resolved)) or ["Bash", "Read"]
        if args.verbose:
            print(f"[execute] predicted → resolved tools: {predicted_tools} → {resolved}",
                  file=sys.stderr)

        # Step 3: Delegate to harness with informed tool set
        harness_path = Path(__file__).parent / "aios_harness.py"
        harness_argv = [args.goal, "--tools", ",".join(resolved)]
        if base_url:
            harness_argv += ["--base-url", base_url]
        if model:
            harness_argv += ["--model", model]
        if api_key:
            harness_argv += ["--api-key", api_key]
        if args.verbose:
            harness_argv += ["--verbose"]
        if args.as_json:
            harness_argv += ["--json"]
        harness_spec = importlib.util.spec_from_file_location("aios_harness", harness_path)
        harness_mod  = importlib.util.module_from_spec(harness_spec)
        harness_spec.loader.exec_module(harness_mod)
        return harness_mod.main(harness_argv)

    result = run_single(args.goal, provider=provider,
                        api_key=api_key, verbose=args.verbose,
                        base_url=base_url, model=model, api_key_compat=compat_k)

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
