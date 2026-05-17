from __future__ import annotations

import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
CHALLENGE_SCRIPT = ROOT / "scripts" / "aios_genesis_challenge.py"
DISPATCH_SCRIPT = ROOT / "scripts" / "aios_dispatch.py"


CONTRACT = """---
contract_id: ASC-TEST
status: accepted
goal: AIOS dispatch contract ledger provider monitor should close.
---

# ASC-TEST

repos:

- `myworld`

allowed_files:

- `scripts/aios_dispatch.py`

forbidden_files:

- `.env`

AIOS dispatch monitor contract ledger cli provider should continue through the
same dispatch monitor contract ledger cli provider pattern without assumptions,
time horizons, or analogy.
"""


class AiosGenesisChallengeTest(unittest.TestCase):
    def make_root(self, tmp: str) -> tuple[Path, Path]:
        root = Path(tmp)
        (root / "GenesisOS").symlink_to(ROOT / "GenesisOS", target_is_directory=True)
        contracts = root / "docs" / "contracts"
        contracts.mkdir(parents=True, exist_ok=True)
        contract = contracts / "ASC-TEST-sample.md"
        contract.write_text(CONTRACT, encoding="utf-8")
        return root, contract

    def run_dispatch(self, root: Path, *args: str) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            [sys.executable, DISPATCH_SCRIPT.as_posix(), *args],
            cwd=root,
            text=True,
            capture_output=True,
            check=False,
        )

    def test_standalone_challenge_cli(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root, _contract = self.make_root(tmp)
            result = subprocess.run(
                [
                    sys.executable,
                    CHALLENGE_SCRIPT.as_posix(),
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
            self.assertIn(payload["risk_level"], {"low", "medium", "high"})
            self.assertTrue(Path(payload["output_path"]).exists())

    def test_release_soft_block_and_override(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root, contract = self.make_root(tmp)
            create = self.run_dispatch(root, "create", contract.as_posix(), "--dispatch-id", "d-test")
            self.assertEqual(create.returncode, 0, create.stderr)

            blocked = self.run_dispatch(root, "release", "--dispatch-id", "d-test", "--reason", "tested")
            self.assertNotEqual(blocked.returncode, 0)
            self.assertIn("genesis_challenge", blocked.stdout)
            self.assertIn("recommendation", blocked.stdout)

            override = self.run_dispatch(
                root,
                "release",
                "--dispatch-id",
                "d-test",
                "--operator-override-genesis-block",
                "--reason",
                "tested",
            )
            self.assertEqual(override.returncode, 0, override.stderr)
            payload = json.loads(override.stdout)
            self.assertEqual(payload["status"], "released")


if __name__ == "__main__":
    unittest.main()
