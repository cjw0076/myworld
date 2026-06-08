#!/usr/bin/env python3
"""AIOS Speculative Multiverse Execution (SMX) — the flagship synthesis invention.

(See docs/AIOS_SYNTHESIS_INVENTIONS.md.) A CPU does not run one branch and hope —
it speculatively executes several possible futures, commits the one that resolves,
squashes the rest. SMX does that at the AGENT level: fork K divergent plans, run
each in its OWN sandbox, deterministically score survivability, apply ONLY the
winner's diff, and keep the losing universes as *counterfactual memory* (negative
episodes the graph learns from). The sandbox (aios_sandbox.py, built today) is what
makes running several real futures safe — it converts GenesisOS divergence from
advisory ("speculative_only") into executable.

Invariant kept at the execution layer: the model PROPOSES universes; deterministic
CODE scores survivability and picks the winner (no model self-judging — avoids the
known self-refine degradation). Where OS isolation is unavailable, execution
degrades to dry-run (scored by static signal) and is honestly labelled — never
silently applied unsandboxed.

Schema: aios.smx.v1
"""
from __future__ import annotations

import json
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable

ROOT = Path(__file__).resolve().parents[1]
SCHEMA_VERSION = "aios.smx.v1"


@dataclass
class Universe:
    """One divergent plan and the outcome of (speculatively) executing it."""
    id: str
    branch_type: str                      # inversion / constraint-removal / alien-domain / baseline
    files_touched: list[str] = field(default_factory=list)  # blast radius
    verified_ok: bool = False             # did the deterministic verifier pass?
    reverts: int = 0                      # self-repair attempts before passing
    executed: bool = True                 # False = dry-run (isolation unavailable)
    note: str = ""


def score_universe(u: Universe) -> float:
    """Deterministic survivability score — CODE judges, not a model.

    Rewards a verified plan; penalizes blast radius (files touched) and reverts.
    A dry-run (un-executed) universe is scored but capped below any real verified
    one, so a genuinely-executed+verified universe always wins when present.
    """
    score = 0.0
    score += 5.0 if u.verified_ok else 0.0
    score -= 0.5 * len(u.files_touched)        # smaller blast radius is safer
    score -= 1.0 * u.reverts                    # fewer repair cycles is better
    if not u.executed:
        score = min(score, 2.0) - 0.1           # dry-run cannot outrank a real verified plan
    return round(score, 3)


def select_winner(universes: list[Universe]) -> Universe | None:
    """Pick the highest-scoring universe; stable tie-break by id for determinism."""
    if not universes:
        return None
    return max(universes, key=lambda u: (score_universe(u), -_ord(u.id)))


def _ord(s: str) -> int:
    return sum(ord(c) for c in s)  # cheap stable tiebreak key


def counterfactual_episode(loser: Universe, winner_id: str) -> dict:
    """A losing/reverted universe becomes a negative episode (DNA #3: no record
    destroyed — applied to ACTIONS, not just facts). The training signal for the
    scorer and the antidote to repeating a mistake a prior session already made."""
    return {
        "id": loser.id,
        "branch_type": loser.branch_type,
        "score": score_universe(loser),
        "verified_ok": loser.verified_ok,
        "files_touched": loser.files_touched,
        "executed": loser.executed,
        "why_not_chosen": (
            "failed verification" if not loser.verified_ok else
            f"lower survivability than winner {winner_id}"),
        "note": loser.note,
    }


def write_counterfactuals(losers: list[dict], directory: Path) -> Path | None:
    """Persist counterfactual episodes (draft-first negative memory)."""
    if not losers:
        return None
    directory.mkdir(parents=True, exist_ok=True)
    stamp = time.strftime("%Y%m%dT%H%M%S")
    out = directory / f"counterfactual-{stamp}.json"
    out.write_text(json.dumps({"schema_version": "aios.counterfactual.v1",
                               "episodes": losers}, ensure_ascii=False, indent=2),
                   encoding="utf-8")
    return out


def run_multiverse(
    universes: list[Universe],
    *,
    apply_fn: Callable[[Universe], None] | None = None,
    cf_dir: Path | None = None,
) -> dict:
    """Score the universes, apply ONLY the winner, send losers to counterfactual
    memory, return a provenance receipt. apply_fn defaults to no-op (caller wires
    the real diff-apply). Pure orchestration — unit-testable with synthetic universes.
    """
    scored = [{"id": u.id, "branch_type": u.branch_type, "score": score_universe(u),
               "verified_ok": u.verified_ok, "executed": u.executed} for u in universes]
    winner = select_winner(universes)
    losers = [u for u in universes if winner is None or u.id != winner.id]
    cf = [counterfactual_episode(u, winner.id if winner else "none") for u in losers]
    cf_path = write_counterfactuals(cf, cf_dir or (ROOT / ".aios" / "counterfactual"))
    applied = False
    if winner is not None and winner.verified_ok and winner.executed and apply_fn is not None:
        apply_fn(winner)                      # commit ONLY the winning universe
        applied = True
    return {
        "schema_version": SCHEMA_VERSION,
        "generated_at": time.strftime("%Y-%m-%d"),
        "universes": scored,
        "winner": winner.id if winner else None,
        "winner_applied": applied,
        "any_real_execution": any(u.executed for u in universes),
        "counterfactuals": len(cf),
        "counterfactual_ref": cf_path.as_posix() if cf_path else None,
        "provenance": "deterministic survivability score (code judges); winner-only "
                      "apply; losers kept as counterfactual memory",
    }


def sandboxed_universe_executor(workspace: str | Path, command_of: Callable[[Universe], list[str]]):
    """Build an executor that runs each universe's command in its OWN sandbox,
    degrading to dry-run (executed=False) where OS isolation is unavailable —
    honestly labelled, never silently run unsandboxed."""
    import sys

    sys.path.insert(0, (ROOT / "scripts").as_posix())
    import aios_sandbox as sb

    def execute(u: Universe) -> Universe:
        try:
            code, _out, err = sb.run_sandboxed(command_of(u), workspace=workspace,
                                               allow_network=False)
            u.executed = True
            u.verified_ok = u.verified_ok and code == 0
            if code != 0:
                u.note = (u.note + f" sandbox rc={code} {err.strip()[:80]}").strip()
        except sb.SandboxUnavailable as exc:
            u.executed = False               # graceful degrade — scored, not applied
            u.note = (u.note + f" dry-run (isolation unavailable: {str(exc)[:60]})").strip()
        return u

    return execute


if __name__ == "__main__":
    # demo with synthetic universes (no LLM, no isolation needed)
    demo = [
        Universe("u-baseline", "baseline", ["a.py"], verified_ok=True, reverts=1),
        Universe("u-inversion", "inversion", ["a.py", "b.py", "c.py"], verified_ok=True),
        Universe("u-alien", "alien-domain", ["a.py"], verified_ok=False),
    ]
    print(json.dumps(run_multiverse(demo), ensure_ascii=False, indent=2))
