import json
import subprocess
import sys
import unittest
from pathlib import Path

from scripts.aios_work_praxis import draft_praxis, validate_praxis


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "aios_work_praxis.py"


class AiosWorkPraxisTests(unittest.TestCase):
    def test_draft_assigns_os_layers_and_specialists(self) -> None:
        payload = draft_praxis("Build AIOS visual control app with provider API routes")

        self.assertEqual(payload["schema_version"], "aios.production_praxis.v1")
        self.assertEqual(payload["memory_context"]["owner"], "MemoryOS")
        self.assertEqual(payload["capability_routes"]["owner"], "CapabilityOS")
        self.assertEqual(payload["genesis_reframe"]["owner"], "GenesisOS")
        self.assertEqual(payload["hive_execution_plan"]["owner"], "Hive Mind")
        self.assertEqual(payload["external_resource_check"]["status"], "required")
        agents = {item["agent"] for item in payload["specialist_assignment"]}
        self.assertIn("codex", agents)
        self.assertIn("claude", agents)
        self.assertIn("local-llm", agents)

    def test_validate_accepts_complete_praxis_fixture(self) -> None:
        payload = json.loads((ROOT / "tests" / "fixtures" / "praxis" / "valid_praxis.json").read_text(encoding="utf-8"))

        self.assertEqual(validate_praxis(payload), [])

    def test_validate_rejects_flat_single_agent_plan(self) -> None:
        payload = draft_praxis("Implement a product feature")
        payload["memory_context"] = {"status": "used", "evidence_refs": ["aios://memory/mem_1"]}
        payload["capability_routes"] = {"status": "used", "routes": ["aios://capability/cap_1"]}
        payload["external_resource_check"] = {"status": "optional_with_reason", "reason": "local deterministic test"}
        payload["genesis_reframe"] = {
            "status": "used",
            "frictions": ["The current workflow hides the next action."],
            "alternative_frames": ["queue", "cockpit"],
        }
        payload["hive_execution_plan"] = {"status": "planned", "verification_gate": "python -m unittest tests/test_x.py"}
        payload["specialist_assignment"] = [{"agent": "codex", "strength": "general", "job": "do everything"}]

        self.assertIn("specialist_assignment_too_flat", validate_praxis(payload))

    def test_validate_rejects_missing_used_evidence(self) -> None:
        payload = json.loads((ROOT / "tests" / "fixtures" / "praxis" / "valid_praxis.json").read_text(encoding="utf-8"))
        payload["memory_context"]["evidence_refs"] = []
        payload["capability_routes"]["routes"] = []
        payload["external_resource_check"]["evidence_refs"] = []
        payload["genesis_reframe"]["alternative_frames"] = []
        payload["hive_execution_plan"]["verification_gate"] = ""

        errors = validate_praxis(payload)

        self.assertIn("memory_context_evidence_missing", errors)
        self.assertIn("capability_routes_missing", errors)
        self.assertIn("external_resource_evidence_missing", errors)
        self.assertIn("genesis_alternatives_missing", errors)
        self.assertIn("hive_gate_missing", errors)

    def test_cli_draft_and_validate_emit_json(self) -> None:
        draft = subprocess.run(
            [sys.executable, SCRIPT.as_posix(), "draft", "--task", "AIOS multimodal control app", "--json"],
            cwd=ROOT,
            text=True,
            capture_output=True,
            check=True,
        )
        self.assertEqual(json.loads(draft.stdout)["external_resource_check"]["status"], "required")

        valid = subprocess.run(
            [
                sys.executable,
                SCRIPT.as_posix(),
                "validate",
                "tests/fixtures/praxis/valid_praxis.json",
                "--json",
            ],
            cwd=ROOT,
            text=True,
            capture_output=True,
            check=True,
        )
        self.assertTrue(json.loads(valid.stdout)["ok"])


if __name__ == "__main__":
    unittest.main()
