#!/usr/bin/env python3
"""
aios_provider.py — AIOS multi-provider caller.

AIOS sits ABOVE the provider layer: routes tasks to the right LLM CLI
and returns structured results. Handles:
  - gemini   → `gemini -p --output-format text`
  - claude   → via Anthropic API (requires ANTHROPIC_API_KEY)
  - local    → ollama HTTP API at :11434

Usage:
  python3 scripts/aios_provider.py call --provider gemini --prompt "..."
  python3 scripts/aios_provider.py call --provider local --model qwen3-coder:30b --prompt "..."
  python3 scripts/aios_provider.py call --provider claude --model claude-sonnet-4-6 --prompt "..."
  python3 scripts/aios_provider.py route --prompt "..." --auto   # CapabilityOS routing

Environment:
  ANTHROPIC_API_KEY   required for --provider claude
  AIOS_VAULT_DIR      vault location (for aios_vault.py integration)
  OLLAMA_HOST         ollama host (default: http://localhost:11434)
"""

import argparse
import json
import os
import subprocess
import sys
import urllib.error
import urllib.request
from pathlib import Path

OLLAMA_HOST = os.environ.get("OLLAMA_HOST", "http://localhost:11434")
DEFAULT_LOCAL_MODEL = "qwen3-coder:30b"
DEFAULT_CLAUDE_MODEL = "claude-sonnet-4-6"
DEFAULT_GEMINI_MODEL = "gemini-2.0-flash"

# ── provider implementations ──────────────────────────────────────────────────

def call_gemini(prompt: str, model: str | None = None, timeout: int = 60) -> dict:
    """Call Gemini CLI in headless mode and return result dict."""
    cmd = ["gemini", "-p", prompt, "--output-format", "text"]
    if model:
        cmd += ["--model", model]
    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=timeout,
        )
        return {
            "provider": "gemini",
            "model": model or DEFAULT_GEMINI_MODEL,
            "ok": result.returncode == 0,
            "text": result.stdout.strip(),
            "error": result.stderr.strip() if result.returncode != 0 else None,
        }
    except subprocess.TimeoutExpired:
        return {"provider": "gemini", "ok": False, "error": f"timeout after {timeout}s", "text": ""}
    except FileNotFoundError:
        return {"provider": "gemini", "ok": False, "error": "gemini CLI not found", "text": ""}


def get_best_local_model() -> str:
    """Return the best available local model from ollama, falling back to default."""
    # Preference order: coding-specialist first, then general
    preference = ["qwen3-coder:30b", "qwen3-coder", "qwen3:14b", "qwen3:7b", "qwen3:1.7b"]
    try:
        with urllib.request.urlopen(f"{OLLAMA_HOST}/api/tags", timeout=3) as resp:
            data = json.loads(resp.read())
            available = {m["name"] for m in data.get("models", [])}
            for p in preference:
                if p in available:
                    return p
            if available:
                return next(iter(available))
    except Exception:
        pass
    return DEFAULT_LOCAL_MODEL


