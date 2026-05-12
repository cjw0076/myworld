import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from scripts.aios_contract_autodraft import draft_contract


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "aios_contract_autodraft.py"


def sample_plan(blocked: bool = False) -> dict:
    return {
        "schema_version": "aios.goal_evolution.v1",
        "generated_at": "2026-05-12T19:00:00+09:00",
        "goal": {"goal_id": "AIOS-GOAL-TEST", "status": "active"},
        "evidence": {"monitor_health": "clear", "readiness_level_name": "L6 repeatable"},
        "recommendation": {
            "path": "goal:test_autodraft_surface",
            "domain": "myworld",
            "candidate_task": "turn a goal recommendation into a proposed contract draft.",
            "policy_decision": "goal_preferred",
            "policy_reason": "test fixture",
            "alignment_reasons": ["goal_preferred_next"],
            "blocked_reasons": ["blocked"] if blocked else [],
            "blocked": blocked,
        },
        "top_candidates": [],
        "stop_conditions": ["recommended_candidate_blocked"] if blocked else [],
    }


class AiosContractAutodraftTest(unittest.TestCase):
    def test_draft_contract_is_proposed_and_not_auto_accepted(self) -> None:
        draft = draft_contract(sample_plan(), "ASC-0990")

        self.assertEqual(draft["schema_version"], "aios.contract_autodraft.v1")
        self.assertEqual(draft["status"], "proposed")
        self.assertFalse(draft["auto_accept"])
        self.assertIn("status: proposed", draft["body"])
        self.assertIn("accepted:", draft["body"])
        self.assertIn("operator acceptance", draft["body"].lower())

    def test_draft_contract_rejects_blocked_recommendation(self) -> None:
        with self.assertRaises(ValueError):
            draft_contract(sample_plan(blocked=True), "ASC-0991")

    def test_cli_writes_contract_to_requested_output_dir(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            plan = Path(tmp) / "plan.json"
            plan.write_text(json.dumps(sample_plan()), encoding="utf-8")
            result = subprocess.run(
                [
                    sys.executable,
                    SCRIPT.as_posix(),
                    "--root",
                    ROOT.as_posix(),
                    "draft",
                    "--plan-json",
                    plan.as_posix(),
                    "--contract-id",
                    "ASC-0992",
                    "--output-dir",
                    tmp,
                    "--write",
                    "--json",
                ],
                cwd=ROOT,
                text=True,
                capture_output=True,
                check=False,
            )

            self.assertEqual(result.returncode, 0, result.stderr)
            payload = json.loads(result.stdout)
            self.assertTrue(payload["written"])
            self.assertEqual(payload["contract_id"], "ASC-0992")
            path = Path(payload["path"])
            self.assertTrue(path.exists())
            text = path.read_text(encoding="utf-8")
            self.assertIn("status: proposed", text)
            self.assertIn("## Verification Gate", text)


if __name__ == "__main__":
    unittest.main()
