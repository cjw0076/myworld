#!/usr/bin/env python3
"""aios_cls_gate — Phase C gates for the dream→weights bridge (draft-first for weights).

The actual narrow QLoRA training run is GPU-heavy and near-irreversible (a weight
artifact), so it stays behind a founder GO. What lives HERE is everything that must
be decided BEFORE and AFTER that run — pure python, runnable now, fully testable:

  1. corpus gate  — which captured runs are training-eligible?
       non-doom-loop, enough signal, diversity-capped per mode; human-intervention
       runs (Phase B supervision signal) weighted UP — corrected runs are worth more.
  2. eval harness — a held-out behavior eval + a promotion rule.
       Draft-first for weights (gate #97 of AIOS_SELF_IMPROVING): a fine-tune is a
       DRAFT until its held-out behavior score beats the baseline by a margin.
       Otherwise it is discarded, never deployed.

Provenance (gate): a corpus manifest carries a content hash of the exact slice +
the eval it must beat, so any weight update can cite where it came from.

Schemas: aios.cls_corpus.v1 / aios.cls_eval_gate.v1
"""
from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


# ── corpus gate ─────────────────────────────────────────────────────────────────

def _ref(m: dict) -> str:
    r = m.get("id") or m.get("ref")
    if r:
        return str(r)
    return hashlib.sha256(json.dumps(m, sort_keys=True).encode()).hexdigest()[:16]


def _dominant_tool(freq: dict) -> str | None:
    return max(freq, key=freq.get) if freq else None


def _infer_loop_type(freq: dict) -> str:
    """Infer loop_type from a stored tool_freq when the record predates the
    loop_type field (mirrors aios_agent_behavior._classify_loop_type, minus
    doom_loop which needs the tool SEQUENCE — and doom runs are already dropped
    at ingest, so a persisted record is non-doom by construction)."""
    total = sum(freq.values())
    if total == 0:
        return "unknown"
    if total < 5:
        return "quick"
    distinct = len(freq)
    unique_ratio = distinct / total
    bash = sum(c for t, c in freq.items() if t.startswith("Bash")) / total
    edit = sum(c for t, c in freq.items() if t.startswith("Edit")) / total
    read = sum(c for t, c in freq.items() if t.startswith("Read")) / total
    if edit > 0.15 and bash > 0.10:
        return "react_code"
    if read > 0.30 and unique_ratio > 0.5:
        return "exploration"
    if unique_ratio < 0.25:
        return "repetitive"
    return "react_general"


def _corpus_hash(eligible: list[dict]) -> str:
    refs = sorted(c["ref"] for c in eligible)
    return hashlib.sha256("\n".join(refs).encode()).hexdigest()[:16]


def _is_aggregate(m: dict) -> bool:
    """Bulk dataset imports carry a 'dataset' key and store AGGREGATE tool_freq
    (counts merged across many runs), not a single run's trajectory. They cannot
    carry loop_type / intervention supervision, so they are not per-run training data."""
    return "dataset" in m


def select_corpus(memories: list[dict], *, min_tools: int = 5,
                  max_per_bucket: int = 200,
                  include_aggregates: bool = False) -> tuple[list[dict], dict]:
    """Pick training-eligible per-run records. Returns (eligible, manifest).

    Training corpus = session-derived per-run trajectories only:
    - aggregate dataset imports excluded by default (not per-run; opt in with
      include_aggregates=True if you really want frequency priors in the mix).
    - doom-loop runs excluded (contaminated).
    - too little signal (<min_tools tool uses) excluded.
    - diversity cap: at most max_per_bucket per loop_type.
    - sample weight: human-intervention runs weighted up to 3x — a steered/corrected
      run carries supervision the agent didn't produce on its own (Phase B → C).

    The manifest also carries corpus_quality: an honest readout of WHY the corpus
    is or isn't training-ready (session-derived vs aggregate, labeled vs unlabeled).
    """
    quality = {"total": len(memories), "session_derived": 0, "aggregate_import": 0,
               "labeled_loop_type": 0, "multi_tool": 0}
    eligible: list[dict] = []
    buckets: dict[str, int] = {}
    for m in memories:
        agg = _is_aggregate(m)
        quality["aggregate_import" if agg else "session_derived"] += 1
        freq = m.get("tool_freq") or {}
        if isinstance(freq, str):
            try:
                freq = json.loads(freq)
            except Exception:  # noqa: BLE001
                freq = {}
        # use the persisted loop_type; for stale records that predate the field,
        # infer it from tool_freq (aggregates are excluded below, so this only
        # ever labels per-run session records).
        lt = m.get("loop_type")
        if (not lt or lt == "unknown") and not agg:
            lt = _infer_loop_type(freq)
        if lt and lt != "unknown":
            quality["labeled_loop_type"] += 1
        if sum(freq.values()) >= min_tools and len(freq) > 1:
            quality["multi_tool"] += 1

        if agg and not include_aggregates:
            continue
        if lt == "doom_loop":
            continue
        if sum(freq.values()) < min_tools:
            continue
        bucket = lt or "unknown"
        if buckets.get(bucket, 0) >= max_per_bucket:
            continue
        buckets[bucket] = buckets.get(bucket, 0) + 1
        ir = float(m.get("intervention_rate") or 0)
        weight = 1.0 + min(2.0, ir * 4)        # corrected runs up to 3x
        eligible.append({
            "ref": _ref(m), "tool_freq": freq, "loop_type": bucket,
            "category": m.get("category"), "weight": round(weight, 3),
        })
    manifest = {
        "schema": "aios.cls_corpus.v1",
        "from": len(memories), "selected": len(eligible),
        "buckets": buckets, "provenance": _corpus_hash(eligible),
        "corpus_quality": quality,
        "training_ready": len(eligible) > 0 and buckets.get("unknown", 0) < len(eligible),
    }
    return eligible, manifest


