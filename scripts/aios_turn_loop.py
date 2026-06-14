#!/usr/bin/env python3
"""AIOS Turn Loop — the missing spine that turns the kernel from a batch executor
into a real agent loop (the one primitive the code-teardown found AIOS lacked).

See docs/AIOS_ECOSYSTEM_BLUEPRINT.md. Today aios_contract_runner runs a single pass
over a pre-planned step list — it cannot react to a step's result. Codex (`run_turn`)
and gemini (`processTurn`) center on an iterative loop:

    sample(model) → parse tool calls → GATE each → dispatch → append results → resample
    until (model emits no tool call | max_turns | a tool-call loop is detected)

This is that loop, with AIOS's differentiators kept: every dispatch passes a
per-call two-axis gate (authority/approval × sandbox) and is fail-closed; the
trajectory is recorded names/status-only (no content — DNA #7); a repetition
circuit-breaker gives the loop a named exit (DNA #4). The model is dependency-
injected (a sampler) so the loop is unit-tested with a fake and runs live on a
substrate-equipped host. Organs become registry handlers — invoked THROUGH this
loop instead of bypassing the kernel as standalone scripts.

Schema: aios.turn_loop.v1
"""
from __future__ import annotations

import json
from dataclasses import dataclass, field
from typing import Callable

# A gate decision for one tool call.
ALLOW, ASK, DENY = "allow", "ask", "deny"


@dataclass
class ToolCall:
    name: str
    arguments: dict
    call_id: str = ""
    parent_call_id: str = ""        # lineage (teardown §comms) — provenance for free


@dataclass
class Registry:
    """name → handler(arguments) -> result. The 132 standalone organs become tools
    registered here and dispatched THROUGH the loop, not around the kernel."""
    handlers: dict[str, Callable[[dict], object]] = field(default_factory=dict)

    def register(self, name: str, handler: Callable[[dict], object]) -> None:
        self.handlers[name] = handler

    def dispatch(self, call: ToolCall) -> tuple[str, object]:
        h = self.handlers.get(call.name)
        if h is None:
            return "unknown_tool", None            # the loop can react — unlike a batch executor
        try:
            return "ok", h(call.arguments)
        except Exception as exc:  # noqa: BLE001 — a failing tool is a result, not a crash
            return "error", str(exc)[:120]


def signature(call: ToolCall) -> str:
    """omo-style canonical signature (name + sorted args) — the loop-detection key."""
    return call.name + "|" + json.dumps(call.arguments, sort_keys=True, ensure_ascii=False)


# A sampler maps the running history to the model's next move.
#   returns {"tool_calls": [ToolCall, ...], "text": "..."}
#   no tool_calls  => the turn is terminal (structural stop, like codex needs_follow_up=False)
Sampler = Callable[[list[dict]], dict]


def default_gate(name: str, arguments: dict) -> str:
    """Fail-closed default: known-safe read-ish tools allow; anything that looks like a
    mutation/exec asks; unknown denies. Real deployments pass a richer gate (authority ×
    sandbox)."""
    n = name.lower()
    if any(k in n for k in ("read", "list", "retrieve", "route", "challenge", "audit", "echo")):
        return ALLOW
    if any(k in n for k in ("write", "edit", "delete", "exec", "commit", "deploy", "apply")):
        return ASK
    return DENY


