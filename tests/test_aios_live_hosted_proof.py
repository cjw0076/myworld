import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "aios_live_hosted_proof.py"


class AiosLiveHostedProofTest(unittest.TestCase):
    def test_hive_runtime_receipt_projects_to_akashic_index(self) -> None:
        with tempfile.TemporaryDirectory() as hive_tmp, tempfile.TemporaryDirectory() as memory_tmp:
            result = subprocess.run(
                [
                    sys.executable,
                    SCRIPT.as_posix(),
                    "--hive-root",
                    hive_tmp,
                    "--memory-root",
                    memory_tmp,
                    "--write-memory",
                    "--json",
                ],
                text=True,
                capture_output=True,
                check=False,
            )

            self.assertEqual(result.returncode, 0, result.stderr)
            payload = json.loads(result.stdout)
            self.assertEqual(payload["schema_version"], "aios.live_hosted_run_proof.v1")
            self.assertEqual(payload["runtime_receipt_status"], "success")
            self.assertEqual(payload["runtime_network_policy"], "denied")
            self.assertTrue(payload["credential_refs_only"])
            self.assertTrue(payload["akashic_written"])
            self.assertFalse(payload["privacy_receipt"]["raw_provider_history_copied"])
            self.assertFalse(payload["privacy_receipt"]["credential_values_copied"])
            self.assertTrue((Path(memory_tmp) / "memory" / "akashic_work_index.jsonl").exists())


if __name__ == "__main__":
    unittest.main()
