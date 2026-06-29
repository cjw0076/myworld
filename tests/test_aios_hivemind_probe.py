"""
Harness-logic tests for aios_hivemind_probe.py.

Uses MOCK agent + MOCK oracle — no qwen, no GPU, no network required.
Verifies:
  - Equal-budget accounting (ARM A vs ARM B)
  - Composition gap detection logic
  - Solve rate arithmetic over trials
"""

from __future__ import annotations

import importlib.util
import json
import os
import sys
import unittest
from pathlib import Path

# ---------------------------------------------------------------------------
# Load the probe module from scripts/ (mirrors the existing test import pattern)
# ---------------------------------------------------------------------------

REPO_ROOT = Path(__file__).resolve().parent.parent
SCRIPTS = REPO_ROOT / "scripts"
TASK_DIR = REPO_ROOT / "tests" / "hivemind_tasks" / "coding_iface"


def _load_probe():
    spec = importlib.util.spec_from_file_location(
        "aios_hivemind_probe_under_test",
        SCRIPTS / "aios_hivemind_probe.py",
    )
    m = importlib.util.module_from_spec(spec)
    sys.modules["aios_hivemind_probe_under_test"] = m
    if str(SCRIPTS) not in sys.path:
        sys.path.insert(0, str(SCRIPTS))
    spec.loader.exec_module(m)
    return m


_probe = _load_probe()

LeafSpec = _probe.LeafSpec
TaskSpec = _probe.TaskSpec
run_arm_a = _probe.run_arm_a
run_arm_b = _probe.run_arm_b
run_probe = _probe.run_probe


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _load_real_task() -> TaskSpec:
    """Load the coding_iface TaskSpec from the actual task directory."""
    meta = json.loads((TASK_DIR / "task.json").read_text())
    leaves = []
    for leaf in meta["leaves"]:
        prompt = (TASK_DIR / "prompts" / leaf["prompt_file"]).read_text()
        test_path = TASK_DIR / "tests" / leaf["test_file"]
        leaves.append(LeafSpec(name=leaf["name"], prompt=prompt, test_path=test_path))
    whole = (TASK_DIR / "prompts" / "whole.txt").read_text()
    parent_test = TASK_DIR / "tests" / meta["parent_test"]
    return TaskSpec(
        name="coding_iface",
        whole_prompt=whole,
        leaves=leaves,
        parent_test=parent_test,
    )


def _make_mock_task(k: int = 2) -> TaskSpec:
    """Build a minimal TaskSpec with k fake leaves; no files read."""
    leaves = [
        LeafSpec(name=f"mod{i}", prompt=f"write mod{i}", test_path=Path("/dev/null"))
        for i in range(k)
    ]
    return TaskSpec(
        name="mock",
        whole_prompt="write all modules",
        leaves=leaves,
        parent_test=Path("/dev/null"),
    )


class CallCounter:
    """Wraps a mock solve function and counts total compute units consumed."""

    def __init__(self, artifact: str = "def placeholder(): pass"):
        self.calls = 0
        self.artifact = artifact

    def __call__(self, prompt: str, attempts: int) -> str:
        self.calls += attempts
        return self.artifact

    def reset(self) -> None:
        self.calls = 0


def _always_pass(artifact_dir: Path) -> bool:
    return True


def _always_fail(artifact_dir: Path) -> bool:
    return False


# ---------------------------------------------------------------------------
# Task directory smoke test
# ---------------------------------------------------------------------------


class TestTaskDirectory(unittest.TestCase):
    """Verify the coding_iface task dir is well-formed."""

    def test_task_json_loads(self):
        meta = json.loads((TASK_DIR / "task.json").read_text())
        self.assertIn("leaves", meta)
        self.assertIn("parent_test", meta)
        self.assertEqual(len(meta["leaves"]), 2)

    def test_prompt_files_exist(self):
        for fname in ("whole.txt", "leaf_producer.txt", "leaf_consumer.txt"):
            self.assertTrue(
                (TASK_DIR / "prompts" / fname).exists(),
                f"Missing prompt file: {fname}",
            )

    def test_oracle_test_files_exist(self):
        for fname in ("test_producer.py", "test_consumer.py", "test_integration.py"):
            self.assertTrue(
                (TASK_DIR / "tests" / fname).exists(),
                f"Missing oracle test: {fname}",
            )

    def test_solution_files_exist(self):
        for fname in ("producer.py", "consumer.py"):
            self.assertTrue(
                (TASK_DIR / "solution" / fname).exists(),
                f"Missing solution file: {fname}",
            )

    def test_load_task_builds_correct_spec(self):
        task = _load_real_task()
        self.assertEqual(task.name, "coding_iface")
        self.assertEqual(len(task.leaves), 2)
        names = [l.name for l in task.leaves]
        self.assertIn("producer", names)
        self.assertIn("consumer", names)


