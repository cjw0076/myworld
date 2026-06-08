#!/usr/bin/env python3
"""Live SMX wiring — Speculative Multiverse Execution over the deadline copilot.

This connects the SMX flagship (aios_smx.py) to a REAL deterministic verifier
(deadline_copilot.verify_schedule) as the survivability scorer. A model proposes
K divergent study plans (different scheduling strategies — GenesisOS-style branch
framings); each is verified by CODE; SMX picks the survivor; the losing universes
become counterfactual memory. The verifier is the trust anchor: the model's
creativity is bounded by code that checks the exact constraint (no work after a
deadline).

The planner is dependency-injected (default = local substrate via
aios_capability_base.generate) so the orchestration is unit-testable without a
live LLM. On a host with the local substrate up (the AIOS box), `run_live()`
produces a real multiverse receipt; where the substrate is unreachable it fails
fast and says so — it does not fabricate a plan.

Schema: aios.smx_deadline.v1 (extends aios.smx.v1)
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Callable

import aios_smx as smx
from aios_deadline_copilot import extract_schedule, verify_schedule

# GenesisOS-style divergence framings: each makes the model explore a different
# region of the plan space. The deterministic verifier then judges them equally.
FRAMINGS: dict[str, str] = {
    "baseline": "마감 역산으로 급한 것부터 균형 있게 배분하라.",
    "inversion": "일부러 거꾸로: 여유 있는 과목부터 먼저 배치하되 어떤 일도 마감을 넘기지 마라.",
    "constraint-removal": "최소한의 날짜에 몰아서 — 가능한 적은 수의 공부 세션으로 끝내라(마감은 지켜라).",
    "risk-front-load": "가장 어렵고 위험한 과목을 맨 앞으로 몰아 일찍 끝내라(마감은 지켜라).",
}

# A planner turns (assignments, today, framing_instruction) into a schedule list.
Planner = Callable[[list[dict], str, str], list[dict]]


def _default_planner(assignments: list[dict], today: str, framing: str) -> list[dict]:
    """Live planner: ask the local substrate, parse its schedule. Fails fast (no
    fabrication) if the substrate is unreachable."""
    import aios_capability_base as base

    prompt = (
        f"오늘은 {today}. 다음 과제/시험 목록(JSON):\n{json.dumps(assignments, ensure_ascii=False)}\n\n"
        f"전략: {framing}\n"
        "기계가 읽을 스케줄을 fenced ```json 블록으로만 출력: "
        '[{"date":"YYYY-MM-DD","course":"<입력 그대로>","task":"..."}].'
    )
    text, _served, _trail = base.generate(prompt)
    return extract_schedule(text)


def build_universes(
    assignments: list[dict], today: str, *,
    framings: dict[str, str] | None = None,
    planner: Planner = _default_planner,
    executor: Callable[[smx.Universe], smx.Universe] | None = None,
) -> list[smx.Universe]:
    """Generate one universe per divergence framing, scored by the REAL verifier."""
    fr = framings or FRAMINGS
    universes: list[smx.Universe] = []
    for name, instruction in fr.items():
        try:
            schedule = planner(assignments, today, instruction)
        except Exception as exc:  # noqa: BLE001 — substrate failure → record, don't fabricate
            u = smx.Universe(f"u-{name}", name, verified_ok=False, executed=False,
                             note=f"planner failed: {str(exc)[:80]}")
            universes.append(u)
            continue
        v = verify_schedule(schedule, assignments, today)
        u = smx.Universe(
            id=f"u-{name}", branch_type=name,
            files_touched=sorted({str(e.get("course")) for e in schedule}),
            verified_ok=bool(v["ok"]),
            # executed reflects EVIDENCE: a real plan was produced. An empty
            # schedule means the substrate produced nothing (unreachable / failed)
            # — induce live-ness from what happened, don't assert it from a default.
            executed=len(schedule) > 0,
            note="" if v["ok"] else "; ".join(f"{x['course']} {x['issue']}" for x in v["violations"])[:120],
        )
        if executor is not None:
            u = executor(u)
        universes.append(u)
    return universes


def run(assignments: list[dict], today: str, *, planner: Planner = _default_planner,
        cf_dir: Path | None = None) -> dict:
    universes = build_universes(assignments, today, planner=planner)
    result = smx.run_multiverse(universes, cf_dir=cf_dir)
    result["schema_version"] = "aios.smx_deadline.v1"
    result["task"] = "deadline study-plan multiverse"
    return result


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(description="Live SMX over the deadline copilot")
    p.add_argument("--today", default="2026-06-08")
    p.add_argument("--json", action="store_true")
    return p


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    # demo input (the same relatable task as `aios demo`)
    assignments = [
        {"course": "Database Systems", "due": "2026-06-15"},
        {"course": "Linear Algebra", "due": "2026-06-12"},
        {"course": "Operating Systems", "due": "2026-06-20"},
    ]
    result = run(assignments, args.today)
    print(json.dumps(result, ensure_ascii=False, indent=2) if args.json
          else f"winner={result['winner']} applied={result['winner_applied']} "
               f"counterfactuals={result['counterfactuals']} "
               f"live={result['any_real_execution']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
