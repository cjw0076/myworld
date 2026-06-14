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

_OLLAMA_REST_URL = "http://localhost:11434/api/generate"
_OLLAMA_REST_MODEL = "qwen3:1.7b"   # fast; swappable per deployment


def make_ollama_rest_adapter(
    *,
    url: str = _OLLAMA_REST_URL,
    model: str = _OLLAMA_REST_MODEL,
    timeout: int = 60,
) -> "Callable[[str], str]":
    """Build an adapter that calls the Ollama REST API directly — no binary on PATH needed.

    ~0.2-1s latency (vs 25-180s for frontier CLI providers), making it ideal
    for the SSE streaming turn-loop where each turn fires an event.
    The model is expected to return JSON directly; think mode is disabled.
    """
    import json as _json
    import urllib.request as _req

    def adapter(prompt: str) -> str:
        body = _json.dumps({
            "model": model,
            "prompt": prompt,
            "stream": False,
            "think": False,   # disable chain-of-thought (qwen3 feature)
        }).encode()
        request = _req.Request(url, data=body, headers={"Content-Type": "application/json"})
        try:
            with _req.urlopen(request, timeout=timeout) as resp:
                data = _json.loads(resp.read())
                return data.get("response", "")
        except Exception as exc:
            raise RuntimeError(f"ollama_rest: {exc}") from exc

    adapter.__name__ = "adapter_ollama_rest"
    return adapter


def _ollama_rest_available(url: str = _OLLAMA_REST_URL) -> bool:
    """Return True if the Ollama REST endpoint is reachable."""
    import urllib.request as _req
    try:
        _req.urlopen(_req.Request(url.replace("/api/generate", "/api/tags")), timeout=2)
        return True
    except Exception:
        return False


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
        spec = SPECS.get(name)
        if spec is None:
            continue
        if require_present and which(spec.binary) is None:
            continue
        registry[name] = make_adapter(spec, runner)

    # Auto-register ollama_rest when asking for all providers and REST is reachable
    if providers is None and "ollama_rest" not in registry and _rest_ok():
        registry["ollama_rest"] = make_ollama_rest_adapter()

    return registry


if __name__ == "__main__":
    import json
    print(json.dumps({
        "specs": sorted(SPECS),
        "available_now": available_providers(),
    }, indent=2))
