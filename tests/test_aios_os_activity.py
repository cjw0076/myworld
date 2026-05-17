import json
import os
import tempfile
import time
import unittest
from pathlib import Path

from scripts.aios_os_activity import build_activity


class AiosOsActivityTests(unittest.TestCase):
    def write_receipt(self, root: Path, name: str, role_statuses: dict[str, str]) -> Path:
        path = root / ".aios" / "invocations" / name / "receipt.json"
        path.parent.mkdir(parents=True)
        path.write_text(
            json.dumps(
                {
                    "schema_version": "aios.invocation_receipt.v1",
                    "role_statuses": role_statuses,
                }
            ),
            encoding="utf-8",
        )
        return path

    def test_genesis_invocation_counts_as_activity_without_inbox(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            self.write_receipt(root, "recent", {"genesis": "passed"})

            payload = build_activity(root, 24)

            genesis = next(row for row in payload["repos"] if row["repo"] == "GenesisOS")
            self.assertTrue(genesis["active"])
            self.assertEqual(genesis["invocation_recent_count"], 1)
            self.assertNotIn("GenesisOS", payload["ghost_repos"])

    def test_failed_invocation_does_not_count_as_activity(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            self.write_receipt(root, "recent", {"genesis": "failed"})

            payload = build_activity(root, 24)

            genesis = next(row for row in payload["repos"] if row["repo"] == "GenesisOS")
            self.assertFalse(genesis["active"])
            self.assertIn("GenesisOS", payload["ghost_repos"])

    def test_inbox_packet_counts_as_activity(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            inbox = root / ".aios" / "inbox" / "memoryOS"
            inbox.mkdir(parents=True)
            (inbox / "packet.json").write_text("{}", encoding="utf-8")

            payload = build_activity(root, 24)

            memory = next(row for row in payload["repos"] if row["repo"] == "memoryOS")
            self.assertTrue(memory["active"])
            self.assertEqual(memory["inbox_recent_count"], 1)
            self.assertNotIn("memoryOS", payload["ghost_repos"])

    def test_old_invocation_does_not_count(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            receipt = self.write_receipt(root, "old", {"genesis": "passed"})
            old = time.time() - (48 * 3600)
            os.utime(receipt, (old, old))

            payload = build_activity(root, 24)

            self.assertIn("GenesisOS", payload["ghost_repos"])


if __name__ == "__main__":
    unittest.main()
