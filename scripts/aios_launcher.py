#!/usr/bin/env python3
"""Thin AIOS launcher.

The launcher is intentionally stateless. It resolves a MyWorld control-plane
root, then delegates to the AIOS runtime or Hive provider-loop surface.
"""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import time
import webbrowser
from pathlib import Path
from typing import Any


ROOT_MARKER = Path("scripts") / "aios_runtime.py"
SCHEMA_VERSION = "aios.launcher.v1"


def launcher_relative_root() -> Path:
    return Path(__file__).resolve().parents[1]


def is_aios_root(path: Path) -> bool:
    return (path / ROOT_MARKER).exists()


def nearest_aios_root(start: Path) -> Path | None:
    current = start.resolve()
    for candidate in [current, *current.parents]:
        if is_aios_root(candidate):
            return candidate
    return None


def resolve_root(explicit_root: str | None = None, *, cwd: Path | None = None, environ: dict[str, str] | None = None) -> tuple[Path, str]:
    env = environ if environ is not None else os.environ
    if explicit_root:
        root = Path(explicit_root).expanduser().resolve()
        if not is_aios_root(root):
            raise SystemExit(f"not an AIOS root: {root}")
        return root, "explicit"

    start = (cwd or Path.cwd()).resolve()
    nearest = nearest_aios_root(start)
    if nearest:
        return nearest, "nearest_ancestor"

    if env.get("AIOS_HOME"):
        root = Path(env["AIOS_HOME"]).expanduser().resolve()
        if not is_aios_root(root):
            raise SystemExit(f"AIOS_HOME is not an AIOS root: {root}")
        return root, "AIOS_HOME"

    root = launcher_relative_root()
    if not is_aios_root(root):
        raise SystemExit(f"launcher-relative root is not an AIOS root: {root}")
    return root, "launcher_relative"


def runtime_command(root: Path, argv: list[str]) -> list[str]:
    return [sys.executable, (root / "scripts" / "aios_runtime.py").as_posix(), "--root", root.as_posix(), *argv]


def ask_command(root: Path, argv: list[str]) -> list[str]:
    return [sys.executable, (root / "scripts" / "aios_ask.py").as_posix(), "--root", root.as_posix(), *argv]


def chat_command(root: Path, argv: list[str]) -> list[str]:
    return [sys.executable, (root / "scripts" / "aios_chat.py").as_posix(), "--root", root.as_posix(), *argv]


def provider_loop_command(root: Path, argv: list[str]) -> tuple[list[str], Path]:
    hive_root = root / "hivemind"
    if not (hive_root / "hivemind" / "hive.py").exists():
        raise SystemExit(f"Hive Mind repo is not available under AIOS root: {hive_root}")
    return (
        [
            sys.executable,
            "-m",
            "hivemind.hive",
            "--root",
            hive_root.as_posix(),
            "provider-loop",
            *argv,
        ],
        hive_root,
    )


def discover_command(root: Path, argv: list[str]) -> list[str]:
    args = argv if argv and argv[0] in {"scan", "invoke"} else ["scan", *argv]
    # `scan` requires a target --root; default to the current directory so bare
    # `aios discover` works instead of erroring on a missing arg the user can't guess.
    if args and args[0] == "scan" and "--root" not in args:
        args = [args[0], "--root", Path.cwd().as_posix(), *args[1:]]
    return [sys.executable, (root / "scripts" / "aios_project_discovery.py").as_posix(), "--control-root", root.as_posix(), *args]


def init_command(root: Path, argv: list[str]) -> list[str]:
    return [sys.executable, (root / "scripts" / "aios_workbench_init.py").as_posix(), "--root", root.as_posix(), *argv]


def workbench_command(root: Path, argv: list[str]) -> list[str]:
    return [sys.executable, (root / "scripts" / "aios_workbench.py").as_posix(), "--root", root.as_posix(), *argv]


def emit_recap_command(root: Path, argv: list[str]) -> list[str]:
    return [sys.executable, (root / "scripts" / "aios_emit_recap.py").as_posix(), "--root", root.as_posix(), *argv]


def helper_command(root: Path, argv: list[str]) -> list[str]:
    return [sys.executable, (root / "scripts" / "aios_helper.py").as_posix(), "--root", root.as_posix(), *argv]


