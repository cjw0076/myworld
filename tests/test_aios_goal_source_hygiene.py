import tempfile
import sys
import unittest
from pathlib import Path


SCRIPTS_DIR = Path(__file__).resolve().parents[1] / "scripts"
if SCRIPTS_DIR.as_posix() not in sys.path:
    sys.path.insert(0, SCRIPTS_DIR.as_posix())

from aios_goal_candidates import build_candidates  # noqa: E402
from aios_goal_sources import Goal, RadarRow  # noqa: E402


class AiosGoalSourceHygieneTest(unittest.TestCase):
    def test_legacy_surface_source_is_blocked_before_execution_candidate(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            source = root / "hivemind" / "docs" / "TUI_HARNESS.md"
            source.parent.mkdir(parents=True)
            source.write_text(
                "# Hive Mind CLI/TUI\n\n"
                "hive tui\n"
                "`hive live` is the prompt/log surface over the same substrate.\n"
                "Legacy terminal cockpit code was removed after live became the default.\n",
                encoding="utf-8",
            )
            goal = Goal(
                path=root / "docs" / "goals" / "goal.md",
                frontmatter={"goal_id": "goal", "status": "active"},
                body="",
                quality_function=["increase_verified_execution: close real work."],
                anti_cheat_checks=[],
                preferred_next=[],
            )
            rows = [
                RadarRow(
                    score=120,
                    domain="hivemind",
                    path="myworld/hivemind/docs/TUI_HARNESS.md",
                    signals={"verify": 12},
                    candidate_task="issue a Hive Mind packet for execution, harness, or verification follow-up",
                )
            ]

            candidates = build_candidates(root, goal, rows, {"decisions": []})

            self.assertIn("legacy_surface_source_requires_triage", candidates[0]["blocked_reasons"])


if __name__ == "__main__":
    unittest.main()
