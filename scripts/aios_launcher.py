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


def root_report(root: Path, source: str) -> dict[str, Any]:
    return {
        "schema_version": SCHEMA_VERSION,
        "status": "ok",
        "root": root.as_posix(),
        "source": source,
        "runtime": (root / ROOT_MARKER).as_posix(),
        "hivemind": (root / "hivemind").as_posix(),
    }


def run_delegate(command: list[str], *, cwd: Path) -> int:
    completed = subprocess.run(command, cwd=cwd)
    return completed.returncode


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="AIOS global launcher")
    parser.add_argument("--root", help="AIOS control-plane root. Defaults to nearest ancestor, AIOS_HOME, then launcher-relative root.")
    parser.add_argument("cmd", choices=["root", "status", "step", "run", "submit-goal", "provider-loop"])
    parser.add_argument("args", nargs=argparse.REMAINDER)
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    root, source = resolve_root(args.root)

    if args.cmd == "root":
        payload = root_report(root, source)
        if "--json" in args.args:
            print(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True))
        else:
            print(payload["root"])
        return 0

    if args.cmd in {"status", "step", "run", "submit-goal"}:
        return run_delegate(runtime_command(root, [args.cmd, *args.args]), cwd=root)

    if args.cmd == "provider-loop":
        command, cwd = provider_loop_command(root, args.args)
        return run_delegate(command, cwd=cwd)

    parser.error(f"unknown command: {args.cmd}")
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
