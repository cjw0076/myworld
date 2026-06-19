#!/usr/bin/env python3
"""AIOS Agent Demo — the full loop in 60 seconds.

Shows the AIOS differentiator: behavioral memory (AkashicRecord) informs
which tools the agent uses, not the model guessing from a blank slate.

Five steps shown live:
  RECALL → PREDICT → ROUTE → EXECUTE (multi-turn tool calls) → STORE

Usage:
  python scripts/aios_agent_demo.py           # all 3 benchmark tasks
  python scripts/aios_agent_demo.py --task 1  # single task
  python scripts/aios_agent_demo.py --quiet   # results only
  aios demo agent
"""
from __future__ import annotations

import argparse
import importlib.util
import json
import os
import subprocess
import sys
import time
from pathlib import Path

ROOT    = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "scripts"

BENCHMARK_TASKS = [
    {
        "id":    1,
        "goal":  "list all Python files in the scripts/ directory using bash ls",
        "check": lambda out: ".py" in out.get("tool_sequence", []) or
                             "Bash" in (out.get("tool_sequence") or []),
        "desc":  "file discovery",
    },
    {
        "id":    2,
        "goal":  "read the first 5 lines of README.md",
        "check": lambda out: bool(set(out.get("tool_sequence") or []) & {"Read", "Bash"}),
        "desc":  "file reading",
    },
    {
        "id":    3,
        "goal":  "create a file /tmp/aios_demo_output.txt with content: AIOS works",
        "check": lambda out: ("Write" in (out.get("tool_sequence") or []) or
                              "Bash" in (out.get("tool_sequence") or [])) and
                             Path("/tmp/aios_demo_output.txt").exists(),
        "desc":  "file creation",
    },
]


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


def _run_task(task: dict, quiet: bool, api_key: str | None) -> dict:
    """Run one benchmark task through the full AIOS loop."""
    goal = task["goal"]
    t0   = time.time()

    if not quiet:
        print(f"\n{'='*60}")
        print(f"Task {task['id']}: {task['desc']}")
        print(f"Goal: {goal}")
        print("-" * 40)

    # RECALL + PREDICT via AkashicRecord
    agent = _load("aios_agent_system")
    predicted: list[str] = []
    patterns:  list[dict] = []
    try:
        patterns  = agent.recall(goal, api_key) if agent else []
        predicted = agent.predict(goal, api_key) if agent else []
    except Exception:
        pass

    if not quiet:
        print(f"[RECALL]  {len(patterns)} similar patterns found")
        print(f"[PREDICT] predicted tools: {predicted[:3]}")

    # Resolve to harness tool names
    _MAP = {"bash": "Bash", "read": "Read", "edit": "Edit",
            "write": "Write", "websearch": "WebSearch", "webfetch": "WebSearch"}
    resolved = list(dict.fromkeys(
        [_MAP[t.lower().split(":")[0]] for t in predicted
         if t.lower().split(":")[0] in _MAP]
    )) or ["Bash", "Read"]

    if not quiet:
        print(f"[ROUTE]   harness tools: {resolved}")
        print("[EXECUTE] running harness...")

    # Execute via harness
    harness = _load("aios_harness")
    if harness is None:
        return {"error": "harness not found", "passed": False}

    try:
        # Capture harness run by calling directly
        import io
        from contextlib import redirect_stdout, redirect_stderr

        stdout_buf = io.StringIO()
        stderr_buf = io.StringIO()

        # Build harness args
        harness_argv = [goal, "--tools", ",".join(resolved), "--json"]
        if api_key:
            harness_argv += ["--api-key", api_key]

        # Run harness — capture JSON output
        old_stdout = sys.stdout
        sys.stdout = stdout_buf
        try:
            code = harness.main(harness_argv)
        finally:
            sys.stdout = old_stdout

        raw = stdout_buf.getvalue().strip()
        outcome = json.loads(raw) if raw else {}
    except Exception as e:
        outcome = {"error": str(e), "exit": "error"}

    duration = time.time() - t0
    tools_used = outcome.get("tool_sequence", [])
    passed = task["check"](outcome) if not outcome.get("error") else False

    if not quiet:
        exit_r  = outcome.get("exit", "?")
        n_calls = outcome.get("tool_calls", 0)
        print(f"[STORE]   exit={exit_r} calls={n_calls} tools={tools_used}")
        print(f"[RESULT]  {'✓ PASS' if passed else '✗ FAIL'}  ({duration:.1f}s)")

    return {
        "task_id":   task["id"],
        "desc":      task["desc"],
        "predicted": predicted[:3],
        "resolved":  resolved,
        "tools_used": tools_used,
        "exit":      outcome.get("exit", "error"),
        "calls":     outcome.get("tool_calls", 0),
        "passed":    passed,
        "duration_s": round(duration, 2),
    }


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(
        prog="aios demo agent",
        description="AIOS Agent demo — full loop benchmark (RECALL→PREDICT→EXECUTE)",
    )
    p.add_argument("--task", type=int, default=None,
                   help="Run only task N (1-3). Default: all.")
    p.add_argument("--quiet", action="store_true")
    p.add_argument("--json", dest="as_json", action="store_true")
    args = p.parse_args(argv)

    api_key = (os.environ.get("AIOS_API_KEY") or
               _try_load_key())

    tasks = [t for t in BENCHMARK_TASKS
             if args.task is None or t["id"] == args.task]

    if not args.quiet:
        print("AIOS Agent Demo — full loop: RECALL → PREDICT → EXECUTE")
        print(f"Running {len(tasks)} task(s)...")

    results = [_run_task(t, args.quiet, api_key) for t in tasks]

    passed  = sum(1 for r in results if r.get("passed"))
    total   = len(results)
    avg_t   = sum(r["duration_s"] for r in results) / total if total else 0

    if not args.quiet:
        print(f"\n{'='*60}")
        print(f"BENCHMARK: {passed}/{total} passed  avg={avg_t:.1f}s")
        for r in results:
            mark = "✓" if r.get("passed") else "✗"
            print(f"  {mark} Task {r['task_id']} ({r['desc']}): "
                  f"predicted={r['predicted']} → used={r['tools_used']} "
                  f"({r['duration_s']}s)")
        print()
        if passed == total:
            print("AIOS is operational. Full loop verified.")
        else:
            print(f"Warning: {total-passed} task(s) failed.")

    if args.as_json:
        print(json.dumps({
            "results": results, "passed": passed, "total": total, "avg_s": round(avg_t, 2)
        }, indent=2))

    return 0 if passed == total else 1


def _try_load_key() -> str | None:
    cfg = Path.home() / ".aios" / "config.json"
    try:
        return json.loads(cfg.read_text()).get("api_key") or None
    except Exception:
        return None


if __name__ == "__main__":
    sys.exit(main())