def call_local_llm(prompt: str, model: str | None = None, timeout: int = 120) -> dict:
    """Call local LLM via ollama HTTP API. Auto-selects best available model if none specified."""
    model = model or get_best_local_model()
    url = f"{OLLAMA_HOST}/api/generate"
    payload = json.dumps({"model": model, "prompt": prompt, "stream": False}).encode()
    req = urllib.request.Request(url, data=payload, headers={"Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            data = json.loads(resp.read().decode())
            return {
                "provider": "local",
                "model": model,
                "ok": True,
                "text": data.get("response", "").strip(),
                "error": None,
            }
    except urllib.error.URLError as e:
        return {"provider": "local", "ok": False, "error": f"ollama unreachable: {e}", "text": ""}
    except Exception as e:
        return {"provider": "local", "ok": False, "error": str(e), "text": ""}


def call_claude(prompt: str, model: str | None = None, timeout: int = 60) -> dict:
    """Call Claude via Anthropic API (requires ANTHROPIC_API_KEY)."""
    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        # Try vault
        try:
            vault_result = subprocess.run(
                ["python3", str(Path(__file__).parent / "aios_vault.py"), "get", "ANTHROPIC_API_KEY"],
                capture_output=True, text=True, timeout=10,
            )
            if vault_result.returncode == 0:
                api_key = vault_result.stdout.strip()
        except Exception:
            pass
    if not api_key:
        return {"provider": "claude", "ok": False, "error": "ANTHROPIC_API_KEY not set (try aios_vault.py set ANTHROPIC_API_KEY)", "text": ""}

    model = model or DEFAULT_CLAUDE_MODEL
    payload = json.dumps({
        "model": model,
        "max_tokens": 2048,
        "messages": [{"role": "user", "content": prompt}],
    }).encode()
    req = urllib.request.Request(
        "https://api.anthropic.com/v1/messages",
        data=payload,
        headers={
            "x-api-key": api_key,
            "anthropic-version": "2023-06-01",
            "content-type": "application/json",
        },
    )
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            data = json.loads(resp.read().decode())
            text = data.get("content", [{}])[0].get("text", "")
            return {"provider": "claude", "model": model, "ok": True, "text": text.strip(), "error": None}
    except Exception as e:
        return {"provider": "claude", "ok": False, "error": str(e), "text": ""}


# ── routing heuristics ────────────────────────────────────────────────────────

ROUTING_TABLE = [
    # (condition_fn, provider, model, rationale)
    (lambda p: len(p) > 8000, "gemini", None, "long context → Gemini large context window"),
    (lambda p: any(w in p.lower() for w in ["privacy", "private", "secret", "credential", "sensitive"]),
     "local", DEFAULT_LOCAL_MODEL, "privacy → local LLM (data stays on device)"),
    (lambda p: any(w in p.lower() for w in ["web", "search", "latest", "current", "today", "2026"]),
     "gemini", None, "web/current info → Gemini (has web access)"),
    (lambda p: any(w in p.lower() for w in ["code", "python", "javascript", "debug", "implement", "write"]),
     "local", DEFAULT_LOCAL_MODEL, "coding → local qwen3-coder (if available), else claude"),
]

def _gemini_available() -> bool:
    try:
        r = subprocess.run(["gemini", "--version"], capture_output=True, timeout=5)
        return r.returncode == 0
    except (FileNotFoundError, subprocess.TimeoutExpired):
        return False


def auto_route(prompt: str) -> tuple[str, str | None, str]:
    """Return (provider, model, rationale) based on routing heuristics."""
    for condition, provider, model, rationale in ROUTING_TABLE:
        if condition(prompt):
            if provider == "local":
                test = call_local_llm("ping", model=model or DEFAULT_LOCAL_MODEL)
                if not test["ok"]:
                    return "claude", DEFAULT_CLAUDE_MODEL, f"local unavailable ({test['error']}), falling back to claude"
            elif provider == "gemini":
                if not _gemini_available():
                    return "claude", DEFAULT_CLAUDE_MODEL, "gemini unavailable, falling back to claude"
            return provider, model, rationale
    return "claude", DEFAULT_CLAUDE_MODEL, "default → claude sonnet"


# ── commands ──────────────────────────────────────────────────────────────────

def cmd_call(args) -> None:
    provider = args.provider
    prompt = args.prompt
    model = getattr(args, "model", None)

    if provider == "gemini":
        result = call_gemini(prompt, model=model, timeout=args.timeout)
    elif provider == "local":
        result = call_local_llm(prompt, model=model or DEFAULT_LOCAL_MODEL, timeout=args.timeout)
    elif provider == "claude":
        result = call_claude(prompt, model=model, timeout=args.timeout)
    else:
        print(f"Unknown provider: {provider}", file=sys.stderr)
        sys.exit(1)

    if args.json:
        print(json.dumps(result, ensure_ascii=False, indent=2))
    elif result["ok"]:
        print(result["text"])
    else:
        print(f"ERROR [{provider}]: {result['error']}", file=sys.stderr)
        sys.exit(1)


def cmd_route(args) -> None:
    provider, model, rationale = auto_route(args.prompt)
    if args.auto:
        # Actually call the routed provider
        print(f"[aios_provider] routing → {provider} ({rationale})", file=sys.stderr)
        args.provider = provider
        args.model = model
        cmd_call(args)
    else:
        print(f"provider: {provider}")
        print(f"model:    {model or '(default)'}")
        print(f"rationale: {rationale}")


def cmd_status(args) -> None:
    """Check which providers are available right now."""
    results = []

    # Gemini
    try:
        test = subprocess.run(["gemini", "--version"], capture_output=True, text=True, timeout=5)
        results.append(("gemini", test.returncode == 0, test.stdout.strip()))
    except (FileNotFoundError, subprocess.TimeoutExpired) as e:
        results.append(("gemini", False, f"not found: {e}"))

    # Local
    try:
        resp = urllib.request.urlopen(f"{OLLAMA_HOST}/api/tags", timeout=3)
        data = json.loads(resp.read())
        models = [m["name"] for m in data.get("models", [])]
        results.append(("local (ollama)", True, f"models: {models}"))
    except Exception as e:
        results.append(("local (ollama)", False, str(e)))

    # Claude API
    api_key = os.environ.get("ANTHROPIC_API_KEY")
    results.append(("claude (api)", bool(api_key), "ANTHROPIC_API_KEY set" if api_key else "no API key"))

    for name, ok, detail in results:
        status = "✓" if ok else "✗"
        print(f"{status} {name:20s} {detail}")


# ── main ──────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description="AIOS multi-provider caller")
    parser.add_argument("--json", action="store_true", help="Output JSON")
    sub = parser.add_subparsers(dest="command")

    p_call = sub.add_parser("call", help="Call a specific provider")
    p_call.add_argument("--provider", required=True, choices=["gemini", "local", "claude"])
    p_call.add_argument("--prompt", required=True, help="Prompt text")
    p_call.add_argument("--model", help="Override model")
    p_call.add_argument("--timeout", type=int, default=60)

    p_route = sub.add_parser("route", help="Auto-route prompt to best provider")
    p_route.add_argument("--prompt", required=True)
    p_route.add_argument("--auto", action="store_true", help="Actually call the routed provider")
    p_route.add_argument("--model", help="Override model")
    p_route.add_argument("--timeout", type=int, default=60)

    sub.add_parser("status", help="Check which providers are available")

    args = parser.parse_args()
    if args.command is None:
        parser.print_help()
        return

    dispatch = {"call": cmd_call, "route": cmd_route, "status": cmd_status}
    dispatch[args.command](args)


if __name__ == "__main__":
    main()
