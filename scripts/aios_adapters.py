#!/usr/bin/env python3
"""AIOS provider adapter layer — missing head piece #2.

The ContractObject runtime (aios_contract_runner.py) authorizes `provider.<name>`
syscalls but has no live substrate to call. This module is that substrate: a
registry of provider adapters, each a callable `adapter(prompt) -> str` that
shells to a provider CLI (or a local LLM) behind a uniform interface.

Design:
  - Each adapter is built from a *command template* + a *runner* callable. The
    runner is dependency-injected (default = real subprocess) so the whole layer
    is unit-testable without invoking real CLIs (which would recurse / cost / need
    auth). Tests pass a fake runner; production passes the real one.
  - An adapter for an absent CLI is simply not registered. The runner then takes
    its existing "authorized but no live adapter (offline)" named-exit path.
  - No secrets here. API keys live in the provider CLI's own config, never in
    AIOS artifacts (see the leaked-key incident — keys never belong in repo).

Adapters intentionally cover the four substrates from the kernel audit:
  claude / codex / gemini  -> frontier planners & hard reasoning
  ollama_local             -> cheap always-on background cognition (qwen3 etc.)
"""
from __future__ import annotations

import shutil
import subprocess
from dataclasses import dataclass, field
from typing import Callable

# A runner takes an argv list + optional stdin string + timeout and returns (returncode, stdout, stderr).
# Signature: (argv, stdin_text_or_none, timeout) -> (returncode, stdout, stderr)
Runner = Callable[[list[str], "str | None", int], "tuple[int, str, str]"]


def _real_runner(argv: list[str], stdin_text: "str | None", timeout: int) -> tuple[int, str, str]:
    try:
        r = subprocess.run(
            argv, text=True, capture_output=True,
            input=stdin_text if stdin_text is not None else None,
            stdin=None if stdin_text is not None else subprocess.DEVNULL,
            timeout=timeout, check=False,
        )
        return r.returncode, r.stdout, r.stderr
    except subprocess.TimeoutExpired:
        return 124, "", f"timeout after {timeout}s"
    except OSError as exc:
        return 127, "", str(exc)


@dataclass(frozen=True)
class AdapterSpec:
    """How to turn a prompt into an argv (and optional stdin) for one provider."""
    name: str
    binary: str                      # CLI binary name, e.g. "claude"
    argv_template: list[str]         # uses "{prompt}" as placeholder; omit for stdin mode
    timeout: int = 180
    use_stdin: bool = False          # if True, prompt is sent via stdin instead of as a CLI arg

    def build_argv(self, prompt: str) -> list[str]:
        if self.use_stdin:
            # No "{prompt}" substitution — prompt goes to stdin
            return [self.binary if tok == "{binary}" else tok for tok in self.argv_template]
        return [self.binary if tok == "{binary}" else
                (prompt if tok == "{prompt}" else tok)
                for tok in self.argv_template]

    def get_stdin(self, prompt: str) -> "str | None":
        return prompt if self.use_stdin else None


# Command shapes per provider. These are the print/non-interactive forms.
# (Live invocation is opt-in; nothing here runs a CLI by import.)
SPECS: dict[str, AdapterSpec] = {
    # claude -p reads prompt from stdin reliably; positional-arg form triggers
    # MCP server loading + context processing that adds 40-180s latency.
    "claude": AdapterSpec("claude", "claude", ["{binary}", "-p"], use_stdin=True),
    "codex": AdapterSpec("codex", "codex", ["{binary}", "exec", "{prompt}"]),
    "gemini": AdapterSpec("gemini", "gemini", ["{binary}", "-p", "{prompt}"]),
    "ollama_local": AdapterSpec(
        "ollama_local", "ollama", ["{binary}", "run", "qwen3:8b", "{prompt}"],
        timeout=300),
}

# Ollama v1 (OpenAI-compatible) endpoint — works with all Ollama ≥0.1.24.
# Using OpenAI-compat lets future providers (OpenAI, Together.ai, Groq) share the
# same _http_post_json() path without adding any PyPI dependency.
_OLLAMA_REST_BASE = "http://localhost:11434/v1"
_OLLAMA_REST_MODEL = "qwen3:1.7b"   # fast; swappable per deployment
_OLLAMA_HEALTH_URL = "http://localhost:11434/api/tags"

_ANTHROPIC_API_URL = "https://api.anthropic.com/v1/messages"
_ANTHROPIC_REST_MODEL = "claude-haiku-4-5-20251001"  # fastest + cheapest frontier

