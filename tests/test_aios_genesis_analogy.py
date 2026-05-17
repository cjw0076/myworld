from __future__ import annotations

import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "aios_genesis_analogy.py"


SAMPLE_CONTRACT = """---
contract_id: ASC-TEST
status: accepted
goal: AIOS needs provider fallback, failure memory, and prompt-prison escape.
---

# ASC-TEST

Provider backpressure should become failure memory and fallback routing.
"""


class AiosGenesisAnalogyTest(unittest.TestCase):
    def make_root(self, tmp: str) -> Path:
        root = Path(tmp)
        (root / "GenesisOS").symlink_to(ROOT / "GenesisOS", target_is_directory=True)
        contracts = root / "docs" / "contracts"
        contracts.mkdir(parents=True, exist_ok=True)
        (contracts / "ASC-TEST-sample.md").write_text(SAMPLE_CONTRACT, encoding="utf-8")
        return root

    def test_report_writes_top_analogies_without_mutating_contract(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = self.make_root(tmp)
            source = root / "docs" / "contracts" / "ASC-TEST-sample.md"
            before = source.read_bytes()

            sys.path.insert(0, ROOT.as_posix())
            from scripts.aios_genesis_analogy import build_report

            report = build_report(root, contract_id="ASC-TEST")

            self.assertEqual(report["schema_version"], "aios.genesis_analogy.v1")
            self.assertEqual(len(report["matches"]["matches"]), 3)
            self.assertTrue(Path(report["output_path"]).exists())
            self.assertEqual(report["mutated_files"], [])
            self.assertEqual(source.read_bytes(), before)

    def test_cli_json(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = self.make_root(tmp)
            result = subprocess.run(
                [
                    sys.executable,
                    SCRIPT.as_posix(),
                    "--root",
                    root.as_posix(),
                    "--contract-id",
                    "ASC-TEST",
                    "--json",
                ],
                text=True,
                capture_output=True,
                check=False,
            )

            self.assertEqual(result.returncode, 0, result.stderr)
            payload = json.loads(result.stdout)
            self.assertEqual(payload["contract_id"], "ASC-TEST")
            self.assertEqual(len(payload["matches"]["matches"]), 3)


if __name__ == "__main__":
    unittest.main()
