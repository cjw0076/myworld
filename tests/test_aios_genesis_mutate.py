from __future__ import annotations

import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "aios_genesis_mutate.py"


SAMPLE_CONTRACT = """---
contract_id: ASC-TEST
status: accepted
goal: GenesisOS should mutate assumptions before closeout.
---

# ASC-TEST

## Assumptions

- The operator can review generated seeds.
- The source contract should remain unchanged.
- Candidate seeds require MyWorld review before promotion.
"""


class AiosGenesisMutateTest(unittest.TestCase):
    def make_root(self, tmp: str) -> Path:
        root = Path(tmp)
        (root / "GenesisOS").symlink_to(ROOT / "GenesisOS", target_is_directory=True)
        contracts = root / "docs" / "contracts"
        contracts.mkdir(parents=True, exist_ok=True)
        (contracts / "ASC-TEST-sample.md").write_text(SAMPLE_CONTRACT, encoding="utf-8")
        return root

    def test_report_writes_seed_inbox_without_mutating_contract(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = self.make_root(tmp)
            contract_path = root / "docs" / "contracts" / "ASC-TEST-sample.md"
            before = contract_path.read_bytes()

            sys.path.insert(0, ROOT.as_posix())
            from scripts.aios_genesis_mutate import build_report

            report = build_report(root, contract_id="ASC-TEST")

            self.assertEqual(report["schema_version"], "aios.genesis_mutate.v1")
            self.assertEqual(report["authority"], "operator_review_required")
            self.assertTrue(report["recommendation_only"])
            self.assertEqual(report["mutated_files"], [])
            self.assertEqual(report["seed_count"], 6)
            self.assertTrue((root / report["seed_inbox"]).exists())
            self.assertEqual(contract_path.read_bytes(), before)

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
            self.assertEqual(payload["seed_count"], 6)
            self.assertIn(".aios/genesis_seed_inbox/", payload["seed_inbox"])


if __name__ == "__main__":
    unittest.main()

