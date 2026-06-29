#!/usr/bin/env python3
"""
AIOS Hivemind v0 — smallest honest falsification probe.

Tests ONE thesis: does pooled+verified (ARM B) beat a single agent (ARM A) on a coding
Quest, under EQUAL compute, with a REAL machine oracle for both leaves and the whole?

Measures:
  solve_rate_A            — fraction of trials ARM A solved (parent oracle passed)
  solve_rate_B            — fraction of trials ARM B solved (parent oracle passed)
  composition_gap_rate_B  — fraction of trials where ALL leaf oracles passed AND the
                            parent oracle FAILED (the gap the thesis cares about)

Each call to solve_fn(prompt, 1) is ONE compute unit. Budget N is respected exactly:
  ARM A: up to N calls total (stops early on success).
  ARM B: k leaves x floor(N/k) calls each = floor(N/k)*k <= N calls total.

Usage:
    python3 scripts/aios_hivemind_probe.py --task coding_iface --budget 6 --trials 5
    AIOS_PROBE_MODEL=qwen3-coder:7b python3 scripts/aios_hivemind_probe.py --task coding_iface
"""

from __future__ import annotations

import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Callable, List, NamedTuple, Optional

# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------

OLLAMA_URL = "http://localhost:11434/api/generate"
DEFAULT_MODEL = os.environ.get("AIOS_PROBE_MODEL", "qwen3-coder:30b")
TASK_ROOT = Path(__file__).resolve().parent.parent / "tests" / "hivemind_tasks"

# ---------------------------------------------------------------------------
# Agent substrate — local model via ollama HTTP
# ---------------------------------------------------------------------------


def solve(prompt: str, attempts: int, model: str = DEFAULT_MODEL) -> str:
    """Call the local model up to `attempts` times (each = one compute unit).

    Returns the first non-empty response text, or empty string if all fail.
    The `attempts` parameter is intentionally exposed so callers can use it
    directly for one-shot multi-retry without an external loop, or pass 1 for
    fine-grained oracle-checked retry in run_arm_a / run_arm_b.
    """
    import urllib.request

    last = ""
    for _ in range(attempts):
        payload = json.dumps(
            {"model": model, "prompt": prompt, "stream": False}
        ).encode()
        try:
            req = urllib.request.Request(
                OLLAMA_URL,
                data=payload,
                headers={"Content-Type": "application/json"},
                method="POST",
            )
            with urllib.request.urlopen(req, timeout=120) as resp:
                data = json.loads(resp.read())
                text = data.get("response", "")
                if text:
                    last = text
                    return last
        except Exception:
            continue
    return last


# ---------------------------------------------------------------------------
# Oracle — pluggable callable: oracle(artifact_dir: Path) -> bool
# ---------------------------------------------------------------------------

OracleFn = Callable[[Path], bool]


def pytest_oracle(test_path: Path) -> OracleFn:
    """Return an oracle that runs pytest on test_path with artifact_dir in PYTHONPATH.

    The PYTHONPATH injection is how the test file's bare `from producer import get_data`
    resolves to the generated artifact in artifact_dir rather than any installed module.
    """

    def _oracle(artifact_dir: Path) -> bool:
        env = {**os.environ, "PYTHONPATH": str(artifact_dir)}
        result = subprocess.run(
            [sys.executable, "-m", "pytest", str(test_path), "-q", "--tb=no"],
            capture_output=True,
            env=env,
            timeout=30,
        )
        return result.returncode == 0

    return _oracle


