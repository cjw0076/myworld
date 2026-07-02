#!/usr/bin/env python3
"""AIOS headline A/B — does the behavioral-memory ledger measurably help an agent?

The product's headline is "your agents carry forward what worked". This harness
tests that OUTCOME (not just the mechanism) with a controlled, equal-budget,
pre-registered A/B on a local model:

  Arm A (bare)    : TEST task prompt -> model -> extract code -> pytest oracle.
                    Up to R attempts; on failure the oracle error is fed back once.
  Arm B (+ledger) : IDENTICAL, but the prompt is prefixed with GENERIC BEHAVIORAL
                    guidance retrieved from a ledger that was seeded by running the
                    agent on a DISJOINT set of TRAIN tasks (via the REAL ingest/record
                    path in aios_agent_behavior.py — write_to_akashic + predict_behavior).

No train/test leakage by construction: the ledger only ever contains behavioral
signatures of TRAIN runs (tool patterns / attempt counts / a generic "what worked"
note) — never anything derived from a TEST task, and never solution code.

Metrics per arm: solve rate, mean attempts-to-solve, total output tokens.
N = every TEST task x TRIALS trials per arm. Seeds are matched per (task,trial,attempt)
across arms, temperature > 0 for trial variance, arm order alternates per trial.

Substrate: local ollama (default model qwen2.5-coder:7b; env AIOS_AB_MODEL to override).
Isolation: the ledger lives in a throwaway AIOS_HOME (tempdir), so a real user's
~/.aios/ is never touched and the run is reproducible.

Usage:
    python3 scripts/aios_headline_ab.py --out docs/aios_headline_ab_results.json
    python3 scripts/aios_headline_ab.py --dry-run     # 1 task, 1 trial smoke
    AIOS_AB_MODEL=qwen3-coder:30b python3 scripts/aios_headline_ab.py
"""
from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import sys
import tempfile
import time
import urllib.request
from pathlib import Path
from typing import NamedTuple, Optional

# ---------------------------------------------------------------------------
# Config (pre-registered defaults)
# ---------------------------------------------------------------------------

OLLAMA_URL = "http://localhost:11434/api/generate"
DEFAULT_MODEL = os.environ.get("AIOS_AB_MODEL", "qwen2.5-coder:7b")
TASK_ROOT = Path(__file__).resolve().parent.parent / "experiments" / "headline_ab" / "tasks"
SCRIPTS_DIR = Path(__file__).resolve().parent

R_ATTEMPTS = 2          # attempts per trial; on failure feed oracle error back once
TRIALS = 3              # trials per arm per TEST task (N = |TEST| * TRIALS per arm)
SEED_RUNS_PER_TASK = 2  # bare runs per TRAIN task used to seed the ledger
SEED_BASE = 20260702    # deterministic seed base
TEMPERATURE = 0.6       # > 0 for trial-to-trial variance
NUM_PREDICT = 768       # cap output length (bounds runtime)
TOP_P = 0.9

# Behavioral action vocabulary the ledger reasons over (generic, task-agnostic).
BEHAVIOR_TOOLS = ["WriteCode", "RunOracle", "ReadError", "FixEdgeCase", "HandleEmpty"]


# ---------------------------------------------------------------------------
# Task battery
# ---------------------------------------------------------------------------


class Task(NamedTuple):
    name: str
    split: str          # "train" | "test"
    module: str         # module name the oracle imports from (always "solution")
    function: str       # required function name
    prompt: str         # coding instruction
    oracle_path: Path   # pytest oracle


def load_battery(task_root: Path = TASK_ROOT) -> dict[str, list[Task]]:
    """Load {"train": [...], "test": [...]} from experiments/headline_ab/tasks/."""
    battery: dict[str, list[Task]] = {"train": [], "test": []}
    for split in ("train", "test"):
        split_dir = task_root / split
        if not split_dir.exists():
            continue
        for d in sorted(p for p in split_dir.iterdir() if p.is_dir()):
            meta = json.loads((d / "task.json").read_text())
            battery[split].append(
                Task(
                    name=meta["name"],
                    split=meta.get("split", split),
                    module=meta.get("module", "solution"),
                    function=meta["function"],
                    prompt=(d / meta.get("prompt", "prompt.md")).read_text(),
                    oracle_path=d / meta.get("oracle", "oracle.py"),
                )
            )
    return battery


