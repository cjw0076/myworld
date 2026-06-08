#!/usr/bin/env python3
"""AIOS Agent Invoke — summon the per-OS agent, head-on through the authority skeleton.

The registry + role docs + authority model already exist and are correctly
provisioned (codex@hivemind=child_agent→commit, codex@memoryOS=reviewer→accept_memory,
codex@GenesisOS=critic, …). What was missing is the ACTIVATION: nothing summoned
those agents. They were a skeleton the operator pair bypassed by running scripts
directly. This is the activation layer — and it does NOT bypass: every summon is
gated by aios_authority.verify_authority on the agent's domain action. An agent that
the registry does not authorize for its domain is REFUSED, not waved through.

Three ways an OS agent comes alive (founder 2026-06-09):
  - session_start : woken when a session begins (the relevant domains light up).
  - on_call       : routed a task that lands in its domain.
  - self_intervene: raises its own hand when a domain signal appears in the context
                    (GenesisOS on a converging decision, MemoryOS on an un-recalled
                    decision, Hive before execution, CapabilityOS when a route is needed).

Schema: aios.agent_invoke.v1
"""
from __future__ import annotations

import argparse
import json
import time
from dataclasses import dataclass
from pathlib import Path

import aios_authority as authority

ROOT = Path(__file__).resolve().parents[1]
ACTIVATIONS = ROOT / ".aios" / "activations"


@dataclass(frozen=True)
class OSAgent:
    os: str
    identity: str
    domain_action: str           # the authority action that defines its lane
    role: str
    triggers: tuple[str, ...]    # context signals that should wake it (self-intervene)


# the per-OS agents, each bound to the authority action that defines its domain
OS_AGENTS: dict[str, OSAgent] = {
    "hivemind": OSAgent("hivemind", "codex@hivemind", "commit_to_child_repo",
                        "execute / verify / produce receipts",
                        ("run", "execute", "build", "test", "deploy", "apply", "commit", "mutate")),
    "memoryOS": OSAgent("memoryOS", "codex@memoryOS", "accept_memory_draft",
                        "recall context / review memory drafts",
                        ("remember", "recall", "prior", "before", "context", "decided", "memory")),
    "CapabilityOS": OSAgent("CapabilityOS", "codex@CapabilityOS", "propose_contract",
                            "recommend route / capability (no binding)",
                            ("which", "route", "tool", "provider", "capability", "how should", "fallback")),
    "GenesisOS": OSAgent("GenesisOS", "codex@GenesisOS", "propose_contract",
                         "challenge reasoning / diverge (advisory)",
                         ("assume", "obvious", "should we just", "converge", "decide", "best way", "only option")),
    "myworld": OSAgent("myworld", "codex@myworld", "release_dispatch",
                       "control plane / dispatch / status",
                       ("dispatch", "release", "contract", "status", "escalate")),
}


def _receipt(activation: dict) -> Path:
    ACTIVATIONS.mkdir(parents=True, exist_ok=True)
    stamp = time.strftime("%Y%m%dT%H%M%S")
    p = ACTIVATIONS / f"activation-{activation['os']}-{stamp}.json"
    p.write_text(json.dumps(activation, ensure_ascii=False, indent=2), encoding="utf-8")
    return p


def summon(os: str, task: str, trigger: str, *, identity: str | None = None,
           write_receipt: bool = True) -> dict:
    """Wake one OS agent — HEAD-ON through authority. A summon the registry does not
    authorize for the agent's domain action is refused, not bypassed."""
    spec = OS_AGENTS.get(os)
    if spec is None:
        return {"os": os, "summoned": False, "reason": f"unknown OS: {os}"}
    who = identity or spec.identity
    auth = authority.verify_authority(who, spec.domain_action)
    activation = {
        "schema_version": "aios.agent_invoke.v1",
        "os": os, "identity": who, "trigger": trigger,
        "domain_action": spec.domain_action, "role": spec.role,
        "task": task[:160],
        "authorized": bool(auth.allowed),
        "citizenship": auth.citizenship,
        "summoned": bool(auth.allowed),
        "reason": auth.reason,
    }
    if write_receipt:
        activation["receipt"] = _receipt(activation).as_posix()
    return activation


def on_session_start(context: str = "", *, write_receipt: bool = False) -> list[dict]:
    """Which agents wake at session start: the domains the opening context touches,
    or — with no context — the standing set (memory + genesis: recall + challenge are
    always relevant at the start of work)."""
    ctx = context.lower()
    woken = [os for os, spec in OS_AGENTS.items() if any(t in ctx for t in spec.triggers)]
    if not woken:
        woken = ["memoryOS", "GenesisOS"]      # always: recall what's known, challenge the frame
    return [summon(os, context or "session start", "session_start", write_receipt=write_receipt)
            for os in woken]


def self_interventions(context: str, *, write_receipt: bool = False) -> list[dict]:
    """Agents raising their OWN hand: any OS whose domain signal appears in the
    context proposes to intervene (with the signal that triggered it)."""
    ctx = context.lower()
    out = []
    for os, spec in OS_AGENTS.items():
        hits = [t for t in spec.triggers if t in ctx]
        if hits:
            act = summon(os, context, "self_intervene", write_receipt=write_receipt)
            act["intervene_because"] = hits
            out.append(act)
    return out


def route_call(task: str, *, write_receipt: bool = False) -> dict | None:
    """On-call routing: the single best OS agent for a task, by domain-signal match."""
    ctx = task.lower()
    scored = [(os, sum(1 for t in spec.triggers if t in ctx)) for os, spec in OS_AGENTS.items()]
    best = max(scored, key=lambda kv: kv[1])
    if best[1] == 0:
        return None
    return summon(best[0], task, "on_call", write_receipt=write_receipt)


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(description="Summon per-OS agents through the authority skeleton")
    sub = p.add_subparsers(dest="cmd", required=True)
    s = sub.add_parser("summon"); s.add_argument("os"); s.add_argument("task")
    ss = sub.add_parser("session-start"); ss.add_argument("context", nargs="?", default="")
    si = sub.add_parser("intervene"); si.add_argument("context")
    rc = sub.add_parser("route"); rc.add_argument("task")
    for x in (s, ss, si, rc):
        x.add_argument("--json", action="store_true")
    return p


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    if args.cmd == "summon":
        r = summon(args.os, args.task, "on_call")
    elif args.cmd == "session-start":
        r = on_session_start(args.context)
    elif args.cmd == "intervene":
        r = self_interventions(args.context)
    else:
        r = route_call(args.task)
    if getattr(args, "json", False):
        print(json.dumps(r, ensure_ascii=False, indent=2))
    elif isinstance(r, list):
        for a in r:
            mark = "✓" if a.get("summoned") else "✗"
            extra = f" (because {a['intervene_because']})" if a.get("intervene_because") else ""
            print(f"  {mark} {a['os']:13} [{a['trigger']}] {a['role']}{extra}")
    elif r:
        print(f"{'✓' if r['summoned'] else '✗'} {r['os']} — {r['role']} (auth: {r['reason']})")
    else:
        print("(no OS agent matched)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