def lean_oracle(lean_file: Path) -> OracleFn:
    """Return an oracle that runs lean on a .lean file found in artifact_dir.

    Checks artifact_dir / lean_file.name first (the model's generated .lean file).
    Falls back to running lean_file itself when no generated file exists in
    artifact_dir — this handles static composition-gap checks (e.g. parent_compose.lean)
    where the oracle file never lands in the artifact directory.

    Returns True iff lean exits with code 0 (proof accepted by Lean 4).
    Mirrors pytest_oracle's signature and structure.
    """
    _lean_bin = Path.home() / ".elan" / "bin" / "lean"

    def _oracle(artifact_dir: Path) -> bool:
        generated = artifact_dir / lean_file.name
        check = generated if generated.exists() else lean_file
        env = {
            **os.environ,
            "PATH": str(_lean_bin.parent) + ":" + os.environ.get("PATH", ""),
        }
        result = subprocess.run(
            [str(_lean_bin), str(check)],
            capture_output=True,
            env=env,
            timeout=60,
        )
        return result.returncode == 0

    return _oracle


# ---------------------------------------------------------------------------
# Task spec
# ---------------------------------------------------------------------------


class LeafSpec(NamedTuple):
    name: str
    prompt: str
    test_path: Path


class TaskSpec(NamedTuple):
    name: str
    whole_prompt: str
    leaves: List[LeafSpec]
    parent_test: Path
    oracle_type: str = "pytest"  # "pytest" | "lean"


def load_task(task_name: str) -> TaskSpec:
    """Load a TaskSpec from tests/hivemind_tasks/<task_name>/.

    Reads optional "oracle" field from task.json ("pytest" | "lean"; default "pytest")
    and sets oracle_type on the returned TaskSpec so run_arm_a / run_arm_b can select
    the correct oracle factory without additional configuration.
    """
    task_dir = TASK_ROOT / task_name
    whole_prompt = (task_dir / "prompts" / "whole.txt").read_text()
    meta = json.loads((task_dir / "task.json").read_text())
    oracle_type = meta.get("oracle", "pytest")

    leaves: List[LeafSpec] = []
    for leaf in meta["leaves"]:
        prompt = (task_dir / "prompts" / leaf["prompt_file"]).read_text()
        test_path = task_dir / "tests" / leaf["test_file"]
        leaves.append(LeafSpec(name=leaf["name"], prompt=prompt, test_path=test_path))

    parent_test = task_dir / "tests" / meta["parent_test"]
    return TaskSpec(
        name=task_name,
        whole_prompt=whole_prompt,
        leaves=leaves,
        parent_test=parent_test,
        oracle_type=oracle_type,
    )


# ---------------------------------------------------------------------------
# Artifact helpers
# ---------------------------------------------------------------------------


def _extract_code(text: str) -> str:
    """Extract the first Python fenced code block; fall back to raw text."""
    matches = re.findall(r"```(?:python)?\n(.*?)```", text, re.DOTALL)
    return matches[0].strip() if matches else text.strip()


def _extract_lean_code(text: str) -> str:
    """Extract the first Lean fenced code block; fall back to raw text."""
    matches = re.findall(r"```(?:lean4?)\n(.*?)```", text, re.DOTALL)
    if not matches:
        matches = re.findall(r"```\n(.*?)```", text, re.DOTALL)
    return matches[0].strip() if matches else text.strip()


def _parse_whole_output(text: str, leaf_names: List[str]) -> dict:
    """Parse whole-task model output into {leaf_name: code_str}.

    Strategy (in order):
    1. Look for a labeled block: # {name}.py ...```python...```
    2. Fall back to unlabeled fenced blocks assigned in leaf order.
    3. Fill missing names with empty string.
    """
    result: dict = {}

    # Pass 1: labeled blocks
    for name in leaf_names:
        pattern = rf"#\s*{re.escape(name)}\.py.*?```(?:python)?\n(.*?)```"
        m = re.search(pattern, text, re.DOTALL | re.IGNORECASE)
        if m:
            result[name] = m.group(1).strip()

    # Pass 2: unlabeled blocks for anything still missing
    if len(result) < len(leaf_names):
        blocks = re.findall(r"```(?:python)?\n(.*?)```", text, re.DOTALL)
        unlabeled_idx = 0
        for name in leaf_names:
            if name not in result and unlabeled_idx < len(blocks):
                result[name] = blocks[unlabeled_idx].strip()
                unlabeled_idx += 1

    # Pass 3: empty string for any still-missing name
    for name in leaf_names:
        result.setdefault(name, "")

    return result


