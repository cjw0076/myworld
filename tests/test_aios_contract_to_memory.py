import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "aios_contract_to_memory.py"


CONTRACT = """---
contract_id: ASC-0991
slug: memoryos-auto-writeback-test
status: closed
goal: Verify closeout memory emission.
closed: 2026-05-13T00:00:00+09:00
---

# ASC-0991 Test

## Receipts

- `abc1234` myworld commit
- `.aios/outbox/myworld/asc-0991.myworld.result.json`
- Closeout wrote only draft memory.
"""


class AiosContractToMemoryTest(unittest.TestCase):
    def test_emit_contract_closeout_payload_has_evidence(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_str:
            root = Path(tmp_str)
            contracts = root / "docs" / "contracts"
            contracts.mkdir(parents=True)
            (contracts / "ASC-0991-test.md").write_text(CONTRACT, encoding="utf-8")
            ledger = root / "docs" / "AIOS_AGENT_LEDGER.md"
            ledger.write_text("## ASC-0991\n- released with draft-first memory.\n", encoding="utf-8")

            result = subprocess.run(
                [sys.executable, SCRIPT.as_posix(), "emit", "--root", root.as_posix(), "--contract", "ASC-0991", "--json"],
                check=False,
                capture_output=True,
                text=True,
            )

            self.assertEqual(result.returncode, 0, result.stderr)
            payload = json.loads(result.stdout)
            self.assertEqual(payload["schema_version"], "aios.contract_closeout_memory.v1")
            self.assertEqual(payload["contract_id"], "ASC-0991")
            self.assertEqual(payload["status"], "closed")
            self.assertIn("docs/contracts/ASC-0991-test.md", payload["evidence_refs"])
            self.assertIn("docs/AIOS_AGENT_LEDGER.md", payload["evidence_refs"])
            self.assertFalse(payload["privacy"]["raw_provider_output_included"])


if __name__ == "__main__":
    unittest.main()
