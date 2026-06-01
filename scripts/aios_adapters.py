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
from dataclasses import dataclass
from typing import Callable

# A runner takes an argv list + timeout and returns (returncode, stdout, stderr).
Runner = Callable[[list[str], int], "tuple[int, str, str]"]


def _real_runner(argv: list[str], timeout: int) -> tuple[int, str, str]:
    try:
        r = subprocess.run(argv, text=True, capture_output=True,
                           timeout=timeout, check=False)
        return r.returncode, r.stdout, r.stderr
    except subprocess.TimeoutExpired:
        return 124, "", f"timeout after {timeout}s"
    except OSError as exc:
        return 127, "", str(exc)


@dataclass(frozen=True)
class AdapterSpec:
    """How to turn a prompt into an argv for one provider."""
    name: str
    binary: str                      # CLI binary name, e.g. "claude"
    argv_template: list[str]         # uses "{prompt}" as the placeholder token
    timeout: int = 180

    def build_argv(self, prompt: str) -> list[str]:
        return [self.binary if tok == "{binary}" else
                (prompt if tok == "{prompt}" else tok)
                for tok in self.argv_template]


# Command shapes per provider. These are the print/non-interactive forms.
# (Live invocation is opt-in; nothing here runs a CLI by import.)
SPECS: dict[str, AdapterSpec] = {
    "claude": AdapterSpec("claude", "claude", ["{binary}", "-p", "{prompt}"]),
    "codex": AdapterSpec("codex", "codex", ["{binary}", "exec", "{prompt}"]),
    "gemini": AdapterSpec("gemini", "gemini", ["{binary}", "-p", "{prompt}"]),
    "ollama_local": AdapterSpec(
        "ollama_local", "ollama", ["{binary}", "run", "qwen3:8b", "{prompt}"],
        timeout=300),
}


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
        code, out, err = runner(argv, spec.timeout)
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
) -> dict[str, Callable[[str], str]]:
    """Construct the adapter registry the runner consumes.

    By default only builds adapters whose binary is present on PATH, so an
    absent provider cleanly falls through to the runner's offline named-exit.
    Pass require_present=False to build regardless (e.g. with a fake runner).
    """
    names = providers if providers is not None else list(SPECS)
    registry: dict[str, Callable[[str], str]] = {}
    for name in names:
        spec = SPECS.get(name)
        if spec is None:
            continue
        if require_present and which(spec.binary) is None:
            continue
        registry[name] = make_adapter(spec, runner)
    return registry


if __name__ == "__main__":
    import json
    print(json.dumps({
        "specs": sorted(SPECS),
        "available_now": available_providers(),
    }, indent=2))
