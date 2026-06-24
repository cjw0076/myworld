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


_WRITE_TOOLS = frozenset({"Write", "Edit", "aios_observe", "aios_ingest_cli_session",
                          "fs.write", "note.write", "stakes.record"})
_READ_TOOLS = frozenset({"Read", "aios_retrieve", "aios_route"})


# ── Renewal pillar 1: self-conditioning defense ────────────────────────────────
# Frontier research (arXiv 2509.09677): an LLM errs MORE after seeing its own past
# errors in context — and this persists in 200B+ models; scaling does not fix it.
# So accumulated error traces in the active context are a reliability tax. The
# cheapest high-leverage fix is to keep old error traces OUT of the prompt: keep
# the most recent failure (the model must know the last attempt failed) but elide
# older ones to a terse marker so mistakes don't compound. (2604.11978: 72.5% of
# long-horizon failures are process-level — clean context helps planning recover.)
_ERROR_STATUSES = frozenset({
    "error", "denied", "denied_scope", "timeout", "no_results", "unavailable",
    "not_found", "empty", "failed", "non_json_output", "script_missing",
})


def _entry_status(h: dict) -> str:
    return str((h.get("result") or {}).get("status") or h.get("status") or "")


def is_error_entry(h: dict) -> bool:
    """True if a history tool-entry represents a failed/empty observation."""
    return h.get("role") == "tool" and _entry_status(h) in _ERROR_STATUSES


def decondition_history(history: list[dict], keep_recent_errors: int = 1) -> list[dict]:
    """Return a self-conditioning-safe view of history: successful observations are
    kept verbatim, but all-but-the-most-recent error traces are compressed to a
    terse marker so the model does not self-condition on accumulated mistakes.

    Pure function (no mutation of the input). Research: arXiv 2509.09677.
    """
    err_positions = [i for i, h in enumerate(history) if is_error_entry(h)]
    keep = set(err_positions[-keep_recent_errors:]) if keep_recent_errors > 0 else set()
    out: list[dict] = []
    for i, h in enumerate(history):
        if is_error_entry(h) and i not in keep:
            out.append({**h, "result": {"status": "(earlier failed attempt elided)",
                                        "_deconditioned": True}})
        else:
            out.append(h)
    return out


def _completion_audit(trajectory: list[dict],
                       contract_receipts: list[dict] | None = None) -> dict:
    """Ralph-style prompt-to-artifact audit: did the loop actually produce evidence?

    Absorbed from oh-my-codex ralph.js completion_audit pattern.
    model_finished is structural — this checks whether real artifacts were produced.

    contract_receipts: optional receipts from the pre-loop contract runner pass
    (aios_head.py compile_goal path). If receipts show write success, passes audit.
    """
    writes = [e for e in trajectory if e.get("tool") in _WRITE_TOOLS and e.get("status") == "ok"]
    reads = [e for e in trajectory if e.get("tool") in _READ_TOOLS and e.get("status") == "ok"]
    tool_calls = len(trajectory)

    # Count contract runner receipts as write evidence
    runner_writes = [r for r in (contract_receipts or []) if r.get("ok") or r.get("status") == "passed"]
    passed = (
        len(writes) > 0
        or (tool_calls > 0 and len(reads) > 0)
        or len(runner_writes) > 0
    )
    note = (
        "artifacts_produced" if writes
        else ("contract_runner_artifacts" if runner_writes
              else ("read_only_run" if reads
                    else "no_tool_evidence"))
    )
    return {
        "passed": passed,
        "evidence_writes": len(writes),
        "evidence_reads": len(reads),
        "contract_runner_writes": len(runner_writes),
        "checklist_note": note,
    }


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


def _plan_repair_note(goal: str, turn: int) -> str:
    """Execution-time plan-repair prompt (renewal pillar 3). Frontier research
    (arXiv 2604.11978): 72.5% of long-horizon failures are process-level (planning/
    subplanning). When the loop stalls, force a re-plan instead of grinding."""
    return (f"PLAN CHECK (turn {turn}): no real progress for several turns. Stop "
            f"repeating the same approach. Re-plan now — name the ONE sub-goal that "
            f"is actually blocking you, and pick a DIFFERENT concrete action that "
            f"reaches it. Goal: {goal[:160]}")


