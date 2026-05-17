from __future__ import annotations

import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "aios_genesis_modal.py"


SAMPLE_CONTRACT = """---
contract_id: ASC-TEST
status: accepted
goal: AIOS should compare a contract through multiple modalities.
---

# ASC-TEST

AIOS should route the goal through GenesisOS, MemoryOS, CapabilityOS, and Hive.
"""


class AiosGenesisModalTest(unittest.TestCase):
    def make_root(self, tmp: str) -> tuple[Path, Path]:
        root = Path(tmp)
        (root / "GenesisOS").symlink_to(ROOT / "GenesisOS", target_is_directory=True)
        contracts = root / "docs" / "contracts"
        contracts.mkdir(parents=True, exist_ok=True)
        source = contracts / "ASC-TEST-sample.md"
        source.write_text(SAMPLE_CONTRACT, encoding="utf-8")
        return root, source

    def test_report_writes_modal_view_without_mutating_source(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root, source = self.make_root(tmp)
            before = source.read_bytes()

            sys.path.insert(0, ROOT.as_posix())
            from scripts.aios_genesis_modal import build_report

            report = build_report(root, contract_id="ASC-TEST")

            self.assertEqual(report["schema_version"], "aios.genesis_modal.v1")
            self.assertEqual(report["authority"], "advisory_only")
            self.assertEqual(len(report["view"]["translations"]), 6)
            self.assertTrue(Path(report["output_path"]).exists())
            self.assertEqual(source.read_bytes(), before)
            self.assertEqual(report["mutated_files"], [])

    def test_cli_json(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root, _source = self.make_root(tmp)
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
            self.assertEqual(payload["artifact_id"].split("-", 2)[0], "ASC")
            self.assertEqual(len(payload["view"]["translations"]), 6)


if __name__ == "__main__":
    unittest.main()
