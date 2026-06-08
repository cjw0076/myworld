#!/usr/bin/env python3
"""AIOS execution sandbox — real OS-level isolation for tool/provider subprocesses.

The named biggest gap (AIOS_PROVIDER_REVERSE_ENGINEERING.md A1, converged across
Codex's bubblewrap sandbox and Gemini's docker/seatbelt): AIOS runs provider
CLIs (`codex exec`, `claude -p`, `ollama run`) via bare subprocess.run. Those
agents can read/write/execute ANYWHERE on the host on behalf of a model — the
most dangerous surface in AIOS, and until now ungoverned.

This wraps a subprocess in a bubblewrap (`bwrap`) namespace so it physically
cannot:
  - write outside its declared workspace (the rest of the filesystem is mounted
    read-only; /tmp is a private tmpfs; $HOME is readable but not writable);
  - reach the network (default: a fresh empty net namespace — egress denied),
    unless the caller explicitly grants it (provider CLIs need their API).

It is FAIL-CLOSED: if `bwrap` is unavailable or namespaces are denied, it raises
SandboxUnavailable and the caller MUST refuse to run — it NEVER silently falls
back to an unsandboxed subprocess. (That fallback is exactly how "sandboxed"
systems leak.)

The isolation here is enforced by the OS kernel, not by Python — so the
adversarial tests in tests/test_aios_sandbox.py actually attempt an escape and
assert the kernel blocked it.

Usage:
    from aios_sandbox import run_sandboxed, sandboxed_runner, bwrap_available
    code, out, err = run_sandboxed(["sh", "-c", "echo hi"], workspace="/path/ws")
"""
from __future__ import annotations

import shutil
import subprocess
from pathlib import Path
from typing import Callable


class SandboxUnavailable(RuntimeError):
    """Raised when OS isolation cannot be established. Fail-closed: do not run."""


def bwrap_available(which: Callable[[str], str | None] = shutil.which) -> bool:
    return which("bwrap") is not None


def build_bwrap_argv(
    argv: list[str],
    *,
    workspace: Path,
    allow_network: bool = False,
    allow_write: list[Path] | None = None,
    bwrap_bin: str = "bwrap",
) -> list[str]:
    """Construct the bwrap command that runs `argv` isolated to `workspace`.

    The whole root is bound read-only (so the program can find its binaries,
    libraries, and config), then the workspace (and any explicitly allowed
    paths) is bound read-write ON TOP — later binds win in bwrap, so only those
    paths are writable. /tmp is a private tmpfs. Network is unshared unless
    explicitly allowed.
    """
    ws = Path(workspace).resolve()
    cmd = [
        bwrap_bin,
        "--ro-bind", "/", "/",        # whole FS readable
        "--dev", "/dev",              # minimal device nodes
        "--proc", "/proc",            # private /proc
        "--tmpfs", "/tmp",            # private, ephemeral /tmp (host /tmp hidden)
        "--bind", str(ws), str(ws),   # workspace writable (overrides ro-bind /)
        "--unshare-pid",
        "--unshare-ipc",
        "--unshare-uts",
        "--die-with-parent",
        "--new-session",
        "--chdir", str(ws),
    ]
    if not allow_network:
        cmd += ["--unshare-net"]      # fresh empty net namespace → egress denied
    for p in (allow_write or []):
        rp = Path(p).resolve()
        cmd += ["--bind", str(rp), str(rp)]
    cmd += ["--", *argv]
    return cmd