def dream_command(root: Path, argv: list[str]) -> list[str]:
    return [sys.executable, (root / "scripts" / "aios_dream.py").as_posix(), "--root", root.as_posix(), *argv]


def research_fetch_command(root: Path, argv: list[str]) -> list[str]:
    return [sys.executable, (root / "scripts" / "aios_research_fetch.py").as_posix(), "--root", root.as_posix(), *argv]


def mcp_command(root: Path, argv: list[str]) -> list[str]:
    return [sys.executable, (root / "scripts" / "aios_mcp_server.py").as_posix(), "--root", root.as_posix(), *argv]


def sovereignty_command(root: Path, argv: list[str]) -> list[str]:
    return [sys.executable, (root / "scripts" / "aios_sovereignty.py").as_posix(), "--root", root.as_posix(), *argv]


def local_operator_command(root: Path, argv: list[str]) -> list[str]:
    return [sys.executable, (root / "scripts" / "aios_local_operator.py").as_posix(), "--root", root.as_posix(), *argv]


def self_evolve_command(root: Path, argv: list[str]) -> list[str]:
    return [sys.executable, (root / "scripts" / "aios_self_evolve.py").as_posix(), "--root", root.as_posix(), *argv]


def verify_command(root: Path, argv: list[str]) -> list[str]:
    return [sys.executable, (root / "scripts" / "aios_verify.py").as_posix(), "--root", root.as_posix(), *argv]


def complete_command(root: Path, argv: list[str]) -> list[str]:
    return [sys.executable, (root / "scripts" / "aios_completion.py").as_posix(), "--root", root.as_posix(), *argv]


def ingest_conversations_command(root: Path, argv: list[str]) -> list[str]:
    return [sys.executable, (root / "scripts" / "aios_ingest_conversations.py").as_posix(), "--root", root.as_posix(), *argv]


def librarian_command(root: Path, argv: list[str]) -> list[str]:
    return [sys.executable, (root / "scripts" / "aios_librarian.py").as_posix(), "--root", root.as_posix(), *argv]


def setup_command(root: Path, argv: list[str]) -> list[str]:
    return [sys.executable, (root / "scripts" / "aios_setup.py").as_posix(), "--root", root.as_posix(), *argv]


def capability_feedback_command(root: Path, argv: list[str]) -> list[str]:
    return [sys.executable, (root / "scripts" / "aios_capability_feedback.py").as_posix(), "--root", root.as_posix(), *argv]


def device_profile_command(root: Path, argv: list[str]) -> list[str]:
    return [sys.executable, (root / "scripts" / "aios_device_profile.py").as_posix(), "--root", root.as_posix(), *argv]


def self_model_command(root: Path, argv: list[str]) -> list[str]:
    return [sys.executable, (root / "scripts" / "aios_self_model.py").as_posix(), "--root", root.as_posix(), *argv]


def demo_command(root: Path, argv: list[str]) -> list[str]:
    if argv and argv[0] == "agent":
        return [sys.executable, (root / "scripts" / "aios_agent_demo.py").as_posix(), *argv[1:]]
    return [sys.executable, (root / "scripts" / "aios_demo.py").as_posix(), *argv]


def dispatch_reconcile_command(root: Path, argv: list[str]) -> list[str]:
    return [sys.executable, (root / "scripts" / "aios_dispatch_reconcile.py").as_posix(), "--root", root.as_posix(), *argv]


def jobs_command(root: Path, argv: list[str]) -> list[str]:
    return [sys.executable, (root / "scripts" / "aios_jobs.py").as_posix(), "--root", root.as_posix(), *argv]


def hooks_command(root: Path, argv: list[str]) -> list[str]:
    return [sys.executable, (root / "scripts" / "aios_hooks.py").as_posix(), "--root", root.as_posix(), *argv]


def install_command(root: Path, argv: list[str]) -> list[str]:
    return [sys.executable, (root / "scripts" / "aios_install.py").as_posix(), "--root", root.as_posix(), "install", *argv]


def uninstall_command(root: Path, argv: list[str]) -> list[str]:
    return [sys.executable, (root / "scripts" / "aios_install.py").as_posix(), "--root", root.as_posix(), "uninstall", *argv]


def local_app_command(root: Path, argv: list[str]) -> list[str]:
    return [sys.executable, (root / "scripts" / "aios_local_app.py").as_posix(), "--root", root.as_posix(), *argv]


