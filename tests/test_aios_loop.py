import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "aios_loop.py"


CONTRACT = """---
contract_id: ASC-0100
status: accepted
goal: Test autonomous dispatch.
accepted: now
closed:
---

# ASC-0100 Test

repos:

- `CapabilityOS`

allowed_files:

- `CapabilityOS/README.md`

forbidden_files:

- `.env`
"""


MISSING_REPOS_CONTRACT = """---
contract_id: ASC-0101
status: accepted
goal: Missing repo scope should block dispatch.
accepted: now
closed:
---

# ASC-0101 Test

## Scope

- repos: _to be filled_
"""


class AiosLoopTest(unittest.TestCase):
    def run_loop(self, root: Path, *args: str) -> dict:
        result = subprocess.run(
            [sys.executable, SCRIPT.as_posix(), "once", "--json", *args],
            cwd=root,
            text=True,
            capture_output=True,
            check=True,
        )
        return json.loads(result.stdout)

    def test_plan_mode_does_not_write_packet(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            contracts = root / "docs" / "contracts"
            contracts.mkdir(parents=True)
            (contracts / "ASC-0100-test.md").write_text(CONTRACT, encoding="utf-8")

            payload = self.run_loop(root)

            actions = {action["action"] for action in payload["actions"]}
            self.assertIn("would_create_dispatch", actions)
            self.assertIn("would_send_packet", actions)
            self.assertFalse((root / ".aios" / "inbox" / "CapabilityOS" / "asc-0100.CapabilityOS.json").exists())

    def test_apply_mode_creates_dispatch_and_packet(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            contracts = root / "docs" / "contracts"
            contracts.mkdir(parents=True)
            (contracts / "ASC-0100-test.md").write_text(CONTRACT, encoding="utf-8")

            payload = self.run_loop(root, "--apply")

            actions = {action["action"] for action in payload["actions"]}
            self.assertIn("create_dispatch", actions)
            self.assertIn("send_packet", actions)
            packet = root / ".aios" / "inbox" / "CapabilityOS" / "asc-0100.CapabilityOS.json"
            self.assertTrue(packet.exists())
            data = json.loads(packet.read_text(encoding="utf-8"))
            self.assertEqual(data["target_repo"], "CapabilityOS")

    def test_accepted_contract_without_repo_scope_does_not_dispatch(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            contracts = root / "docs" / "contracts"
            contracts.mkdir(parents=True)
            (contracts / "ASC-0101-test.md").write_text(MISSING_REPOS_CONTRACT, encoding="utf-8")

            payload = self.run_loop(root, "--apply")

            self.assertFalse(payload["actions"])
            self.assertEqual(payload["observations"][0]["next"], "checkpoint_missing_repos")
            self.assertFalse((root / ".aios" / "state" / "dispatches.jsonl").exists())


if __name__ == "__main__":
    unittest.main()
