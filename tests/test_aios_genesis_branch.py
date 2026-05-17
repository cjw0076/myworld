from __future__ import annotations

import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "aios_genesis_branch.py"


GOAL_DOC = """---
goal_id: GOAL-TEST
goal: AIOS should keep competing Genesis branches alive before contract drafting.
status: active
---

# Goal Test
"""


class AiosGenesisBranchTest(unittest.TestCase):
    def make_root(self, tmp: str) -> tuple[Path, Path]:
        root = Path(tmp)
        (root / "GenesisOS").symlink_to(ROOT / "GenesisOS", target_is_directory=True)
        goals = root / "docs" / "goals"
        goals.mkdir(parents=True, exist_ok=True)
        goal_path = goals / "GOAL-TEST.md"
        goal_path.write_text(GOAL_DOC, encoding="utf-8")
        return root, goal_path

    def test_fork_list_collapse_flow(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root, goal_path = self.make_root(tmp)

            sys.path.insert(0, ROOT.as_posix())
            from scripts.aios_genesis_branch import build_report

            forked = build_report(root, action="fork", goal_path=goal_path.as_posix(), n=3)
            self.assertEqual(forked["schema_version"], "aios.genesis_branch.v1")
            self.assertEqual(forked["authority"], "operator_review_required")
            self.assertEqual(len(forked["result"]["branches"]), 3)
            winner = forked["result"]["branches"][0]["branch_id"]

            listed = build_report(root, action="list")
            self.assertEqual(len(listed["result"]["branches"]), 3)

            collapsed = build_report(
                root,
                action="collapse",
                goal_path=goal_path.as_posix(),
                winner=winner,
                reason="test operator choice",
            )
            self.assertEqual(collapsed["result"]["winner_branch_id"], winner)
            self.assertEqual(collapsed["result"]["canonical_branch"]["branch_id"], winner)
            alive = [branch for branch in collapsed["result"]["branches"] if branch["alive"]]
            self.assertEqual(len(alive), 1)

    def test_cli_json(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root, goal_path = self.make_root(tmp)
            result = subprocess.run(
                [
                    sys.executable,
                    SCRIPT.as_posix(),
                    "--root",
                    root.as_posix(),
                    "fork",
                    "--goal-path",
                    goal_path.as_posix(),
                    "--n",
                    "3",
                    "--json",
                ],
                text=True,
                capture_output=True,
                check=False,
            )

            self.assertEqual(result.returncode, 0, result.stderr)
            payload = json.loads(result.stdout)
            self.assertEqual(payload["action"], "fork")
            self.assertEqual(len(payload["result"]["branches"]), 3)
            self.assertEqual(payload["mutated_files"], [])


if __name__ == "__main__":
    unittest.main()
