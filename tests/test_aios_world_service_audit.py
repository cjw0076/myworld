import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "aios_world_service_audit.py"


def touch(root: Path, rel: str) -> None:
    path = root / rel
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("# fixture\n", encoding="utf-8")


class AiosWorldServiceAuditTest(unittest.TestCase):
    def run_audit_process(self, root: Path, *, json_flag: bool = True) -> subprocess.CompletedProcess[str]:
        args = [sys.executable, SCRIPT.as_posix(), "--root", root.as_posix()]
        if json_flag:
            args.append("--json")
        return subprocess.run(args, text=True, capture_output=True, check=False)

    def run_audit(self, root: Path) -> dict:
        result = self.run_audit_process(root)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertTrue(result.stdout)
        return json.loads(result.stdout)

    def requirement(self, payload: dict, requirement_id: str) -> dict:
        return next(row for row in payload["requirements"] if row["requirement_id"] == requirement_id)

    def test_empty_root_is_not_complete(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            payload = self.run_audit(Path(tmp))

        self.assertEqual(payload["schema_version"], "aios.world_service_objective_audit.v1")
        self.assertEqual(payload["audit_type"], "read_only_objective_fit")
        self.assertFalse(payload["ready_for_goal_completion"])
        self.assertEqual(payload["counts"]["proven"], 0)
        self.assertEqual(payload["counts"]["missing"], payload["requirement_count"])
        self.assertIn("existing_gates", payload)

    def test_weak_marker_does_not_count_as_partial_or_proven(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            touch(root, "docs/contracts/ASC-0277-memoryos-cli-log-asset-pool-ledger.md")

            payload = self.run_audit(root)

        row = self.requirement(payload, "cli_log_asset_pool")
        self.assertEqual(row["status"], "weak")
        self.assertIn("memoryOS/memoryos/cli_log_asset.py", row["missing_proof"])
        self.assertFalse(payload["ready_for_goal_completion"])

    def test_requirement_is_proven_only_when_all_proof_markers_exist(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            touch(root, "memoryOS/memoryos/cli_log_asset.py")
            touch(root, "memoryOS/tests/test_cli_log_asset.py")

            payload = self.run_audit(root)

        row = self.requirement(payload, "cli_log_asset_pool")
        self.assertEqual(row["status"], "proven")
        self.assertEqual(row["missing_proof"], [])

    def test_partial_marker_keeps_requirement_partial(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            touch(root, "docs/AIOS_DEPLOY_MANIFEST.md")
            touch(root, "scripts/aios_launcher.py")

            payload = self.run_audit(root)

        row = self.requirement(payload, "live_public_hosting_proof")
        self.assertEqual(row["status"], "partial")
        self.assertIn(".aios/serving/proofs/public_url.json", row["missing_proof"])

    def test_contract_hygiene_flags_green_gate_with_proposed_contract(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            for rel in (
                ".aios/serving/design_gate.json",
                "docs/product/AIOS_SERVING_DESIGN_BRIEF.md",
                "apps/serving/index.html",
                "tests/test_aios_serving_e2e.py",
                ".aios/serving/proofs/browser_375.json",
                ".aios/serving/proofs/browser_1280.json",
                "scripts/aios_serving_session.py",
                "tests/test_aios_serving_session.py",
                "tests/test_aios_dispatch.py",
                "tests/test_aios_round_controller.py",
                "hivemind/hivemind/serving_worker.py",
                "hivemind/tests/test_serving_worker.py",
                "memoryOS/memoryos/serving_memory.py",
                "memoryOS/tests/test_serving_memory.py",
                "CapabilityOS/capabilityos/serving_access.py",
                "CapabilityOS/tests/test_serving_access.py",
                "scripts/aios_serving_support.py",
                "tests/test_aios_serving_support.py",
                "docs/research/AIOS_AGENT_SERVICE_BASELINE_2026-06-13.md",
                "scripts/aios_serving_release_gate.py",
                "tests/test_aios_serving_release_gate.py",
                "scripts/aios_world_readiness.py",
                "tests/test_aios_world_readiness.py",
                "GenesisOS/genesisos/serving_prelaunch.py",
                "GenesisOS/tests/test_serving_prelaunch.py",
                ".aios/serving/proofs/genesis_prelaunch.json",
                "docs/contracts/ASC-0253-end-user-serving-prototype-scope.md",
            ):
                touch(root, rel)
            (root / ".aios/serving/design_gate.json").write_text(
                json.dumps(
                    {
                        "schema_version": "aios.serving_design_gate.v1",
                        "product_goal": "Real AIOS serving",
                        "visual_target_type": "design_system",
                        "visual_target_ref": "apps/control/",
                        "interactivity_level": "full",
                        "confirmed_by_user": True,
                        "next_product_design_step": "prototype",
                        "build_allowed": True,
                        "stop_conditions": [
                            "ui_implementation_before_visual_target",
                            "serving_ui_reuses_operator_control_center",
                            "user_memory_not_visible",
                            "session_boundary_ambiguous",
                            "approval_path_missing",
                            "privacy_boundary_ambiguous",
                            "world_readiness_claim_without_browser_proof",
                        ],
                    }
                ),
                encoding="utf-8",
            )
            (root / "docs/contracts/ASC-0253-end-user-serving-prototype-scope.md").write_text(
                "---\ncontract_id: ASC-0253\nstatus: proposed\n---\n",
                encoding="utf-8",
            )

            payload = self.run_audit(root)

        self.assertTrue(payload["existing_gates"]["serving_release_gate"]["ready"])
        self.assertTrue(any(note["contract_id"] == "ASC-0253" for note in payload["contract_hygiene"]))
        self.assertFalse(payload["completion_claim_supported"])

    def test_text_mode_returns_nonzero_when_goal_not_complete(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            result = self.run_audit_process(Path(tmp), json_flag=False)

        self.assertEqual(result.returncode, 1)
        self.assertIn("world_service_goal_complete=False", result.stdout)

    def test_current_repo_audit_is_honest_about_remaining_gaps(self) -> None:
        payload = self.run_audit(ROOT)

        self.assertFalse(payload["ready_for_goal_completion"])
        self.assertFalse(payload["completion_claim_supported"])
        statuses = {row["requirement_id"]: row["status"] for row in payload["requirements"]}
        self.assertIn(statuses["cli_log_asset_pool"], {"weak", "partial", "missing"})
        self.assertIn(statuses["provider_managed_state_absorption"], {"weak", "partial", "missing"})
        self.assertIn("existing_gates", payload)


if __name__ == "__main__":
    unittest.main()
