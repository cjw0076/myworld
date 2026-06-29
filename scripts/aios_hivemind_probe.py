#!/usr/bin/env python3
"""
AIOS Hivemind v0 — smallest honest falsification probe.

The hivemind is the coordination/verify/compose layer; the agent is a pluggable
substrate — any product's agent attaches via an AgentAdapter.  The same experiment
(ARM A vs ARM B) runs unchanged on any agent that exposes a generate(prompt) method.

Tests ONE thesis: does pooled+verified (ARM B) beat a single agent (ARM A) on a coding
Quest, under EQUAL compute, with a REAL machine oracle for both leaves and the whole?

Measures:
  solve_rate_A            — fraction of trials ARM A solved (parent oracle passed)
  solve_rate_B            — fraction of trials ARM B solved (parent oracle passed)
  composition_gap_rate_B  — fraction of trials where ALL leaf oracles passed AND the
                            parent oracle FAILED (the gap the thesis cares about)

Each call to solve(adapter, prompt, 1) is ONE compute unit. Budget N is respected exactly:
  ARM A: up to N calls total (stops early on success).
  ARM B: k leaves x floor(N/k) calls each = floor(N/k)*k <= N calls total.

Plugging in a different agent (env vars — all optional):
  AIOS_PROBE_AGENT     - "ollama" (default) | "openai"
  AIOS_PROBE_BASE_URL  - base URL for openai adapter (e.g. http://localhost:8000)
  AIOS_PROBE_MODEL     - model name (default: qwen3-coder:30b)
  AIOS_PROBE_API_KEY   - API key (optional; for OpenAI / Claude-compatible endpoints)

Examples:
    # default (qwen3-coder:30b via local ollama)
    python3 scripts/aios_hivemind_probe.py --task coding_iface --budget 6 --trials 5

    # vLLM server running Llama-3
    AIOS_PROBE_AGENT=openai AIOS_PROBE_BASE_URL=http://localhost:8000 \\
    AIOS_PROBE_MODEL=meta-llama/Llama-3.1-70B-Instruct \\
    python3 scripts/aios_hivemind_probe.py --task coding_iface

    # OpenAI cloud
    AIOS_PROBE_AGENT=openai AIOS_PROBE_BASE_URL=https://api.openai.com \\
    AIOS_PROBE_MODEL=gpt-4o AIOS_PROBE_API_KEY=sk-... \\
    python3 scripts/aios_hivemind_probe.py --task coding_iface

    # quick model override (ollama)
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
from typing import Protocol, runtime_checkable

# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------

OLLAMA_URL = "http://localhost:11434/api/generate"
DEFAULT_MODEL = os.environ.get("AIOS_PROBE_MODEL", "qwen3-coder:30b")
TASK_ROOT = Path(__file__).resolve().parent.parent / "tests" / "hivemind_tasks"

# ---------------------------------------------------------------------------
# AgentAdapter — pluggable agent substrate
# ---------------------------------------------------------------------------


@runtime_checkable
class AgentAdapter(Protocol):
    """Pluggable agent substrate interface.

    Any product agent attaches to the hivemind probe by implementing this
    single method.  The hivemind (ARM A / ARM B / run_probe) is agnostic to
    the underlying model, provider, or product — it only calls generate().
    """

    def generate(self, prompt: str) -> str:
        """Send prompt to the agent; return the response text (empty on failure)."""
        ...


class OllamaAdapter:
    """Agent substrate: local model via ollama HTTP API (http://localhost:11434)."""

    def __init__(self, model: str = DEFAULT_MODEL, url: str = OLLAMA_URL) -> None:
        self.model = model
        self.url = url

    def generate(self, prompt: str) -> str:
        import urllib.request

        payload = json.dumps(
            {"model": self.model, "prompt": prompt, "stream": False}
        ).encode()
        req = urllib.request.Request(
            self.url,
            data=payload,
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        with urllib.request.urlopen(req, timeout=120) as resp:
            data = json.loads(resp.read())
            return data.get("response", "")


class OpenAICompatAdapter:
    """Agent substrate: any OpenAI-compatible chat API.

    Works for: vLLM, LM Studio, OpenAI, Anthropic-via-proxy, or any product
    agent that exposes a POST /v1/chat/completions endpoint.

    Example — plug in a vLLM server:
        AIOS_PROBE_AGENT=openai AIOS_PROBE_BASE_URL=http://localhost:8000
        AIOS_PROBE_MODEL=meta-llama/Llama-3.1-70B-Instruct
    """

    def __init__(
        self,
        base_url: str,
        model: str,
        api_key: Optional[str] = None,
    ) -> None:
        self.base_url = base_url.rstrip("/")
        self.model = model
        self.api_key = api_key

    def generate(self, prompt: str) -> str:
        import urllib.request

        headers: dict = {"Content-Type": "application/json"}
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"
        payload = json.dumps(
            {
                "model": self.model,
                "messages": [{"role": "user", "content": prompt}],
            }
        ).encode()
        req = urllib.request.Request(
            f"{self.base_url}/v1/chat/completions",
            data=payload,
            headers=headers,
            method="POST",
        )
        with urllib.request.urlopen(req, timeout=120) as resp:
            data = json.loads(resp.read())
            return data["choices"][0]["message"]["content"]


def _default_adapter() -> AgentAdapter:
    """Create an adapter from env vars (all optional; defaults to OllamaAdapter).

    AIOS_PROBE_AGENT     - "ollama" (default) | "openai"
    AIOS_PROBE_BASE_URL  - base URL for openai adapter
    AIOS_PROBE_MODEL     - model name (default: qwen3-coder:30b)
    AIOS_PROBE_API_KEY   - API key (optional)
    """
    agent_type = os.environ.get("AIOS_PROBE_AGENT", "ollama")
    model = os.environ.get("AIOS_PROBE_MODEL", "qwen3-coder:30b")
    if agent_type == "openai":
        base_url = os.environ.get("AIOS_PROBE_BASE_URL", "http://localhost:8080")
        api_key = os.environ.get("AIOS_PROBE_API_KEY") or None
        return OpenAICompatAdapter(base_url=base_url, model=model, api_key=api_key)
    return OllamaAdapter(model=model)


def solve(adapter: AgentAdapter, prompt: str, attempts: int) -> str:
    """Call adapter.generate(prompt) up to `attempts` times (each = one compute unit).

    Returns the first non-empty response text, or empty string if all fail.
    The `attempts` parameter allows callers to pass 1 for fine-grained
    oracle-checked retry in run_arm_a / run_arm_b.
    """
    last = ""
    for _ in range(attempts):
        try:
            text = adapter.generate(prompt)
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
    adapter: Optional[AgentAdapter] = None,
) -> dict:
    """ARM A: one agent, up to `budget` compute units on the whole task.

    Each iteration calls solve_fn(whole_prompt, 1) — one compute unit — writes the
    produced artifacts to a tmpdir, and checks the parent oracle. Stops on first pass.

    Pass `adapter` to attach any AgentAdapter substrate (OllamaAdapter,
    OpenAICompatAdapter, or a custom product agent).  Pass `solve_fn` to inject
    a mock callable (str, int) -> str for tests.  `solve_fn` takes precedence.

    Returns {"solved": bool, "attempts": int}.
    """
    if solve_fn is not None:
        _solve = solve_fn
    else:
        _adapter = adapter if adapter is not None else _default_adapter()
        _solve = lambda p, n: solve(_adapter, p, n)
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
    adapter: Optional[AgentAdapter] = None,
) -> dict:
    """ARM B: budget split across k leaves; each leaf oracle-checked per attempt.

    Equal-budget accounting:
      leaf_budget = budget // k  (floor division)
      total compute = k * leaf_budget = k * floor(budget / k) <= budget

    After all leaves, compose artifacts into a single dir and run the parent oracle.

    composition_gap is True iff all leaf oracles passed AND parent oracle failed.
    This is the signal the thesis cares about: verified leaves that fail to compose.

    Pass `adapter` to attach any AgentAdapter substrate.  Pass `solve_fn` for
    test injection.  `solve_fn` takes precedence over `adapter`.

    Returns {"solved": bool, "all_leaves_passed": bool, "composition_gap": bool}.
    """
    if solve_fn is not None:
        _solve = solve_fn
    else:
        _adapter = adapter if adapter is not None else _default_adapter()
        _solve = lambda p, n: solve(_adapter, p, n)
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
    adapter: Optional[AgentAdapter] = None,
) -> dict:
    """Run both arms `trials` times under equal budget; return aggregate metrics.

    Pass `adapter` to run the same experiment on any AgentAdapter substrate.
    Pass `solve_fn` to inject a mock callable for tests; it takes precedence.

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
        ra = run_arm_a(task, budget, solve_fn=solve_fn, parent_oracle=parent_oracle, adapter=adapter)
        rb = run_arm_b(
            task,
            budget,
            solve_fn=solve_fn,
            parent_oracle=parent_oracle,
            leaf_oracle_factory=leaf_oracle_factory,
            adapter=adapter,
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

    _adapter = _default_adapter()
    task = load_task(args.task)
    k = len(task.leaves)
    agent_label = (
        f"openai:{_adapter.base_url}/{_adapter.model}"
        if isinstance(_adapter, OpenAICompatAdapter)
        else f"ollama:{_adapter.model}"
    )
    print(
        f"probe: task={args.task} budget={args.budget} trials={args.trials} "
        f"agent={agent_label} leaves={[l.name for l in task.leaves]}"
    )
    print(
        f"budget split: ARM A <= {args.budget} total | "
        f"ARM B {k} leaves x {args.budget // k} each = {k * (args.budget // k)} total"
    )

    results = run_probe(task, args.budget, args.trials, adapter=_adapter)
    print(json.dumps(results, indent=2))
