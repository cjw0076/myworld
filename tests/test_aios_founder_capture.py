import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from scripts.aios_founder_capture import build_payload, classify


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "aios_founder_capture.py"


class AiosFounderCaptureTests(unittest.TestCase):
    def test_classifies_founder_reframes(self) -> None:
        self.assertEqual(classify("AIOS = Government and DNA constitution"), "vision")
        self.assertEqual(classify("너가 나의 역할을 대신해서 operator로 있어"), "role")
        self.assertEqual(classify("불편함이 창의적인 것을 만든다"), "discomfort")

    def test_extracts_quoted_founder_directive_from_contract(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            contract = root / "docs" / "contracts" / "ASC-9999-demo.md"
            contract.parent.mkdir(parents=True)
            contract.write_text(
                """---
contract_id: ASC-9999
status: accepted
acceptance_authority: founder said "AIOS를 정부처럼 설계해"
origin: founder directive "계속 진행해"
---
""",
                encoding="utf-8",
            )

            payload = build_payload(root, [contract])

        texts = {row["directive_text"] for row in payload["directives"]}
        self.assertIn("AIOS를 정부처럼 설계해", texts)
        self.assertIn("계속 진행해", texts)
        self.assertTrue(all(row["raw_refs"] for row in payload["directives"]))

    def test_cli_default_extracts_many_founder_directives(self) -> None:
        result = subprocess.run(
            [sys.executable, SCRIPT.as_posix(), "--root", ROOT.as_posix(), "--json"],
            text=True,
            capture_output=True,
            check=False,
        )

        self.assertEqual(result.returncode, 0, result.stderr)
        payload = json.loads(result.stdout)
        self.assertEqual(payload["schema_version"], "aios.founder_directive_memory.v1")
        self.assertGreaterEqual(len(payload["directives"]), 20)

    def test_cli_text_capture(self) -> None:
        result = subprocess.run(
            [sys.executable, SCRIPT.as_posix(), "--root", ROOT.as_posix(), "--text", "AIOS를 계속 진화시켜", "--json"],
            text=True,
            capture_output=True,
            check=False,
        )

        self.assertEqual(result.returncode, 0, result.stderr)
        payload = json.loads(result.stdout)
        self.assertEqual(payload["directives"][0]["directive_text"], "AIOS를 계속 진화시켜")


if __name__ == "__main__":
    unittest.main()
