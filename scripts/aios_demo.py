#!/usr/bin/env python3
"""`aios demo` — the 30-second, zero-setup showcase of what makes AIOS different.

No API key. No GPU. No network. No model download. Runs anywhere Python runs, in
under a second. It exists so a stranger who just ran the installer can SEE the one
idea AIOS is built around, instead of reading docs about it.

The idea, in plain language:

  Most AI agents hand you an answer and hope it's right. AIOS makes the AI only
  *propose* — then a separate piece of ordinary, deterministic code checks the
  part that has to be exact. If the check fails, the answer is rejected, not
  shipped.

This demo shows that on a tiny, relatable task — turning class deadlines into a
study plan. We run the SAME deterministic checker on two plans:

  1. a good plan   → the checker passes it.
  2. a plan with a realistic AI slip (a study session scheduled AFTER its
     deadline) → the checker CATCHES it and says exactly what's wrong.

The AI is not in the loop here on purpose: the trustworthy part of AIOS is the
check, and the check is just code — so you can audit it, and it runs offline.
Every run also drops a small provenance file on disk so the result is auditable
later. That's the whole pitch: verifiable output, with a paper trail.

Schema: aios.demo.v1
Usage: python scripts/aios_demo.py [--json]
"""
from __future__ import annotations

import argparse
import importlib.util
import json
import os
import sys
import tempfile
import time
from pathlib import Path

import aios_capability_base as base
from aios_deadline_copilot import verify_schedule

SCHEMA_VERSION = "aios.demo.v1"

_SCRIPTS_DIR = Path(__file__).resolve().parent
_REPO_ROOT = _SCRIPTS_DIR.parent

# Example goal for --chat mode: exercises memory recall + synthesis, no network needed.
CHAT_GOAL = "What is AIOS and how does the organic pipeline work?"


