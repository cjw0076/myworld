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

    def test_myworld_local_operator_scope_allows_without_private_remote_escalation(self) -> None:
        result = evaluate_action(
            {
                "action_type": "dispatch_packet",
                "target_repo": "myworld",
                "authority": "accepted_contract",
                "risk": "low",
                "privacy": "local",
                "cost": "free",
                "has_contract": True,
                "evidence_refs": ["docs/contracts/ASC-0037-child-watcher-locale-aware-fallback.md"],
                "human_approved": False,
                "irreversible": False,
                "external_effect": False,
                "uses_credentials": False,
                "public_communication": False,
                "legal_or_safety_impact": False,
                "real_world_authority": False,
                "sends_private_data": False,
                "repos": ["myworld"],
                "allowed_files": ["scripts/aios_child_watcher.sh", "docs/contracts/ASC-0037-child-watcher-locale-aware-fallback.md"],
                "forbidden_files": [".cache/**"],
            }
        )

        self.assertEqual(result.decision, "allow")
        self.assertIn("myworld_local_operator_scope", result.reason_codes)
        self.assertNotIn("human_checkpoint_required:private_remote_data", result.reason_codes)

    def test_myworld_local_operator_scope_does_not_cover_cross_repo_contracts(self) -> None:
        result = evaluate_action(
            {
                "action_type": "dispatch_packet",
                "target_repo": "hivemind",
                "authority": "accepted_contract",
                "risk": "low",
                "privacy": "local",
                "cost": "free",
                "has_contract": True,
                "evidence_refs": ["docs/contracts/ASC-0036-cross-repo-semantic-alignment.md"],
                "repos": ["myworld", "hivemind", "memoryOS", "CapabilityOS"],
                "allowed_files": ["hivemind/AGENTS.md", "memoryOS/AGENTS.md"],
                "forbidden_files": [".env"],
            }
        )

        self.assertEqual(result.decision, "allow")
        self.assertNotIn("myworld_local_operator_scope", result.reason_codes)

    def test_myworld_local_operator_scope_escalates_private_raw_paths(self) -> None:
        result = evaluate_action(
            {
                "action_type": "dispatch_packet",
                "target_repo": "myworld",
                "authority": "accepted_contract",
                "risk": "low",
                "privacy": "local",
                "cost": "free",
                "has_contract": True,
                "evidence_refs": ["docs/contracts/ASC-0060-action-policy-scope-aware.md"],
                "repos": ["myworld"],
                "allowed_files": ["_from_desktop/export.json"],
                "forbidden_files": [".env"],
            }
        )

        self.assertEqual(result.decision, "escalate")
        self.assertIn("human_checkpoint_required:private_remote_data", result.reason_codes)

    def test_bind_capability_is_policy_forbidden(self) -> None:
        result = evaluate_action(
            {
                "action_type": "bind_capability",
                "target_repo": "CapabilityOS",
                "risk": "low",
                "privacy": "local",
                "cost": "free",
                "has_contract": True,
                "evidence_refs": ["docs/contracts/ASC-0107-citizenship-implementation.md"],
                "agent": "codex@myworld",
            }
        )

        self.assertEqual(result.decision, "deny")
        self.assertIn("forbidden_action:bind_capability", result.reason_codes)

    def test_citizenship_denial_is_visible_to_policy(self) -> None:
        result = evaluate_action(
            {
                "action_type": "release_dispatch",
                "target_repo": "myworld",
                "risk": "low",
                "privacy": "local",
                "cost": "free",
                "has_contract": True,
                "evidence_refs": ["docs/contracts/ASC-0107-citizenship-implementation.md"],
                "agent": "unknown_outsider",
            }
        )

        self.assertEqual(result.decision, "hold")
        self.assertTrue(any(reason.startswith("authority_denied:") for reason in result.reason_codes))

    def test_owner_bound_human_approved_dispatch_allows_child_repo_boundary_work(self) -> None:
        result = evaluate_action(
            {
                "action_type": "dispatch_packet",
                "target_repo": "hivemind",
                "authority": "accepted_contract",
                "risk": "low",
                "privacy": "remote",
                "cost": "free",
                "has_contract": True,
                "evidence_refs": ["docs/contracts/ASC-0263-hivemind-serving-worker-resume.md"],
                "human_approved": True,
                "irreversible": False,
                "external_effect": True,
                "uses_credentials": True,
                "public_communication": False,
                "legal_or_safety_impact": False,
                "real_world_authority": False,
                "sends_private_data": False,
                "repos": ["hivemind"],
                "allowed_files": [
                    "hivemind/hivemind/serving_worker.py",
                    "hivemind/tests/test_serving_worker.py",
                    "hivemind/docs/**",
                ],
                "forbidden_files": [".env", "credential vault contents", "raw provider logs"],
            }
        )

        self.assertEqual(result.decision, "allow")
        self.assertTrue(result.allowed_to_execute)
        self.assertIn("owner_bound_human_approved_dispatch", result.reason_codes)

    def test_owner_bound_dispatch_does_not_allow_cross_repo_files(self) -> None:
        result = evaluate_action(
            {
                "action_type": "dispatch_packet",
                "target_repo": "hivemind",
                "authority": "accepted_contract",
                "risk": "low",
                "privacy": "remote",
                "cost": "free",
                "has_contract": True,
                "evidence_refs": ["docs/contracts/ASC-0263-hivemind-serving-worker-resume.md"],
                "human_approved": True,
                "irreversible": False,
                "external_effect": True,
                "uses_credentials": True,
                "public_communication": False,
                "legal_or_safety_impact": False,
                "real_world_authority": False,
                "sends_private_data": False,
                "repos": ["hivemind"],
                "allowed_files": ["hivemind/hivemind/serving_worker.py", "memoryOS/memoryos/serving_memory.py"],
                "forbidden_files": [".env"],
            }
        )

        self.assertEqual(result.decision, "hold")
        self.assertIn("requires_more_specific_policy", result.reason_codes)

    def test_owner_bound_dispatch_still_escalates_without_human_approval(self) -> None:
        result = evaluate_action(
            {
                "action_type": "dispatch_packet",
                "target_repo": "hivemind",
                "authority": "accepted_contract",
                "risk": "low",
                "privacy": "remote",
                "cost": "free",
                "has_contract": True,
                "evidence_refs": ["docs/contracts/ASC-0263-hivemind-serving-worker-resume.md"],
                "human_approved": False,
                "irreversible": False,
                "external_effect": True,
                "uses_credentials": True,
                "public_communication": False,
                "legal_or_safety_impact": False,
                "real_world_authority": False,
                "sends_private_data": False,
                "repos": ["hivemind"],
                "allowed_files": ["hivemind/hivemind/serving_worker.py"],
                "forbidden_files": [".env"],
            }
        )

        self.assertEqual(result.decision, "escalate")
        self.assertIn("human_checkpoint_required:external_effect", result.reason_codes)

    def test_myworld_human_approved_local_dispatch_allows_redaction_boundary_terms(self) -> None:
        result = evaluate_action(
            {
                "action_type": "dispatch_packet",
                "target_repo": "myworld",
                "authority": "accepted_contract",
                "risk": "high",
                "privacy": "remote",
                "cost": "free",
                "has_contract": True,
                "evidence_refs": ["docs/contracts/ASC-0267-serving-support-redaction.md"],
                "human_approved": True,
                "irreversible": False,
                "external_effect": True,
                "uses_credentials": True,
                "public_communication": False,
                "legal_or_safety_impact": False,
                "real_world_authority": False,
                "sends_private_data": False,
                "repos": ["myworld"],
                "allowed_files": [
                    "scripts/aios_serving_support.py",
                    "tests/test_aios_serving_support.py",
                    "docs/contracts/ASC-0267-serving-support-redaction.md",
                ],
                "forbidden_files": [".env", "credential vault contents", "raw provider logs"],
            }
        )

        self.assertEqual(result.decision, "allow")
        self.assertTrue(result.allowed_to_execute)
        self.assertIn("myworld_human_approved_local_dispatch", result.reason_codes)

    def test_myworld_human_approved_local_dispatch_blocks_private_paths(self) -> None:
        result = evaluate_action(
            {
                "action_type": "dispatch_packet",
                "target_repo": "myworld",
                "authority": "accepted_contract",
                "risk": "high",
                "privacy": "remote",
                "cost": "free",
                "has_contract": True,
                "evidence_refs": ["docs/contracts/ASC-0267-serving-support-redaction.md"],
                "human_approved": True,
                "irreversible": False,
                "external_effect": True,
                "uses_credentials": True,
                "public_communication": False,
                "legal_or_safety_impact": False,
                "real_world_authority": False,
                "sends_private_data": False,
                "repos": ["myworld"],
                "allowed_files": ["scripts/aios_serving_support.py", "_from_desktop/private.json"],
                "forbidden_files": [".env"],
            }
        )

        self.assertEqual(result.decision, "hold")
        self.assertIn("requires_more_specific_policy", result.reason_codes)


if __name__ == "__main__":
    unittest.main()
