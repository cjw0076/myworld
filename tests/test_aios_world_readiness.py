import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "aios_world_readiness.py"


def touch(root: Path, rel: str) -> None:
    path = root / rel
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("# fixture\n", encoding="utf-8")


def write_concrete_design_gate(root: Path) -> None:
    path = root / ".aios" / "serving" / "design_gate.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(
            {
                "schema_version": "aios.serving_design_gate.v1",
                "product_goal": "Real end-user AIOS serving product.",
                "visual_target_type": "screenshot",
                "visual_target_ref": "docs/product/serving-target.png",
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


def write_serving_release_markers(root: Path) -> None:
    write_concrete_design_gate(root)
    for rel in (
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
        "scripts/aios_serving_release_gate.py",
        "tests/test_aios_serving_release_gate.py",
        "scripts/aios_world_readiness.py",
        "tests/test_aios_world_readiness.py",
        "GenesisOS/genesisos/serving_prelaunch.py",
        "GenesisOS/tests/test_serving_prelaunch.py",
        ".aios/serving/proofs/genesis_prelaunch.json",
    ):
        touch(root, rel)


class AiosWorldReadinessTest(unittest.TestCase):
    def run_readiness_process(self, root: Path, *, json_flag: bool = True) -> subprocess.CompletedProcess[str]:
        args = [sys.executable, SCRIPT.as_posix(), "--root", root.as_posix()]
        if json_flag:
            args.append("--json")
        return subprocess.run(
            args,
            text=True,
            capture_output=True,
            check=False,
        )

    def run_readiness(self, root: Path) -> dict:
        result = self.run_readiness_process(root)
        self.assertTrue(result.stdout, result.stderr)
        return json.loads(result.stdout)

    def test_empty_repo_is_not_world_ready(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            payload = self.run_readiness(Path(tmp))

            self.assertEqual(payload["schema_version"], "aios.world_readiness.v1")
            self.assertFalse(payload["ready_for_world_deployment"])
            self.assertEqual(payload["met_count"], 0)
            self.assertEqual(payload["missing_count"], 8)
            self.assertEqual(payload["next_action"], "ASC-0235")

    def test_json_mode_returns_zero_even_when_not_world_ready(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            result = self.run_readiness_process(Path(tmp), json_flag=True)

            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertFalse(json.loads(result.stdout)["ready_for_world_deployment"])

    def test_text_mode_returns_nonzero_when_not_world_ready(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            result = self.run_readiness_process(Path(tmp), json_flag=False)

            self.assertEqual(result.returncode, 1)
            self.assertIn("world_deployment_ready=False", result.stdout)

    def test_partial_markers_do_not_overclaim_world_readiness(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            for rel in (
                "scripts/aios_loop.py",
                "scripts/aios_work.py",
                "scripts/aios_sandbox.py",
                "scripts/aios_vault.py",
                "scripts/aios_multi_substrate.py",
                "scripts/aios_boundary_classifier.py",
                "scripts/aios_convergence_audit.py",
            ):
                touch(root, rel)

            payload = self.run_readiness(root)

            self.assertFalse(payload["ready_for_world_deployment"])
            self.assertEqual(payload["met_count"], 0)
            self.assertEqual(payload["partial_count"], 7)
            self.assertEqual(payload["missing_count"], 1)  # serving axis still missing
            self.assertIn("local self-maintaining", payload["local_completion"]["scope"])

    def test_seven_infra_markers_alone_not_world_ready(self) -> None:
        # ASC-0252: infrastructure axes alone must not claim world-ready;
        # the serving axis is still missing when only the 7 infra files exist.
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            for rel in (
                "scripts/aios_turn_loop.py",
                "scripts/aios_work_lineage.py",
                "hivemind/hivemind/cloud_isolation.py",
                "scripts/aios_credential_broker.py",
                "scripts/aios_trace_graph.py",
                "CapabilityOS/capabilityos/skillos_registry.py",
                "scripts/aios_seci_entropy.py",
            ):
                touch(root, rel)

            payload = self.run_readiness(root)

            self.assertFalse(payload["ready_for_world_deployment"])
            self.assertEqual(payload["met_count"], 7)
            self.assertEqual(payload["partial_count"], 1)   # serving release gate is not ready
            self.assertEqual(payload["missing_count"], 0)
            self.assertTrue(payload["gaps"])

    def test_asc0251_spec_docs_alone_not_world_ready(self) -> None:
        # The design/spec docs from ASC-0251 are partial markers only;
        # they must not satisfy the serving axis.
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            for rel in (
                "docs/product/AIOS_END_USER_SERVING_INTERFACE_SPEC.md",
                "docs/product/AIOS_SERVING_INTERFACE_ROUTE_MAP.md",
            ):
                touch(root, rel)

            payload = self.run_readiness(root)

            self.assertFalse(payload["ready_for_world_deployment"])
            serving = next(c for c in payload["checks"] if c["axis_id"] == "end_user_serving_readiness")
            self.assertEqual(serving["status"], "partial")
            self.assertNotEqual(serving["status"], "met")

    def test_serving_session_primitive_alone_is_partial_not_met(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            touch(root, "scripts/aios_serving_session.py")

            payload = self.run_readiness(root)

            self.assertFalse(payload["ready_for_world_deployment"])
            serving = next(c for c in payload["checks"] if c["axis_id"] == "end_user_serving_readiness")
            self.assertEqual(serving["status"], "partial")
            self.assertEqual(
                serving["evidence"],
                ["aios_serving_release_gate:not_ready", "scripts/aios_serving_session.py"],
            )
            self.assertNotEqual(serving["status"], "met")

    def test_serving_design_gate_script_is_partial_not_met(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            touch(root, "scripts/aios_serving_design_gate.py")

            payload = self.run_readiness(root)

            self.assertFalse(payload["ready_for_world_deployment"])
            serving = next(c for c in payload["checks"] if c["axis_id"] == "end_user_serving_readiness")
            self.assertEqual(serving["status"], "partial")
            self.assertEqual(
                serving["evidence"],
                ["scripts/aios_serving_design_gate.py", "aios_serving_release_gate:not_ready"],
            )
            self.assertIn("Product Design gate", serving["gap"])
            self.assertNotEqual(serving["status"], "met")

    def test_old_serving_markers_alone_do_not_reach_world_ready(self) -> None:
        # ASC-0261: the old three serving markers are not enough; the
        # production-serving release gate must also pass all ASC-0260 slices.
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            for rel in (
                "scripts/aios_turn_loop.py",
                "scripts/aios_work_lineage.py",
                "hivemind/hivemind/cloud_isolation.py",
                "scripts/aios_credential_broker.py",
                "scripts/aios_trace_graph.py",
                "CapabilityOS/capabilityos/skillos_registry.py",
                "scripts/aios_seci_entropy.py",
                # serving axis met_markers
                "apps/serving/index.html",
                "scripts/aios_serving_session.py",
                "tests/test_aios_serving_e2e.py",
            ):
                touch(root, rel)

            payload = self.run_readiness(root)

            self.assertFalse(payload["ready_for_world_deployment"])
            serving = next(c for c in payload["checks"] if c["axis_id"] == "end_user_serving_readiness")
            self.assertEqual(serving["status"], "partial")
            self.assertIn("production-serving release gate", serving["gap"])

    def test_all_eight_axes_met_reach_world_ready(self) -> None:
        # Only when all 8 axes and the ASC-0260 serving-release slices have
        # their evidence markers does world-ready become true.
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            for rel in (
                "scripts/aios_turn_loop.py",
                "scripts/aios_work_lineage.py",
                "hivemind/hivemind/cloud_isolation.py",
                "scripts/aios_credential_broker.py",
                "scripts/aios_trace_graph.py",
                "CapabilityOS/capabilityos/skillos_registry.py",
                "scripts/aios_seci_entropy.py",
            ):
                touch(root, rel)
            write_serving_release_markers(root)

            payload = self.run_readiness(root)

            self.assertTrue(payload["ready_for_world_deployment"])
            self.assertEqual(payload["met_count"], 8)
            self.assertFalse(payload["gaps"])

    def test_current_repo_serving_spec_only_not_world_ready(self) -> None:
        # Current repo: 7 infra axes met + serving axis partial (spec exists, no implementation).
        payload = self.run_readiness(ROOT)

        self.assertFalse(payload["ready_for_world_deployment"])
        self.assertTrue(payload["local_completion"]["present"])
        self.assertIn("not world-deployment readiness", payload["local_completion"]["scope"])
        self.assertEqual(payload["met_count"], 7)
        self.assertEqual(payload["partial_count"], 1)
        serving = next(c for c in payload["checks"] if c["axis_id"] == "end_user_serving_readiness")
        self.assertEqual(serving["status"], "partial")
        self.assertEqual(serving["next_contract"], "ASC-0253")


if __name__ == "__main__":
    unittest.main()
