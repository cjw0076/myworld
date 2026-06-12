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
    def run_readiness(self, root: Path) -> dict:
        result = subprocess.run(
            [sys.executable, SCRIPT.as_posix(), "--root", root.as_posix(), "--json"],
            text=True,
            capture_output=True,
            check=False,
        )
        self.assertTrue(result.stdout, result.stderr)
        return json.loads(result.stdout)

    def test_empty_repo_is_not_world_ready(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            payload = self.run_readiness(Path(tmp))

            self.assertEqual(payload["schema_version"], "aios.world_readiness.v1")
            self.assertFalse(payload["ready_for_world_deployment"])
            self.assertEqual(payload["met_count"], 0)
            self.assertEqual(payload["missing_count"], 7)
            self.assertEqual(payload["next_action"], "ASC-0235")

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
            self.assertIn("local self-maintaining", payload["local_completion"]["scope"])

    def test_all_dedicated_markers_reach_world_ready(self) -> None:
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

            self.assertTrue(payload["ready_for_world_deployment"])
            self.assertEqual(payload["met_count"], 7)
            self.assertFalse(payload["gaps"])

    def test_current_repo_keeps_local_completion_scope_separate(self) -> None:
        payload = self.run_readiness(ROOT)

        self.assertTrue(payload["ready_for_world_deployment"])
        self.assertTrue(payload["local_completion"]["present"])
        self.assertIn("not world-deployment readiness", payload["local_completion"]["scope"])
        self.assertEqual(payload["met_count"], 7)
        self.assertEqual(payload["partial_count"], 0)
        self.assertFalse(payload["gaps"])


if __name__ == "__main__":
    unittest.main()