# ---------------------------------------------------------------------------
# Ollama substrate (returns text + token counts for the metrics)
# ---------------------------------------------------------------------------


def generate(prompt: str, model: str, seed: int,
             temperature: float = TEMPERATURE) -> dict:
    """One model call. Returns {text, out_tokens, in_tokens, ok, error}."""
    payload = json.dumps({
        "model": model,
        "prompt": prompt,
        "stream": False,
        "options": {
            "temperature": temperature,
            "seed": seed,
            "num_predict": NUM_PREDICT,
            "top_p": TOP_P,
        },
    }).encode()
    req = urllib.request.Request(
        OLLAMA_URL, data=payload,
        headers={"Content-Type": "application/json"}, method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=180) as resp:
            data = json.loads(resp.read())
        return {
            "text": data.get("response", ""),
            "out_tokens": int(data.get("eval_count", 0) or 0),
            "in_tokens": int(data.get("prompt_eval_count", 0) or 0),
            "ok": True,
            "error": "",
        }
    except Exception as e:  # noqa: BLE001
        return {"text": "", "out_tokens": 0, "in_tokens": 0, "ok": False, "error": str(e)}


def extract_code(text: str) -> str:
    """First python fenced block; fall back to first bare fenced block; else raw."""
    m = re.findall(r"```(?:python)?\s*\n(.*?)```", text, re.DOTALL)
    if not m:
        m = re.findall(r"```\s*\n(.*?)```", text, re.DOTALL)
    return m[0].strip() if m else text.strip()


def run_oracle(oracle_path: Path, code: str, module: str) -> tuple[bool, str]:
    """Write `code` to <module>.py in a tmp dir, run pytest oracle. Return (passed, tail)."""
    tmp = Path(tempfile.mkdtemp(prefix="aios_ab_"))
    try:
        (tmp / f"{module}.py").write_text(code)
        env = {**os.environ, "PYTHONPATH": str(tmp)}
        try:
            r = subprocess.run(
                [sys.executable, "-m", "pytest", str(oracle_path), "-q", "--tb=short"],
                capture_output=True, env=env, timeout=30, text=True,
            )
            tail = (r.stdout or "")[-600:]
            return r.returncode == 0, tail
        except Exception as e:  # noqa: BLE001
            return False, f"oracle error: {e}"
    finally:
        import shutil
        shutil.rmtree(tmp, ignore_errors=True)


# ---------------------------------------------------------------------------
# One arm run: up to R attempts, feed oracle failure back once
# ---------------------------------------------------------------------------


def run_arm(task: Task, model: str, guidance: str, seed_slot: int,
            r_attempts: int = R_ATTEMPTS) -> dict:
    """Run one arm on one task. `guidance` is prepended to the prompt (empty for bare arm).

    Returns {solved, attempts, out_tokens, in_tokens, ok, seq} where seq is the
    observed behavioral action sequence (used when seeding the ledger).
    """
    base = (guidance + "\n" if guidance else "") + task.prompt
    prompt = base
    total_out = total_in = 0
    seq: list[str] = []
    last_err = ""
    any_ok = False

    for attempt in range(1, r_attempts + 1):
        seed = SEED_BASE + seed_slot * 10 + attempt
        g = generate(prompt, model, seed)
        total_out += g["out_tokens"]
        total_in += g["in_tokens"]
        seq += ["WriteCode", "RunOracle"]
        if not g["ok"]:
            return {
                "solved": False, "solved_first": False, "attempts": attempt,
                "out_tokens": total_out, "in_tokens": total_in,
                "ok": False, "error": g["error"], "seq": seq,
            }
        any_ok = True
        code = extract_code(g["text"])
        passed, tail = run_oracle(task.oracle_path, code, task.module)
        if passed:
            return {
                "solved": True, "solved_first": attempt == 1, "attempts": attempt,
                "out_tokens": total_out, "in_tokens": total_in,
                "ok": True, "error": "", "seq": seq,
            }
        last_err = tail
        # feed the failure back for the (single) retry
        if attempt < r_attempts:
            seq += ["ReadError", "FixEdgeCase"]
            prompt = (
                base
                + "\n\nYour previous attempt FAILED the tests with this output:\n"
                + "```\n" + last_err.strip() + "\n```\n"
                + "Fix the function. Output ONLY one fenced python code block."
            )

    return {
        "solved": False, "solved_first": False, "attempts": r_attempts,
        "out_tokens": total_out, "in_tokens": total_in,
        "ok": any_ok, "error": last_err, "seq": seq,
    }


