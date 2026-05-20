#!/usr/bin/env python3
"""ASC-0212 — AIOS-side CapabilityOS MCP wrapper.

Exposes CapabilityOS read-only operations (recommend / audit / observe)
as MCP-shaped tools, *callable directly* (no MCP SDK required). Mirrors
memoryOS/memoryos/mcp.py TOOL_REGISTRY pattern.

This is the *2nd OS* MCP surface (memoryOS being the 1st). Write into
myworld/scripts/ rather than CapabilityOS/ to preserve child-repo
ownership boundary (CapabilityOS edits belong to codex@CapabilityOS).
When that agent is active, the in-package version will land at
CapabilityOS/capabilityos/mcp.py and this proxy can be retired.

DNA: Invariant 1 (advisory only — `recommend` returns plans, never
executes), Invariant 7 (privacy — refuses paths under
_from_desktop/dain/minyoung).
"""
from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parent.parent
CAPABILITYOS_ROOT = REPO_ROOT / "CapabilityOS"


PRIVATE_PATH_PREFIXES = (
    "_from_desktop/", "dain/", "minyoung/", ".env",
)


def _looks_private(value: str) -> bool:
    v = value.lstrip("./")
    return any(v.startswith(p) for p in PRIVATE_PATH_PREFIXES)


def _run_capability_cli(*args: str) -> dict[str, Any]:
    """Invoke `python -m capabilityos.cli ...` and return parsed JSON.

    CapabilityOS cli accepts the global `--catalog FILE` option (not --json)
    and most subcommands already emit JSON to stdout. We just forward args.
    """
    cmd = [sys.executable, "-m", "capabilityos.cli", *args]
    r = subprocess.run(
        cmd, cwd=str(CAPABILITYOS_ROOT),
        capture_output=True, text=True, check=False,
    )
    if r.returncode != 0:
        return {"ok": False, "returncode": r.returncode,
                "stderr": r.stderr.strip(),
                "stdout": r.stdout.strip()}
    try:
        return {"ok": True, "result": json.loads(r.stdout)}
    except json.JSONDecodeError:
        return {"ok": True, "raw": r.stdout.strip()}


def tool_capability_recommend(task: str, limit: int = 3) -> dict[str, Any]:
    """Return ranked capability cards for a task description."""
    if _looks_private(task):
        return {"error": "task contains private path prefix", "value": task}
    return _run_capability_cli("recommend", "--task", task, "--limit", str(limit), "--json")


def tool_capability_audit() -> dict[str, Any]:
    """Audit the capability catalog (read-only)."""
    return _run_capability_cli("audit", "--json")


def tool_capability_show(card_id: str) -> dict[str, Any]:
    """Show a capability card by id."""
    if _looks_private(card_id):
        return {"error": "card_id contains private path prefix", "value": card_id}
    return _run_capability_cli("show", card_id, "--json")


def tool_capability_list_catalog(domain: str | None = None) -> dict[str, Any]:
    """List the capability catalog, optionally filtered by domain."""
    args = ["list", "--json"]
    if domain:
        if _looks_private(domain):
            return {"error": "domain contains private path prefix", "value": domain}
        args += ["--domain", domain]
    return _run_capability_cli(*args)


TOOL_REGISTRY: dict[str, Any] = {
    "capability.recommend": tool_capability_recommend,
    "capability.audit": tool_capability_audit,
    "capability.show": tool_capability_show,
    "capability.list": tool_capability_list_catalog,
}


def list_tools() -> list[dict[str, Any]]:
    return [
        {
            "name": name,
            "doc": (fn.__doc__ or "").strip().splitlines()[0] if fn.__doc__ else "",
        }
        for name, fn in TOOL_REGISTRY.items()
    ]


def call_tool(name: str, **kwargs: Any) -> dict[str, Any]:
    fn = TOOL_REGISTRY.get(name)
    if fn is None:
        return {"error": f"unknown tool: {name}",
                "available": sorted(TOOL_REGISTRY.keys())}
    return fn(**kwargs)


def run_server() -> None:
    """Start the MCP stdio server. Requires `pip install mcp>=1.0`."""
    try:
        from mcp.server.fastmcp import FastMCP  # type: ignore[import]
    except ImportError:
        raise SystemExit("MCP SDK not installed. Run: pip install mcp>=1.0")
    server = FastMCP("aios.capability")
    for name, fn in TOOL_REGISTRY.items():
        server.add_tool(fn, name=name)
    server.run()


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description="AIOS CapabilityOS MCP wrapper")
    sub = p.add_subparsers(dest="cmd", required=True)
    sub.add_parser("list-tools", help="list available MCP tools")
    sub.add_parser("serve", help="start stdio MCP server (needs mcp SDK)")
    call_p = sub.add_parser("call", help="invoke a single tool directly")
    call_p.add_argument("tool")
    call_p.add_argument("--kwargs", default="{}",
                        help="JSON dict of kwargs")
    args = p.parse_args(argv)

    if args.cmd == "list-tools":
        print(json.dumps(list_tools(), indent=2, ensure_ascii=False))
    elif args.cmd == "serve":
        run_server()
    elif args.cmd == "call":
        kw = json.loads(args.kwargs) if args.kwargs else {}
        print(json.dumps(call_tool(args.tool, **kw), indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    sys.exit(main())
