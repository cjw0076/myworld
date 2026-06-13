#!/usr/bin/env python3
"""AIOS Tools — register existing organs as turn-loop tools (blueprint step 2).

The teardown's verdict: AIOS is a pile because 132 organs are standalone scripts that
BYPASS the kernel. This is the fix — a name→handler registry (aios_turn_loop.Registry)
that exposes the organs AS TOOLS the loop dispatches, each behind an authority-backed
per-call gate. No new capability: the organs already exist; this routes them THROUGH
the kernel instead of around it.

Tool classes drive the gate:
  read / advisory : allowed for any authorized agent (recall, route, critique, audit)
  write           : gated by aios_authority.verify_authority on the tool's domain
                    action — an unauthorized agent escalates (ASK), never silently writes.

In-process organs (self_audit, trace_interior, stakes) run here; sibling-backed ones
(memory.retrieve, capability.route, genesis.challenge) shell out and DEGRADE honestly
to a status the loop can react to — they never fabricate a result.

Schema: aios.tools.v1
"""
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import aios_authority as authority
import aios_self_audit as audit
import aios_stakes as stakes
import aios_trace_interior as interior
import aios_turn_loop as loop

ROOT = Path(__file__).resolve().parents[1]

# tool → (class, authority action, one-line description for sampler prompts)
TOOL_SPEC: dict[str, tuple[str, str, str]] = {
    "memory.retrieve":   ("advisory", "", "Recall past knowledge or context relevant to the goal"),
    "capability.route":  ("advisory", "", "Recommend the best provider/tool for a given sub-task"),
    "genesis.challenge": ("advisory", "", "Stress-test a plan or assumption; find weak points"),
    "self.audit":        ("read", "",    "Check agent state, health, or recent decisions"),
    "interior.read":     ("read", "",    "Read internal reasoning trace or agent reflection"),
    "fs.read":           ("read", "",    "Read a file from the local filesystem"),
    "stakes.record":     ("write", "propose_contract", "Record a formal proposal or contract draft"),
    "fs.write":          ("write", "commit_to_child_repo", "Write or update a file (requires authority)"),
}


def _sibling(cmd: list[str], cwd: Path) -> dict:
    """Shell to a sibling OS CLI; degrade honestly (never fabricate)."""
    try:
        p = subprocess.run(cmd, cwd=cwd, capture_output=True, text=True, timeout=60)
    except (subprocess.TimeoutExpired, OSError) as exc:
        return {"status": "unavailable", "reason": str(exc)[:80]}
    if p.returncode != 0:
        return {"status": "unavailable", "reason": (p.stderr or "").strip()[:80]}
    try:
        return {"status": "ok", "data": json.loads(p.stdout)}
    except json.JSONDecodeError:
        return {"status": "ok", "raw_len": len(p.stdout)}


# --- handlers: each adapts an existing organ; returns names/status, not content ----

def _h_retrieve(a: dict) -> dict:
    r = _sibling([sys.executable, "-m", "memoryos", "context", "build", "--task",
                  str(a.get("task", "")), "--json"], ROOT / "memoryOS")
    if r["status"] != "ok":
        return {"status": r["status"], "hits": 0}
    data = r.get("data") or {}
    # context_items is the real count; decisions has actual content
    hits = data.get("context_items", 0) or len(data.get("selected", []))
    decisions = data.get("decisions", [])
    top_decision = decisions[0].get("content", "")[:80] if decisions else ""
    return {"status": "ok", "hits": hits, "decisions": len(decisions),
            **({"top": top_decision} if top_decision else {})}


def _h_route(a: dict) -> dict:
    r = _sibling([sys.executable, "-m", "capabilityos.cli", "recommend", "--task",
                  str(a.get("task", "")), "--json"], ROOT / "CapabilityOS")
    if r["status"] != "ok":
        return {"status": r["status"]}
    recs = (r.get("data") or {}).get("recommendations", [])
    top = recs[0] if recs else {}
    return {"status": "ok", "top_id": top.get("id", ""), "top_desc": top.get("description", "")[:80],
            "count": len(recs)}


def _h_challenge(a: dict) -> dict:
    import tempfile
    with tempfile.NamedTemporaryFile("w", suffix=".txt", delete=False) as fh:
        fh.write(str(a.get("text", "")))
        tmp = fh.name
    r = _sibling([sys.executable, "-m", "genesisos.cli", "critic", "--text", tmp, "--json"],
                 ROOT / "GenesisOS")
    Path(tmp).unlink(missing_ok=True)
    if r["status"] != "ok":
        return {"status": r["status"]}
    data = r.get("data") or {}
    vectors = data.get("escape_vectors", [])
    return {"status": "ok", "confidence": data.get("confidence"),
            "top_vector": vectors[0] if vectors else None, "vector_count": len(vectors)}


def _h_self_audit(a: dict) -> dict:
    claims = [audit.Claim(c["text"], audit.file_exists(c["path"]) if c.get("path") else audit.uncheckable())
              for c in a.get("claims", [])]
    r = audit.audit(claims)
    return {"status": "ok", "backed_rate": r["backed_rate"], "trustworthy": r["trustworthy"]}


def _h_interior(a: dict) -> dict:
    r = interior.report(a.get("traces", []))
    return {"status": "ok", "itch": (r.get("the_itch") or {}).get("dimension"),
            "ambiguities": len(r.get("ambiguities", []))}


def _h_stakes(a: dict) -> dict:
    pid = stakes.record(str(a.get("claim", "")), float(a.get("confidence", 0.5)))
    return {"status": "ok", "prediction_id": pid}


def _h_fs_read(a: dict) -> dict:
    p = (ROOT / str(a.get("path", ""))).resolve()
    if ROOT not in p.parents and p != ROOT:
        return {"status": "denied_scope"}            # bounded to the repo
    if not p.is_file():
        return {"status": "not_found"}
    return {"status": "ok", "bytes": p.stat().st_size}   # size only, never content


def _h_fs_write(a: dict) -> dict:
    # the gate decides IF this runs; the handler records intent (real write wiring is
    # the contract_runner's backed-up syscall — kept behind the gate here)
    return {"status": "ok", "would_write": str(a.get("path", ""))[:80]}


HANDLERS = {
    "memory.retrieve": _h_retrieve, "capability.route": _h_route,
    "genesis.challenge": _h_challenge, "self.audit": _h_self_audit,
    "interior.read": _h_interior, "stakes.record": _h_stakes,
    "fs.read": _h_fs_read, "fs.write": _h_fs_write,
}


def build_registry() -> loop.Registry:
    reg = loop.Registry()
    for name, handler in HANDLERS.items():
        reg.register(name, handler)
    return reg


def gate_for(agent_id: str):
    """An authority-backed per-call gate: read/advisory tools allow; write tools are
    gated by verify_authority on the tool's domain action — unauthorized → ASK."""
    def gate(name: str, arguments: dict) -> str:
        spec = TOOL_SPEC.get(name)
        if spec is None:
            return loop.DENY                          # unknown tool, fail-closed
        cls, action, _desc = spec
        if cls in ("read", "advisory"):
            return loop.ALLOW
        res = authority.verify_authority(agent_id, action)
        return loop.ALLOW if res.allowed else loop.ASK
    return gate


def list_tools() -> list[dict]:
    """Discovery surface (teardown §comms: list_tools)."""
    return [{"name": n, "class": c, "domain_action": a or None, "description": d}
            for n, (c, a, d) in TOOL_SPEC.items()]


if __name__ == "__main__":
    print(json.dumps({"tools": list_tools()}, ensure_ascii=False, indent=2))