# ---------------------------------------------------------------------------
# ARM A budget accounting
# ---------------------------------------------------------------------------


class TestArmABudget(unittest.TestCase):
    def test_uses_full_budget_when_oracle_always_fails(self):
        """ARM A must call solve_fn exactly N times when oracle never passes."""
        task = _make_mock_task()
        counter = CallCounter()
        N = 6

        run_arm_a(task, budget=N, solve_fn=counter, parent_oracle=_always_fail)

        self.assertEqual(
            counter.calls, N,
            f"ARM A should consume exactly {N} compute units; got {counter.calls}",
        )

    def test_stops_after_first_success(self):
        """ARM A stops immediately when oracle passes on the first attempt."""
        task = _make_mock_task()
        counter = CallCounter()

        run_arm_a(task, budget=6, solve_fn=counter, parent_oracle=_always_pass)

        self.assertEqual(
            counter.calls, 1,
            "ARM A should stop after the first successful oracle check",
        )

    def test_result_solved_true_on_pass(self):
        task = _make_mock_task()
        result = run_arm_a(
            task, budget=4, solve_fn=CallCounter(), parent_oracle=_always_pass
        )
        self.assertTrue(result["solved"])

    def test_result_solved_false_on_full_fail(self):
        task = _make_mock_task()
        result = run_arm_a(
            task, budget=4, solve_fn=CallCounter(), parent_oracle=_always_fail
        )
        self.assertFalse(result["solved"])


# ---------------------------------------------------------------------------
# ARM B budget accounting
# ---------------------------------------------------------------------------