# ---------------------------------------------------------------------------
# ARM A — single agent on the whole task
# ---------------------------------------------------------------------------


def run_arm_a(
    task: TaskSpec,
    budget: int,
    solve_fn: Optional[Callable] = None,
    parent_oracle: Optional[OracleFn] = None,
) -> dict:
    """ARM A: one agent, up to `budget` compute units on the whole task.

    Each iteration calls solve_fn(whole_prompt, 1) — one compute unit — writes the
    produced artifacts to a tmpdir, and checks the parent oracle. Stops on first pass.

    Returns {"solved": bool, "attempts": int}.
    """
    _solve = solve_fn or solve
    _oracle = parent_oracle or (
        lean_oracle(task.parent_test) if task.oracle_type == "lean"
        else pytest_oracle(task.parent_test)
    )
    leaf_names = [leaf.name for leaf in task.leaves]

    tmpdir = Path(tempfile.mkdtemp(prefix="aios_a_"))
    try:
        for attempt in range(1, budget + 1):
            text = _solve(task.whole_prompt, 1)
            if task.oracle_type == "lean":
                code = _extract_lean_code(text)
                for name in leaf_names:
                    (tmpdir / f"{name}.lean").write_text(code)
            else:
                modules = _parse_whole_output(text, leaf_names)
                for name, code in modules.items():
                    (tmpdir / f"{name}.py").write_text(code)
            if _oracle(tmpdir):
                return {"solved": True, "attempts": attempt}
        return {"solved": False, "attempts": budget}
    finally:
        shutil.rmtree(tmpdir, ignore_errors=True)


# ---------------------------------------------------------------------------
# ARM B — pooled + verified (hand-decomposed leaves)
# ---------------------------------------------------------------------------


def run_arm_b(
    task: TaskSpec,
    budget: int,
    solve_fn: Optional[Callable] = None,
    parent_oracle: Optional[OracleFn] = None,
    leaf_oracle_factory: Optional[Callable[[LeafSpec], OracleFn]] = None,
) -> dict:
    """ARM B: budget split across k leaves; each leaf oracle-checked per attempt.

    Equal-budget accounting:
      leaf_budget = budget // k  (floor division)
      total compute = k * leaf_budget = k * floor(budget / k) <= budget

    After all leaves, compose artifacts into a single dir and run the parent oracle.

    composition_gap is True iff all leaf oracles passed AND parent oracle failed.
    This is the signal the thesis cares about: verified leaves that fail to compose.

    Returns {"solved": bool, "all_leaves_passed": bool, "composition_gap": bool}.
    """
    _solve = solve_fn or solve
    _parent_oracle = parent_oracle or (
        lean_oracle(task.parent_test) if task.oracle_type == "lean"
        else pytest_oracle(task.parent_test)
    )
    _leaf_oracle_factory = leaf_oracle_factory or (
        (lambda leaf: lean_oracle(leaf.test_path)) if task.oracle_type == "lean"
        else (lambda leaf: pytest_oracle(leaf.test_path))
    )

    k = len(task.leaves)
    leaf_budget = budget // k  # compute units per leaf; total = k * leaf_budget <= budget

    tmpdir = Path(tempfile.mkdtemp(prefix="aios_b_"))
    try:
        leaf_passed: dict = {}
        leaf_artifacts: dict = {}

        for leaf in task.leaves:
            oracle = _leaf_oracle_factory(leaf)
            leaf_dir = tmpdir / leaf.name
            leaf_dir.mkdir(exist_ok=True)
            best_code = ""
            passed = False

            for _ in range(leaf_budget):
                text = _solve(leaf.prompt, 1)
                if task.oracle_type == "lean":
                    code = _extract_lean_code(text)
                    (leaf_dir / f"{leaf.name}.lean").write_text(code)
                else:
                    code = _extract_code(text)
                    (leaf_dir / f"{leaf.name}.py").write_text(code)
                if oracle(leaf_dir):
                    passed = True
                    best_code = code
                    break
                best_code = code  # keep last attempt even if it failed

            leaf_passed[leaf.name] = passed
            leaf_artifacts[leaf.name] = best_code

        all_leaves_passed = all(leaf_passed.values())

        # Compose: place all leaf artifacts in one directory for the parent oracle
        compose_dir = tmpdir / "_compose"
        compose_dir.mkdir(exist_ok=True)
        ext = ".lean" if task.oracle_type == "lean" else ".py"
        for leaf in task.leaves:
            (compose_dir / f"{leaf.name}{ext}").write_text(leaf_artifacts[leaf.name])

        parent_passed = _parent_oracle(compose_dir)
        composition_gap = all_leaves_passed and not parent_passed

        return {
            "solved": parent_passed,
            "all_leaves_passed": all_leaves_passed,
            "composition_gap": composition_gap,
        }
    finally:
        shutil.rmtree(tmpdir, ignore_errors=True)


