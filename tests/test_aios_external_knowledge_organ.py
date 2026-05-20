"""ASC-0205 CC4 — external knowledge organ unit tests."""
from __future__ import annotations

import json
import sys
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
SCRIPTS = REPO_ROOT / "scripts"
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

import aios_external_knowledge_organ as organ  # noqa: E402


class ExternalKnowledgeOrganTest(unittest.TestCase):
    def _tmp_root(self) -> Path:
        from tempfile import mkdtemp
        return Path(mkdtemp(prefix="aios_organ_"))

    def test_build_packets_creates_receipt_and_packet_per_claim(self):
        root = self._tmp_root()
        receipt_path, packets = organ.build_packets(
            topic="Hermes Agent memory model",
            url="https://github.com/NousResearch/hermes-agent",
            claims=["claim one paraphrased", "claim two paraphrased"],
            publisher="GitHub README",
            memory_type="observation",
            confidence=0.55,
            project="AIOS",
            root=root,
        )
        self.assertTrue(receipt_path.exists())
        receipt = json.loads(receipt_path.read_text())
        self.assertEqual(receipt["schema_version"], "aios.web_research_receipt.v1")
        self.assertEqual(len(receipt["sources"]), 1)
        self.assertEqual(receipt["sources"][0]["claims"],
                         ["claim one paraphrased", "claim two paraphrased"])

        self.assertEqual(len(packets), 2)
        for idx, pp in enumerate(packets):
            packet = json.loads(pp.read_text())
            self.assertEqual(packet["schema_version"], "aios.memory_draft_review_request.v1")
            self.assertEqual(packet["draft_id"], f"ext:hermes-agent-memory-model:{idx}")
            self.assertEqual(packet["contract_id"], "ASC-0205")
            self.assertEqual(packet["draft"]["status"], "draft")
            self.assertEqual(packet["draft"]["origin"], "external_knowledge_organ")
            self.assertEqual(packet["draft"]["type"], "observation")
            self.assertFalse(packet["review_policy"]["auto_accept"])
            self.assertTrue(packet["review_policy"]["draft_first"])
            # source_artifact must be repo-relative
            self.assertFalse(packet["source_artifact"].startswith("/"))
            self.assertIn("web_receipts", packet["source_artifact"])
            # draft body holds the actual claim, not the topic
            self.assertEqual(packet["draft"]["content"],
                             ["claim one paraphrased", "claim two paraphrased"][idx])

    def test_invalid_memory_type_raises(self):
        root = self._tmp_root()
        with self.assertRaises(ValueError):
            organ.build_packets(
                topic="t",
                url="https://x/y",
                claims=["c"],
                publisher=None,
                memory_type="not_a_real_type",
                confidence=0.5,
                project="AIOS",
                root=root,
            )

    def test_empty_claims_raises(self):
        root = self._tmp_root()
        with self.assertRaises(ValueError):
            organ.build_packets(
                topic="t",
                url="https://x/y",
                claims=[],
                publisher=None,
                memory_type="observation",
                confidence=0.5,
                project="AIOS",
                root=root,
            )

    def test_slug_truncates_and_normalizes(self):
        self.assertEqual(organ._slug("Hermes Agent memory model!"),
                         "hermes-agent-memory-model")
        self.assertEqual(organ._slug("   ::ALL Symbols.. "),
                         "all-symbols")
        # long topic truncated
        s = organ._slug("a" * 100)
        self.assertLessEqual(len(s), 48)

    def test_packet_lands_in_memoryos_inbox(self):
        root = self._tmp_root()
        _, packets = organ.build_packets(
            topic="t",
            url="https://x/y",
            claims=["c"],
            publisher=None,
            memory_type="observation",
            confidence=0.5,
            project="AIOS",
            root=root,
        )
        self.assertEqual(packets[0].parent, root / ".aios" / "inbox" / "memoryOS")


if __name__ == "__main__":
    unittest.main()
