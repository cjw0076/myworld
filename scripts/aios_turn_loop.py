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

import datetime
import json
import os
import uuid
from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable

# Append-only run log directory — written once on first use
_RUNS_DIR = Path.home() / ".aios" / "runs"

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


def _classify_run_tools(tools: list[str]) -> str:
    """Classify agent loop type from observed tool sequence (mirrors aios_agent_behavior)."""
    if not tools:
        return "empty"
    if len(tools) < 5:
        return "quick"
    total = len(tools)
    unique_ratio = len(set(tools)) / total
    bash_ratio = sum(1 for t in tools if t.startswith("Bash")) / total
    edit_ratio = sum(1 for t in tools if t.startswith("Edit")) / total
    read_ratio = sum(1 for t in tools if t.startswith("Read")) / total
    # doom-loop: any tool repeated ≥ 3× consecutively
    run = 1
    for i in range(1, len(tools)):
        run = run + 1 if tools[i] == tools[i - 1] else 1
        if run >= 3:
            return "doom_loop"
    if edit_ratio > 0.15 and bash_ratio > 0.10:
        return "react_code"
    if read_ratio > 0.30 and unique_ratio > 0.5:
        return "exploration"
    if unique_ratio < 0.25:
        return "repetitive"
    return "react_general"


def make_session_log(session_id: str | None = None) -> Path:
    """Create and return path to ~/.aios/runs/<session_id>.jsonl (append-only)."""
    _RUNS_DIR.mkdir(parents=True, exist_ok=True)
    sid = session_id or str(uuid.uuid4())[:16]
    return _RUNS_DIR / f"{sid}.jsonl"


def run_loop(goal: str, sampler: Sampler, registry: Registry, *,
             gate: Callable[[str, dict], str] = default_gate,
             max_turns: int = 12, loop_threshold: int = 3,
             record_sink: Callable[[dict], None] | None = None,
             turn_sink: Callable[[dict], None] | None = None,
             run_log: Path | None = None,
             session_id: str | None = None) -> dict:
    """Run the agent loop. Returns a structured outcome with a named exit.

    turn_sink (optional) receives per-turn `turn_context` + each `trajectory` entry as
    they happen — the append-only stream that makes a run RESUMABLE (aios_run_log).

    run_log (optional): if provided (or if session_id is given), events are written
    append-only to ~/.aios/runs/<session_id>.jsonl — the durable run record."""
    # Resolve run log path
    if run_log is None and session_id is not None:
        run_log = make_session_log(session_id)
    _log_file = open(run_log, "a", encoding="utf-8") if run_log else None  # noqa: WPS515

    history: list[dict] = [{"role": "user", "kind": "goal"}]   # names/roles only, no content
    trajectory: list[dict] = []
    last_sig, sig_count = None, 0
    all_tools: list[str] = []   # ordered tool sequence for loop-type + AkashicRecord

    def emit(rec: dict) -> None:
        if turn_sink:
            turn_sink(rec)
        if _log_file:
            _log_file.write(json.dumps(rec, ensure_ascii=False) + "\n")
            _log_file.flush()

    try:
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
                all_tools.append(call.name)
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
                elif decision == ASK:                        # escalate as typed control result, not prose
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
                    # Compact result summary — content-safe keys only (DNA #7)
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
    finally:
        if _log_file:
            _log_file.close()

    loop_type = _classify_run_tools(all_tools)
    outcome = {"schema_version": "aios.turn_loop.v1", "goal": goal[:120],
               "tool_calls": len(trajectory),
               "loop_type": loop_type,
               "tool_sequence": all_tools[:200],
               "kernel_routed": all(t.get("decision") in (ALLOW, ASK, DENY) for t in trajectory),
               **outcome}
    if record_sink:
        record_sink(outcome)
    return outcome


# ── Event log — append-only JSONL per session ────────────────────────────────

def make_event_log_sink(session_id: str | None = None, aios_home: str | None = None):
    """Factory for append-only event log sinks wired into run_loop().

    Returns (turn_sink, record_sink, session_id, path).

    Usage:
        ts, rs, sid, path = make_event_log_sink()
        outcome = run_loop(goal, sampler, registry, turn_sink=ts, record_sink=rs)
        # ~/.aios/runs/<sid>.jsonl now has per-step events + final summary
    """
    sid = session_id or uuid.uuid4().hex[:12]
    home = Path(aios_home) if aios_home else Path(os.environ.get("AIOS_HOME", Path.home() / ".aios"))
    runs_dir = home / "runs"
    runs_dir.mkdir(parents=True, exist_ok=True)
    log_path = runs_dir / f"{sid}.jsonl"
    _fh = log_path.open("a", encoding="utf-8")

    def _write(rec: dict) -> None:
        rec["ts"] = datetime.datetime.utcnow().isoformat() + "Z"
        _fh.write(json.dumps(rec, ensure_ascii=False) + "\n")
        _fh.flush()

    def turn_sink(rec: dict) -> None:
        kind = rec.get("kind")
        if kind == "turn_context":
            _write({"type": "turn_start", "turn": rec.get("turn")})
        elif kind == "trajectory":
            entry = {
                "type": "tool_call",
                "turn": rec.get("turn"),
                "tool": rec.get("tool"),
                "call_id": rec.get("call_id", ""),
                "decision": rec.get("decision"),
                "status": rec.get("status"),
            }
            _fh.write(json.dumps(entry, ensure_ascii=False) + "\n")
            _fh.flush()

    def record_sink(outcome: dict) -> None:
        exit_reason = outcome.get("exit", "unknown")
        if exit_reason == "loop_detected":
            _write({
                "type": "doom_loop_detected",
                "repeated_tool": outcome.get("repeated"),
                "step": outcome.get("turns"),
            })
        _write({
            "type": "session_end",
            "exit": exit_reason,
            "turns": outcome.get("turns"),
            "tool_calls": outcome.get("tool_calls"),
            "session_id": sid,
        })
        _fh.close()

    return turn_sink, record_sink, sid, log_path


if __name__ == "__main__":
    # demo: a scripted sampler — call a read tool, then finish
    reg = Registry()
    reg.register("aios_read", lambda a: "ok")
    steps = [{"tool_calls": [ToolCall("aios_read", {"path": "x"}, call_id="c1")]},
             {"tool_calls": []}]
    it = iter(steps)
    print(json.dumps(run_loop("inspect x", lambda h: next(it), reg), ensure_ascii=False, indent=2))
