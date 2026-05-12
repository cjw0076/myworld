import json
import subprocess
import sys
import unittest
from pathlib import Path

from scripts.aios_action_policy import evaluate_action


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "aios_action_policy.py"


class AiosActionPolicyTest(unittest.TestCase):
    def test_allows_low_risk_local_contracted_action(self) -> None:
        result = evaluate_action(
            {
                "action_type": "local_verification",
                "target_repo": "myworld",
                "risk": "low",
                "privacy": "local",
                "cost": "free",
                "has_contract": True,
                "evidence_refs": ["docs/contracts/ASC-0034-governance-action-policy-engine.md"],
            }
        )

        self.assertEqual(result.decision, "allow")
        self.assertTrue(result.allowed_to_execute)
        self.assertFalse(result.required_checkpoint)

    def test_holds_when_contract_or_evidence_missing(self) -> None:
        result = evaluate_action(
            {
                "action_type": "child_repo_edit",
                "target_repo": "hivemind",
                "risk": "medium",
                "privacy": "local",
                "cost": "free",
                "has_contract": False,
                "evidence_refs": [],
            }
        )

        self.assertEqual(result.decision, "hold")
        self.assertIn("missing_contract", result.reason_codes)
        self.assertIn("missing_evidence_refs", result.reason_codes)

    def test_denies_forbidden_action(self) -> None:
        result = evaluate_action(
            {
                "action_type": "secret_exfiltration",
                "target_repo": "external",
                "risk": "high",
                "privacy": "remote",
                "has_contract": True,
                "evidence_refs": ["operator_request"],
            }
        )

        self.assertEqual(result.decision, "deny")
        self.assertTrue(result.required_checkpoint)
        self.assertFalse(result.allowed_to_execute)

    def test_escalates_public_authority_without_human_approval(self) -> None:
        result = evaluate_action(
            {
                "action_type": "public_statement",
                "target_repo": "external",
                "risk": "high",
                "privacy": "remote",
                "cost": "free",
                "has_contract": True,
                "evidence_refs": ["docs/AIOS_GOVERNANCE_MODEL.md"],
                "public_communication": True,
                "real_world_authority": True,
                "human_approved": False,
            }
        )

        self.assertEqual(result.decision, "escalate")
        self.assertTrue(result.required_checkpoint)
        self.assertIn("human_checkpoint_required:public_communication", result.reason_codes)

    def test_cli_examples_emit_json(self) -> None:
        completed = subprocess.run(
            [sys.executable, SCRIPT.as_posix(), "evaluate", "--example", "low_risk_local", "--json"],
            cwd=ROOT,
            text=True,
            capture_output=True,
            check=True,
        )

        payload = json.loads(completed.stdout)
        self.assertEqual(payload["schema_version"], "aios.action_policy.v1")
        self.assertEqual(payload["decision"], "allow")
        self.assertTrue(payload["allowed_to_execute"])

    def test_cli_public_authority_escalates(self) -> None:
        completed = subprocess.run(
            [sys.executable, SCRIPT.as_posix(), "evaluate", "--example", "public_authority", "--json"],
            cwd=ROOT,
            text=True,
            capture_output=True,
            check=True,
        )

        payload = json.loads(completed.stdout)
        self.assertEqual(payload["decision"], "escalate")
        self.assertFalse(payload["allowed_to_execute"])
        self.assertTrue(payload["required_checkpoint"])


if __name__ == "__main__":
    unittest.main()
