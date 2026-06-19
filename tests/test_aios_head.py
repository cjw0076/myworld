"""aios <goal> head tests — fake planner, no real LLM."""
from __future__ import annotations

import importlib.util
import json
import sys
import tempfile
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
SCRIPTS = REPO_ROOT / "scripts"


def _load(name: str):
    full = f"{name}_under_test"
    spec = importlib.util.spec_from_file_location(full, SCRIPTS / f"{name}.py")
    m = importlib.util.module_from_spec(spec)
    sys.modules[full] = m
    if str(SCRIPTS) not in sys.path:
        sys.path.insert(0, str(SCRIPTS))
    spec.loader.exec_module(m)
    return m


class HeadTest(unittest.TestCase):
    def setUp(self):
        self.head = _load("aios_head")
        self._td = tempfile.TemporaryDirectory()
        self.root = Path(self._td.name)

    def tearDown(self):
        self._td.cleanup()

    def _planner(self, plan):
        return lambda goal, ctx: json.dumps(plan)

    def test_skeleton_is_read_only_by_default(self):
        c = self.head.build_skeleton("x", workspace_root=str(self.root))
        self.assertEqual(c.filesystem_scope.write_paths, [])
        self.assertFalse(c.authority_scope.network)
        # privacy paths always denied
        self.assertTrue(any("dain/" in d for d in c.filesystem_scope.deny_paths))

    def test_extract_json_array_handles_fences_and_noise(self):
        text = "Here is the plan:\n```json\n[{\"id\":\"s1\"}]\n```\nthanks"
        out = self.head._extract_json_array(text)
        self.assertEqual(out, [{"id": "s1"}])

    def test_compile_read_only_goal_validates(self):
        (self.root / "a.txt").write_text("hi")
        plan = [{"id": "s1", "description": "read a", "tool": "fs.read",
                 "inputs": {"path": str(self.root / "a.txt")}}]
        c, errors = self.head.compile_goal(
            "read the file", workspace_root=str(self.root), planner=self._planner(plan))
        self.assertEqual(errors, [], errors)
        self.assertEqual(len(c.steps), 1)

    def test_plan_exceeding_authority_is_rejected(self):
        # plan asks for a write but no write scope granted -> fail-closed
        plan = [{"id": "s1", "description": "write", "tool": "fs.write",
                 "inputs": {"path": str(self.root / "out.txt"), "content": "x"}}]
        c, errors = self.head.compile_goal(
            "write a file", workspace_root=str(self.root), planner=self._planner(plan))
        self.assertTrue(errors)
        self.assertTrue(any("not in scope" in e for e in errors))

    def test_plan_touching_private_path_rejected_even_with_write(self):
        # grant write over root, but plan targets dain/ which is always denied
        dain = self.root / "dain"
        plan = [{"id": "s1", "description": "write secret", "tool": "fs.write",
                 "inputs": {"path": str(dain / "x.txt"), "content": "x"}}]
        c, errors = self.head.compile_goal(
            "write into dain", workspace_root=str(self.root),
            planner=self._planner(plan), allow_write=[str(self.root)])
        self.assertTrue(errors)

    def test_end_to_end_compile_then_run(self):
        (self.root / "src.txt").write_text("original")
        plan = [
            {"id": "s1", "description": "read", "tool": "fs.read",
             "inputs": {"path": str(self.root / "src.txt")}},
            {"id": "s2", "description": "write", "tool": "fs.write",
             "inputs": {"path": str(self.root / "src.txt"), "content": "rewritten"}},
        ]
        c, errors = self.head.compile_goal(
            "tidy src", workspace_root=str(self.root),
            planner=self._planner(plan), allow_write=[str(self.root)])
        self.assertEqual(errors, [], errors)
        summary = self.head.runner.run_contract(c)
        self.assertEqual(summary["status"], "closed", summary)
        self.assertEqual((self.root / "src.txt").read_text(), "rewritten")
        # reversible
        self.head.runner.rollback(c)
        self.assertEqual((self.root / "src.txt").read_text(), "original")

    def test_planner_receipt_attached_on_success(self):
        """Successful planner call must produce an auditable planner receipt."""
        plan = [{"id": "s1", "description": "read", "tool": "fs.read",
                 "inputs": {"path": str(self.root)}}]
        c, errors = self.head.compile_goal(
            "read workspace", workspace_root=str(self.root),
            planner=self._planner(plan), planner_label="fake-test",
        )
        pr = c.planner_receipt
        self.assertIsNotNone(pr, "planner_receipt must be attached")
        self.assertEqual(pr.schema_version, "aios.planner_receipt.v0")
        self.assertEqual(pr.parse_status, "ok")
        self.assertEqual(pr.step_count, 1)
        self.assertEqual(pr.planner_label, "fake-test")
        self.assertEqual(pr.memory_count, 0)
        # workspace / write_paths / network context recorded
        self.assertEqual(pr.workspace_root, str(self.root))
        self.assertIsInstance(pr.write_paths, list)
        self.assertIsInstance(pr.network, bool)

    def test_planner_receipt_no_raw_body(self):
        """Raw planner text must NOT appear in the ContractObject receipt."""
        raw_sentinel = "SENSITIVE_PLANNER_OUTPUT_DO_NOT_STORE_THIS"
        planner = lambda goal, ctx: json.dumps(
            [{"id": "s1", "description": raw_sentinel, "tool": "user.checkpoint"}]
        )
        c, _ = self.head.compile_goal(
            "goal", workspace_root=str(self.root), planner=planner,
        )
        # Serialize the whole contract — raw sentinel must not appear
        serialized = json.dumps(c.planner_receipt.__dict__ if hasattr(c.planner_receipt, '__dict__') else {})
        self.assertNotIn(raw_sentinel, serialized,
                         "raw planner body must not be stored in planner_receipt")
        # hash and length are stored instead
        self.assertIsNotNone(c.planner_receipt.raw_body_hash)
        self.assertGreater(c.planner_receipt.raw_body_len, 0)

    def test_planner_receipt_on_parse_failure(self):
        """Parse failure must preserve a hash/length diagnostic receipt, not be invisible."""
        bad_planner = lambda goal, ctx: "this is NOT valid json - no array here"
        c, errors = self.head.compile_goal(
            "bad goal", workspace_root=str(self.root), planner=bad_planner,
        )
        self.assertTrue(errors, "errors must be non-empty on parse failure")
        pr = c.planner_receipt
        self.assertIsNotNone(pr, "planner_receipt must exist even after parse failure")
        self.assertEqual(pr.parse_status, "failed")
        self.assertEqual(pr.step_count, 0)
        self.assertIsNotNone(pr.error)
        # hash and length recorded even for bad output
        self.assertIsNotNone(pr.raw_body_hash)
        self.assertGreater(pr.raw_body_len, 0)

    def test_planner_receipt_memory_count_not_bodies(self):
        """Memory inputs are counted, raw memory bodies must not appear in the receipt."""
        memories = ["trace_id_abc", "trace_id_xyz", "trace_id_123"]
        retriever = lambda goal: memories
        plan = [{"id": "s1", "description": "step", "tool": "user.checkpoint"}]
        c, _ = self.head.compile_goal(
            "recall goal", workspace_root=str(self.root),
            planner=self._planner(plan), retriever=retriever,
        )
        pr = c.planner_receipt
        self.assertEqual(pr.memory_count, 3)
        # raw memory bodies must not be in the receipt
        for mem in memories:
            self.assertNotIn(mem, pr.raw_body_hash)