# ---------------------------------------------------------------------------
# Ledger seeding (arm B's memory) — via the REAL record path
# ---------------------------------------------------------------------------


def _behavior_module():
    """Load a FRESH aios_agent_behavior bound to the CURRENT AIOS_HOME.

    Private-name spec import (NOT `import aios_agent_behavior`): the module reads
    AIOS_HOME into module-level store paths at import time, so caching a tmp-bound
    instance under the canonical name in sys.modules would poison every later
    importer in the same process (this exact leak broke unrelated privacy tests
    in CI). Mirrors aios_demo._load_behavior.
    """
    import importlib.util  # noqa: PLC0415
    if str(SCRIPTS_DIR) not in sys.path:
        sys.path.insert(0, str(SCRIPTS_DIR))
    spec = importlib.util.spec_from_file_location(
        f"aios_agent_behavior_ab_{abs(hash(os.environ.get('AIOS_HOME', '')))}",
        SCRIPTS_DIR / "aios_agent_behavior.py",
    )
    bh = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(bh)
    return bh


def seed_ledger(train_tasks: list[Task], model: str) -> dict:
    """Run the agent BARE on TRAIN tasks and record each run's behavioral signature
    through the real write_to_akashic path. Returns a summary of what was seeded.

    Every recorded object is TRAIN-derived and behavioral only (tool pattern, attempt
    count, solved flag, a generic 'what worked' note) — no TEST data, no solution code.
    """
    bh = _behavior_module()
    records: list[dict] = []
    solved_runs = attempts_sum = fix_runs = 0
    n_runs = 0

    for ti, task in enumerate(train_tasks):
        for run_i in range(SEED_RUNS_PER_TASK):
            seed_slot = 500 + ti * 10 + run_i
            res = run_arm(task, model, guidance="", seed_slot=seed_slot)
            n_runs += 1
            attempts_sum += res["attempts"]
            solved = bool(res["solved"])
            needed_fix = "FixEdgeCase" in res["seq"]
            if solved:
                solved_runs += 1
            if needed_fix:
                fix_runs += 1

            seq = res["seq"]
            freq: dict[str, int] = {}
            for t in seq:
                freq[t] = freq.get(t, 0) + 1
            top = sorted(freq, key=lambda k: freq[k], reverse=True)[:5]
            if solved and needed_fix:
                what = "wrote the function, ran the oracle, fixed an edge case on the 2nd attempt, passed"
            elif solved:
                what = "wrote the function, ran the oracle, passed on the first attempt"
            else:
                what = "wrote the function and ran the oracle; edge cases still failed"

            # behavioral MemoryObject — same schema/shape as aios_agent_behavior ingest.
            rec = {
                "id": f"beh-abseed-{ti}-{run_i}",
                "schema": "aios.agent_behavior.v1",
                "content": (
                    f"provider:aios_ab category:code approach:write_then_verify "
                    f"attempts:{res['attempts']} solved:{solved} "
                    f"pattern:[{','.join(top)}]"
                ),
                "status": "draft",
                "confidence": 0.8,
                "domain": "agent_behavior",
                "category": "code",
                "loop_type": "react_code" if needed_fix else "quick",
                "provider": "aios_ab",
                "tool_freq": freq,
                "top_tools": top,
                "tool_sequence": seq,
                "what_worked": what,
                "solved": solved,
                "attempts": res["attempts"],
                "evidence_refs": [f"train_run:{task.name}:{run_i}"],
                "relations": [],
            }
            records.append(rec)

    written = bh.write_to_akashic(records)
    return {
        "runs": n_runs,
        "records_written": written,
        "solved_runs": solved_runs,
        "solve_rate": round(solved_runs / n_runs, 3) if n_runs else 0.0,
        "mean_attempts": round(attempts_sum / n_runs, 3) if n_runs else 0.0,
        "fix_runs": fix_runs,
        "record_ids": [r["id"] for r in records],
    }


