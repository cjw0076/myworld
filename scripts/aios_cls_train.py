#!/usr/bin/env python3
"""aios_cls_train — Phase C training organ (the dream→weights bridge).

Turns the gated corpus (aios_cls_gate) into a narrow QLoRA fine-tune of the local
model. Everything that does NOT need a GPU runs here and is testable now: build the
instruction dataset, expand it by the Phase-D replay schedule, validate corpus
readiness, and emit the QLoRA config. The actual fine-tune (train()) is the only
GPU-heavy, near-irreversible step — it is FOUNDER-GATED: it refuses to run unless
apply=True AND AIOS_TRAIN_GO=1, and it imports peft/transformers/trl lazily only
then. NEVER LiteLLM (banned 2026-03-24 supply-chain incident).

What the corpus can honestly teach (persisted data is aggregate tool_freq, not call
traces): the BEHAVIORAL PRIOR + 5-OS routing — "in a {category}/{loop_type} session,
these are the tools you reach for." Tool-call FORMAT reliability needs per-call
payloads, which are not persisted (privacy: tool명만); that is out of scope for this
corpus and noted, not faked.

Privacy: examples carry tool NAMES + category/loop_type only — no content, no args.
Draft-first for weights: a produced adapter is a draft until aios_cls_gate's held-out
eval beats the baseline (gate_promote). Provenance: the dataset carries the corpus
hash it was built from.

Schemas: aios.cls_trainset.v1 / aios.cls_qlora_config.v1
"""
from __future__ import annotations

import json
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

# tokens that appear in tool_freq but are not real tools (session bookkeeping)
_PSEUDO = {"last-prompt", "queue-operation", "thinking", "text"}


def _real_tools(freq: dict) -> list[tuple[str, int]]:
    """Keep real tool names (Uppercase-led or mcp__…), drop pseudo bookkeeping
    tokens, sorted by frequency desc."""
    items = []
    for name, n in (freq or {}).items():
        nm = str(name)
        if nm in _PSEUDO:
            continue
        if nm[:1].isupper() or nm.startswith("mcp__"):
            items.append((nm, int(n)))
    return sorted(items, key=lambda x: -x[1])


def to_example(run: dict, top_k: int = 6) -> dict | None:
    """One behavioral-prior instruction example (chat format, TRL-compatible).
    Returns None if the run has no real tools to teach from."""
    tools = _real_tools(run.get("tool_freq") or {})[:top_k]
    if not tools:
        return None
    cat = run.get("category") or "general"
    lt = run.get("loop_type") or "unknown"
    tool_names = [t for t, _ in tools]
    user = (f"You are an AIOS agent starting a {cat} task whose interaction pattern is "
            f"'{lt}'. List, most-used first, the tools you will primarily rely on.")
    assistant = ", ".join(tool_names)
    return {
        "messages": [
            {"role": "system", "content": "You are AIOS, a local agent OS. Answer with tool names only."},
            {"role": "user", "content": user},
            {"role": "assistant", "content": assistant},
        ],
        "_meta": {"ref": run.get("ref"), "category": cat, "loop_type": lt},
    }


def build_dataset(corpus: list[dict], schedule: list[dict]) -> list[dict]:
    """Expand eligible runs into training examples by their replay_count (Phase D).
    Falls back to one example per run when no replay_count is present."""
    by_ref = {s["ref"]: s for s in schedule}
    out: list[dict] = []
    for run in corpus:
        ex = to_example(run)
        if ex is None:
            continue
        count = int(by_ref.get(run["ref"], {}).get("replay_count", 1) or 1)
        out.extend(ex for _ in range(max(1, count)))
    return out


def qlora_config(base_model: str = "Qwen/Qwen2.5-Coder-7B-Instruct") -> dict:
    """QLoRA config (pure data — no GPU, no import). Narrow adapter on the local
    base model: 4-bit base, low-rank LoRA on attention+MLP projections."""
    return {
        "schema": "aios.cls_qlora_config.v1",
        "base_model": base_model,
        "load_in_4bit": True,
        "lora": {"r": 16, "alpha": 32, "dropout": 0.05,
                 "target_modules": ["q_proj", "k_proj", "v_proj", "o_proj",
                                    "gate_proj", "up_proj", "down_proj"]},
        "train": {"epochs": 1, "lr": 2e-4, "batch_size": 4, "grad_accum": 4,
                  "max_seq_len": 1024, "warmup_ratio": 0.03},
        "trainer": "trl.SFTTrainer",   # NOT LiteLLM — direct HF/peft/trl
    }


def validate_ready(manifest: dict, examples: list[dict], min_examples: int = 50,
                   distinct_runs: int | None = None, min_distinct: int = 20) -> dict:
    """Corpus-readiness gate before any GPU run. draft-first: refuse to train on a
    corpus that is unlabeled, too small, or — crucially — too few DISTINCT runs.
    Replay (Phase D) inflates the example COUNT but not diversity; training on a
    handful of runs replayed many times overfits, so distinct_runs is gated too."""
    reasons = []
    if not manifest.get("training_ready"):
        reasons.append("corpus not training_ready (unlabeled / no diversity)")
    if len(examples) < min_examples:
        reasons.append(f"too few examples: {len(examples)} < {min_examples}")
    if distinct_runs is not None and distinct_runs < min_distinct:
        reasons.append(f"too few distinct runs: {distinct_runs} < {min_distinct} "
                       f"(replay inflates count, not diversity)")
    return {"ready": not reasons, "examples": len(examples),
            "distinct_runs": distinct_runs, "min_examples": min_examples,
            "min_distinct": min_distinct, "blockers": reasons,
            "corpus_provenance": manifest.get("provenance")}


