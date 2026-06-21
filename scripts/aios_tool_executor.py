#!/usr/bin/env python3
"""AIOS Tool Executor — route → execute bridge.

Closes the gap between CapabilityOS recommendation and actual tool invocation.
Given a task description, this script:
  1. Routes via CapabilityOS recommend (cap_tool_* cards)
  2. Maps the top recommendation to a local domain tool script
  3. Executes it with synthesized arguments
  4. Returns structured output with provenance

This is the organism's "last mile" — AIOS coordinates tools without needing
to understand their internals, only route and invoke.

Usage:
  python3 scripts/aios_tool_executor.py --task "detect fraud in transactions"
  python3 scripts/aios_tool_executor.py --task "optimize inventory for 20 SKUs"
  python3 scripts/aios_tool_executor.py --task "predict network intrusion"
  python3 scripts/aios_tool_executor.py --task "forecast supply chain demand"
"""
from __future__ import annotations

import json
import subprocess
import sys
import time
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
CAPABILITYOS_ROOT = ROOT / "CapabilityOS"
SCRIPTS = ROOT / "scripts"

# Registry: cap_tool_* capability ID → (script, default_args_factory)
# Each factory receives the original task string and returns CLI args list.

def _financemind_args(task: str) -> list[str]:
    return [sys.executable, str(SCRIPTS / "financemind.py"), "--json"]

def _logisticsmind_args(task: str) -> list[str]:
    import re
    n_match = re.search(r"(\d+)\s*sku", task, re.IGNORECASE)
    n = int(n_match.group(1)) if n_match else 20
    n = max(5, min(n, 100))
    return [sys.executable, str(SCRIPTS / "logisticsmind.py"), "--json", f"--n-products={n}"]

def _cybersentinel_args(task: str) -> list[str]:
    return [sys.executable, str(SCRIPTS / "cybersentinel.py"), "--json"]

def _gridmind_args(task: str) -> list[str]:
    return [sys.executable, str(SCRIPTS / "gridmind.py"), "--json"]

def _farmmind_args(task: str) -> list[str]:
    return [sys.executable, str(SCRIPTS / "farmmind.py"), "--json"]

TOOL_REGISTRY: dict[str, Any] = {
    "cap_tool_financemind":   _financemind_args,
    "cap_tool_logisticsmind": _logisticsmind_args,
    "cap_tool_cybersentinel": _cybersentinel_args,
    "cap_tool_gridmind":      _gridmind_args,
    "cap_tool_farmmind":      _farmmind_args,
}


def route(task: str) -> list[dict]:
    """Ask CapabilityOS to recommend capabilities for a task."""
    cmd = [
        sys.executable, "-m", "capabilityos.cli",
        "recommend", "--task", task, "--json",
    ]
    try:
        proc = subprocess.run(cmd, cwd=CAPABILITYOS_ROOT, capture_output=True,
                              text=True, timeout=30)
        if proc.returncode == 0:
            data = json.loads(proc.stdout)
            return data.get("recommendations", [])
    except (subprocess.TimeoutExpired, json.JSONDecodeError, OSError):
        pass
    return []


def execute_tool(cap_id: str, task: str, dry_run: bool = False) -> dict[str, Any]:
    """Execute the domain tool mapped to cap_id."""
    factory = TOOL_REGISTRY.get(cap_id)
    if factory is None:
        return {"status": "no_executor", "cap_id": cap_id,
                "note": "No local executor registered for this capability."}

    cmd = factory(task)
    if dry_run:
        return {"status": "dry_run", "cap_id": cap_id, "would_run": cmd}

    script_path = Path(cmd[1])
    if not script_path.exists():
        return {"status": "script_missing", "cap_id": cap_id, "path": str(script_path)}

    t0 = time.monotonic()
    try:
        proc = subprocess.run(cmd, capture_output=True, text=True, timeout=120)
    except subprocess.TimeoutExpired:
        return {"status": "timeout", "cap_id": cap_id}
    elapsed = round(time.monotonic() - t0, 2)

    if proc.returncode != 0:
        return {"status": "error", "cap_id": cap_id, "stderr": proc.stderr[:500],
                "elapsed_s": elapsed}

    try:
        result = json.loads(proc.stdout)
        result["_executor"] = {"cap_id": cap_id, "elapsed_s": elapsed, "status": "ok"}
        return result
    except json.JSONDecodeError:
        return {"status": "non_json_output", "cap_id": cap_id,
                "stdout": proc.stdout[:500], "elapsed_s": elapsed}


def run(task: str, dry_run: bool = False, top_k: int = 3) -> dict[str, Any]:
    """Full pipeline: route → filter to executable → execute top match."""
    recs = route(task)

    # Filter to tool cards we can execute
    executable = [r for r in recs if r["id"] in TOOL_REGISTRY]

    if not executable:
        all_ids = [r["id"] for r in recs[:top_k]]
        return {
            "status": "no_executable_match",
            "task": task,
            "top_recommendations": all_ids,
            "note": "Task routed to non-tool capabilities. Adjust task description.",
        }

    top = executable[0]
    cap_id = top["id"]
    score  = top.get("score", 0)
    name   = top.get("name", cap_id)

    result = execute_tool(cap_id, task, dry_run=dry_run)
    return {
        "task":          task,
        "routed_to":     cap_id,
        "capability":    name,
        "route_score":   score,
        "alternatives":  [r["id"] for r in executable[1:top_k]],
        "result":        result,
    }


def main() -> None:
    import argparse
    parser = argparse.ArgumentParser(description="AIOS Tool Executor — route → execute")
    parser.add_argument("--task", required=True, help="natural-language task description")
    parser.add_argument("--dry-run", action="store_true", help="show routing without executing")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()

    if not args.json:
        print(f"[AIOS] Routing: {args.task!r}", file=sys.stderr)

    output = run(task=args.task, dry_run=args.dry_run)

    if args.json:
        print(json.dumps(output, indent=2, ensure_ascii=False))
    else:
        print(f"[AIOS] Routed to: {output['routed_to']} (score {output['route_score']})")
        if output.get("alternatives"):
            print(f"[AIOS] Alternatives: {', '.join(output['alternatives'])}")
        result = output.get("result", {})
        if result.get("status") == "dry_run":
            print(f"[AIOS] Would run: {' '.join(result['would_run'])}")
        elif result.get("_executor", {}).get("status") == "ok":
            print(f"[AIOS] Completed in {result['_executor']['elapsed_s']}s")
            summary = {k: v for k, v in result.items() if not k.startswith("_")}
            print(json.dumps(summary, indent=2))
        else:
            print(f"[AIOS] Result: {result}")


if __name__ == "__main__":
    main()