# ── eval harness (held-out behavior eval + promotion rule) ───────────────────────

def split_holdout(corpus: list[dict], frac: float = 0.2) -> tuple[list[dict], list[dict]]:
    """Deterministic train/holdout split (hash-ordered — reproducible, no RNG)."""
    ranked = sorted(corpus, key=lambda c: hashlib.sha256(str(c["ref"]).encode()).hexdigest())
    k = max(1, int(len(ranked) * frac)) if len(ranked) > 1 else 0
    return ranked[k:], ranked[:k]


def _freq_prior(train: list[dict]) -> dict[str, float]:
    prior: dict[str, float] = {}
    for c in train:
        w = float(c.get("weight", 1.0))
        for t, n in (c.get("tool_freq") or {}).items():
            prior[t] = prior.get(t, 0.0) + n * w
    return prior


def eval_behavior(train: list[dict], holdout: list[dict]) -> dict:
    """Baseline held-out behavior eval: build a weighted tool prior from TRAIN, then
    predict each holdout run's dominant tool. acc@1 = fraction predicted right.

    This is the floor a fine-tune must beat. It is honest, not impressive — a frozen
    frequency prior; the whole point of Phase C is for a trained adapter to clear it."""
    prior = _freq_prior(train)
    if not holdout:
        return {"n": 0, "acc": 0.0, "baseline": "freq_prior"}
    pred_global = max(prior, key=prior.get) if prior else None
    hits = sum(1 for c in holdout if _dominant_tool(c.get("tool_freq") or {}) == pred_global)
    return {"n": len(holdout), "acc": round(hits / len(holdout), 3),
            "baseline": "freq_prior", "predicts": pred_global}


def replay_schedule(corpus: list[dict], *, epoch_size: int = 0) -> tuple[list[dict], dict]:
    """Phase D — replay selection policy. Decide which eligible runs to replay during
    dream→train, and how often. Prioritized replay (CLS analogue of prioritized
    experience replay): replay_weight = base value × diversity balance × inverse
    redundancy, so high-supervision, under-represented, non-duplicate runs are
    replayed more — preventing the fine-tune from overfitting the dominant mode.

    - base value: the select_corpus weight (intervention-boosted).
    - diversity balance: inverse frequency of the run's loop_type bucket.
    - inverse redundancy: inverse frequency of its dominant tool (near-dup profiles
      share a dominant tool; downweight so duplicates don't dominate replay).

    Returns (schedule, summary). schedule is corpus sorted by replay_weight desc, each
    item carrying replay_weight + (if epoch_size>0) replay_count for one epoch."""
    if not corpus:
        return [], {"schema": "aios.cls_replay.v1", "items": 0, "epoch_size": epoch_size}
    bucket_n: dict[str, int] = {}
    domtool_n: dict[str, int] = {}
    for c in corpus:
        bucket_n[c.get("loop_type") or "unknown"] = bucket_n.get(c.get("loop_type") or "unknown", 0) + 1
        dt = _dominant_tool(c.get("tool_freq") or {}) or "none"
        domtool_n[dt] = domtool_n.get(dt, 0) + 1

    scored = []
    for c in corpus:
        base = float(c.get("weight", 1.0))
        bucket = c.get("loop_type") or "unknown"
        dt = _dominant_tool(c.get("tool_freq") or {}) or "none"
        diversity = 1.0 / bucket_n[bucket]          # rarer mode → replayed more
        redundancy = 1.0 / domtool_n[dt]            # rarer dominant tool → replayed more
        rw = base * diversity * redundancy
        scored.append({**c, "replay_weight": round(rw, 5)})

    total = sum(s["replay_weight"] for s in scored) or 1.0
    if epoch_size > 0:
        for s in scored:
            s["replay_count"] = max(1, round(epoch_size * s["replay_weight"] / total))
    scored.sort(key=lambda s: s["replay_weight"], reverse=True)
    summary = {"schema": "aios.cls_replay.v1", "items": len(scored),
               "epoch_size": epoch_size, "buckets": bucket_n,
               "top_ref": scored[0]["ref"], "top_weight": scored[0]["replay_weight"]}
    return scored, summary