def open_control_app(root: Path, argv: list[str]) -> int:
    args = [item for item in argv if item not in {"--no-browser", "--json"}]
    no_browser = "--no-browser" in argv
    json_mode = "--json" in argv
    up_args = ["up", *args]
    if "--json" not in up_args:
        up_args.append("--json")
    rc = run_delegate(local_app_command(root, up_args), cwd=root)
    if rc != 0:
        return rc
    url = "http://127.0.0.1:8765/"
    if not no_browser:
        webbrowser.open(url)
    if not json_mode:
        print(url)
    return 0


def root_report(root: Path, source: str) -> dict[str, Any]:
    return {
        "schema_version": SCHEMA_VERSION,
        "status": "ok",
        "root": root.as_posix(),
        "source": source,
        "runtime": (root / ROOT_MARKER).as_posix(),
        "hivemind": (root / "hivemind").as_posix(),
    }


def _serve(root: Path, argv: list[str]) -> int:
    """Start the AIOS end-user serving UI + API.

    Usage: aios serve [--port PORT] [--host HOST] [--tunnel]

    --tunnel: pipe traffic through a cloudflared quick tunnel so the
              serving UI is accessible from outside localhost.
    """
    import argparse as _ap
    import threading as _threading
    import time as _time

    p = _ap.ArgumentParser(prog="aios serve")
    p.add_argument("--port", type=int, default=8741)
    p.add_argument("--host", default="127.0.0.1")
    p.add_argument("--tunnel", action="store_true",
                   help="expose via cloudflared quick tunnel (requires cloudflared)")
    opts = p.parse_args(argv)

    api_script = root / "scripts" / "aios_serving_api.py"
    if not api_script.exists():
        print(f"[aios serve] error: {api_script} not found — run from AIOS root", flush=True)
        return 1

    host = "0.0.0.0" if opts.tunnel else opts.host
    api_proc = subprocess.Popen(
        [sys.executable, str(api_script), "--host", host, "--port", str(opts.port)],
        cwd=root,
    )
    # Give the API a moment to bind, then confirm it actually came up before
    # claiming success — otherwise a bind failure (port in use) prints "started"
    # and lies to the user.
    time.sleep(1.0)
    if api_proc.poll() is not None:
        print(f"[aios serve] API failed to start on :{opts.port} "
              f"(port in use? try --port). exit={api_proc.returncode}", flush=True)
        return 1
    print(f"[aios serve] API started on http://{host}:{opts.port}/", flush=True)

    tunnel_proc = None
    if opts.tunnel:
        cf = subprocess.run(["which", "cloudflared"], capture_output=True)
        if cf.returncode != 0:
            print("[aios serve] --tunnel requires cloudflared — install from https://github.com/cloudflare/cloudflared/releases", flush=True)
            api_proc.terminate()
            return 1
        # cloudflared prints the public URL to stderr: https://xxxx.trycloudflare.com
        tunnel_proc = subprocess.Popen(
            ["cloudflared", "tunnel", "--url", f"http://localhost:{opts.port}"],
            stderr=subprocess.PIPE, text=True,
        )
        print("[aios serve] cloudflared tunnel starting…", flush=True)
        url = None
        import re as _re
        for _ in range(90):
            line = tunnel_proc.stderr.readline()
            if not line:
                break
            if "trycloudflare.com" in line:
                m = _re.search(r'https://[\w.-]+\.trycloudflare\.com', line)
                if m:
                    url = m.group(0)
                    break
        if url:
            print(f"\n[aios serve] PUBLIC URL: {url}", flush=True)
            print(f"[aios serve] Share this URL — anyone can access your AIOS serving UI.", flush=True)
        else:
            print("[aios serve] tunnel URL not detected — check cloudflared output above", flush=True)

    try:
        api_proc.wait()
    except KeyboardInterrupt:
        print("\n[aios serve] stopping…", flush=True)
    finally:
        api_proc.terminate()
        if tunnel_proc:
            tunnel_proc.terminate()
    return 0


def run_delegate(command: list[str], *, cwd: Path) -> int:
    completed = subprocess.run(command, cwd=cwd)
    return completed.returncode