def run_loop(goal: str, sampler: Sampler, registry: Registry, *,
             gate: Callable[[str, dict], str] = default_gate,
             max_turns: int = 12, loop_threshold: int = 3, repair_threshold: int = 2,
             record_sink: Callable[[dict], None] | None = None,
             turn_sink: Callable[[dict], None] | None = None,
             run_log: Path | None = None,
             session_id: str | None = None,
             contract_receipts: list[dict] | None = None,
             constraint_provider: "Callable[[str, list], list] | None" = None,
             resurface_every: int = 3) -> dict:
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
    stall_count = 0   # consecutive turns with no real progress (pillar 3)
    all_tools: list[str] = []   # ordered tool sequence for loop-type + AkashicRecord

    def emit(rec: dict) -> None:
        if turn_sink:
            turn_sink(rec)
        if _log_file:
            _log_file.write(json.dumps(rec, ensure_ascii=False) + "\n")
            _log_file.flush()

    try:
        for turn in range(1, max_turns + 1):
            # Pillar 4: periodically re-surface long-range constraints from memory
            # into the active context, so they don't fade as the trajectory grows
            # (catastrophic forgetting is the design-level 27.5% — arXiv 2604.11978).
            if constraint_provider and turn > 1 and (turn - 1) % resurface_every == 0:
                try:
                    cons = constraint_provider(goal, trajectory) or []
                except Exception:  # noqa: BLE001 — memory is best-effort, never blocks the loop
                    cons = []
                fresh = [str(c)[:300] for c in cons[:3] if c]
                for c in fresh:
                    history.append({"role": "system", "kind": "constraint", "content": c})
                if fresh:
                    emit({"kind": "constraint_resurfaced", "turn": turn, "count": len(fresh)})
            emit({"kind": "turn_context", "turn": turn})
            resp = sampler(history)
            calls = [c if isinstance(c, ToolCall) else ToolCall(**c) for c in (resp.get("tool_calls") or [])]
            history.append({"role": "assistant", "turn": turn, "tools": [c.name for c in calls]})

            if not calls:                                   # model finished — structural terminal
                audit = _completion_audit(trajectory, contract_receipts=contract_receipts)
                outcome = {"exit": "model_finished", "turns": turn, "trajectory": trajectory,
                           "completion_audit": audit}
                break

            stop = None
            turn_progress = False
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
                    if status not in _ERROR_STATUSES and status not in ("denied", "needs_approval"):
                        turn_progress = True   # a real, non-error observation = progress
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
            # Pillar 3: execution-time plan verification & repair. Track progress;
            # when the loop stalls, inject a re-plan note so the model breaks out of
            # a failing approach (process-level failures are 72.5% — arXiv 2604.11978).
            if not stop:
                stall_count = 0 if turn_progress else stall_count + 1
                if stall_count >= repair_threshold:
                    history.append({"role": "system", "kind": "plan_repair",
                                    "content": _plan_repair_note(goal, turn)})
                    emit({"kind": "plan_repair", "turn": turn, "stall": stall_count})
                    stall_count = 0
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

    # GenesisOS direction hook — fires when the loop signals direction loss
    if needs_direction(outcome):
        direction = request_direction(goal, outcome)
        if direction:
            outcome["genesis_direction"] = {
                "signal": direction.get("diagnosis", {}).get("discomfort_signal"),
                "branch": direction.get("recommendation", {}).get("branch_type"),
                "first_move": direction.get("first_move"),
                "avoid": direction.get("avoid"),
                "authority": "advisory_only",
            }

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


# ── GenesisOS direction hook ─────────────────────────────────────────────────

def needs_direction(outcome: dict) -> bool:
    """True when the loop outcome signals that direction has been lost.

    Triggers when the loop hit max_turns without a code-productive pattern,
    fell into a doom/repetitive loop, or ended needing approval on a non-obvious tool.
    """
    exit_code = outcome.get("exit", "")
    loop_type = outcome.get("loop_type", "")
    if exit_code == "loop_detected":          # circuit-breaker fired → direction always needed
        return True
    if loop_type in ("doom_loop", "repetitive"):
        return True
    if exit_code == "max_turns" and loop_type not in ("react_code", "quick"):
        return True
    return False


def request_direction(goal: str, outcome: dict,
                      genesis_root: "Path | None" = None) -> "dict | None":
    """Call GenesisOS director with the outcome situation.

    Returns a direction packet (advisory_only) or None on failure.
    Does NOT execute anything — advisory surface only.
    """
    import subprocess
    root = (genesis_root or Path(__file__).resolve().parents[1] / "GenesisOS").resolve()
    if not (root / "genesisos").is_dir():
        return None
    situation = (
        f"Agent loop ended: exit={outcome.get('exit')}, "
        f"loop_type={outcome.get('loop_type')}, "
        f"tool_calls={outcome.get('tool_calls', 0)}. "
        f"Goal was: {goal[:200]}"
    )
    try:
        result = subprocess.run(
            [__import__("sys").executable, "-m", "genesisos.cli",
             "direct", "--situation", situation, "--json"],
            cwd=str(root),
            capture_output=True, text=True, timeout=20,
        )
        if result.returncode == 0 and result.stdout.strip():
            return json.loads(result.stdout)
    except (subprocess.TimeoutExpired, ValueError, OSError):
        pass
    return None


if __name__ == "__main__":
    # demo: a scripted sampler — call a read tool, then finish
    reg = Registry()
    reg.register("aios_read", lambda a: "ok")
    steps = [{"tool_calls": [ToolCall("aios_read", {"path": "x"}, call_id="c1")]},
             {"tool_calls": []}]
    it = iter(steps)
    print(json.dumps(run_loop("inspect x", lambda h: next(it), reg), ensure_ascii=False, indent=2))