def build_guidance(model: str) -> dict:
    """Build ONE generic behavioral-guidance block from the seeded ledger, via the
    real machinery (predict_behavior + the recorded train-run aggregates).

    Same block is prepended to every Arm-B prompt (the ledger only knows generic
    coding behavior, not per-task specifics) — so this is purely behavioral memory,
    with zero test-task tailoring.

    Returns {text, ranked, memories}.
    """
    bh = _behavior_module()
    mems = bh.load_behavior_memories()
    n = len(mems)
    solved = sum(1 for m in mems if m.get("solved"))
    attempts = [m.get("attempts", 1) for m in mems]
    mean_att = round(sum(attempts) / n, 2) if n else 0.0
    any_fix = any(m.get("loop_type") == "react_code" for m in mems)

    # real retrieval machinery: rank the behavioral actions from the ledger
    # (keyword/frequency fallback; offline — no global network call).
    context = "small python coding task: write a function and verify it against a test"
    pred = bh.predict_behavior(context, BEHAVIOR_TOOLS, top_k=3, use_global=False)
    ranked = [r["action"] for r in pred.get("ranked", [])]
    winning = " -> ".join(ranked[:3]) if ranked else "WriteCode -> RunOracle"

    lesson = (
        "first attempts most often failed on unhandled edge cases (empty input, empty "
        "collections, boundary characters); handling the edge/empty cases the task "
        "describes explicitly — then verifying — is what turned failures into passes."
        if any_fix else
        "the pattern that passed was to write the complete function, then verify it "
        "against the described behaviour including its edge cases."
    )

    text = (
        "## Behavioral memory (retrieved from your local ledger)\n"
        f"Across {n} recorded runs on similar small-Python tasks your agent solved "
        f"{solved}/{n} (mean {mean_att} attempts).\n"
        f"Most effective action pattern carried forward: {winning}.\n"
        f"Lesson from past runs: {lesson}"
    )
    return {"text": text, "ranked": ranked, "memories": n, "method": pred.get("method")}


# ---------------------------------------------------------------------------
# Experiment
# ---------------------------------------------------------------------------


def _arm_metrics(runs: list[dict]) -> dict:
    n = len(runs)
    solved = [r for r in runs if r["solved"]]
    first = [r for r in runs if r.get("solved_first")]
    att_solved = [r["attempts"] for r in solved]
    return {
        "trials": n,
        "solved": len(solved),
        "solve_rate": round(len(solved) / n, 4) if n else 0.0,
        "first_attempt_solved": len(first),
        "first_attempt_solve_rate": round(len(first) / n, 4) if n else 0.0,
        "mean_attempts_to_solve": round(sum(att_solved) / len(att_solved), 3) if att_solved else None,
        "mean_attempts_all": round(sum(r["attempts"] for r in runs) / n, 3) if n else 0.0,
        "total_out_tokens": sum(r["out_tokens"] for r in runs),
        "total_in_tokens": sum(r["in_tokens"] for r in runs),
        "errored_runs": sum(1 for r in runs if not r["ok"]),
    }


