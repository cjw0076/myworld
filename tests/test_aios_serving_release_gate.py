import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "aios_serving_release_gate.py"


def touch(root: Path, rel: str) -> None:
    path = root / rel
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("# fixture\n", encoding="utf-8")


def write_design_gate(root: Path, *, concrete: bool) -> None:
    artifact = root / ".aios" / "serving" / "design_gate.json"
    artifact.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "schema_version": "aios.serving_design_gate.v1",
        "product_goal": "Real end-user AIOS serving product.",
        "visual_target_type": "screenshot" if concrete else "needs_ideation",
        "visual_target_ref": "docs/product/serving-target.png" if concrete else "",
        "interactivity_level": "full",
        "confirmed_by_user": True,
        "next_product_design_step": "prototype" if concrete else "ideate",
        "build_allowed": concrete,
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
    artifact.write_text(json.dumps(payload), encoding="utf-8")


class AiosServingReleaseGateTest(unittest.TestCase):
    def run_gate(self, root: Path, *, json_flag: bool = True) -> subprocess.CompletedProcess[str]:
        args = [sys.executable, SCRIPT.as_posix(), "assess", "--root", root.as_posix()]
        if json_flag:
            args.append("--json")
        return subprocess.run(args, text=True, capture_output=True, check=False)

    def load_gate(self, root: Path) -> dict:
        result = self.run_gate(root)
        self.assertEqual(result.returncode, 0, result.stderr)
        return json.loads(result.stdout)

    def test_missing_repo_is_not_ready(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            payload = self.load_gate(Path(tmp))

            self.assertEqual(payload["schema_version"], "aios.serving_release_gate.v1")
            self.assertFalse(payload["ready_for_production_serving"])
            self.assertEqual(payload["met_count"], 0)
            self.assertEqual(payload["missing_count"], 9)
            self.assertIn("Product Design ideation", payload["next_action"])

    def test_text_mode_returns_nonzero_until_ready(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            result = self.run_gate(Path(tmp), json_flag=False)

            self.assertEqual(result.returncode, 1)
            self.assertIn("serving_release_ready=False", result.stdout)

    def test_needs_ideation_design_gate_is_partial_not_build_ready(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            write_design_gate(root, concrete=False)
            touch(root, "docs/product/AIOS_END_USER_SERVING_INTERFACE_SPEC.md")

            payload = self.load_gate(root)

            design = payload["slices"][0]
            self.assertEqual(design["slice_id"], "product_design_visual_target")
            self.assertEqual(design["status"], "partial")
            self.assertEqual(design["design_gate"]["status"], "needs_ideation")
            self.assertIn("build_allowed=true", design["missing"])
            self.assertFalse(payload["ready_for_production_serving"])

    def test_concrete_design_gate_still_requires_design_brief_marker(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            write_design_gate(root, concrete=True)

            payload = self.load_gate(root)

            design = payload["slices"][0]
            self.assertEqual(design["status"], "partial")
            self.assertIn("docs/product/AIOS_SERVING_DESIGN_BRIEF.md", design["missing"])

    def test_all_slice_markers_ready(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            write_design_gate(root, concrete=True)
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
                "docs/research/AIOS_AGENT_SERVICE_BASELINE_2026-06-13.md",
                "scripts/aios_serving_release_gate.py",
                "tests/test_aios_serving_release_gate.py",
                "scripts/aios_world_readiness.py",
                "tests/test_aios_world_readiness.py",
                "GenesisOS/genesisos/serving_prelaunch.py",
                "GenesisOS/tests/test_serving_prelaunch.py",
                ".aios/serving/proofs/genesis_prelaunch.json",
            ):
                touch(root, rel)

            payload = self.load_gate(root)

            self.assertTrue(payload["ready_for_production_serving"], payload)
            self.assertEqual(payload["met_count"], 9)
            self.assertEqual(payload["missing_count"], 0)

    def test_current_repo_not_ready(self) -> None:
        payload = self.load_gate(ROOT)

        self.assertFalse(payload["ready_for_production_serving"])
        self.assertEqual(payload["slice_count"], 9)
        design = payload["slices"][0]
        self.assertEqual(design["status"], "partial")
        self.assertFalse(design["design_gate"]["build_allowed"])


if __name__ == "__main__":
    unittest.main()