def gate_promote(base_acc: float, candidate_acc: float | None, *, margin: float = 0.02) -> dict:
    """Draft-first for weights: promote a fine-tune ONLY if its held-out score beats
    the baseline by >= margin. candidate_acc=None ⇒ no trained adapter yet (awaiting
    the GPU run, founder-gated) ⇒ not promotable."""
    if candidate_acc is None:
        return {"schema": "aios.cls_eval_gate.v1", "promote": False,
                "base": base_acc, "candidate": None, "margin": margin,
                "status": "awaiting_training (founder GO for GPU run)"}
    promote = candidate_acc >= base_acc + margin
    return {"schema": "aios.cls_eval_gate.v1", "promote": promote,
            "base": base_acc, "candidate": candidate_acc, "margin": margin,
            "status": "promote" if promote else "stays_draft (eval not beaten)"}


# ── Phase E — close the CLS loop (capture→gate→replay→eval→promote) ──────────────

def run_cycle(memories: list[dict], *, frac: float = 0.2,
              candidate_acc: float | None = None, epoch_size: int = 0,
              at: str | None = None) -> dict:
    """One full draft-first CLS cycle, GPU step excepted. Closes the loop:
      capture (A/B, upstream) → corpus gate (C) → replay policy (D)
      → held-out eval + promotion gate (E).

    Everything here runs without a GPU and emits ONE provenance-stamped report.
    The only open step is the dream→weights QLoRA run (founder-gated): pass its
    held-out acc@1 as candidate_acc to get a real promote/discard decision; omit it
    and the gate reports 'awaiting training'. The baseline acc is the benchmark the
    trained adapter must beat — recorded with the corpus hash so it is auditable."""
    eligible, manifest = select_corpus(memories)
    schedule, replay = replay_schedule(eligible, epoch_size=epoch_size)
    train, holdout = split_holdout(eligible, frac=frac)
    baseline = eval_behavior(train, holdout)
    gate = gate_promote(baseline["acc"], candidate_acc)
    return {
        "schema": "aios.cls_cycle.v1",
        "at": at,
        "corpus": manifest,
        "replay": replay,
        "split": {"train": len(train), "holdout": len(holdout)},
        "baseline": baseline,
        "gate": gate,
        "loop_closed": manifest["training_ready"] and len(holdout) > 0,
        "open_step": "dream→weights QLoRA run (founder GO for GPU)",
    }


# ── CLI ──────────────────────────────────────────────────────────────────────────

def _load_memories() -> list[dict]:
    sp = str(ROOT / "scripts")
    if sp not in sys.path:
        sys.path.insert(0, sp)
    import aios_agent_behavior as AB  # noqa: PLC0415
    return AB.load_behavior_memories()


def main(argv: list[str] | None = None) -> int:
    import argparse
    p = argparse.ArgumentParser(prog="aios cls-gate",
        description="Phase C gates: training-corpus selection + held-out eval (draft-first for weights).")
    sub = p.add_subparsers(dest="cmd")
    c = sub.add_parser("corpus")
    c.add_argument("--min-tools", type=int, default=5)
    c.add_argument("--max-per-bucket", type=int, default=200)
    e = sub.add_parser("eval")
    e.add_argument("--frac", type=float, default=0.2)
    e.add_argument("--candidate", type=float, default=None,
                   help="held-out acc@1 of a trained adapter (omit = none yet)")
    r = sub.add_parser("replay")
    r.add_argument("--epoch-size", type=int, default=0,
                   help="if >0, emit replay_count per run for one replay epoch")
    cy = sub.add_parser("cycle")
    cy.add_argument("--frac", type=float, default=0.2)
    cy.add_argument("--candidate", type=float, default=None,
                    help="trained-adapter held-out acc@1 (omit = awaiting founder-gated run)")
    cy.add_argument("--epoch-size", type=int, default=0)
    args = p.parse_args(argv)

    mems = _load_memories()
    eligible, manifest = select_corpus(
        mems, min_tools=getattr(args, "min_tools", 5),
        max_per_bucket=getattr(args, "max_per_bucket", 200))

    if args.cmd == "cycle":
        from datetime import datetime, timezone
        rep = run_cycle(mems, frac=args.frac, candidate_acc=args.candidate,
                        epoch_size=getattr(args, "epoch_size", 0),
                        at=datetime.now(timezone.utc).isoformat(timespec="seconds"))
        print(json.dumps(rep, ensure_ascii=False, indent=2))
        return 0

    if args.cmd == "replay":
        sched, summary = replay_schedule(eligible, epoch_size=getattr(args, "epoch_size", 0))
        print(json.dumps({"corpus": manifest, "replay": summary, "top": sched[:5]},
                         ensure_ascii=False, indent=2))
        return 0

    if args.cmd == "eval":
        train, holdout = split_holdout(eligible, frac=args.frac)
        base = eval_behavior(train, holdout)
        gate = gate_promote(base["acc"], args.candidate)
        print(json.dumps({"corpus": manifest, "split": {"train": len(train), "holdout": len(holdout)},
                          "baseline": base, "gate": gate}, ensure_ascii=False, indent=2))
        return 0

    # default: corpus
    print(json.dumps({"corpus": manifest, "sample": eligible[:5]}, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
