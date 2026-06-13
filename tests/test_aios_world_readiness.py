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
            self.assertEqual(payload["missing_count"], 1)   # serving axis missing
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
            self.assertEqual(serving["evidence"], ["scripts/aios_serving_session.py"])
            self.assertNotEqual(serving["status"], "met")

    def test_all_eight_axes_met_reach_world_ready(self) -> None:
        # Only when all 8 axes have their met_markers does world-ready become true.
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
