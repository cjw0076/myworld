import json
import subprocess
import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "aios_release_archive_proof.py"


class AiosReleaseArchiveProofTest(unittest.TestCase):
    def test_selected_source_archive_smoke_and_backend_selection(self) -> None:
        result = subprocess.run(
            [sys.executable, SCRIPT.as_posix(), "--root", ROOT.as_posix(), "--json"],
            text=True,
            capture_output=True,
            timeout=90,
            check=False,
        )

        self.assertEqual(result.returncode, 0, result.stderr)
        payload = json.loads(result.stdout)
        self.assertEqual(payload["schema_version"], "aios.release_archive_proof.v1")
        self.assertTrue(payload["ok"])
        self.assertEqual(payload["install_returncode"], 0)
        self.assertEqual(payload["provider_status_returncode"], 0)
        self.assertEqual(payload["privacy_receipt"]["archive_forbidden_runtime_or_private_paths_present"], [])
        self.assertTrue(payload["privacy_receipt"]["smoke_generated_isolated_runtime_state"])
        self.assertFalse(payload["privacy_receipt"]["wrote_operator_shell_rc"])
        self.assertFalse(payload["privacy_receipt"]["credential_values_printed"])
        self.assertEqual(payload["backend_selection"]["selected_first_tier"], "local_first_release_archive")
        tiers = {item["tier"] for item in payload["backend_selection"]["optional_hosted_tiers"]}
        self.assertIn("codex_cloud_optional", tiers)
        self.assertIn("anthropic_managed_agents_optional", tiers)
        self.assertIn("gemini_interactions_research_optional", tiers)


if __name__ == "__main__":
    unittest.main()
