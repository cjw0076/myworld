#!/usr/bin/env python3
"""Inductive survivability scorer — turn intuition into math from experiment.

SMX's hand-coded scorer (aios_smx.score_universe) uses magic numbers
(5*verified - 0.5*blast - 1*reverts). Those are an INTUITION asserted as math.
The inductive/experimental alternative (founder steer 2026-06-08): generate a
population of candidate plans, label each with the REAL deterministic verifier as
ground truth, and FIT a scorer from that data — the coefficients are induced, not
guessed.

This is the cheap-pre-screen pattern: learn a model that predicts whether a plan
will pass the (potentially expensive) verifier from cheap schedule features, so
SMX can rank/prune universes before paying for full verification. The verifier
stays the trust anchor; the learned model only PRIORITIZES.

No numpy/sklearn — a small, seeded, pure-Python logistic regression so the
experiment is reproducible and dependency-free. Honest reporting: accuracy is
measured on a held-out split and compared to the majority-class baseline; we do
not claim more than the data shows.

Schema: aios.smx_learn.v1
"""
from __future__ import annotations

import argparse
import json
import math
import random
from datetime import date, timedelta

from aios_deadline_copilot import verify_schedule

HORIZON_DAYS = 21


def _d(s: str) -> date:
    y, m, dd = (int(x) for x in s.split("-"))
    return date(y, m, dd)


def features(schedule: list[dict], assignments: list[dict], today: str) -> list[float]:
    """Cheap schedule summary stats — deliberately NOT per-course due comparison
    (that is the verifier's job). The model must induce the relationship."""
    t = _d(today)
    courses = {a["course"] for a in assignments}
    scheduled_courses = {str(e.get("course")) for e in schedule if e.get("course")}
    dates = [(_d(e["date"]) - t).days for e in schedule if e.get("date")]
    covered = len(scheduled_courses & courses) / max(1, len(courses))
    max_out = (max(dates) / HORIZON_DAYS) if dates else 0.0
    min_out = (min(dates) / HORIZON_DAYS) if dates else 0.0
    density = len(schedule) / max(1, len(courses))
    return [1.0, covered, max_out, min_out, density]  # 1.0 = bias term


def _random_schedule(assignments, today, rng, *, bias_valid: bool):
    """One candidate schedule. bias_valid=True aims for a passing plan (all courses
    in [today, due]); False injects a violation (late/early/missing). Aiming is not
    guaranteeing — the REAL verifier still has the final say on the label."""
    t = _d(today)
    schedule = []
    sabotage = None if bias_valid else rng.choice(["late", "early", "skip"])
    skip_course = rng.choice(assignments)["course"] if sabotage == "skip" else None
    for a in assignments:
        if a["course"] == skip_course:
            continue
        due = (_d(a["due"]) - t).days
        for _k in range(rng.choice([1, 1, 2])):
            if sabotage == "late" and rng.random() < 0.5:
                off = rng.randint(due + 1, due + 6)        # after the deadline
            elif sabotage == "early" and rng.random() < 0.5:
                off = rng.randint(-4, -1)                  # before today
            else:
                off = rng.randint(0, max(0, due))          # valid window [today, due]
            schedule.append({"date": (t + timedelta(days=off)).isoformat(),
                             "course": a["course"], "task": "x"})
    return schedule


def gen_population(assignments: list[dict], today: str, n: int, seed: int) -> list[tuple[list[float], int]]:
    """Generate a CLASS-BALANCED population (≈half aimed-valid, half sabotaged),
    each labeled by the REAL verifier. Balance gives the model signal to learn —
    a lesson the first (imbalanced) run surfaced experimentally."""
    rng = random.Random(seed)
    rows: list[tuple[list[float], int]] = []
    for i in range(n):
        schedule = _random_schedule(assignments, today, rng, bias_valid=(i % 2 == 0))
        label = 1 if verify_schedule(schedule, assignments, today)["ok"] else 0
        rows.append((features(schedule, assignments, today), label))
    rng.shuffle(rows)
    return rows


def _sigmoid(z: float) -> float:
    if z < -60:
        return 0.0
    if z > 60:
        return 1.0
    return 1.0 / (1.0 + math.exp(-z))


def fit_logreg(rows: list[tuple[list[float], int]], *, lr: float = 0.3,
               epochs: int = 400, l2: float = 0.001) -> list[float]:
    """Plain-Python logistic regression by gradient descent. Returns weights."""
    if not rows:
        return []
    dim = len(rows[0][0])
    w = [0.0] * dim
    n = len(rows)
    for _ in range(epochs):
        grad = [0.0] * dim
        for x, y in rows:
            p = _sigmoid(sum(wi * xi for wi, xi in zip(w, x)))
            err = p - y
            for j in range(dim):
                grad[j] += err * x[j]
        for j in range(dim):
            w[j] -= lr * (grad[j] / n + l2 * w[j])
    return w


def predict(w: list[float], x: list[float]) -> int:
    return 1 if _sigmoid(sum(wi * xi for wi, xi in zip(w, x))) >= 0.5 else 0


def accuracy(w: list[float], rows: list[tuple[list[float], int]]) -> float:
    if not rows:
        return 0.0
    return sum(1 for x, y in rows if predict(w, x) == y) / len(rows)


def run_experiment(assignments: list[dict], today: str, *, n: int = 400, seed: int = 7) -> dict:
    """The experiment: induce the scorer from verifier-labeled data, report honestly."""
    rows = gen_population(assignments, today, n, seed)
    split = int(len(rows) * 0.75)
    train, test = rows[:split], rows[split:]
    w = fit_logreg(train)
    pos = sum(y for _x, y in test)
    majority = max(pos, len(test) - pos) / max(1, len(test))
    feat_names = ["bias", "covered", "max_out", "min_out", "density"]
    return {
        "schema_version": "aios.smx_learn.v1",
        "n": n, "train": len(train), "test": len(test),
        "induced_weights": {name: round(wi, 3) for name, wi in zip(feat_names, w)},
        "test_accuracy": round(accuracy(w, test), 3),
        "majority_baseline": round(majority, 3),
        "beats_baseline": accuracy(w, test) > majority,
        "label_balance": round(pos / max(1, len(test)), 3),
        "method": "verifier-labeled population → pure-Python logistic regression (induced, not hand-set)",
    }


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(description="Inductive survivability scorer experiment")
    p.add_argument("--today", default="2026-06-08")
    p.add_argument("--n", type=int, default=400)
    p.add_argument("--seed", type=int, default=7)
    p.add_argument("--json", action="store_true")
    return p


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    assignments = [
        {"course": "Database Systems", "due": "2026-06-15"},
        {"course": "Linear Algebra", "due": "2026-06-12"},
        {"course": "Operating Systems", "due": "2026-06-20"},
    ]
    r = run_experiment(assignments, args.today, n=args.n, seed=args.seed)
    if args.json:
        print(json.dumps(r, ensure_ascii=False, indent=2))
    else:
        print(f"induced weights: {r['induced_weights']}")
        print(f"test acc {r['test_accuracy']} vs majority {r['majority_baseline']} "
              f"→ {'beats baseline ✓' if r['beats_baseline'] else 'no better than baseline'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
