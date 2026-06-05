import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from scripts.aios_goal_evolution import Goal, stop_conditions


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
| 98 | myworld | `myworld/docs/AIOS_WORK_DISPATCH.md` | `aios:12,next:8,verify:5` | promote this control-plane signal into an AIOS contract or readiness gate |
| 95 | hivemind | `myworld/hivemind/docs/AGENT_WORKLOG.md` | `hivemind:12,next:12,verify:9` | source-read registry that can flag divergent interpretations |
| 92 | myworld | `myworld/docs/AIOS_AGENT_LEDGER.md` | `aios:12,contract:12,next:9` | promote this control-plane signal into an AIOS contract or readiness gate |
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
        todo_path = root / "hivemind" / "docs" / "TODO.md"
        todo_path.parent.mkdir(parents=True)
        todo_path.write_text(
            "\n".join(
                [
                    "# Hive TODO",
                    "",
                    "- [x] Add arrival packs generated from live run state.",
                    "- [x] Add source-read registry that can flag shared source input with divergent agent interpretations.",
                    "- [x] Add `HANDOFF.json`/shared-folder compatibility import so old MemoryOS pingpong loops can be replayed into Hive run artifacts.",
                    "- [ ] Add first-class `hive evaluate` or `hive subagents review` command that runs verifier, product evaluator, and actual-user persona checks into durable artifacts.",
                    "- [ ] Add semantic verifier LLM review for high-risk runs.",
                ]
            )
            + "\n",
            encoding="utf-8",
        )
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
            self.assertEqual(data["recommendation"]["path"], "myworld/hivemind/docs/TODO.md#hive-evaluate")
            self.assertEqual(data["recommendation"]["source_path"], "myworld/hivemind/docs/RADAR_GAP_TRIAGE.md")
            self.assertIn("hive evaluate", data["recommendation"]["candidate_task"])
            self.assertFalse(data["recommendation"]["blocked"])
            self.assertIn("reduces_user_context_relay", data["recommendation"]["alignment_reasons"])
            self.assertIn("concrete_hive_todo", data["recommendation"]["alignment_reasons"])

    def test_goal_plan_selects_semantic_verifier_after_evaluate_closes(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            goal_path = self.write_fixture(root)
            todo_path = root / "hivemind" / "docs" / "TODO.md"
            todo_path.write_text(
                todo_path.read_text(encoding="utf-8").replace(
                    "- [ ] Add first-class `hive evaluate` or `hive subagents review` command",
                    "- [x] Add first-class `hive evaluate` or `hive subagents review` command",
                ),
                encoding="utf-8",
            )

            result = self.run_plan(root, goal_path, "--json")

            self.assertEqual(result.returncode, 0, result.stderr)
            data = json.loads(result.stdout)
            self.assertEqual(data["recommendation"]["path"], "myworld/hivemind/docs/TODO.md#semantic-verifier")
            self.assertEqual(data["recommendation"]["source_path"], "myworld/hivemind/docs/RADAR_GAP_TRIAGE.md")
            self.assertIn("semantic verifier", data["recommendation"]["candidate_task"])
            self.assertIn("concrete_hive_todo", data["recommendation"]["alignment_reasons"])

    def test_goal_plan_blocks_stale_hive_radar_gap_when_todos_are_closed(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            goal_path = self.write_fixture(root)
            todo_path = root / "hivemind" / "docs" / "TODO.md"
            todo_path.write_text(
                todo_path.read_text(encoding="utf-8")
                .replace("- [ ] Add first-class `hive evaluate`", "- [x] Add first-class `hive evaluate`")
                .replace("- [ ] Add semantic verifier", "- [x] Add semantic verifier"),
                encoding="utf-8",
            )

            result = self.run_plan(root, goal_path, "--json")

            self.assertEqual(result.returncode, 0, result.stderr)
            data = json.loads(result.stdout)
            by_path = {item["path"]: item for item in data["top_candidates"]}
            radar_gap = by_path["myworld/hivemind/docs/RADAR_GAP_TRIAGE.md"]
            self.assertIn("stale_hive_radar_gap_source", radar_gap["blocked_reasons"])
            self.assertNotEqual(data["recommendation"]["path"], "myworld/hivemind/docs/RADAR_GAP_TRIAGE.md")

    def test_goal_plan_blocks_closed_contract_and_private_paths(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            goal_path = self.write_fixture(root)

            result = self.run_plan(root, goal_path, "--json")

            data = json.loads(result.stdout)
            by_path = {item["path"]: item for item in data["top_candidates"]}
            self.assertIn("closed_contract_source", by_path["myworld/docs/contracts/ASC-0001-closed.md"]["blocked_reasons"])
            self.assertIn("private_or_operator_gated_path", by_path["_from_desktop/Uri/docs/TODO.md"]["blocked_reasons"])
            self.assertIn("history_source_requires_triage", by_path["myworld/hivemind/docs/AGENT_WORKLOG.md"]["blocked_reasons"])
            self.assertIn("index_source_requires_triage", by_path["myworld/docs/AIOS_AGENT_LEDGER.md"]["blocked_reasons"])
            self.assertIn("reference_source_requires_contract", by_path["myworld/docs/AIOS_WORK_DISPATCH.md"]["blocked_reasons"])

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
            self.assertIn("myworld/hivemind/docs/TODO.md#hive-evaluate", text)

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

    def test_info_only_monitor_watch_does_not_stop_goal_evolution(self) -> None:
        goal = Goal(
            path=Path("docs/goals/AIOS-GOAL-TEST.md"),
            frontmatter={"goal_id": "AIOS-GOAL-TEST", "status": "active"},
            body="",
            quality_function=["increase_repeatability: keep loops moving."],
            anti_cheat_checks=[],
            preferred_next=[],
        )
        monitor = {
            "health": "watch",
            "findings": [
                {
                    "code": "persona_axis_advisory",
                    "severity": "info",
                }
            ],
        }
        recommendation = {"blocked": False}

        stops = stop_conditions(goal, monitor, {"ready": True}, recommendation)

        self.assertNotIn("monitor_not_clear", stops)


if __name__ == "__main__":
    unittest.main()
