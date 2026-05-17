import re
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SPEC = ROOT / "docs" / "AIOS_AGENT_INTERFACE.md"


class AiosAgentInterfaceSpecTest(unittest.TestCase):
    def text(self) -> str:
        return SPEC.read_text(encoding="utf-8")

    def test_spec_exists_and_stays_tiny(self) -> None:
        text = self.text()

        self.assertLessEqual(len(text.splitlines()), 100)
        self.assertIn("AIOS Agent Interface v0.1", text)

    def test_required_schema_fields_are_present(self) -> None:
        text = self.text()
        fields = [
            "spec_version",
            "agent_id",
            "substrate",
            "observed_at",
            "context",
            "event_type",
            "summary",
            "evidence_refs",
            "privacy_class",
            "recommended_route",
        ]

        for field in fields:
            self.assertRegex(text, rf"(^|[^A-Za-z0-9_]){re.escape(field)}([^A-Za-z0-9_]|$)")

    def test_design_requirements_from_asc_0089_are_represented(self) -> None:
        text = self.text()

        self.assertIn("$AIOS_ROOT/.aios/observation_buffer/<agent_id>/", text)
        self.assertIn("~/.aios/observation_buffer/<agent_id>/", text)
        self.assertIn("source_file", text)
        self.assertIn("operator_turn", text)
        self.assertIn("Known Limitations", text)
        self.assertIn("No sync daemon", text)
        self.assertIn("Retention", text)

    def test_b5_infrastructure_is_not_claimed(self) -> None:
        text = self.text()

        self.assertNotIn("aios_observation_sync.py", text)
        self.assertNotIn("aios_observation_buffer.py", text)
        self.assertNotIn("HTTP endpoint", text)
        self.assertFalse((ROOT / "scripts" / "aios_observation_sync.py").exists())
        self.assertFalse((ROOT / "scripts" / "aios_observation_buffer.py").exists())


if __name__ == "__main__":
    unittest.main()
