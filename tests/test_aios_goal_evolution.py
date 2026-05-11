import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "aios_goal_evolution.py"


GOAL = """---
goal_id: AIOS-GOAL-TEST
slug: test-goal
status: active
---

# Test Goal

## Quality Function

- reduce_user_relay: reduce manual relay.
- increase_repeatability: make future runs repeatable.

## Anti-Cheat Checks

- Do not reopen closed contracts.
- Do not auto-accept private paths.

## Preferred Next Improvements

- source_read_registry: record shared source reads.
"""


RADAR = """# AIOS Task Radar

## Top Task Signals

| Score | Domain | Path | Signals | Candidate Task |
| ---: | --- | --- | --- | --- |
| 90 | myworld | `myworld/docs/contracts/ASC-0001-closed.md` | `aios:12,contract:12,verify:12` | promote this control-plane signal into an AIOS contract or readiness gate |
| 85 | _from_desktop | `_from_desktop/Uri/docs/TODO.md` | `p0:2,next:1` | triage as external workspace context before importing into AIOS |
| 80 | hivemind | `myworld/hivemind/docs/RADAR_GAP_TRIAGE.md` | `hivemind:12,next:12,verify:3` | source-read registry that can flag divergent interpretations |
"""


class AiosGoalEvolutionTest(unittest.TestCase):
    def write_fixture(self, root: Path) -> Path:
        goal_path = root / "docs" / "goals" / "AIOS-GOAL-TEST.md"
        goal_path.parent.mkdir(parents=True)
        goal_path.write_text(GOAL, encoding="utf-8")
        contract_dir = root / "docs" / "contracts"
        contract_dir.mkdir(parents=True)
        (contract_dir / "ASC-0001-closed.md").write_text(
            "---\ncontract_id: ASC-0001\nstatus: closed\n---\n",
            encoding="utf-8",
        )
        (root / "docs" / "AIOS_TASK_RADAR.md").write_text(RADAR, encoding="utf-8")
        return goal_path

    def run_plan(self, root: Path, goal_path: Path, *args: str) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            [
                sys.executable,
                SCRIPT.as_posix(),
                "plan",
                "--root",
                root.as_posix(),
                "--goal",
                goal_path.as_posix(),
                *args,
            ],
            text=True,
            capture_output=True,
            check=False,
        )

    def test_goal_plan_selects_unblocked_goal_aligned_candidate(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            goal_path = self.write_fixture(root)

            result = self.run_plan(root, goal_path, "--json")

            self.assertEqual(result.returncode, 0, result.stderr)
            data = json.loads(result.stdout)
            self.assertEqual(data["schema_version"], "aios.goal_evolution.v1")
            self.assertEqual(data["goal"]["goal_id"], "AIOS-GOAL-TEST")
            self.assertEqual(data["recommendation"]["path"], "myworld/hivemind/docs/RADAR_GAP_TRIAGE.md")
            self.assertFalse(data["recommendation"]["blocked"])
            self.assertIn("reduces_user_context_relay", data["recommendation"]["alignment_reasons"])

    def test_goal_plan_blocks_closed_contract_and_private_paths(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            goal_path = self.write_fixture(root)

            result = self.run_plan(root, goal_path, "--json")

            data = json.loads(result.stdout)
            by_path = {item["path"]: item for item in data["top_candidates"]}
            self.assertIn("closed_contract_source", by_path["myworld/docs/contracts/ASC-0001-closed.md"]["blocked_reasons"])
            self.assertIn("private_or_operator_gated_path", by_path["_from_desktop/Uri/docs/TODO.md"]["blocked_reasons"])

    def test_goal_plan_writes_markdown(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            goal_path = self.write_fixture(root)
            out = root / "docs" / "goals" / "AIOS-GOAL-TEST-evolution.md"

            result = self.run_plan(root, goal_path, "--write", out.as_posix())

            self.assertEqual(result.returncode, 0, result.stderr)
            text = out.read_text(encoding="utf-8")
            self.assertIn("# AIOS Goal Evolution Plan", text)
            self.assertIn("## Recommendation", text)
            self.assertIn("myworld/hivemind/docs/RADAR_GAP_TRIAGE.md", text)

    def test_goal_without_quality_function_fails(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            goal_path = root / "docs" / "goals" / "bad.md"
            goal_path.parent.mkdir(parents=True)
            goal_path.write_text("---\ngoal_id: bad\nstatus: active\n---\n# Bad\n", encoding="utf-8")
            (root / "docs").mkdir(exist_ok=True)
            (root / "docs" / "AIOS_TASK_RADAR.md").write_text(RADAR, encoding="utf-8")

            result = self.run_plan(root, goal_path, "--json")

            self.assertNotEqual(result.returncode, 0)
            self.assertIn("Quality Function", result.stderr)


if __name__ == "__main__":
    unittest.main()