class TestArmBBudget(unittest.TestCase):
    def test_total_compute_equals_k_times_floor_budget_over_k(self):
        """ARM B total = k * floor(N/k) which is <= N (equal when k divides N)."""
        task = _make_mock_task(k=2)
        counter = CallCounter()
        N = 6
        k = len(task.leaves)  # 2
        expected = k * (N // k)  # 2 * 3 = 6

        run_arm_b(
            task,
            budget=N,
            solve_fn=counter,
            parent_oracle=_always_fail,
            leaf_oracle_factory=lambda leaf: _always_fail,
        )

        self.assertEqual(
            counter.calls, expected,
            f"ARM B should use exactly {expected} compute units; got {counter.calls}",
        )
        self.assertLessEqual(counter.calls, N, "ARM B must not exceed budget N")

    def test_odd_budget_does_not_exceed_N(self):
        """With budget=5 and k=2: each leaf gets 2 units; total = 4 <= 5."""
        task = _make_mock_task(k=2)
        counter = CallCounter()
        N = 5
        k = 2
        expected = k * (N // k)  # 4

        run_arm_b(
            task,
            budget=N,
            solve_fn=counter,
            parent_oracle=_always_fail,
            leaf_oracle_factory=lambda leaf: _always_fail,
        )

        self.assertEqual(counter.calls, expected)
        self.assertLessEqual(counter.calls, N)

    def test_leaf_early_stop_reduces_total_compute(self):
        """Each leaf stops on its first success; with k=2 and always-pass: total = 2."""
        task = _make_mock_task(k=2)
        counter = CallCounter()
        N = 6
        k = len(task.leaves)

        run_arm_b(
            task,
            budget=N,
            solve_fn=counter,
            parent_oracle=_always_fail,
            leaf_oracle_factory=lambda leaf: _always_pass,  # every leaf passes immediately
        )

        self.assertEqual(
            counter.calls, k,
            f"Each leaf should stop after 1 successful call; expected {k} total",
        )

    def test_three_leaves_budget_split(self):
        """k=3, N=9: each leaf gets 3 units; total = 9."""
        task = _make_mock_task(k=3)
        counter = CallCounter()
        N = 9
        k = 3
        expected = k * (N // k)  # 9

        run_arm_b(
            task,
            budget=N,
            solve_fn=counter,
            parent_oracle=_always_fail,
            leaf_oracle_factory=lambda leaf: _always_fail,
        )

        self.assertEqual(counter.calls, expected)
        self.assertLessEqual(counter.calls, N)


# ---------------------------------------------------------------------------
# Composition gap detection
# ---------------------------------------------------------------------------


class TestCompositionGap(unittest.TestCase):
    def test_gap_detected_all_leaves_pass_parent_fails(self):
        """composition_gap = True when every leaf oracle passes AND parent fails."""
        task = _make_mock_task()
        result = run_arm_b(
            task,
            budget=6,
            solve_fn=CallCounter(),
            parent_oracle=_always_fail,
            leaf_oracle_factory=lambda leaf: _always_pass,
        )

        self.assertTrue(result["all_leaves_passed"])
        self.assertFalse(result["solved"])
        self.assertTrue(
            result["composition_gap"],
            "composition_gap must be True when all leaves pass and parent fails",
        )

    def test_no_gap_when_parent_also_passes(self):
        """composition_gap = False when parent passes (gap requires parent failure)."""
        task = _make_mock_task()
        result = run_arm_b(
            task,
            budget=6,
            solve_fn=CallCounter(),
            parent_oracle=_always_pass,
            leaf_oracle_factory=lambda leaf: _always_pass,
        )

        self.assertTrue(result["solved"])
        self.assertFalse(result["composition_gap"])

    def test_no_gap_when_a_leaf_fails(self):
        """composition_gap = False when at least one leaf oracle fails (not ALL leaves passed)."""
        task = _make_mock_task(k=2)
        leaves = list(task.leaves)

        def _first_passes_second_fails(leaf: LeafSpec):
            return _always_pass if leaf.name == leaves[0].name else _always_fail

        result = run_arm_b(
            task,
            budget=6,
            solve_fn=CallCounter(),
            parent_oracle=_always_fail,
            leaf_oracle_factory=_first_passes_second_fails,
        )

        self.assertFalse(result["all_leaves_passed"])
        self.assertFalse(
            result["composition_gap"],
            "composition_gap must be False when not all leaves passed",
        )

    def test_gap_is_exclusive_disjunction(self):
        """Enumerate all 4 (leaf_pass, parent_pass) combos and check gap logic."""
        task = _make_mock_task()
        cases = [
            # (all_leaves_pass, parent_pass, expected_gap)
            (True,  True,  False),
            (True,  False, True),
            (False, True,  False),
            (False, False, False),
        ]
        for leaves_pass, parent_pass, expected_gap in cases:
            with self.subTest(leaves_pass=leaves_pass, parent_pass=parent_pass):
                leaf_oracle = _always_pass if leaves_pass else _always_fail
                parent_oracle = _always_pass if parent_pass else _always_fail
                result = run_arm_b(
                    task,
                    budget=4,
                    solve_fn=CallCounter(),
                    parent_oracle=parent_oracle,
                    leaf_oracle_factory=lambda leaf, lo=leaf_oracle: lo,
                )
                self.assertEqual(result["composition_gap"], expected_gap)


# ---------------------------------------------------------------------------
# Solve rate arithmetic
# ---------------------------------------------------------------------------


class TestSolveRate(unittest.TestCase):
    def test_zero_when_always_fail(self):
        task = _make_mock_task()
        results = run_probe(
            task,
            budget=4,
            trials=3,
            solve_fn=CallCounter(),
            parent_oracle=_always_fail,
            leaf_oracle_factory=lambda leaf: _always_fail,
        )
        self.assertEqual(results["solve_rate_A"], 0.0)
        self.assertEqual(results["solve_rate_B"], 0.0)

    def test_one_when_always_pass(self):
        task = _make_mock_task()
        results = run_probe(
            task,
            budget=4,
            trials=3,
            solve_fn=CallCounter(),
            parent_oracle=_always_pass,
            leaf_oracle_factory=lambda leaf: _always_pass,
        )
        self.assertEqual(results["solve_rate_A"], 1.0)
        self.assertEqual(results["solve_rate_B"], 1.0)

    def test_composition_gap_rate_all_trials(self):
        """When leaves always pass and parent always fails, gap rate = 1.0."""
        task = _make_mock_task()
        TRIALS = 4
        results = run_probe(
            task,
            budget=4,
            trials=TRIALS,
            solve_fn=CallCounter(),
            parent_oracle=_always_fail,
            leaf_oracle_factory=lambda leaf: _always_pass,
        )
        self.assertEqual(results["composition_gap_rate_B"], 1.0)
        self.assertEqual(results["solve_rate_B"], 0.0)

    def test_composition_gap_rate_no_trials(self):
        """When leaves fail, gap rate = 0.0 (gap requires all-leaves-passed)."""
        task = _make_mock_task()
        results = run_probe(
            task,
            budget=4,
            trials=3,
            solve_fn=CallCounter(),
            parent_oracle=_always_fail,
            leaf_oracle_factory=lambda leaf: _always_fail,
        )
        self.assertEqual(results["composition_gap_rate_B"], 0.0)

    def test_metadata_fields_present(self):
        task = _make_mock_task()
        results = run_probe(
            task,
            budget=4,
            trials=2,
            solve_fn=CallCounter(),
            parent_oracle=_always_fail,
            leaf_oracle_factory=lambda leaf: _always_fail,
        )
        for key in ("solve_rate_A", "solve_rate_B", "composition_gap_rate_B", "trials", "budget"):
            self.assertIn(key, results, f"Missing key: {key}")
        self.assertEqual(results["trials"], 2)
        self.assertEqual(results["budget"], 4)

    def test_rates_are_fractions(self):
        """Rates must be floats in [0.0, 1.0]."""
        task = _make_mock_task()
        results = run_probe(
            task,
            budget=4,
            trials=3,
            solve_fn=CallCounter(),
            parent_oracle=_always_fail,
            leaf_oracle_factory=lambda leaf: _always_fail,
        )
        for key in ("solve_rate_A", "solve_rate_B", "composition_gap_rate_B"):
            v = results[key]
            self.assertIsInstance(v, float, f"{key} must be float")
            self.assertGreaterEqual(v, 0.0)
            self.assertLessEqual(v, 1.0)


# ---------------------------------------------------------------------------
# Reference solution oracle smoke test (uses real pytest subprocess)
# ---------------------------------------------------------------------------


class TestReferenceSolution(unittest.TestCase):
    """Run real pytest oracle on the reference solution files to verify the task is set up correctly."""

    def setUp(self):
        self.task = _load_real_task()
        self.solution_dir = TASK_DIR / "solution"

    def test_producer_leaf_oracle_passes_on_reference(self):
        """Reference producer.py must pass the producer leaf oracle."""
        from scripts.aios_hivemind_probe import pytest_oracle  # noqa: F401 — direct import for clarity

        _probe_mod = importlib.import_module("aios_hivemind_probe_under_test")
        oracle = _probe_mod.pytest_oracle(
            TASK_DIR / "tests" / "test_producer.py"
        )
        self.assertTrue(
            oracle(self.solution_dir),
            "Reference producer.py should pass test_producer.py",
        )

    def test_consumer_leaf_oracle_passes_on_reference(self):
        _probe_mod = importlib.import_module("aios_hivemind_probe_under_test")
        oracle = _probe_mod.pytest_oracle(
            TASK_DIR / "tests" / "test_consumer.py"
        )
        self.assertTrue(
            oracle(self.solution_dir),
            "Reference consumer.py should pass test_consumer.py",
        )

    def test_integration_oracle_passes_on_reference(self):
        _probe_mod = importlib.import_module("aios_hivemind_probe_under_test")
        oracle = _probe_mod.pytest_oracle(
            TASK_DIR / "tests" / "test_integration.py"
        )
        self.assertTrue(
            oracle(self.solution_dir),
            "Reference solution/ should pass test_integration.py",
        )

    def test_composition_gap_is_real_with_wrong_producer(self):
        """A producer returning {'amount': 42} passes the leaf oracle but breaks integration."""
        import tempfile
        import shutil

        _probe_mod = importlib.import_module("aios_hivemind_probe_under_test")
        leaf_oracle = _probe_mod.pytest_oracle(TASK_DIR / "tests" / "test_producer.py")
        parent_oracle = _probe_mod.pytest_oracle(TASK_DIR / "tests" / "test_integration.py")

        tmpdir = Path(tempfile.mkdtemp(prefix="aios_gap_test_"))
        try:
            # Wrong producer: uses key "amount" instead of "value"
            (tmpdir / "producer.py").write_text(
                'def get_data() -> dict:\n    return {"amount": 42}\n'
            )
            # Correct consumer (from reference)
            (tmpdir / "consumer.py").write_text(
                (self.solution_dir / "consumer.py").read_text()
            )

            self.assertTrue(
                leaf_oracle(tmpdir),
                "Leaf oracle must pass when producer returns {'amount': 42}",
            )
            self.assertFalse(
                parent_oracle(tmpdir),
                "Integration oracle must FAIL when producer returns 'amount' but consumer reads 'value'",
            )
        finally:
            shutil.rmtree(tmpdir, ignore_errors=True)


# ---------------------------------------------------------------------------
# Lean oracle selection and accounting (mock lean — no real lean in unit tests)
# ---------------------------------------------------------------------------

LEAN_TASK_DIR = REPO_ROOT / "tests" / "hivemind_tasks" / "lean_compose"


def _make_lean_mock_task(k: int = 2) -> TaskSpec:
    """Build a minimal lean TaskSpec with oracle_type='lean'."""
    leaves = [
        LeafSpec(name=f"p{i}", prompt=f"prove p{i}", test_path=Path("/dev/null"))
        for i in range(k)
    ]
    return TaskSpec(
        name="lean_mock",
        whole_prompt="prove T",
        leaves=leaves,
        parent_test=Path("/dev/null"),
        oracle_type="lean",
    )


class TestLeanTaskDirectory(unittest.TestCase):
    """Verify the lean_compose task directory is well-formed."""

    def test_task_json_loads_with_oracle_field(self):
        meta = json.loads((LEAN_TASK_DIR / "task.json").read_text())
        self.assertIn("leaves", meta)
        self.assertIn("parent_test", meta)
        self.assertEqual(meta.get("oracle"), "lean")
        self.assertEqual(len(meta["leaves"]), 2)

    def test_prompt_files_exist(self):
        for fname in ("whole.txt", "leaf_p0.txt", "leaf_p1.txt"):
            self.assertTrue(
                (LEAN_TASK_DIR / "prompts" / fname).exists(),
                f"Missing prompt file: {fname}",
            )

    def test_lean_oracle_files_exist(self):
        for fname in ("p0.lean", "p1.lean", "parent_compose.lean"):
            self.assertTrue(
                (LEAN_TASK_DIR / "tests" / fname).exists(),
                f"Missing oracle file: {fname}",
            )

    def test_solution_files_exist(self):
        for fname in ("p0.lean", "p1.lean", "t_direct.lean"):
            self.assertTrue(
                (LEAN_TASK_DIR / "solution" / fname).exists(),
                f"Missing solution file: {fname}",
            )

    def test_load_task_returns_lean_oracle_type(self):
        task = _probe.load_task("lean_compose")
        self.assertEqual(task.oracle_type, "lean")
        self.assertEqual(len(task.leaves), 2)
        names = [l.name for l in task.leaves]
        self.assertIn("p0", names)
        self.assertIn("p1", names)

    def test_load_task_leaf_test_paths_are_lean_files(self):
        task = _probe.load_task("lean_compose")
        for leaf in task.leaves:
            self.assertTrue(
                str(leaf.test_path).endswith(".lean"),
                f"Leaf {leaf.name} test_path should be a .lean file: {leaf.test_path}",
            )

    def test_parent_test_is_lean_file(self):
        task = _probe.load_task("lean_compose")
        self.assertTrue(
            str(task.parent_test).endswith(".lean"),
            f"parent_test should be a .lean file: {task.parent_test}",
        )


class TestLeanOracleSelection(unittest.TestCase):
    """Verify lean oracle is selected and accounting still works with mock lean oracle."""

    def test_default_task_spec_oracle_type_is_pytest(self):
        """TaskSpec without oracle_type defaults to 'pytest'."""
        task = _make_mock_task()
        self.assertEqual(task.oracle_type, "pytest")

    def test_lean_task_spec_oracle_type_is_lean(self):
        task = _make_lean_mock_task()
        self.assertEqual(task.oracle_type, "lean")

    def test_arm_a_lean_task_budget_accounting_with_mock_oracle(self):
        """Budget accounting is unchanged for lean tasks."""
        task = _make_lean_mock_task()
        counter = CallCounter()
        N = 4

        result = run_arm_a(
            task, budget=N, solve_fn=counter, parent_oracle=_always_fail
        )

        self.assertEqual(counter.calls, N)
        self.assertFalse(result["solved"])

    def test_arm_a_lean_task_stops_on_first_success(self):
        """ARM A stops after first mock-oracle success on a lean task."""
        task = _make_lean_mock_task()
        counter = CallCounter()

        result = run_arm_a(
            task, budget=6, solve_fn=counter, parent_oracle=_always_pass
        )

        self.assertEqual(counter.calls, 1)
        self.assertTrue(result["solved"])

    def test_arm_b_lean_composition_gap_with_mock_oracles(self):
        """Composition gap detected for lean task: all leaves pass, parent fails."""
        task = _make_lean_mock_task()

        result = run_arm_b(
            task,
            budget=6,
            solve_fn=CallCounter(),
            parent_oracle=_always_fail,
            leaf_oracle_factory=lambda leaf: _always_pass,
        )

        self.assertTrue(result["all_leaves_passed"])
        self.assertFalse(result["solved"])
        self.assertTrue(
            result["composition_gap"],
            "composition_gap must be True when lean leaves pass and parent fails",
        )

    def test_arm_b_lean_budget_split_with_mock_oracles(self):
        """k=2, N=6: each leaf gets 3 units, total=6; equal-budget rule holds for lean."""
        task = _make_lean_mock_task(k=2)
        counter = CallCounter()
        N = 6
        k = 2
        expected = k * (N // k)

        run_arm_b(
            task,
            budget=N,
            solve_fn=counter,
            parent_oracle=_always_fail,
            leaf_oracle_factory=lambda leaf: _always_fail,
        )

        self.assertEqual(counter.calls, expected)
        self.assertLessEqual(counter.calls, N)

    def test_run_probe_lean_task_gap_rate_with_mock_oracles(self):
        """gap_rate=1.0 when lean leaf mocks always pass and parent mock always fails."""
        task = _make_lean_mock_task()
        TRIALS = 3

        results = run_probe(
            task,
            budget=4,
            trials=TRIALS,
            solve_fn=CallCounter(),
            parent_oracle=_always_fail,
            leaf_oracle_factory=lambda leaf: _always_pass,
        )

        self.assertEqual(results["composition_gap_rate_B"], 1.0)
        self.assertEqual(results["solve_rate_B"], 0.0)


# ---------------------------------------------------------------------------
# AgentAdapter abstraction — FakeAdapter injected, no network
# ---------------------------------------------------------------------------

AgentAdapter = _probe.AgentAdapter
OllamaAdapter = _probe.OllamaAdapter
OpenAICompatAdapter = _probe.OpenAICompatAdapter


class FakeAdapter:
    """Minimal AgentAdapter for unit tests — no network, no GPU required."""

    def __init__(self, responses: list) -> None:
        self._responses = list(responses)
        self._idx = 0
        self.calls = 0

    def generate(self, prompt: str) -> str:
        self.calls += 1
        if self._idx < len(self._responses):
            r = self._responses[self._idx]
            self._idx += 1
            return r
        return ""


class TestAgentAdapterAbstraction(unittest.TestCase):
    """Verify AgentAdapter Protocol and solve() adapter injection — no network."""

    def test_fake_adapter_satisfies_protocol(self):
        """FakeAdapter must be recognized as an AgentAdapter (runtime_checkable Protocol)."""
        adapter = FakeAdapter(["hello"])
        self.assertIsInstance(adapter, AgentAdapter)

    def test_ollama_adapter_satisfies_protocol(self):
        """OllamaAdapter must be recognized as an AgentAdapter."""
        adapter = OllamaAdapter(model="test-model")
        self.assertIsInstance(adapter, AgentAdapter)

    def test_openai_compat_adapter_satisfies_protocol(self):
        """OpenAICompatAdapter must be recognized as an AgentAdapter."""
        adapter = OpenAICompatAdapter(base_url="http://localhost:8000", model="llama3")
        self.assertIsInstance(adapter, AgentAdapter)

    def test_solve_returns_first_nonempty(self):
        """solve() returns the first non-empty generate() result and stops."""
        adapter = FakeAdapter(["", "second"])
        result = _probe.solve(adapter, "prompt", attempts=3)
        self.assertEqual(result, "second")
        self.assertEqual(adapter.calls, 2)  # first was empty, second succeeded

    def test_solve_stops_on_first_success(self):
        """solve() does not call generate() after the first non-empty result."""
        adapter = FakeAdapter(["good", "also good"])
        result = _probe.solve(adapter, "prompt", attempts=3)
        self.assertEqual(result, "good")
        self.assertEqual(adapter.calls, 1)

    def test_solve_returns_empty_when_all_fail(self):
        """solve() returns '' when every generate() call returns empty."""
        adapter = FakeAdapter(["", ""])
        result = _probe.solve(adapter, "prompt", attempts=2)
        self.assertEqual(result, "")
        self.assertEqual(adapter.calls, 2)

    def test_solve_handles_generate_exception(self):
        """solve() catches generate() exceptions and tries remaining attempts."""

        class ExplodingThenGoodAdapter:
            def __init__(self) -> None:
                self.calls = 0

            def generate(self, prompt: str) -> str:
                self.calls += 1
                if self.calls == 1:
                    raise RuntimeError("boom")
                return "recovered"

        adapter = ExplodingThenGoodAdapter()
        result = _probe.solve(adapter, "prompt", attempts=3)
        self.assertEqual(result, "recovered")
        self.assertEqual(adapter.calls, 2)

    def test_run_arm_a_accepts_adapter(self):
        """run_arm_a with adapter= uses FakeAdapter — no network call."""
        task = _make_mock_task()
        adapter = FakeAdapter(["def placeholder(): pass"] * 10)
        result = run_arm_a(task, budget=3, adapter=adapter, parent_oracle=_always_pass)
        self.assertTrue(result["solved"])
        self.assertGreater(adapter.calls, 0)

    def test_run_arm_b_accepts_adapter(self):
        """run_arm_b with adapter= uses FakeAdapter — no network call."""
        task = _make_mock_task()
        adapter = FakeAdapter(["def placeholder(): pass"] * 20)
        result = run_arm_b(
            task,
            budget=4,
            adapter=adapter,
            parent_oracle=_always_pass,
            leaf_oracle_factory=lambda leaf: _always_pass,
        )
        self.assertTrue(result["solved"])
        self.assertGreater(adapter.calls, 0)

    def test_solve_fn_takes_precedence_over_adapter(self):
        """When solve_fn is given, adapter is ignored (backward compat)."""

        class BoomAdapter:
            def generate(self, p: str) -> str:
                raise AssertionError("adapter must not be called when solve_fn is provided")

        task = _make_mock_task()
        counter = CallCounter(artifact="def placeholder(): pass")
        run_arm_a(
            task,
            budget=2,
            solve_fn=counter,
            adapter=BoomAdapter(),
            parent_oracle=_always_fail,
        )
        self.assertEqual(counter.calls, 2)


# ---------------------------------------------------------------------------
# Env-based adapter selection — _default_adapter() reads env vars
# ---------------------------------------------------------------------------


def _with_env(overrides: dict, clear: list = None):
    """Apply env overrides, call _default_adapter(), restore env. Returns adapter."""
    saved = {}
    for k in (clear or []):
        saved[k] = os.environ.pop(k, None)
    for k, v in overrides.items():
        saved.setdefault(k, os.environ.get(k))
        os.environ[k] = v
    try:
        adapter = _probe._default_adapter()
    finally:
        for k, v in saved.items():
            if v is None:
                os.environ.pop(k, None)
            else:
                os.environ[k] = v
    return adapter


class TestEnvAdapterSelection(unittest.TestCase):
    """Verify _default_adapter() reads AIOS_PROBE_* env vars correctly — no network."""

    def test_default_is_ollama_adapter(self):
        """No AIOS_PROBE_AGENT (or 'ollama') returns OllamaAdapter."""
        adapter = _with_env(
            {"AIOS_PROBE_MODEL": "test-model"},
            clear=["AIOS_PROBE_AGENT"],
        )
        self.assertIsInstance(adapter, OllamaAdapter)
        self.assertEqual(adapter.model, "test-model")

    def test_openai_agent_selects_openai_compat_adapter(self):
        """AIOS_PROBE_AGENT=openai returns OpenAICompatAdapter with correct attrs."""
        adapter = _with_env(
            {
                "AIOS_PROBE_AGENT": "openai",
                "AIOS_PROBE_BASE_URL": "http://localhost:9999",
                "AIOS_PROBE_MODEL": "llama3",
                "AIOS_PROBE_API_KEY": "sk-test",
            }
        )
        self.assertIsInstance(adapter, OpenAICompatAdapter)
        self.assertEqual(adapter.model, "llama3")
        self.assertEqual(adapter.base_url, "http://localhost:9999")
        self.assertEqual(adapter.api_key, "sk-test")

    def test_openai_adapter_api_key_none_when_unset(self):
        """AIOS_PROBE_API_KEY not set => api_key=None on OpenAICompatAdapter."""
        adapter = _with_env(
            {
                "AIOS_PROBE_AGENT": "openai",
                "AIOS_PROBE_BASE_URL": "http://localhost:8000",
                "AIOS_PROBE_MODEL": "llama3",
            },
            clear=["AIOS_PROBE_API_KEY"],
        )
        self.assertIsInstance(adapter, OpenAICompatAdapter)
        self.assertIsNone(adapter.api_key)

    def test_ollama_model_from_env(self):
        """AIOS_PROBE_MODEL controls OllamaAdapter.model."""
        adapter = _with_env(
            {"AIOS_PROBE_MODEL": "my-custom-model"},
            clear=["AIOS_PROBE_AGENT"],
        )
        self.assertIsInstance(adapter, OllamaAdapter)
        self.assertEqual(adapter.model, "my-custom-model")

    def test_openai_base_url_trailing_slash_stripped(self):
        """OpenAICompatAdapter strips trailing slash from base_url."""
        adapter = _with_env(
            {
                "AIOS_PROBE_AGENT": "openai",
                "AIOS_PROBE_BASE_URL": "http://localhost:8000/",
                "AIOS_PROBE_MODEL": "llama3",
            },
            clear=["AIOS_PROBE_API_KEY"],
        )
        self.assertIsInstance(adapter, OpenAICompatAdapter)
        self.assertEqual(adapter.base_url, "http://localhost:8000")


# ---------------------------------------------------------------------------
# coding_iface_contract — contract-enforcing leaf oracles
# ---------------------------------------------------------------------------

CODING_IFACE_CONTRACT_TASK_DIR = (
    REPO_ROOT / "tests" / "hivemind_tasks" / "coding_iface_contract"
)


class TestCodingIfaceContractTask(unittest.TestCase):
    """Verify coding_iface_contract loads and has contract-enforcing leaf oracles."""

    def test_task_json_loads(self):
        meta = json.loads((CODING_IFACE_CONTRACT_TASK_DIR / "task.json").read_text())
        self.assertIn("leaves", meta)
        self.assertIn("parent_test", meta)
        self.assertEqual(len(meta["leaves"]), 2)

    def test_prompt_files_exist(self):
        for fname in ("whole.txt", "leaf_producer.txt", "leaf_consumer.txt"):
            self.assertTrue(
                (CODING_IFACE_CONTRACT_TASK_DIR / "prompts" / fname).exists(),
                f"Missing prompt file: {fname}",
            )

    def test_oracle_test_files_exist(self):
        for fname in ("test_producer.py", "test_consumer.py", "test_integration.py"):
            self.assertTrue(
                (CODING_IFACE_CONTRACT_TASK_DIR / "tests" / fname).exists(),
                f"Missing oracle test: {fname}",
            )

    def test_load_task_returns_correct_spec(self):
        """load_task('coding_iface_contract') returns well-formed TaskSpec."""
        task = _probe.load_task("coding_iface_contract")
        self.assertEqual(task.name, "coding_iface_contract")
        self.assertEqual(len(task.leaves), 2)
        names = [l.name for l in task.leaves]
        self.assertIn("producer", names)
        self.assertIn("consumer", names)

    def test_producer_prompt_states_contract(self):
        """Producer leaf prompt must explicitly state the 'value' key contract."""
        prompt = (
            CODING_IFACE_CONTRACT_TASK_DIR / "prompts" / "leaf_producer.txt"
        ).read_text()
        self.assertIn('"value"', prompt,
                      "Producer prompt must state the exact key 'value' contract")

    def test_contract_oracle_rejects_wrong_key(self):
        """Contract-enforcing producer oracle FAILS when key is not 'value'."""
        import tempfile
        import shutil

        _probe_mod = importlib.import_module("aios_hivemind_probe_under_test")
        oracle = _probe_mod.pytest_oracle(
            CODING_IFACE_CONTRACT_TASK_DIR / "tests" / "test_producer.py"
        )
        tmpdir = Path(tempfile.mkdtemp(prefix="aios_contract_reject_"))
        try:
            # 'amount' key passes weak oracle (coding_iface) but must FAIL strong oracle
            (tmpdir / "producer.py").write_text(
                'def get_data() -> dict:\n    return {"amount": 42}\n'
            )
            self.assertFalse(
                oracle(tmpdir),
                "Contract oracle must FAIL when key is 'amount', not 'value'",
            )
        finally:
            shutil.rmtree(tmpdir, ignore_errors=True)

    def test_contract_oracle_passes_correct_key(self):
        """Contract-enforcing producer oracle PASSES when key is 'value'."""
        import tempfile
        import shutil

        _probe_mod = importlib.import_module("aios_hivemind_probe_under_test")
        oracle = _probe_mod.pytest_oracle(
            CODING_IFACE_CONTRACT_TASK_DIR / "tests" / "test_producer.py"
        )
        tmpdir = Path(tempfile.mkdtemp(prefix="aios_contract_pass_"))
        try:
            (tmpdir / "producer.py").write_text(
                'def get_data() -> dict:\n    return {"value": 42}\n'
            )
            self.assertTrue(
                oracle(tmpdir),
                "Contract oracle must PASS when key is 'value'",
            )
        finally:
            shutil.rmtree(tmpdir, ignore_errors=True)

    def test_solution_passes_contract_oracle(self):
        """Reference solution must pass the contract-enforcing producer oracle."""
        _probe_mod = importlib.import_module("aios_hivemind_probe_under_test")
        oracle = _probe_mod.pytest_oracle(
            CODING_IFACE_CONTRACT_TASK_DIR / "tests" / "test_producer.py"
        )
        solution_dir = CODING_IFACE_CONTRACT_TASK_DIR / "solution"
        self.assertTrue(
            oracle(solution_dir),
            "Reference solution must pass the contract-enforcing oracle",
        )

    def test_weak_oracle_would_pass_wrong_key(self):
        """Confirm the gap: the OLD weak oracle passes 'amount' key (coding_iface behaviour)."""
        import tempfile
        import shutil

        _probe_mod = importlib.import_module("aios_hivemind_probe_under_test")
        # Use the ORIGINAL coding_iface weak oracle
        weak_oracle = _probe_mod.pytest_oracle(
            TASK_DIR / "tests" / "test_producer.py"
        )
        tmpdir = Path(tempfile.mkdtemp(prefix="aios_weak_oracle_"))
        try:
            (tmpdir / "producer.py").write_text(
                'def get_data() -> dict:\n    return {"amount": 42}\n'
            )
            self.assertTrue(
                weak_oracle(tmpdir),
                "Weak oracle must PASS 'amount' key (this is the gap coding_iface exposes)",
            )
        finally:
            shutil.rmtree(tmpdir, ignore_errors=True)


if __name__ == "__main__":
    unittest.main()
