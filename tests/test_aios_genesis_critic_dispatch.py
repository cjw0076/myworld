from __future__ import annotations

import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "aios_genesis_critic_dispatch.py"


class AiosGenesisCriticDispatchTest(unittest.TestCase):
    def make_contract(self, root: Path, name: str, status: str, body: str) -> None:
        contracts = root / "docs" / "contracts"
        contracts.mkdir(parents=True, exist_ok=True)
        (contracts / name).write_text(
            "\n".join(
                [
                    "---",
                    f"contract_id: {name.split('-', 1)[0]}",
                    f"status: {status}",
                    "goal: Test prompt prison detection",
                    "---",
                    "",
                    body,
                    "",
                ]
            ),
            encoding="utf-8",
        )

    def test_report_is_advisory_and_mutates_nothing(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "GenesisOS").symlink_to(ROOT / "GenesisOS", target_is_directory=True)
            self.make_contract(
                root,
                "ASC-9999-test.md",
                "accepted",
                "AIOS dispatch monitor contract ledger cli provider should continue "
                "through dispatch monitor contract ledger cli provider. The agent "
                "will update dispatch status, run tests, close the contract, and "
                "repeat the same contract dispatch monitor ledger cli pattern.",
            )

            sys.path.insert(0, ROOT.as_posix())
            from scripts.aios_genesis_critic_dispatch import build_report

            report = build_report(root)

        self.assertEqual("aios.genesis_critic_dispatch.v1", report["schema_version"])
        self.assertEqual("advisory_only", report["authority"])
        self.assertTrue(report["recommendation_only"])
        self.assertEqual([], report["mutated_files"])
        self.assertEqual(1, report["flagged_count"])
        self.assertGreaterEqual(report["flagged"][0]["signature_count"], 2)

    def test_cli_json(self) -> None:
        result = subprocess.run(
            [sys.executable, SCRIPT.as_posix(), "--root", ROOT.as_posix(), "--limit", "3", "--json"],
            text=True,
            capture_output=True,
            check=False,
        )

        self.assertEqual(result.returncode, 0, result.stderr)
        payload = json.loads(result.stdout)
        self.assertEqual("advisory_only", payload["authority"])
        self.assertIn("flagged_count", payload)


if __name__ == "__main__":
    unittest.main()
