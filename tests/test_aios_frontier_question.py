"""ASC-0211 L3 routine #3 — frontier-question tests."""
from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
SCRIPTS = REPO_ROOT / "scripts"
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

import aios_frontier_question as fq  # noqa: E402


def _fake_repo(td: Path) -> tuple[Path, Path]:
    mem = td / "memory"
    contracts = td / "contracts"
    mem.mkdir()
    contracts.mkdir()

    # Two reference memos
    (mem / "reference_alpha.md").write_text(
        "---\nname: reference-alpha\ndescription: alpha topic about X.\nmetadata:\n  type: reference\n---\n\nbody.\n",
        encoding="utf-8",
    )
    (mem / "reference_beta.md").write_text(
        "---\nname: reference-beta\ndescription: beta topic about Y.\nmetadata:\n  type: reference\n---\n\nbody.\n",
        encoding="utf-8",
    )
    # One peer file with blindspot section
    (mem / "project_user_agent_test.md").write_text(
        "---\nname: project-user-agent-test\n---\n\n## Named blindspots\n\nthings I don't know.\n",
        encoding="utf-8",
    )
    # One contract citing only reference_alpha
    (contracts / "ASC-9001-demo.md").write_text(
        "---\ncontract_id: ASC-9001\nstatus: closed\n---\n\n[[reference-alpha]] is cited here.\n",
        encoding="utf-8",
    )
    return mem, contracts


class FrontierQuestionTest(unittest.TestCase):
    def test_uncited_memo_detection(self):
        with tempfile.TemporaryDirectory() as td:
            mem, contracts = _fake_repo(Path(td))
            corpus = fq.contract_text_corpus(contracts)
            uncited = fq.uncited_reference_memos(mem, corpus)
            uncited_names = [p.name for p in uncited]
            self.assertIn("reference_beta.md", uncited_names)
            self.assertNotIn("reference_alpha.md", uncited_names)

    def test_questions_have_draft_first_invariant(self):
        with tempfile.TemporaryDirectory() as td:
            mem, contracts = _fake_repo(Path(td))
            corpus = fq.contract_text_corpus(contracts)
            uncited = fq.uncited_reference_memos(mem, corpus)
            qs = fq.build_questions_for_uncited(uncited)
            drafts = [fq.build_draft_packet(q) for q in qs]
            self.assertGreater(len(drafts), 0)
            for d in drafts:
                self.assertEqual(d["schema_version"], "aios.memory_draft_review_request.v1")
                self.assertFalse(d["review_policy"]["auto_accept"])
                self.assertTrue(d["review_policy"]["draft_first"])
                self.assertEqual(d["draft"]["status"], "draft")
                self.assertEqual(d["draft"]["origin"], "aios_frontier_question")

    def test_peer_blindspot_questions(self):
        with tempfile.TemporaryDirectory() as td:
            mem, contracts = _fake_repo(Path(td))
            qs = fq.build_questions_for_peer_blindspots(mem)
            self.assertEqual(len(qs), 1)
            self.assertEqual(qs[0]["type"], "peer_blindspot")
            self.assertIn("user@test", qs[0]["peer"])

    def test_extract_topic_summary_picks_description(self):
        with tempfile.TemporaryDirectory() as td:
            mem, _ = _fake_repo(Path(td))
            topic = fq.extract_topic_summary(mem / "reference_alpha.md")
            self.assertIn("alpha topic", topic)


if __name__ == "__main__":
    unittest.main()