def run_sandboxed(
    argv: list[str],
    *,
    workspace: str | Path,
    allow_network: bool = False,
    allow_write: list[Path] | None = None,
    timeout: int = 180,
    bwrap_bin: str | None = None,
    which: Callable[[str], str | None] = shutil.which,
) -> tuple[int, str, str]:
    """Run argv under OS isolation. Returns (returncode, stdout, stderr).

    Fail-closed: raises SandboxUnavailable if bwrap is missing — the caller must
    not run the command unsandboxed.
    """
    binary = bwrap_bin or "bwrap"
    if bwrap_bin is None and which(binary) is None:
        raise SandboxUnavailable("bwrap not found — refusing to run unsandboxed")
    ws = Path(workspace).resolve()
    if not ws.is_dir():
        raise SandboxUnavailable(f"workspace is not a directory: {ws}")
    cmd = build_bwrap_argv(argv, workspace=ws, allow_network=allow_network,
                           allow_write=allow_write, bwrap_bin=binary)
    try:
        r = subprocess.run(cmd, text=True, capture_output=True,
                           timeout=timeout, check=False)
    except FileNotFoundError as exc:                 # bwrap path bogus → fail-closed
        raise SandboxUnavailable(f"bwrap exec failed: {exc}") from exc
    except subprocess.TimeoutExpired:
        return 124, "", f"timeout after {timeout}s"
    # bwrap itself exits 1 on a namespace setup failure with no program run.
    # That is a sandbox failure, not a program failure — surface it fail-closed.
    if r.returncode == 1 and "bwrap:" in (r.stderr or ""):
        raise SandboxUnavailable(f"namespace setup failed: {r.stderr.strip()[:200]}")
    return r.returncode, r.stdout, r.stderr


def sandbox_self_test(which: Callable[[str], str | None] = shutil.which) -> dict:
    """Probe whether REAL kernel isolation can be established in this environment.

    Runs a trivial isolated command and reports the outcome. Used by tests and by
    the execution policy to decide between (real isolation) and (fail-closed
    refusal). Honest about WHY it can't isolate — never claims success it can't back.
    """
    if not bwrap_available(which):
        return {"isolated": False, "reason": "bwrap_not_found"}
    import tempfile

    with tempfile.TemporaryDirectory(prefix="aios_sbtest_") as ws:
        try:
            code, out, _ = run_sandboxed(["sh", "-c", "echo ok"], workspace=ws,
                                         allow_network=False, timeout=20)
        except SandboxUnavailable as exc:
            return {"isolated": False, "reason": str(exc)[:120]}
        return {"isolated": code == 0 and out.strip() == "ok", "reason": "ok" if code == 0 else "nonzero"}


# Set AIOS_ALLOW_UNSANDBOXED=1 to permit running provider subprocesses WITHOUT
# isolation when the kernel can't provide it. Default is secure (refuse). The
# override is loud: callers log it to the receipt.
UNSANDBOXED_OVERRIDE_ENV = "AIOS_ALLOW_UNSANDBOXED"


def sandboxed_runner(
    workspace: str | Path,
    *,
    allow_network: bool = False,
    allow_write: list[Path] | None = None,
) -> Callable[[list[str], int], tuple[int, str, str]]:
    """Return an aios_adapters.Runner that executes every argv inside the sandbox.

    Drop-in for the adapter layer: build_adapters(..., runner=sandboxed_runner(ws,
    allow_network=True)) makes even a provider CLI unable to write outside ws.
    """
    def runner(argv: list[str], timeout: int) -> tuple[int, str, str]:
        return run_sandboxed(argv, workspace=workspace, allow_network=allow_network,
                             allow_write=allow_write, timeout=timeout)
    return runner


if __name__ == "__main__":
    import json
    import sys

    ws = sys.argv[1] if len(sys.argv) > 1 else "."
    probe = ["sh", "-c", "echo sandbox-ok; id -u"]
    try:
        code, out, err = run_sandboxed(probe, workspace=ws, allow_network=False)
        print(json.dumps({"bwrap_available": bwrap_available(), "returncode": code,
                          "stdout": out.strip(), "stderr": err.strip()[:200]}, indent=2))
    except SandboxUnavailable as exc:
        print(json.dumps({"bwrap_available": bwrap_available(),
                          "sandbox_unavailable": str(exc)}, indent=2))
        raise SystemExit(3)
