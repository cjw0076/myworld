import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "aios_share_projection.py"
FIXTURES = ROOT / "tests" / "fixtures" / "share_projection"


class AiosShareProjectionTest(unittest.TestCase):
    def run_verify(self, fixture: str) -> dict:
        result = subprocess.run(
            [sys.executable, SCRIPT.as_posix(), "verify", (FIXTURES / fixture).as_posix(), "--json"],
            cwd=ROOT,
            text=True,
            capture_output=True,
            check=True,
        )
        return json.loads(result.stdout)

    def test_valid_capability_observation_passes(self) -> None:
        payload = self.run_verify("valid_capability_observation.json")

        self.assertEqual(payload["schema_version"], "aios.share_projection.verify.v1")
        self.assertEqual(payload["status"], "passed")
        self.assertEqual(payload["errors"], [])
        self.assertFalse(payload["network_used"])
        self.assertFalse(payload["git_sync_used"])
        self.assertFalse(payload["memory_acceptance_used"])
        self.assertFalse(payload["provider_execution_used"])

    def test_raw_memory_is_blocked(self) -> None:
        payload = self.run_verify("reject_raw_memory.json")

        self.assertEqual(payload["status"], "blocked")
        self.assertIn("record_kind_not_share_eligible:memory_object", payload["errors"])

    def test_secret_path_is_blocked(self) -> None:
        payload = self.run_verify("reject_secret_path.json")

        self.assertEqual(payload["status"], "blocked")
        self.assertIn("hard_ban_source_ref", payload["errors"])
        self.assertIn("payload_contains_hard_ban_path", payload["errors"])

    def test_default_deny_requires_visibility_share_true(self) -> None:
        record = json.loads((FIXTURES / "valid_capability_observation.json").read_text(encoding="utf-8"))
        record["visibility"]["share"] = False
        with tempfile.NamedTemporaryFile("w", suffix=".json", encoding="utf-8", delete=False) as fp:
            path = Path(fp.name)
            json.dump(record, fp)
        try:
            result = subprocess.run(
                [sys.executable, SCRIPT.as_posix(), "verify", path.as_posix(), "--json"],
                cwd=ROOT,
                text=True,
                capture_output=True,
                check=True,
            )
            payload = json.loads(result.stdout)
        finally:
            path.unlink(missing_ok=True)

        self.assertEqual(payload["status"], "blocked")
        self.assertIn("visibility_default_deny", payload["errors"])

    def test_signature_field_is_required(self) -> None:
        record = json.loads((FIXTURES / "valid_capability_observation.json").read_text(encoding="utf-8"))
        record["signature"] = {"algorithm": "ed25519-placeholder", "value": ""}
        with tempfile.NamedTemporaryFile("w", suffix=".json", encoding="utf-8", delete=False) as fp:
            path = Path(fp.name)
            json.dump(record, fp)
        try:
            result = subprocess.run(
                [sys.executable, SCRIPT.as_posix(), "verify", path.as_posix(), "--json"],
                cwd=ROOT,
                text=True,
                capture_output=True,
                check=True,
            )
            payload = json.loads(result.stdout)
        finally:
            path.unlink(missing_ok=True)

        self.assertEqual(payload["status"], "blocked")
        self.assertIn("signature_value_missing", payload["errors"])


if __name__ == "__main__":
    unittest.main()