def _import_head():
    """Lazy-load aios_head to avoid circular imports at module level."""
    if str(_SCRIPTS_DIR) not in sys.path:
        sys.path.insert(0, str(_SCRIPTS_DIR))
    spec = importlib.util.spec_from_file_location("aios_head", _SCRIPTS_DIR / "aios_head.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def run_chat(goal: str = CHAT_GOAL, max_turns: int = 4) -> dict:
    """Run one goal through the full organic pipeline (preamble → loop → synthesis).

    Provider priority: Ollama (local) → Gemini REST (free tier) → Anthropic REST.
    Returns a dict with keys: ok, provider_used, final_answer, memory_hits, turns, exit.
    """
    head = _import_head()
    adapters_mod = head._load("aios_adapters")

    if adapters_mod._ollama_rest_available():
        provider_label = "ollama_rest (local Ollama — no cost)"
    elif adapters_mod._gemini_rest_available():
        provider_label = "gemini_rest (Gemini free tier)"
    elif adapters_mod._anthropic_rest_available():
        provider_label = "anthropic_rest (Anthropic Claude)"
    else:
        return {
            "ok": False,
            "error": (
                "No provider available. Choose one:\n"
                "  GEMINI_API_KEY    — free tier, 1500 req/day\n"
                "  ANTHROPIC_API_KEY — paid\n"
                "  or: aios setup apply  (install local Ollama models)"
            ),
            "exit_code": 1,
        }

    adapters = head._default_adapters("auto")
    sampler = head.make_provider_sampler("auto", adapters, goal=goal)
    result = head.run_organic_goal(goal, sampler=sampler, max_turns=max_turns, root=_REPO_ROOT)

    preamble = result.get("organic_pipeline", {}).get("preamble", {})
    # run_organic_goal does preamble+loop+postamble but NOT synthesis — call separately
    final_answer = head._organ_synthesis(goal, result, preamble=preamble, root=_REPO_ROOT)

    return {
        "ok": True,
        "provider_used": provider_label,
        "goal": goal,
        "final_answer": final_answer,
        "memory_hits": preamble.get("memory_hits", 0),
        "memory_status": preamble.get("memory_status", "unknown"),
        "turns": result.get("turns", 0),
        "exit": result.get("exit", "unknown"),
    }


def narrate_chat(chat: dict) -> str:
    if not chat.get("ok"):
        return f"\n  [aios demo --chat] ERROR: {chat['error']}\n"
    lines = [
        "",
        "  ┌─────────────────────────────────────────────────────────────┐",
        "  │  AIOS demo --chat  — live organic pipeline run               │",
        "  └─────────────────────────────────────────────────────────────┘",
        "",
        f"  Goal:     {chat['goal']}",
        f"  Provider: {chat['provider_used']}",
        f"  Memory:   {chat['memory_hits']} hit(s) recalled from memoryOS",
        f"  Turns:    {chat['turns']}   exit={chat['exit']}",
        "",
        "  Answer:",
        "",
    ]
    for ln in (chat.get("final_answer") or "(no answer generated)").splitlines():
        lines.append(f"    {ln}")
    lines += [
        "",
        "  Provenance: organic pipeline (preamble → loop → synthesis), no hardcoded output.",
        "  Next: `aios serve` → http://localhost:8741/ for the full interactive UI.",
        "",
    ]
    return "\n".join(lines)

# ── MEMORY ACT — the headline: an agent that learns from every run ───────────
# The one idea AIOS is built around: the ledger LEARNS. Run the same task twice —
# once with an empty ledger (starts from zero), once after the first run is
# recorded (carries forward what worked). No GPU, no key, no network: the whole
# act runs against an isolated temp ledger via the real behavioral-memory engine,
# pinned to its offline keyword/frequency fallback so it's identical everywhere.

MEMORY_SCHEMA_VERSION = "aios.demo.memory.v1"
MEMORY_TASK = "fix the failing test in the auth module"
MEMORY_CANDIDATES = ["Read", "Edit", "Bash", "Grep", "Write"]

# A tiny, fixed, synthetic "successful fix-the-test" agent run, in the same
# privacy-safe Claude-session shape (assistant tool_use events, tool NAMES only)
# that `aios behavior ingest` reads from real CLI logs: read the code, grep the
# symbol, edit the fix, run pytest — the loop that resolved the failure.
_SYNTHETIC_RUN_TOOLS = ["Read", "Grep", "Read", "Edit", "Bash", "Edit", "Bash"]


def _load_behavior(home: Path):
    """Load a FRESH aios_agent_behavior bound to an ISOLATED AIOS_HOME.

    The engine reads AIOS_HOME at import time into its module-level store paths, so
    we set the env var and import a fresh instance — the stranger's real ~/.aios is
    never touched, and the demo is reproducible. We then pin the module to the
    OFFLINE first-run reality of a fresh install:
      • no embeddings  — ollama absent → the real keyword/frequency fallback
      • no DescentNet  — a private research repo, not part of the OSS core
    This is faithful to a real external install (NOT a fake): the code that runs
    below is the real machinery, just held to the no-GPU/no-network path so the
    result is deterministic and identical on every machine.
    """
    if str(_SCRIPTS_DIR) not in sys.path:
        sys.path.insert(0, str(_SCRIPTS_DIR))
    os.environ["AIOS_HOME"] = str(home)
    spec = importlib.util.spec_from_file_location(
        f"aios_agent_behavior_demo_{abs(hash(str(home)))}",
        _SCRIPTS_DIR / "aios_agent_behavior.py",
    )
    beh = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(beh)
    beh._embed_batch = lambda texts: None  # ollama unavailable → offline fallback
    beh.DESCENTNET = None                  # no torch/GPU scorer on a fresh install
    return beh


def _record_run(beh, home: Path) -> tuple[list[dict], int]:
    """Record one agent run into the ledger via the REAL ingest → write path.

    Writes a synthetic Claude-session JSONL, points the engine's session scan at
    it, and runs the actual ingest_sessions() + write_to_akashic() pipeline — so
    parse → classify → loop-typing → AkashicRecord append all really execute, not a
    shortcut that hand-crafts the stored object.
    """
    sessions_dir = home / "synthetic_sessions"
    sessions_dir.mkdir(parents=True, exist_ok=True)
    events = [
        {"type": "assistant", "message": {"content": [{"type": "tool_use", "name": t}]}}
        for t in _SYNTHETIC_RUN_TOOLS
    ]
    (sessions_dir / "fix-failing-test.jsonl").write_text(
        "\n".join(json.dumps(e) for e in events), encoding="utf-8"
    )
    beh.SESSION_PATHS = {"claude": [sessions_dir]}
    mems = beh.ingest_sessions("claude", frozenset({"code"}))
    written = beh.write_to_akashic(mems)
    return mems, written


def run_memory_act(home: Path | None = None) -> dict:
    """Run the SAME task twice against an isolated ledger: empty first, learned second.

    Returns a structured result. `memory_ok` is the honesty gate: True only when
    run 1 is genuinely empty (no prior data) AND run 2 is genuinely grounded in the
    run recorded between them (a real frequency signal contributed).
    """
    home = home or Path(tempfile.mkdtemp(prefix="aios-demo-mem-"))
    prev_home = os.environ.get("AIOS_HOME")
    try:
        beh = _load_behavior(home)

        # ── Run 1 — brand-new agent, empty ledger ──
        run1 = beh.predict_behavior(MEMORY_TASK, MEMORY_CANDIDATES, use_global=False)

        # ── Record the run (real ingest → AkashicRecord append) ──
        t_rec = time.time()
        mems, written = _record_run(beh, home)

        # ── Run 2 — same task, same question, now with memory ──
        run2 = beh.predict_behavior(MEMORY_TASK, MEMORY_CANDIDATES, use_global=False)
        age_s = time.time() - t_rec

        recorded = mems[0] if mems else {}
        run1_empty = run1.get("method") == "no_data" and run1.get("memories_used", 0) == 0
        run2_grounded = (
            written >= 1
            and run2.get("memories_used", 0) >= 1
            and bool(run2.get("ranked"))
            and any(r.get("freq_score", 0) > 0 for r in run2.get("ranked", []))
        )
        return {
            "schema_version": MEMORY_SCHEMA_VERSION,
            "task": MEMORY_TASK,
            "candidates": MEMORY_CANDIDATES,
            "aios_home": str(home),
            "run1": {
                "method": run1.get("method"),
                "memories_used": run1.get("memories_used", 0),
                "top": run1["ranked"][0]["action"] if run1.get("ranked") else None,
                "ranked": run1.get("ranked", []),
            },
            "recorded": {
                "written": written,
                "id": recorded.get("id"),
                "content": recorded.get("content"),
                "top_tools": recorded.get("top_tools", []),
                "evidence_refs": recorded.get("evidence_refs", []),
                "age_s": round(age_s, 1),
            },
            "run2": {
                "method": run2.get("method"),
                "memories_used": run2.get("memories_used", 0),
                "top": run2["ranked"][0]["action"] if run2.get("ranked") else None,
                "ranked": run2.get("ranked", []),
            },
            "memory_ok": bool(run1_empty and run2_grounded),
        }
    finally:
        # Restore the process env; the fresh module already bound its store to `home`.
        if prev_home is None:
            os.environ.pop("AIOS_HOME", None)
        else:
            os.environ["AIOS_HOME"] = prev_home


def narrate_memory(mem: dict) -> str:
    r1, rec, r2 = mem["run1"], mem["recorded"], mem["run2"]
    lines = [
        "",
        "  ┌─────────────────────────────────────────────────────────────┐",
        "  │  AIOS — a memory layer for AI agents  (no GPU, no key)       │",
        "  └─────────────────────────────────────────────────────────────┘",
        "",
        "  The idea: an AIOS agent learns from every run, so the next run",
        "  carries forward what worked instead of starting from zero.",
        "",
        f"  Task:      {mem['task']}",
        "  Question:  which tool should the agent reach for next?",
        f"  (isolated demo ledger: {mem['aios_home']})",
        "",
        "  ── Run 1 — a brand-new agent, empty memory ───────────────────",
        f"    predictor: {r1['method']}  ({r1['memories_used']} prior runs)",
        "    → no prior runs — starting from zero (nothing to ground a suggestion on).",
        "",
        "  ── AIOS records what the agent just did ──────────────────────",
        f"    ingested 1 run → ledger   (id {rec['id']}, {rec['written']} written)",
        f"    what worked:  {', '.join(rec['top_tools'])}",
        f"    provenance:   {', '.join(rec['evidence_refs'])}",
        "",
        "  ── Run 2 — same task, same question, now WITH memory ─────────",
        f"    predictor: {r2['method']}  "
        f"({r2['memories_used']} prior run recalled, recorded {rec['age_s']}s ago)",
        f"    → top suggestion: {r2['top']}",
    ]
    for r in r2["ranked"][:3]:
        lines.append(f"        {r['action']:<8} score={r['score']:.3f}   {r['explanation'][:52]}")
    lines += [
        "",
        "    Run 1 started from zero; Run 2 carried forward what worked —",
        "    grounded in the run recorded moments ago, no model call needed.",
        "",
    ]
    return "\n".join(lines)


# A fixed, deterministic scenario so the demo shows the same thing for everyone,
# every time, with no clock or randomness involved.
TODAY = "2026-06-08"
ASSIGNMENTS = [
    {"course": "Database Systems", "due": "2026-06-15"},
    {"course": "Linear Algebra", "due": "2026-06-12"},
    {"course": "Operating Systems", "due": "2026-06-20"},
]

# Plan A — every study session lands on or before its deadline (and not in the past).
GOOD_PLAN = [
    {"course": "Linear Algebra", "date": "2026-06-09"},
    {"course": "Database Systems", "date": "2026-06-10"},
    {"course": "Linear Algebra", "date": "2026-06-11"},
    {"course": "Database Systems", "date": "2026-06-13"},
    {"course": "Operating Systems", "date": "2026-06-14"},
    {"course": "Operating Systems", "date": "2026-06-18"},
]

# Plan B — a realistic model slip: the second Database session is scheduled on
# 06-17, which is AFTER that assignment is due on 06-15. Everything else is fine,
# so the mistake is the kind a fluent-but-wrong answer hides.
SLIPPED_PLAN = [
    {"course": "Linear Algebra", "date": "2026-06-09"},
    {"course": "Database Systems", "date": "2026-06-10"},
    {"course": "Linear Algebra", "date": "2026-06-11"},
    {"course": "Database Systems", "date": "2026-06-17"},  # <-- after the 06-15 due date
    {"course": "Operating Systems", "date": "2026-06-14"},
    {"course": "Operating Systems", "date": "2026-06-18"},
]


def run_demo() -> dict:
    """Run the deterministic checker on both plans and return a structured result."""
    good = verify_schedule(GOOD_PLAN, ASSIGNMENTS, TODAY)
    slipped = verify_schedule(SLIPPED_PLAN, ASSIGNMENTS, TODAY)
    return {
        "schema_version": SCHEMA_VERSION,
        "generated_at": TODAY,
        "claim": "AIOS output is checked by deterministic code, not trusted on faith.",
        "today": TODAY,
        "assignments": ASSIGNMENTS,
        "checks": [
            {"plan": "good", "schedule": GOOD_PLAN, "verification": good},
            {"plan": "slipped", "schedule": SLIPPED_PLAN, "verification": slipped},
        ],
        # the demo is only honest if the checker actually behaves as advertised
        "demo_ok": bool(good.get("ok")) and not slipped.get("ok"),
        "provenance": "deterministic date-verify only; no model, no network, no GPU",
    }


def _fmt_plan(schedule: list[dict]) -> str:
    by_course: dict[str, list[str]] = {}
    for e in schedule:
        by_course.setdefault(str(e["course"]), []).append(str(e["date"]))
    return "\n".join(f"      {c}: {', '.join(sorted(ds))}" for c, ds in by_course.items())


def narrate(result: dict, receipt_path: Path | None) -> str:
    good = next(c for c in result["checks"] if c["plan"] == "good")["verification"]
    slipped = next(c for c in result["checks"] if c["plan"] == "slipped")["verification"]
    due = ", ".join(f"{a['course']} (due {a['due']})" for a in result["assignments"])
    lines = [
        "",
        "  ┌─────────────────────────────────────────────────────────────┐",
        "  │  AIOS — verifiable AI output, in 30 seconds                  │",
        "  └─────────────────────────────────────────────────────────────┘",
        "",
        "  Most AI agents hand you an answer and hope it's right.",
        "  AIOS lets the AI propose, then checks the exact part with plain",
        "  code — and rejects the answer if the check fails.",
        "",
        f"  The task: turn class deadlines into a study plan (today is {result['today']}).",
        f"  Deadlines: {due}",
        "",
        "  ── Plan A — a good plan ──────────────────────────────────────",
        _fmt_plan(next(c for c in result["checks"] if c["plan"] == "good")["schedule"]),
        "",
        f"  Checker says: {'PASS ✓' if good['ok'] else 'FAIL'} "
        f"({good['courses_scheduled']} courses scheduled, no deadline violated)",
        "",
        "  ── Plan B — the same task, with a realistic AI slip ──────────",
        _fmt_plan(next(c for c in result["checks"] if c["plan"] == "slipped")["schedule"]),
        "",
        f"  Checker says: {'PASS' if slipped['ok'] else 'CAUGHT ✗'} — the AI scheduled work",
        "  past a deadline, and the code refused to ship it:",
    ]
    for v in slipped["violations"]:
        lines.append(f"      • {v['course']}: {v['issue']}")
    lines += [
        "",
        "  The AI never touched this demo — the trustworthy part is the check,",
        "  and the check is just code: auditable, and it runs fully offline.",
    ]
    if receipt_path is not None:
        lines += [
            "",
            f"  A provenance record was written to:  {receipt_path}",
            "  (every AIOS result leaves an auditable paper trail.)",
        ]
    lines += [
        "",
        "  This is one of four working copilots (deadlines, grades, exams,",
        "  tuition), each with its own deterministic verifier. Next:",
        "      aios onboard           # guided setup: wire AIOS into your agent CLI",
        "      aios behavior status   # your local behavioral-memory ledger",
        "      docs/AIOS_NORTHSTAR.md # where this is going",
        "",
    ]
    return "\n".join(lines)


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(description="AIOS 30-second verifiable-output demo")
    p.add_argument("--json", action="store_true", help="emit the structured result, no narration")
    p.add_argument("--no-receipt", action="store_true", help="skip writing the provenance file")
    p.add_argument(
        "--chat",
        action="store_true",
        help="run one goal through the full organic pipeline (preamble → loop → synthesis)",
    )
    p.add_argument(
        "--goal",
        default=CHAT_GOAL,
        help="goal for --chat mode (default: CHAT_GOAL constant)",
    )
    return p


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)

    if args.chat:
        chat = run_chat(goal=args.goal)
        if args.json:
            print(json.dumps(chat, ensure_ascii=False, indent=2))
        else:
            print(narrate_chat(chat))
        return 0 if chat.get("ok") else 1

    # Act 1+2 — the headline: memory that learns (isolated temp ledger, offline).
    memory = run_memory_act()

    # Act 3 (closing) — the verify-first copilot demo: AI proposes, code verifies.
    result = run_demo()
    receipt_path: Path | None = None
    if not args.no_receipt:
        out_dir, stamp = base.write_receipt("demo", result)
        receipt_path = out_dir / f"receipt-{stamp}.json"
    if args.json:
        print(json.dumps(
            {"memory": memory, **result,
             "receipt": receipt_path.as_posix() if receipt_path else None},
            ensure_ascii=False, indent=2))
    else:
        print(narrate_memory(memory))
        print("  ── Closing act — AI proposes, code verifies ─────────────────")
        print(narrate(result, receipt_path))
    return 0 if (memory["memory_ok"] and result["demo_ok"]) else 1


if __name__ == "__main__":
    raise SystemExit(main())