# Curated command surface (hermes-style): a tight core up front, the rest grouped.
# Every command stays functional — grouping only changes how `aios --help` reads.
_CORE_COMMANDS = [
    ("do",      "Run a task end-to-end: plan → tools → result"),
    ("onboard", "Absorb this device's LLMs + agent CLIs and verify what's usable"),
    ("chat",    "Interactive AIOS session"),
    ("serve",   "Start the local web UI + API (http://localhost:8741)"),
    ("status",  "Runtime health and findings"),
    ("demo",    "30-second verifiable-AI demo"),
    ("ask",     "Single-shot question to the organism"),
    ("setup",   "Install local models / configure providers"),
]
_MEMORY_COMMANDS = [
    ("behavior",   "Behavioral memory: predict / contribute / status"),
    ("dream",      "Consolidate memory (dream cycle)"),
    ("self-model", "What AIOS knows about itself"),
]
# Operator / advanced — functional but not front-of-house for new users.
_ADVANCED_COMMANDS = [
    "run", "submit-goal", "sprint-loop", "provider-loop", "step", "discover",
    "init", "workbench", "emit-recap", "helper", "research-fetch", "mcp",
    "sovereignty", "local-operator", "self-evolve", "verify", "complete",
    "ingest-conversations", "agent", "harness", "librarian", "capability-feedback",
    "device-profile", "dispatch-reconcile", "jobs", "hooks", "install",
    "uninstall", "up", "open", "stop", "root",
]
_ALL_COMMANDS = (
    [n for n, _ in _CORE_COMMANDS]
    + [n for n, _ in _MEMORY_COMMANDS]
    + _ADVANCED_COMMANDS
)


