import json
import subprocess
import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "aios_packaging_proof.py"


class AiosPackagingProofTest(unittest.TestCase):
    def test_fresh_copy_install_smoke_uses_isolated_state(self) -> None:
        result = subprocess.run(
            [sys.executable, SCRIPT.as_posix(), "--root", ROOT.as_posix(), "--json"],
            text=True,
            capture_output=True,
            timeout=90,
            check=False,
        )

        self.assertEqual(result.returncode, 0, result.stderr)
        payload = json.loads(result.stdout)
        self.assertEqual(payload["schema_version"], "aios.packaging_proof.v1")
        self.assertTrue(payload["ok"])
        self.assertTrue(payload["dry_run"])
        self.assertFalse(payload["privacy_receipt"]["copied_git_dir"])
        self.assertFalse(payload["privacy_receipt"]["copied_aios_runtime_state"])
        self.assertTrue(payload["privacy_receipt"]["generated_isolated_runtime_state"])
        self.assertFalse(payload["privacy_receipt"]["wrote_operator_shell_rc"])


if __name__ == "__main__":
    unittest.main()
