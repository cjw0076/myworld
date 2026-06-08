#!/usr/bin/env python3
"""SMX experience loop — Learned Divergence made real (the inductive loop closed).

aios_smx_learn induced a scorer from a one-off experiment. This closes the loop:
every SMX run logs its universes + outcomes to an append-only experience store;
the universe scorer is RE-FIT from that accumulating history; the re-fit scorer
drives the next run's winner selection — which logs more experience. Over time the
multiverse narrows toward what has actually worked (the "Learned Divergence" /
"memory cells" invention from AIOS_SYNTHESIS_INVENTIONS.md), instead of trusting
the hand-coded magic numbers forever.

Cold-start safety: with too little data (or one class only) it falls back to the
hand-coded prior (aios_smx.score_universe). The prior is a reasonable default; the
learned scorer earns its place only once the data supports it.

Label (honest, derivable without live execution for losers): a universe is a
positive training example if it verified and was not later reverted; negative
otherwise. The winner additionally carries its post-apply outcome when known.

Schema: aios.smx_experience.v1
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Callable

import aios_smx as smx
from aios_smx_learn import fit_logreg, _sigmoid

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_STORE = ROOT / ".aios" / "smx_experience" / "experience.jsonl"
MIN_ROWS = 24          # below this, trust the prior (cold start)
BLAST_NORM = 5.0       # normalizers so features sit on a comparable scale
REVERT_NORM = 3.0


def universe_features(u: smx.Universe) -> list[float]:
    """Numeric feature vector for one universe (bias + the survivability signals)."""
    return [
        1.0,                                    # bias
        1.0 if u.verified_ok else 0.0,
        min(len(u.files_touched), 10) / BLAST_NORM,
        min(u.reverts, 6) / REVERT_NORM,
        1.0 if u.executed else 0.0,
    ]


FEATURE_NAMES = ["bias", "verified", "blast", "reverts", "executed"]


def universe_label(u: smx.Universe, reverted: bool = False) -> int:
    """Was this universe a GOOD choice? Positive = verified, executed, not reverted."""
    return 1 if (u.verified_ok and u.executed and not reverted) else 0


def log_experience(universes: list[smx.Universe], winner: smx.Universe | None,
                   *, store: Path = DEFAULT_STORE, reverted_winner: bool = False) -> None:
    """Append every universe's (features, label) to the experience store."""
    store.parent.mkdir(parents=True, exist_ok=True)
    with store.open("a", encoding="utf-8") as fh:
        for u in universes:
            reverted = reverted_winner and winner is not None and u.id == winner.id
            fh.write(json.dumps({
                "x": universe_features(u),
                "y": universe_label(u, reverted),
                "id": u.id, "branch_type": u.branch_type,
            }, ensure_ascii=False) + "\n")


def load_experience(store: Path = DEFAULT_STORE) -> list[tuple[list[float], int]]:
    if not store.exists():
        return []
    rows: list[tuple[list[float], int]] = []
    for line in store.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        try:
            r = json.loads(line)
            rows.append((r["x"], int(r["y"])))
        except (json.JSONDecodeError, KeyError, ValueError):
            continue
    return rows


def make_scorer(store: Path = DEFAULT_STORE, *, min_rows: int = MIN_ROWS) -> Callable[[smx.Universe], float]:
    """Return a universe scorer: LEARNED from experience if there's enough
    two-class data, else the hand-coded prior (cold-start safe)."""
    rows = load_experience(store)
    classes = {y for _x, y in rows}
    if len(rows) < min_rows or len(classes) < 2:
        prior = smx.score_universe
        prior.scorer_name = "prior(cold-start)"
        return prior
    w = fit_logreg(rows)

    def learned(u: smx.Universe) -> float:
        z = sum(wi * xi for wi, xi in zip(w, universe_features(u)))
        return _sigmoid(z)                      # 0..1 survivability probability

    learned.scorer_name = f"learned(n={len(rows)})"
    learned.weights = {n: round(wi, 3) for n, wi in zip(FEATURE_NAMES, w)}
    return learned


# ---- experiment: does the learned scorer ADAPT when reality differs from the
# ---- hand-coded prior, where the fixed prior cannot? --------------------------

def _synth_universes(rng, k: int) -> list[smx.Universe]:
    us = []
    for i in range(k):
        verified = rng.random() < 0.6
        blast = rng.randint(0, 6)
        reverts = rng.randint(0, 3)
        us.append(smx.Universe(f"u{i}", "synthetic", files_touched=["f"] * blast,
                               verified_ok=verified, reverts=reverts, executed=True))
    return us


def _true_best(universes, true_rule) -> smx.Universe:
    return max(universes, key=lambda u: (true_rule(u), -smx._ord(u.id)))


def run_experiment(*, seed: int = 5, n_runs: int = 120, k: int = 4) -> dict:
    """Simulate a WORLD whose real success-driver weights blast radius far more
    than the prior's -0.5 does. Train the learned scorer on that world's outcomes;
    measure top-1 selection accuracy (does the scorer pick the truly-best universe?)
    for the fixed prior vs the learned scorer on held-out multiverses.
    """
    import random
    rng = random.Random(seed)

    # the world's TRUE success rule: verified dominates, but blast is heavily
    # penalized (unlike the prior's mild -0.5) — reality differs from intuition.
    def true_rule(u: smx.Universe) -> float:
        return (10.0 if u.verified_ok else 0.0) - 2.0 * len(u.files_touched) - 1.0 * u.reverts

    rows: list[tuple[list[float], int]] = []
    for _ in range(n_runs):
        us = _synth_universes(rng, k)
        best = _true_best(us, true_rule)
        for u in us:
            rows.append((universe_features(u), 1 if u.id == best.id else 0))

    split = int(len(rows) * 0.75)
    w = fit_logreg(rows[:split])

    def learned(u):
        return _sigmoid(sum(wi * xi for wi, xi in zip(w, universe_features(u))))

    # held-out multiverses: did each scorer pick the truly-best universe?
    rng2 = random.Random(seed + 100)
    fixed_hits = learned_hits = trials = 0
    for _ in range(200):
        us = _synth_universes(rng2, k)
        truth = _true_best(us, true_rule).id
        if smx.select_winner(us, smx.score_universe).id == truth:
            fixed_hits += 1
        if smx.select_winner(us, learned).id == truth:
            learned_hits += 1
        trials += 1

    return {
        "schema_version": "aios.smx_experience.v1",
        "world": "blast penalized 4x more than the prior assumes",
        "learned_weights": {n: round(wi, 3) for n, wi in zip(FEATURE_NAMES, w)},
        "prior_top1_accuracy": round(fixed_hits / trials, 3),
        "learned_top1_accuracy": round(learned_hits / trials, 3),
        "learned_adapts_better": learned_hits > fixed_hits,
        "method": "experience-fit universe scorer vs fixed prior; top-1 selection vs ground truth",
    }


if __name__ == "__main__":
    import argparse

    p = argparse.ArgumentParser(description="SMX Learned-Divergence experiment")
    p.add_argument("--json", action="store_true")
    args = p.parse_args()
    r = run_experiment()
    if args.json:
        print(json.dumps(r, ensure_ascii=False, indent=2))
    else:
        print(f"learned weights: {r['learned_weights']}")
        print(f"top-1 selection — prior {r['prior_top1_accuracy']} vs learned "
              f"{r['learned_top1_accuracy']} → "
              f"{'learned adapts ✓' if r['learned_adapts_better'] else 'no gain'}")