_GEMINI_API_URL = "https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent"
_GEMINI_REST_MODEL = "gemini-2.0-flash-lite"  # free tier: 1500 req/day, 30 req/min


def _http_post_json(url: str, body: dict, headers: dict, timeout: int) -> dict:
    """Single stdlib HTTP POST + JSON parse, shared by all REST adapters."""
    import json as _json
    import urllib.request as _req
    data = _json.dumps(body).encode()
    req = _req.Request(url, data=data, headers={"Content-Type": "application/json", **headers})
    with _req.urlopen(req, timeout=timeout) as resp:
        return _json.loads(resp.read())


def make_ollama_rest_adapter(
    *,
    base_url: str = _OLLAMA_REST_BASE,
    model: str = _OLLAMA_REST_MODEL,
    timeout: int = 60,
    # Legacy alias kept for callers that pass url= keyword argument.
    url: "str | None" = None,
) -> "Callable[[str], str]":
    """Build an adapter that calls Ollama via its OpenAI-compatible REST API.

    Uses /v1/chat/completions (OpenAI format) instead of the native /api/generate
    so any future OpenAI-compatible provider can reuse the same code path.
    think mode is suppressed via a /no_think system message (qwen3 feature).
    ~0.2-1s latency, stdlib-only, no PyPI dependency.
    """
    if url is not None:
        # Legacy callers passed url=/api/generate — silently upgrade to v1 base.
        base_url = url.replace("/api/generate", "").rstrip("/") + "/v1"

    def adapter(prompt: str) -> str:
        chat_url = base_url.rstrip("/") + "/chat/completions"
        body = {
            "model": model,
            "stream": False,
            "messages": [
                {"role": "system", "content": "/no_think"},
                {"role": "user", "content": prompt},
            ],
        }
        try:
            data = _http_post_json(chat_url, body, {}, timeout)
            return data["choices"][0]["message"]["content"]
        except Exception as exc:
            raise RuntimeError(f"ollama_rest: {exc}") from exc

    adapter.__name__ = "adapter_ollama_rest"
    return adapter


def _ollama_rest_available(url: str = _OLLAMA_HEALTH_URL) -> bool:
    """Return True if the Ollama REST endpoint is reachable."""
    import urllib.request as _req
    # Accept both legacy /api/generate URLs and the new health URL.
    health_url = url if "/api/tags" in url else _OLLAMA_HEALTH_URL
    try:
        _req.urlopen(_req.Request(health_url), timeout=2)
        return True
    except Exception:
        return False


def _anthropic_rest_available() -> bool:
    """Return True if ANTHROPIC_API_KEY is set (Anthropic REST API usable)."""
    import os
    return bool(os.environ.get("ANTHROPIC_API_KEY"))


def _gemini_rest_available() -> bool:
    """Return True if GEMINI_API_KEY or GOOGLE_API_KEY is set (Gemini REST API usable)."""
    import os
    return bool(os.environ.get("GEMINI_API_KEY") or os.environ.get("GOOGLE_API_KEY"))


def make_gemini_rest_adapter(
    *,
    model: str = _GEMINI_REST_MODEL,
    timeout: int = 60,
) -> "Callable[[str], str]":
    """Build an adapter that calls the Gemini generateContent API directly.

    Activates when GEMINI_API_KEY or GOOGLE_API_KEY is set. Free tier:
    gemini-2.0-flash-lite → 1500 req/day, 30 req/min. No billing required.
    Priority: Ollama (free local) → Gemini (free cloud) → Anthropic (paid cloud).
    """
    import os as _os

    def adapter(prompt: str) -> str:
        api_key = _os.environ.get("GEMINI_API_KEY") or _os.environ.get("GOOGLE_API_KEY", "")
        if not api_key:
            raise RuntimeError("gemini_rest: GEMINI_API_KEY or GOOGLE_API_KEY not set")
        url = _GEMINI_API_URL.format(model=model) + f"?key={api_key}"
        body = {
            "contents": [{"parts": [{"text": prompt}]}],
            "generationConfig": {"maxOutputTokens": 2048},
        }
        try:
            data = _http_post_json(url, body, {}, timeout)
            return data["candidates"][0]["content"]["parts"][0]["text"]
        except Exception as exc:
            raise RuntimeError(f"gemini_rest: {exc}") from exc

    adapter.__name__ = "adapter_gemini_rest"
    return adapter