def _help_epilog() -> str:
    def _rows(rows):
        return "\n".join(f"  {n:<14}{d}" for n, d in rows)
    return (
        "core commands:\n" + _rows(_CORE_COMMANDS) + "\n\n"
        "memory & behavior:\n" + _rows(_MEMORY_COMMANDS) + "\n\n"
        "advanced / operator:\n  " + ", ".join(_ADVANCED_COMMANDS) + "\n\n"
        "Run 'aios <command> -h' for command-specific help."
    )


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="aios",
        usage="aios [--root ROOT] <command> [args...]",
        description="AIOS — local-first AI operating layer that wraps provider "
                    "agent CLIs and learns from every run.",
        epilog=_help_epilog(),
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument("--root", help="AIOS control-plane root. Defaults to nearest ancestor, AIOS_HOME, then launcher-relative root.")
    # metavar keeps argparse from dumping the full 40-item choices blob in usage;
    # nargs='?' lets a bare `aios` print help instead of erroring.
    parser.add_argument("cmd", nargs="?", metavar="<command>", choices=_ALL_COMMANDS,
                        help=argparse.SUPPRESS)
    parser.add_argument("args", nargs=argparse.REMAINDER, help=argparse.SUPPRESS)
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    if args.cmd is None:                 # bare `aios` → show the curated help, not an error
        parser.print_help()
        return 0

    root, source = resolve_root(args.root)

    if args.cmd == "root":
        payload = root_report(root, source)
        if "--json" in args.args:
            print(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True))
        else:
            print(payload["root"])
        return 0

    if args.cmd == "demo":
        return run_delegate(demo_command(root, args.args), cwd=root)

    if args.cmd in {"status", "step", "run", "submit-goal", "sprint-loop"}:
        return run_delegate(runtime_command(root, [args.cmd, *args.args]), cwd=root)

    if args.cmd == "ask":
        return run_delegate(ask_command(root, args.args), cwd=root)

    if args.cmd == "chat":
        return run_delegate(chat_command(root, args.args), cwd=root)

    if args.cmd == "provider-loop":
        command, cwd = provider_loop_command(root, args.args)
        return run_delegate(command, cwd=cwd)

    if args.cmd == "discover":
        return run_delegate(discover_command(root, args.args), cwd=root)

    if args.cmd == "init":
        return run_delegate(init_command(root, args.args), cwd=Path.cwd())

    if args.cmd == "workbench":
        return run_delegate(workbench_command(root, args.args), cwd=root)

    if args.cmd == "emit-recap":
        return run_delegate(emit_recap_command(root, args.args), cwd=root)

    if args.cmd == "helper":
        return run_delegate(helper_command(root, args.args), cwd=root)

    if args.cmd == "dream":
        return run_delegate(dream_command(root, args.args), cwd=root)

    if args.cmd == "research-fetch":
        return run_delegate(research_fetch_command(root, args.args), cwd=root)

    if args.cmd == "mcp":
        return run_delegate(mcp_command(root, args.args), cwd=root)

    if args.cmd == "sovereignty":
        return run_delegate(sovereignty_command(root, args.args), cwd=root)

    if args.cmd == "local-operator":
        return run_delegate(local_operator_command(root, args.args), cwd=root)

    if args.cmd == "self-evolve":
        return run_delegate(self_evolve_command(root, args.args), cwd=root)

    if args.cmd == "verify":
        return run_delegate(verify_command(root, args.args), cwd=root)

    if args.cmd == "complete":
        return run_delegate(complete_command(root, args.args), cwd=root)

    if args.cmd == "ingest-conversations":
        return run_delegate(ingest_conversations_command(root, args.args), cwd=Path.cwd())

    if args.cmd == "behavior":
        cmd = [sys.executable, (root / "scripts" / "aios_agent_behavior.py").as_posix(), *args.args]
        return run_delegate(cmd, cwd=Path.cwd())

    if args.cmd == "agent":
        cmd = [sys.executable, (root / "scripts" / "aios_agent_system.py").as_posix(), *args.args]
        return run_delegate(cmd, cwd=Path.cwd())

    if args.cmd == "harness":
        cmd = [sys.executable, (root / "scripts" / "aios_harness.py").as_posix(), *args.args]
        return run_delegate(cmd, cwd=Path.cwd())

    if args.cmd == "do":
        # Zero-friction task execution: aios do "goal" → harness with smart defaults.
        # Model is left unpinned so the harness routes by task horizon (renewal
        # pillar 2): long/multi-step tasks → reasoning model, short → fast model.
        harness_args = list(args.args)
        if "--base-url" not in " ".join(harness_args) and "--model" not in " ".join(harness_args):
            harness_args += ["--base-url", "http://localhost:11434"]
        cmd = [sys.executable, (root / "scripts" / "aios_harness.py").as_posix(), *harness_args]
        return run_delegate(cmd, cwd=Path.cwd())

    if args.cmd == "librarian":
        return run_delegate(librarian_command(root, args.args), cwd=root)

    if args.cmd == "setup":
        return run_delegate(setup_command(root, args.args), cwd=root)

    if args.cmd == "capability-feedback":
        return run_delegate(capability_feedback_command(root, args.args), cwd=root)

    if args.cmd == "device-profile":
        return run_delegate(device_profile_command(root, args.args), cwd=root)

    if args.cmd == "self-model":
        return run_delegate(self_model_command(root, args.args), cwd=root)

    if args.cmd == "onboard":
        return run_delegate(
            [sys.executable, (root / "scripts" / "aios_onboard.py").as_posix(), *args.args],
            cwd=root)

    if args.cmd == "dispatch-reconcile":
        return run_delegate(dispatch_reconcile_command(root, args.args), cwd=root)

    if args.cmd == "jobs":
        return run_delegate(jobs_command(root, args.args), cwd=root)

    if args.cmd == "hooks":
        return run_delegate(hooks_command(root, args.args), cwd=root)

    if args.cmd == "install":
        install_args = args.args or ["--json", "--enable-now"]
        return run_delegate(install_command(root, install_args), cwd=root)

    if args.cmd == "uninstall":
        uninstall_args = args.args or ["--json", "--disable-now"]
        return run_delegate(uninstall_command(root, uninstall_args), cwd=root)

    if args.cmd == "up":
        up_args = args.args or ["--json"]
        if up_args and up_args[0] not in {"refresh", "start", "serve", "stop", "status", "up"}:
            up_args = ["up", *up_args]
        elif not up_args or up_args[0] != "up":
            up_args = ["up", *up_args]
        return run_delegate(local_app_command(root, up_args), cwd=root)

    if args.cmd == "serve":
        return _serve(root, args.args)

    if args.cmd == "open":
        return open_control_app(root, args.args)

    if args.cmd == "stop":
        rc_app = run_delegate(local_app_command(root, ["stop", "--json", *args.args]), cwd=root)
        rc_round = run_delegate([sys.executable, (root / "scripts" / "aios_round_controller.py").as_posix(), "stop", "--root", root.as_posix()], cwd=root)
        return rc_app or rc_round

    parser.error(f"unknown command: {args.cmd}")
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