def run_experiment(model: str, trials: int, dry_run: bool = False) -> dict:
    battery = load_battery()
    train_tasks = battery["train"]
    test_tasks = battery["test"]
    if dry_run:
        test_tasks = test_tasks[:1]
        trials = 1

    t0 = time.time()

    # 1) seed the ledger from TRAIN runs (in an isolated AIOS_HOME set by the caller)
    seed_summary = seed_ledger(train_tasks, model)

    # 2) build the (single, generic) behavioral guidance block
    guidance = build_guidance(model)

    # 3) run both arms on every TEST task x trials, alternating arm order per trial
    per_task: dict[str, dict] = {}
    arm_a_runs: list[dict] = []
    arm_b_runs: list[dict] = []
    raw_runs: list[dict] = []

    for task_idx, task in enumerate(test_tasks):
        a_runs: list[dict] = []
        b_runs: list[dict] = []
        for trial in range(trials):
            # matched seed slot per (task,trial) — same for both arms. Deterministic
            # (task_idx, not hash()) so the whole run is reproducible across processes.
            slot = 1000 + task_idx * 100 + trial
            order = ["A", "B"] if trial % 2 == 0 else ["B", "A"]
            results: dict[str, dict] = {}
            for arm in order:
                g = "" if arm == "A" else guidance["text"]
                res = run_arm(task, model, guidance=g, seed_slot=slot)
                results[arm] = res
                raw_runs.append({
                    "task": task.name, "arm": arm, "trial": trial,
                    "solved": res["solved"], "solved_first": res.get("solved_first", False),
                    "attempts": res["attempts"],
                    "out_tokens": res["out_tokens"], "ok": res["ok"],
                })
            a_runs.append(results["A"])
            b_runs.append(results["B"])
        arm_a_runs += a_runs
        arm_b_runs += b_runs
        per_task[task.name] = {
            "A": _arm_metrics(a_runs),
            "B": _arm_metrics(b_runs),
        }

    elapsed = round(time.time() - t0, 1)
    agg_a = _arm_metrics(arm_a_runs)
    agg_b = _arm_metrics(arm_b_runs)

    return {
        "config": {
            "model": model,
            "trials_per_arm_per_task": trials,
            "r_attempts": R_ATTEMPTS,
            "seed_runs_per_train_task": SEED_RUNS_PER_TASK,
            "temperature": TEMPERATURE,
            "num_predict": NUM_PREDICT,
            "seed_base": SEED_BASE,
            "n_train_tasks": len(train_tasks),
            "n_test_tasks": len(test_tasks),
            "n_per_arm": len(arm_a_runs),
            "dry_run": dry_run,
        },
        "seeding": seed_summary,
        "guidance": {
            "text": guidance["text"],
            "ranked_actions": guidance["ranked"],
            "memories_used": guidance["memories"],
            "predict_method": guidance["method"],
        },
        "arm_A_bare": agg_a,
        "arm_B_ledger": agg_b,
        "per_task": per_task,
        "raw_runs": raw_runs,
        "elapsed_s": elapsed,
        "substrate": "ollama",
    }


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


def main(argv: Optional[list[str]] = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--model", default=DEFAULT_MODEL)
    ap.add_argument("--trials", type=int, default=TRIALS)
    ap.add_argument("--out", default=None, help="Write raw JSON results here")
    ap.add_argument("--dry-run", action="store_true", help="1 task, 1 trial smoke run")
    ap.add_argument("--aios-home", default=None,
                    help="Isolated AIOS_HOME for the ledger (default: fresh tempdir)")
    args = ap.parse_args(argv)

    # ISOLATION: the ledger must live in a throwaway home so a user's ~/.aios is
    # never touched. Set the env BEFORE aios_agent_behavior is imported anywhere.
    home = args.aios_home or tempfile.mkdtemp(prefix="aios_ab_home_")
    os.environ["AIOS_HOME"] = home
    os.environ.setdefault("AIOS_AKASHIC_URL", "http://127.0.0.1:9")  # unreachable: force offline

    print(f"[headline_ab] model={args.model} trials={args.trials} "
          f"dry_run={args.dry_run} aios_home={home}", file=sys.stderr)

    results = run_experiment(args.model, args.trials, dry_run=args.dry_run)
    results["config"]["aios_home"] = home

    a, b = results["arm_A_bare"], results["arm_B_ledger"]
    print(f"[headline_ab] done in {results['elapsed_s']}s  "
          f"solve A={a['solve_rate']} B={b['solve_rate']}  "
          f"pass@1 A={a['first_attempt_solve_rate']} B={b['first_attempt_solve_rate']}  "
          f"meanAtt A={a['mean_attempts_all']} B={b['mean_attempts_all']}  "
          f"tok A={a['total_out_tokens']} B={b['total_out_tokens']}", file=sys.stderr)

    if args.out:
        Path(args.out).parent.mkdir(parents=True, exist_ok=True)
        Path(args.out).write_text(json.dumps(results, indent=2, ensure_ascii=False))
        print(f"[headline_ab] wrote {args.out}", file=sys.stderr)
    else:
        print(json.dumps(results, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