class GoalFilesystemDetectionTest(unittest.TestCase):
    """Test that _goal_needs_filesystem() correctly identifies filesystem goals."""

    def setUp(self):
        self.head = _load("aios_head")

    def test_list_files_is_filesystem(self):
        self.assertTrue(self.head._goal_needs_filesystem("list all python files in scripts/"))

    def test_file_extension_is_filesystem(self):
        self.assertTrue(self.head._goal_needs_filesystem("read the .py files"))

    def test_korean_read_is_filesystem(self):
        self.assertTrue(self.head._goal_needs_filesystem("파일 읽어줘"))

    def test_directory_path_is_filesystem(self):
        self.assertTrue(self.head._goal_needs_filesystem("find everything in docs/"))

    def test_pure_math_is_not_filesystem(self):
        self.assertFalse(self.head._goal_needs_filesystem("what is 2 + 2"))

    def test_concept_explanation_is_not_filesystem(self):
        self.assertFalse(self.head._goal_needs_filesystem("explain what a REST API is"))

    def test_early_exit_suppressed_for_fs_goal(self):
        """Filesystem goals must NOT get the early-exit hint on turn 0."""
        import re as _re
        # Simulate the early_exit_hint computation
        goal = "list all python files in scripts/"
        fs_goal = self.head._goal_needs_filesystem(goal)
        early_exit_hint = (
            '' if fs_goal else 'emit done'
        )
        self.assertEqual(early_exit_hint, '')

    def test_early_exit_present_for_knowledge_goal(self):
        """Knowledge goals CAN get the early-exit hint."""
        goal = "explain what a monad is"
        fs_goal = self.head._goal_needs_filesystem(goal)
        early_exit_hint = (
            '' if fs_goal else 'emit done'
        )
        self.assertNotEqual(early_exit_hint, '')


if __name__ == "__main__":
    unittest.main()
