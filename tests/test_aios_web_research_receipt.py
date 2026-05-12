import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from scripts.aios_web_research_receipt import validate_receipt


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "aios_web_research_receipt.py"
RECEIPT = ROOT / "docs" / "evidence" / "ASC-0031-web-evidence.json"


class AiosWebResearchReceiptTest(unittest.TestCase):
    def test_committed_receipt_validates(self) -> None:
        data = json.loads(RECEIPT.read_text(encoding="utf-8"))

        errors = validate_receipt(data)

        self.assertEqual([], errors)

    def test_validator_rejects_unknown_claim_source(self) -> None:
        data = json.loads(RECEIPT.read_text(encoding="utf-8"))
        data["synthesis_claims"][0]["source_ids"] = ["missing"]

        errors = validate_receipt(data)

        self.assertIn("synthesis_claims[0].source_ids contains unknown source", errors)

    def test_validator_rejects_raw_private_markers(self) -> None:
        data = json.loads(RECEIPT.read_text(encoding="utf-8"))
        data["sources"][0]["claims"].append("raw_exports/private.json")

        errors = validate_receipt(data)

        self.assertIn("forbidden marker present: raw_exports/", errors)

    def test_cli_validate_json_surface(self) -> None:
        result = subprocess.run(
            [sys.executable, SCRIPT.as_posix(), "validate", RECEIPT.as_posix(), "--json"],
            cwd=ROOT,
            text=True,
            capture_output=True,
            check=True,
        )

        payload = json.loads(result.stdout)
        self.assertEqual(payload["schema_version"], "aios.web_research_receipt.validation.v1")
        self.assertTrue(payload["ok"])
        self.assertEqual(payload["errors"], [])

    def test_cli_rejects_invalid_receipt(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "bad.json"
            path.write_text(
                json.dumps(
                    {
                        "schema_version": "aios.web_research_receipt.v1",
                        "route_contract": "wrong",
                        "sources": [],
                    }
                ),
                encoding="utf-8",
            )

            result = subprocess.run(
                [sys.executable, SCRIPT.as_posix(), "validate", path.as_posix(), "--json"],
                cwd=ROOT,
                text=True,
                capture_output=True,
                check=False,
            )

        self.assertNotEqual(result.returncode, 0)
        payload = json.loads(result.stdout)
        self.assertFalse(payload["ok"])
        self.assertIn("route_contract must be capabilityos.web_research_route.v1", payload["errors"])


if __name__ == "__main__":
    unittest.main()