def export(out_path: Path, *, apply: bool = False, min_examples: int = 50) -> dict:
    """Build dataset from the live corpus + replay schedule; validate; write JSONL
    (dry-run by default). GPU-free — this is the verifiable half of Phase C."""
    sp = str(ROOT / "scripts")
    if sp not in sys.path:
        sys.path.insert(0, sp)
    import aios_agent_behavior as AB   # noqa: PLC0415
    import aios_cls_gate as G          # noqa: PLC0415
    mems = AB.load_behavior_memories()
    eligible, manifest = G.select_corpus(mems)
    schedule, _ = G.replay_schedule(eligible, epoch_size=max(min_examples, len(eligible)))
    examples = build_dataset(eligible, schedule)
    distinct = len({ex.get("_meta", {}).get("ref") for ex in examples})
    ready = validate_ready(manifest, examples, min_examples=min_examples,
                           distinct_runs=distinct)
    written = 0
    if apply and examples:
        out_path.parent.mkdir(parents=True, exist_ok=True)
        with out_path.open("w", encoding="utf-8") as f:
            for ex in examples:
                f.write(json.dumps({k: v for k, v in ex.items() if k != "_meta"},
                                   ensure_ascii=False) + "\n")
        written = len(examples)
    return {
        "schema": "aios.cls_trainset.v1",
        "corpus": {"eligible": len(eligible), "provenance": manifest.get("provenance"),
                   "training_ready": manifest.get("training_ready")},
        "examples": len(examples), "written": written,
        "out": out_path.as_posix() if written else None,
        "readiness": ready,
        "mode": "written" if written else "dry-run (use --apply to write JSONL)",
        "sample": ({k: v for k, v in examples[0].items() if k != "_meta"} if examples else None),
    }


def train(dataset_path: Path, *, apply: bool = False, base_model: str | None = None) -> dict:
    """The GPU step. FOUNDER-GATED: refuses unless apply=True AND AIOS_TRAIN_GO=1.
    Imports peft/transformers/trl lazily only when actually training. Never LiteLLM."""
    go = os.environ.get("AIOS_TRAIN_GO") == "1"
    cfg = qlora_config(base_model or "Qwen/Qwen2.5-Coder-7B-Instruct")
    if not (apply and go):
        return {"status": "gated", "ran": False, "config": cfg,
                "hint": "GPU run is founder-gated: pass --apply AND set AIOS_TRAIN_GO=1",
                "dataset": dataset_path.as_posix()}
    if not dataset_path.exists():
        return {"status": "no_dataset", "ran": False, "hint": "run `export --apply` first"}
    # Lazy heavy imports — only reached under explicit founder GO + GPU.
    try:
        import torch  # noqa: F401, PLC0415
        from datasets import load_dataset  # noqa: PLC0415
        from peft import LoraConfig  # noqa: PLC0415
        from transformers import AutoModelForCausalLM, AutoTokenizer, BitsAndBytesConfig  # noqa: PLC0415
        from trl import SFTConfig, SFTTrainer  # noqa: PLC0415
    except ImportError as e:  # noqa: BLE001
        return {"status": "deps_missing", "ran": False, "error": str(e),
                "hint": "pip install torch transformers peft trl datasets bitsandbytes (NOT litellm)"}
    # Real training body intentionally minimal here — wired when founder gives GO and
    # the corpus is at scale. The scaffold above is what is verifiable without a GPU.
    return {"status": "ready_to_train", "ran": False,
            "note": "deps present + gated open; training body to be enabled at corpus scale",
            "config": cfg, "dataset": dataset_path.as_posix()}


def main(argv: list[str] | None = None) -> int:
    import argparse
    p = argparse.ArgumentParser(prog="aios cls-train",
        description="Phase C training organ: corpus→QLoRA dataset (GPU-free) + founder-gated fine-tune.")
    sub = p.add_subparsers(dest="cmd")
    ex = sub.add_parser("export")
    ex.add_argument("--out", default=str(Path.home() / ".aios" / "train" / "cls_trainset.jsonl"))
    ex.add_argument("--apply", action="store_true", help="write the JSONL (default: dry-run)")
    ex.add_argument("--min-examples", type=int, default=50)
    sub.add_parser("config")
    rn = sub.add_parser("run")
    rn.add_argument("--dataset", default=str(Path.home() / ".aios" / "train" / "cls_trainset.jsonl"))
    rn.add_argument("--apply", action="store_true")
    rn.add_argument("--base-model", default=None)
    args = p.parse_args(argv)

    if args.cmd == "config":
        print(json.dumps(qlora_config(), ensure_ascii=False, indent=2))
        return 0
    if args.cmd == "run":
        out = train(Path(args.dataset), apply=args.apply, base_model=args.base_model)
        print(json.dumps(out, ensure_ascii=False, indent=2))
        return 0
    # default: export
    out = export(Path(args.out), apply=getattr(args, "apply", False),
                 min_examples=getattr(args, "min_examples", 50))
    print(json.dumps(out, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
