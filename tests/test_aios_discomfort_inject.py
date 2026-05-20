"""ASC-0211 L3 routine #2 — discomfort injection tests."""
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

import aios_discomfort_inject as inject  # noqa: E402


SAMPLE_AUDIT = {
    "schema_version": "aios.convergence_audit.v1",
    "generated_at": "2026-05-20T09:00:00Z",
    "count": 3,
    "rows": [
        {
            "contract_id": "ASC-1001",
            "path": "docs/contracts/ASC-1001-frame-echo.md",
            "status": "closed",
            "slug": "frame-echo",
            "challenge_score": 2,
            "challenge_hits": {},
            "footprint_score": 4,
            "footprint_hits": {"frame_echo": 1, "auto_close_under_10min": 1},
            "verdict": "footprint_consensus",
        },
        {
            "contract_id": "ASC-1002",
            "path": "docs/contracts/ASC-1002-real-challenge.md",
            "status": "closed",
            "slug": "real-challenge",
            "challenge_score": 10,
            "challenge_hits": {"memory_citation": 5, "genesis_review": 1},
            "footprint_score": 0,
            "footprint_hits": {},
            "verdict": "real_challenge",
        },
        {
            "contract_id": "ASC-1003",
            "path": "docs/contracts/ASC-1003-no-evidence.md",
            "status": "closed",
            "slug": "no-evidence",
            "challenge_score": 3,
            "challenge_hits": {},
            "footprint_score": 2,
            "footprint_hits": {"no_evidence_refs": 1},
            "verdict": "mixed",
        },
    ],
}


class DiscomfortInjectTest(unittest.TestCase):
    def test_real_challenge_not_targeted(self):
        drafts = inject.build_drafts(SAMPLE_AUDIT)
        ids = [d["draft_id"].split(":")[1] for d in drafts]
        self.assertNotIn("ASC-1002", ids,
                         "real_challenge must not get discomfort drafts")

    def test_footprint_consensus_gets_a_draft(self):
        drafts = inject.build_drafts(SAMPLE_AUDIT)
        ids = [d["draft_id"].split(":")[1] for d in drafts]
        self.assertIn("ASC-1001", ids)

    def test_mixed_with_min_footprint_gets_a_draft(self):
        drafts = inject.build_drafts(SAMPLE_AUDIT, min_footprint=2)
        ids = [d["draft_id"].split(":")[1] for d in drafts]
        self.assertIn("ASC-1003", ids)

    def test_drafts_are_draft_first_and_auto_accept_false(self):
        drafts = inject.build_drafts(SAMPLE_AUDIT)
        for d in drafts:
            self.assertEqual(d["schema_version"], "aios.memory_draft_review_request.v1")
            self.assertFalse(d["review_policy"]["auto_accept"])
            self.assertTrue(d["review_policy"]["draft_first"])
            self.assertEqual(d["draft"]["status"], "draft")
            self.assertEqual(d["draft"]["origin"], "aios_discomfort_inject")

    def test_template_picks_match_signals(self):
        drafts = inject.build_drafts(SAMPLE_AUDIT)
        for d in drafts:
            if d["draft_id"].split(":")[1] == "ASC-1001":
                # frame_echo or auto_close picks templates 3 or 4
                self.assertIn(d["draft"]["provenance"]["template_index"], (3, 4))
            if d["draft_id"].split(":")[1] == "ASC-1003":
                # no_evidence_refs picks template 2
                self.assertEqual(d["draft"]["provenance"]["template_index"], 2)

    def test_contract_id_filter(self):
        drafts = inject.build_drafts(SAMPLE_AUDIT, contract_id_filter=["ASC-1001"])
        ids = [d["draft_id"].split(":")[1] for d in drafts]
        self.assertEqual(ids, ["ASC-1001"])


if __name__ == "__main__":
    unittest.main()