def make_anthropic_rest_adapter(
    *,
    model: str = _ANTHROPIC_REST_MODEL,
    timeout: int = 60,
) -> "Callable[[str], str]":
    """Build an adapter that calls the Anthropic Messages API directly.

    Activates automatically when ANTHROPIC_API_KEY is set — no CLI binary needed.
    Used as a fallback when Ollama is unavailable (e.g. GitHub Codespaces free tier).
    """
    import os as _os

    def adapter(prompt: str) -> str:
        api_key = _os.environ.get("ANTHROPIC_API_KEY", "")
        if not api_key:
            raise RuntimeError("anthropic_rest: ANTHROPIC_API_KEY not set")
        body = {
            "model": model,
            "max_tokens": 2048,
            "messages": [{"role": "user", "content": prompt}],
        }
        headers = {
            "x-api-key": api_key,
            "anthropic-version": "2023-06-01",
        }
        try:
            data = _http_post_json(_ANTHROPIC_API_URL, body, headers, timeout)
            return data["content"][0]["text"]
        except Exception as exc:
            raise RuntimeError(f"anthropic_rest: {exc}") from exc

    adapter.__name__ = "adapter_anthropic_rest"
    return adapter


@dataclass
class AdapterResult:
    ok: bool
    text: str = ""
    error: str | None = None


def make_adapter(spec: AdapterSpec, runner: Runner = _real_runner):
    """Build a callable adapter(prompt) -> str from a spec.

    Raises on non-zero return so the runner records a failed receipt with the
    stderr (named exit, not silent success).
    """
    def adapter(prompt: str) -> str:
        argv = spec.build_argv(prompt)
        stdin_text = spec.get_stdin(prompt)
        code, out, err = runner(argv, stdin_text, spec.timeout)
        if code != 0:
            raise RuntimeError(f"{spec.name} exited {code}: {err.strip()[:200]}")
        return out
    adapter.__name__ = f"adapter_{spec.name}"
    return adapter


def available_providers(which: Callable[[str], str | None] = shutil.which) -> list[str]:
    """Provider names whose CLI binary is on PATH right now."""
    return [name for name, spec in SPECS.items() if which(spec.binary) is not None]


def build_adapters(
    providers: list[str] | None = None,
    *,
    runner: Runner = _real_runner,
    which: Callable[[str], str | None] = shutil.which,
    require_present: bool = True,
    rest_available: "Callable[[], bool] | None" = None,
) -> dict[str, Callable[[str], str]]:
    """Construct the adapter registry the runner consumes.

    By default only builds adapters whose binary is present on PATH, so an
    absent provider cleanly falls through to the runner's offline named-exit.
    Pass require_present=False to build regardless (e.g. with a fake runner).
    Also auto-registers ollama_rest if the Ollama HTTP endpoint is reachable.
    Pass rest_available=lambda: False to suppress auto-registration in tests.
    """
    _rest_ok = rest_available if rest_available is not None else _ollama_rest_available
    names = providers if providers is not None else list(SPECS)
    registry: dict[str, Callable[[str], str]] = {}
    for name in names:
        if name == "ollama_rest":
            if _rest_ok():
                registry["ollama_rest"] = make_ollama_rest_adapter()
            continue
        if name == "ollama_rest_8b":
            if _rest_ok():
                registry["ollama_rest_8b"] = make_ollama_rest_adapter(model="qwen3:8b", timeout=120)
            continue
        if name == "anthropic_rest":
            if _anthropic_rest_available():
                registry["anthropic_rest"] = make_anthropic_rest_adapter()
            continue
        if name == "gemini_rest":
            if _gemini_rest_available():
                registry["gemini_rest"] = make_gemini_rest_adapter()
            continue
        spec = SPECS.get(name)
        if spec is None:
            continue
        if require_present and which(spec.binary) is None:
            continue
        registry[name] = make_adapter(spec, runner)

    # Auto-register ollama_rest when asking for all providers and REST is reachable
    if providers is None and "ollama_rest" not in registry and _rest_ok():
        registry["ollama_rest"] = make_ollama_rest_adapter()
    # Auto-register anthropic_rest when ANTHROPIC_API_KEY is present
    if providers is None and "anthropic_rest" not in registry and _anthropic_rest_available():
        registry["anthropic_rest"] = make_anthropic_rest_adapter()
    # Auto-register gemini_rest when GEMINI_API_KEY / GOOGLE_API_KEY is present
    if providers is None and "gemini_rest" not in registry and _gemini_rest_available():
        registry["gemini_rest"] = make_gemini_rest_adapter()

    return registry


if __name__ == "__main__":
    import json
    print(json.dumps({
        "specs": sorted(SPECS),
        "available_now": available_providers(),
    }, indent=2))
