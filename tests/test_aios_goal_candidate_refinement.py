import tempfile
import sys
import unittest
from pathlib import Path


SCRIPTS_DIR = Path(__file__).resolve().parents[1] / "scripts"
if SCRIPTS_DIR.as_posix() not in sys.path:
    sys.path.insert(0, SCRIPTS_DIR.as_posix())

from aios_goal_candidates import concrete_product_eval_candidate  # noqa: E402


class AiosGoalCandidateRefinementTest(unittest.TestCase):
    def test_product_evaluation_candidate_refines_to_first_p0_item(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            source = root / "hivemind" / "docs" / "HIVE_PRODUCT_EVALUATION.md"
            source.parent.mkdir(parents=True)
            source.write_text(
                "# Hive Mind Product Evaluation\n\n"
                "## Next Product P0\n\n"
                "1. Policy-gate or replace the unsafe Claude execute workaround before adding\n"
                "   broader automation.\n"
                "2. Harden DAG step result handling.\n",
                encoding="utf-8",
            )
            base = {
                "path": "myworld/hivemind/docs/HIVE_PRODUCT_EVALUATION.md",
                "candidate_task": "issue a Hive Mind packet for execution, harness, or verification follow-up",
                "goal_score": 183,
                "alignment_reasons": ["verification_signal"],
            }

            refined = concrete_product_eval_candidate(root, base)

            self.assertIsNotNone(refined)
            assert refined is not None
            self.assertEqual(refined["path"], "myworld/hivemind/docs/HIVE_PRODUCT_EVALUATION.md#next-product-p0-1")
            self.assertIn("Policy-gate or replace", refined["candidate_task"])
            self.assertIn("broader automation", refined["candidate_task"])
            self.assertIn("concrete_product_eval_p0", refined["alignment_reasons"])


if __name__ == "__main__":
    unittest.main()