# ---------------------------------------------------------------------------
# run_probe — main measurement function
# ---------------------------------------------------------------------------


def run_probe(
    task: TaskSpec,
    budget: int,
    trials: int,
    solve_fn: Optional[Callable] = None,
    parent_oracle: Optional[OracleFn] = None,
    leaf_oracle_factory: Optional[Callable[[LeafSpec], OracleFn]] = None,
) -> dict:
    """Run both arms `trials` times under equal budget; return aggregate metrics.

    Returns:
        solve_rate_A           float in [0, 1]
        solve_rate_B           float in [0, 1]
        composition_gap_rate_B float in [0, 1]
        trials                 int
        budget                 int
    """
    a_solved = 0
    b_solved = 0
    b_gap = 0

    for _ in range(trials):
        ra = run_arm_a(task, budget, solve_fn=solve_fn, parent_oracle=parent_oracle)
        rb = run_arm_b(
            task,
            budget,
            solve_fn=solve_fn,
            parent_oracle=parent_oracle,
            leaf_oracle_factory=leaf_oracle_factory,
        )
        if ra["solved"]:
            a_solved += 1
        if rb["solved"]:
            b_solved += 1
        if rb["composition_gap"]:
            b_gap += 1

    return {
        "solve_rate_A": a_solved / trials,
        "solve_rate_B": b_solved / trials,
        "composition_gap_rate_B": b_gap / trials,
        "trials": trials,
        "budget": budget,
    }


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(
        description="AIOS Hivemind v0 falsification probe",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    parser.add_argument("--task", default="coding_iface", help="Task name under tests/hivemind_tasks/")
    parser.add_argument("--budget", type=int, default=6, help="Total compute units N (default: 6)")
    parser.add_argument("--trials", type=int, default=5, help="Independent trial runs (default: 5)")
    parser.add_argument("--model", default=None, help=f"Ollama model override (default: {DEFAULT_MODEL})")
    args = parser.parse_args()

    if args.model:
        os.environ["AIOS_PROBE_MODEL"] = args.model

    task = load_task(args.task)
    k = len(task.leaves)
    print(
        f"probe: task={args.task} budget={args.budget} trials={args.trials} "
        f"model={DEFAULT_MODEL} leaves={[l.name for l in task.leaves]}"
    )
    print(
        f"budget split: ARM A <= {args.budget} total | "
        f"ARM B {k} leaves x {args.budget // k} each = {k * (args.budget // k)} total"
    )

    results = run_probe(task, args.budget, args.trials)
    print(json.dumps(results, indent=2))