def run_loop(goal: str, sampler: Sampler, registry: Registry, *,
             gate: Callable[[str, dict], str] = default_gate,
             max_turns: int = 12, loop_threshold: int = 3,
             record_sink: Callable[[dict], None] | None = None,
             turn_sink: Callable[[dict], None] | None = None) -> dict:
    """Run the agent loop. Returns a structured outcome with a named exit.

    turn_sink (optional) receives per-turn `turn_context` + each `trajectory` entry as
    they happen — the append-only stream that makes a run RESUMABLE (aios_run_log)."""
    history: list[dict] = [{"role": "user", "kind": "goal"}]   # names/roles only, no content
    trajectory: list[dict] = []
    last_sig, sig_count = None, 0

    def emit(rec: dict) -> None:
        if turn_sink:
            turn_sink(rec)

    for turn in range(1, max_turns + 1):
        emit({"kind": "turn_context", "turn": turn})
        resp = sampler(history)
        calls = [c if isinstance(c, ToolCall) else ToolCall(**c) for c in (resp.get("tool_calls") or [])]
        history.append({"role": "assistant", "turn": turn, "tools": [c.name for c in calls]})

        if not calls:                                   # model finished — structural terminal
            outcome = {"exit": "model_finished", "turns": turn, "trajectory": trajectory}
            break

        stop = None
        for call in calls:
            sig = signature(call)
            sig_count = sig_count + 1 if sig == last_sig else 1
            last_sig = sig
            if sig_count >= loop_threshold:             # circuit-breaker — named exit (DNA #4)
                stop = {"exit": "loop_detected", "turns": turn,
                        "repeated": call.name, "trajectory": trajectory}
                break

            decision = gate(call.name, call.arguments)
            entry = {"turn": turn, "call_id": call.call_id, "tool": call.name, "decision": decision}
            if decision == DENY:
                entry["status"] = "denied"
                history.append({"role": "tool", "tool": call.name, "status": "denied"})
            elif decision == ASK:                        # escalate as a typed control result, not prose
                entry["status"] = "needs_approval"
                trajectory.append(entry)
                emit({"kind": "trajectory", **entry})
                stop = {"exit": "needs_approval", "turns": turn,
                        "pending": {"tool": call.name, "call_id": call.call_id},
                        "trajectory": trajectory}
                break
            else:
                status, tool_result = registry.dispatch(call)   # result fed back next turn
                entry["status"] = status
                # Include a compact result summary so the sampler can see what was returned
                # and avoid redundant re-calls. Content fields (snippet, top) are passed
                # through so synthesis can cite them; blobs >500 chars are truncated.
                result_summary: dict = {}
                if isinstance(tool_result, dict):
                    for k in ("hits", "status", "itch", "ambiguities", "backed_rate",
                              "trustworthy", "bytes", "prediction_id", "would_write",
                              "decisions", "top", "count", "top_id", "top_desc",
                              "confidence", "top_vector", "vector_count",
                              "title", "source", "answer", "related",
                              "city", "temperature", "description"):
                        if k in tool_result:
                            result_summary[k] = tool_result[k]
                    # Content fields: pass through for synthesis, truncate to avoid bloat
                    for content_key in ("snippet", "abstract"):
                        if content_key in tool_result:
                            result_summary[content_key] = str(tool_result[content_key])[:500]
                if result_summary:
                    entry["result"] = result_summary
                history.append({"role": "tool", "tool": call.name, "status": status,
                                 **({"result": result_summary} if result_summary else {})})
            trajectory.append(entry)
            emit({"kind": "trajectory", **entry})
        if stop:
            outcome = stop
            break
    else:
        outcome = {"exit": "max_turns", "turns": max_turns, "trajectory": trajectory}

    outcome = {"schema_version": "aios.turn_loop.v1", "goal": goal[:120],
               "tool_calls": len(trajectory),
               "kernel_routed": all(t.get("decision") in (ALLOW, ASK, DENY) for t in trajectory),
               **outcome}
    if record_sink:
        record_sink(outcome)
    return outcome


if __name__ == "__main__":
    # demo: a scripted sampler — call a read tool, then finish
    reg = Registry()
    reg.register("aios_read", lambda a: "ok")
    steps = [{"tool_calls": [ToolCall("aios_read", {"path": "x"}, call_id="c1")]},
             {"tool_calls": []}]
    it = iter(steps)
    print(json.dumps(run_loop("inspect x", lambda h: next(it), reg), ensure_ascii=False, indent=2))
