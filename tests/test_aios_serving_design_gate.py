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
        "next_product_design_step": "ideate",
        "build_allowed": False,
        "stop_conditions": REQUIRED_STOP_CONDITIONS,
    }


def selection_gate(root: Path) -> dict:
    asset = root / "docs" / "product" / "assets" / "aios-serving-option-01-task-cabin.png"
    asset.parent.mkdir(parents=True, exist_ok=True)
    asset.write_text("fake image fixture\n", encoding="utf-8")
    return {
        "schema_version": "aios.serving_design_gate.v1",
        "product_goal": "End user creates an AIOS task and reviews progress, approval, memory draft, and artifact output.",
        "visual_target_type": "needs_selection",
        "visual_target_ref": "",
        "interactivity_level": "full",
        "confirmed_by_user": True,
        "next_product_design_step": "select_visual_target",
        "build_allowed": False,
        "ideation_options": [
            {
                "id": "option_1_task_cabin",
                "label": "Task Cabin",
                "path": "docs/product/assets/aios-serving-option-01-task-cabin.png",
            }
        ],
        "selected_option_id": "",
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

    def test_complete_needs_ideation_gate_is_ready_for_ideation_not_build(self) -> None:
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
            self.assertEqual(payload["next_action"], "product_design_ideate")
            self.assertEqual(payload["artifact"]["next_product_design_step"], "ideate")
            self.assertFalse(payload["artifact"]["build_allowed"])

    def test_needs_ideation_cannot_claim_build_allowed(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            artifact = root / ".aios" / "serving" / "design_gate.json"
            artifact.parent.mkdir(parents=True)
            data = complete_gate()
            data["build_allowed"] = True
            artifact.write_text(json.dumps(data), encoding="utf-8")

            result = self.run_gate(root, "assess", "--root", root.as_posix(), "--json")

            self.assertEqual(result.returncode, 0, result.stderr)
            payload = json.loads(result.stdout)
            self.assertFalse(payload["ready"])
            self.assertTrue(any("needs_ideation requires build_allowed=false" in error for error in payload["errors"]))

    def test_concrete_visual_target_requires_prototype_and_build_allowed(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            artifact = root / ".aios" / "serving" / "design_gate.json"
            artifact.parent.mkdir(parents=True)
            data = complete_gate()
            data["visual_target_type"] = "screenshot"
            data["visual_target_ref"] = "assets/serving-target.png"
            data["next_product_design_step"] = "prototype"
            data["build_allowed"] = True
            artifact.write_text(json.dumps(data), encoding="utf-8")

            result = self.run_gate(root, "assess", "--root", root.as_posix(), "--json")

            self.assertEqual(result.returncode, 0, result.stderr)
            payload = json.loads(result.stdout)
            self.assertTrue(payload["ready"], payload["errors"])
            self.assertEqual(payload["artifact"]["next_product_design_step"], "prototype")
            self.assertTrue(payload["artifact"]["build_allowed"])
            self.assertEqual(payload["next_action"], "ASC-0253")

    def test_needs_selection_gate_is_ready_for_selection_not_build(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            artifact = root / ".aios" / "serving" / "design_gate.json"
            artifact.parent.mkdir(parents=True)
            artifact.write_text(json.dumps(selection_gate(root)), encoding="utf-8")

            result = self.run_gate(root, "assess", "--root", root.as_posix(), "--json")

            self.assertEqual(result.returncode, 0, result.stderr)
            payload = json.loads(result.stdout)
            self.assertTrue(payload["ready"], payload["errors"])
            self.assertEqual(payload["next_action"], "product_design_select_visual_target")
            self.assertEqual(payload["artifact"]["next_product_design_step"], "select_visual_target")
            self.assertFalse(payload["artifact"]["build_allowed"])

    def test_questions_outputs_required_intake_fields(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            result = self.run_gate(root, "questions", "--json")

            self.assertEqual(result.returncode, 0, result.stderr)
            payload = json.loads(result.stdout)
            ids = [question["id"] for question in payload["questions"]]
            self.assertEqual(
                ids,
                [
                    "product_goal",
                    "visual_target_type",
                    "visual_target_ref",
                    "interactivity_level",
                    "confirmed_by_user",
                ],
            )
            self.assertEqual(payload["routing_rules"]["needs_ideation"]["next_product_design_step"], "ideate")
            self.assertFalse(payload["routing_rules"]["needs_ideation"]["build_allowed"])

    def test_draft_needs_ideation_does_not_write_without_flag(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            result = self.run_gate(
                root,
                "draft",
                "--root",
                root.as_posix(),
                "--product-goal",
                "End user creates and tracks an AIOS task.",
                "--visual-target-type",
                "needs_ideation",
                "--interactivity-level",
                "full",
                "--confirmed-by-user",
                "--json",
            )

            self.assertEqual(result.returncode, 0, result.stderr)
            payload = json.loads(result.stdout)
            self.assertTrue(payload["ready"], payload["errors"])
            self.assertFalse(payload["written"])
            self.assertEqual(payload["artifact"]["next_product_design_step"], "ideate")
            self.assertFalse(payload["artifact"]["build_allowed"])
            self.assertFalse((root / ".aios" / "serving" / "design_gate.json").exists())

    def test_select_requires_user_confirmation(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            artifact = root / ".aios" / "serving" / "design_gate.json"
            artifact.parent.mkdir(parents=True)
            artifact.write_text(json.dumps(selection_gate(root)), encoding="utf-8")

            result = self.run_gate(
                root,
                "select",
                "--root",
                root.as_posix(),
                "--option-id",
                "option_1_task_cabin",
                "--json",
            )

            self.assertEqual(result.returncode, 0, result.stderr)
            payload = json.loads(result.stdout)
            self.assertFalse(payload["ready"])
            self.assertTrue(any("--confirmed-by-user" in error for error in payload["errors"]))

    def test_select_unknown_option_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            artifact = root / ".aios" / "serving" / "design_gate.json"
            artifact.parent.mkdir(parents=True)
            artifact.write_text(json.dumps(selection_gate(root)), encoding="utf-8")

            result = self.run_gate(
                root,
                "select",
                "--root",
                root.as_posix(),
                "--option-id",
                "option_9_missing",
                "--confirmed-by-user",
                "--json",
            )

            self.assertEqual(result.returncode, 0, result.stderr)
            payload = json.loads(result.stdout)
            self.assertFalse(payload["ready"])
            self.assertTrue(any("unknown option_id" in error for error in payload["errors"]))

    def test_select_option_can_write_concrete_image_target(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            artifact = root / ".aios" / "serving" / "design_gate.json"
            artifact.parent.mkdir(parents=True)
            artifact.write_text(json.dumps(selection_gate(root)), encoding="utf-8")

            result = self.run_gate(
                root,
                "select",
                "--root",
                root.as_posix(),
                "--option-id",
                "option_1_task_cabin",
                "--confirmed-by-user",
                "--write",
                "--json",
            )

            self.assertEqual(result.returncode, 0, result.stderr)
            payload = json.loads(result.stdout)
            self.assertTrue(payload["ready"], payload["errors"])
            self.assertTrue(payload["written"])
            selected = json.loads(artifact.read_text(encoding="utf-8"))
            self.assertEqual(selected["visual_target_type"], "image")
            self.assertEqual(selected["selected_option_id"], "option_1_task_cabin")
            self.assertEqual(selected["next_product_design_step"], "prototype")
            self.assertTrue(selected["build_allowed"])

    def test_draft_concrete_visual_target_can_write_ready_gate(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            result = self.run_gate(
                root,
                "draft",
                "--root",
                root.as_posix(),
                "--product-goal",
                "End user creates and tracks an AIOS task.",
                "--visual-target-type",
                "screenshot",
                "--visual-target-ref",
                "assets/serving-target.png",
                "--interactivity-level",
                "full",
                "--confirmed-by-user",
                "--write",
                "--json",
            )

            self.assertEqual(result.returncode, 0, result.stderr)
            payload = json.loads(result.stdout)
            self.assertTrue(payload["ready"], payload["errors"])
            self.assertTrue(payload["written"])
            self.assertEqual(payload["artifact"]["next_product_design_step"], "prototype")
            self.assertTrue(payload["artifact"]["build_allowed"])
            artifact = root / ".aios" / "serving" / "design_gate.json"
            self.assertEqual(json.loads(artifact.read_text(encoding="utf-8")), payload["artifact"])


if __name__ == "__main__":
    unittest.main()
