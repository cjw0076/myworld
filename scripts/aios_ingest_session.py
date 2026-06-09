#!/usr/bin/env python3
"""AIOS Ingest Session — the FLOW that closes the loop (not a new capability).

Founder (2026-06-09): "사용자의 작업 과정과 기록을 memoryOS, GenesisOS가 먹는거지."
This is that — and it is deliberately NOT a 145th standalone organ. It adds no new
capability; it makes the existing ones FLOW through the per-OS agent skeleton:

  session logs ─▶ aios_session_miner (behavior, privacy-safe)
              ├▶ summon(memoryOS)  [authority-gated] ─▶ draft-first memory proposal
              └▶ summon(GenesisOS) [authority-gated] ─▶ trace_interior (operator's
                    grounded need/discomfort/want + divergent readings)

Every OS is reached by SUMMONING its agent through aios_authority (head-on, not
bypassed): if the registry does not authorize codex@memoryOS / codex@GenesisOS for
its domain action, that arm is skipped with the refusal reason. Memory is draft-first
(DNA #2): this writes a proposal for codex@memoryOS to review — it never accepts.

Schema: aios.ingest_session.v1
"""
from __future__ import annotations

import argparse
import json
import time
from pathlib import Path

import aios_agent_invoke as invoke
import aios_session_miner as miner
import aios_trace_interior as interior

ROOT = Path(__file__).resolve().parents[1]
PROPOSALS = ROOT / ".aios" / "memory_review_proposals"
RECEIPTS = ROOT / ".aios" / "ingest"


def _events(provider: str, limit: int) -> list[miner.Event]:
    if provider == "claude":
        files, parse = list(miner.CLAUDE_PROJECTS.rglob("*.jsonl")), miner.parse_claude_log
    else:
        files, parse = list(miner.CODEX_SESSIONS.rglob("rollout-*.jsonl")), miner.parse_codex_log
    files = sorted(files, key=lambda f: f.stat().st_mtime if f.exists() else 0)[-limit:]
    evs: list[miner.Event] = []
    for f in files:
        evs.extend(parse(f))
    return evs


def _memlang_draft(provider: str, prof: dict) -> str:
    """A draft-first memory proposal (fenced memlang in .md) — behavioral facts only,
    no content. For codex@memoryOS to review; NOT accepted here."""
    top = ", ".join(list(prof.get("tool_histogram", {}))[:5]) or "none"
    seqs = "; ".join(s["seq"] for s in prof.get("top_sequences", [])[:2]) or "none"
    cands = miner.systematization_candidates(prof)
    cand = cands[0]["pattern"] if cands else "none"
    return (
        f"# Draft memory — {provider} operator behavioral profile (session_miner)\n\n"
        "Draft-first (DNA #2): for codex@memoryOS to review, not accepted.\n\n"
        "```memlang\n"
        f"^ {provider} operator: dominant tools [{top}]; recovery_rate "
        f"{prof.get('recovery_rate')}; parallelism {prof.get('mean_parallelism')} "
        f"@aios origin=session_miner confidence=0.55\n"
        f"% recurring workflow worth systematizing: {cand} @aios origin=session_miner\n"
        f"^ frequent tool-sequences: {seqs} @aios origin=session_miner confidence=0.5\n"
        "```\n"
    )


def ingest(provider: str = "claude", limit: int = 15, *, write: bool = True,
           events: list[miner.Event] | None = None) -> dict:
    events = events if events is not None else _events(provider, limit)
    prof = miner.profile(events)

    # --- memoryOS arm: summon head-on, then write a draft-first proposal ---------
    mem = invoke.summon("memoryOS", f"ingest {provider} operator behavioral profile",
                        "on_call", write_receipt=False)
    proposal_path = None
    if mem["summoned"] and write:
        PROPOSALS.mkdir(parents=True, exist_ok=True)
        stamp = time.strftime("%Y%m%dT%H%M%S")
        proposal_path = PROPOSALS / f"proposal-{provider}-behavior-{stamp}.md"
        proposal_path.write_text(_memlang_draft(provider, prof), encoding="utf-8")

    # --- GenesisOS arm: summon head-on, then infer the operator's interior -------
    gen = invoke.summon("GenesisOS", f"infer {provider} operator interior from traces",
                        "on_call", write_receipt=False)
    interior_report = None
    if gen["summoned"]:
        # only tool-bearing events carry behavioral signal — role-only lines are noise
        traces = [{"t": e.ts, "kind": e.tools[0], "status": "flagged" if e.had_error else "ok",
                   "detail": e.tools[0]} for e in events if e.tools]
        interior_report = interior.report(traces)

    result = {
        "schema_version": "aios.ingest_session.v1",
        "provider": provider, "events": len(events), "tool_calls": prof.get("tool_calls"),
        "memoryOS": {"summoned": mem["summoned"], "reason": mem["reason"],
                     "draft_proposal": proposal_path.as_posix() if proposal_path else None,
                     "accepted": False},
        "GenesisOS": {"summoned": gen["summoned"], "reason": gen["reason"],
                      "the_itch": (interior_report or {}).get("the_itch"),
                      "ambiguities": (interior_report or {}).get("ambiguities", [])},
        "provenance": "logs→miner→summon(memoryOS draft-first + GenesisOS interior); "
                      "authority-gated; no memory accepted; no content (DNA #7)",
    }
    if write:
        RECEIPTS.mkdir(parents=True, exist_ok=True)
        (RECEIPTS / f"ingest-{provider}-{time.strftime('%Y%m%dT%H%M%S')}.json").write_text(
            json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    return result


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(description="Flow session logs into memoryOS (draft) + GenesisOS (interior)")
    p.add_argument("--provider", choices=["claude", "codex"], default="claude")
    p.add_argument("--limit", type=int, default=15)
    p.add_argument("--json", action="store_true")
    return p


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    r = ingest(args.provider, args.limit)
    if args.json:
        print(json.dumps(r, ensure_ascii=False, indent=2))
    else:
        m, g = r["memoryOS"], r["GenesisOS"]
        print(f"[{r['provider']}] {r['events']} events, {r['tool_calls']} tool-calls")
        print(f"  memoryOS  {'✓' if m['summoned'] else '✗'} → draft: {m['draft_proposal'] or m['reason']} (accepted={m['accepted']})")
        itch = (g.get('the_itch') or {})
        print(f"  GenesisOS {'✓' if g['summoned'] else '✗'} → itch: "
              f"{itch.get('text','(none)') if itch else '(none)'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
