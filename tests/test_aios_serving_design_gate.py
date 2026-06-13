import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "aios_serving_design_gate.py"


REQUIRED_STOP_CONDITIONS = [
    "ui_implementation_before_visual_target",
    "serving_ui_reuses_operator_control_center",
    "user_memory_not_visible",
    "session_boundary_ambiguous",
    "approval_path_missing",
    "privacy_boundary_ambiguous",
    "world_readiness_claim_without_browser_proof",
]


def complete_gate() -> dict:
    return {
        "schema_version": "aios.serving_design_gate.v1",
        "product_goal": "End user creates an AIOS task and reviews progress, approval, memory draft, and artifact output.",
        "visual_target_type": "needs_ideation",
        "visual_target_ref": "",
        "interactivity_level": "full",
        "confirmed_by_user": True,
        "build_allowed": True,
        "stop_conditions": REQUIRED_STOP_CONDITIONS,
    }


class AiosServingDesignGateTest(unittest.TestCase):
    def run_gate(self, root: Path, *args: str) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            [sys.executable, SCRIPT.as_posix(), *args],
            cwd=root,
            text=True,
            capture_output=True,
            check=False,
        )

    def test_missing_gate_returns_json_not_ready(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            result = self.run_gate(root, "assess", "--root", root.as_posix(), "--json")

            self.assertEqual(result.returncode, 0, result.stderr)
            payload = json.loads(result.stdout)
            self.assertFalse(payload["ready"])
            self.assertEqual(payload["status"], "missing")
            self.assertEqual(payload["next_action"], "product_design_get_context")

    def test_text_mode_returns_nonzero_when_missing(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            result = self.run_gate(root, "assess", "--root", root.as_posix())

            self.assertEqual(result.returncode, 1)
            self.assertIn("serving_design_gate=missing", result.stdout)

    def test_incomplete_gate_requires_user_confirmation_and_stop_conditions(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            artifact = root / ".aios" / "serving" / "design_gate.json"
            artifact.parent.mkdir(parents=True)
            data = complete_gate()
            data["confirmed_by_user"] = False
            data["stop_conditions"] = []
            artifact.write_text(json.dumps(data), encoding="utf-8")

            result = self.run_gate(root, "assess", "--root", root.as_posix(), "--json")

            self.assertEqual(result.returncode, 0, result.stderr)
            payload = json.loads(result.stdout)
            self.assertFalse(payload["ready"])
            self.assertEqual(payload["status"], "incomplete")
            self.assertTrue(any("confirmed_by_user" in error for error in payload["errors"]))
            self.assertTrue(any("stop_conditions missing" in error for error in payload["errors"]))

    def test_visual_target_ref_required_unless_needs_ideation(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            artifact = root / ".aios" / "serving" / "design_gate.json"
            artifact.parent.mkdir(parents=True)
            data = complete_gate()
            data["visual_target_type"] = "screenshot"
            artifact.write_text(json.dumps(data), encoding="utf-8")

            result = self.run_gate(root, "assess", "--root", root.as_posix(), "--json")

            self.assertEqual(result.returncode, 0, result.stderr)
            payload = json.loads(result.stdout)
            self.assertTrue(any("visual_target_ref is required" in error for error in payload["errors"]))

    def test_complete_gate_is_ready_but_only_points_to_asc0253(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            artifact = root / ".aios" / "serving" / "design_gate.json"
            artifact.parent.mkdir(parents=True)
            artifact.write_text(json.dumps(complete_gate()), encoding="utf-8")

            result = self.run_gate(root, "assess", "--root", root.as_posix(), "--json")

            self.assertEqual(result.returncode, 0, result.stderr)
            payload = json.loads(result.stdout)
            self.assertTrue(payload["ready"])
            self.assertEqual(payload["status"], "ready")
            self.assertEqual(payload["next_action"], "ASC-0253")


if __name__ == "__main__":
    unittest.main()
