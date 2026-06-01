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


if __name__ == "__main__":
    unittest.main()
