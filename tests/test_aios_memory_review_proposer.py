import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from scripts.aios_memory_review_proposer import build_batch, validate_batch


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "aios_memory_review_proposer.py"


class AiosMemoryReviewProposerTests(unittest.TestCase):
    def test_builds_recommendation_only_batch(self) -> None:
        rows = [
            {
                "id": "mem_high",
                "status": "draft",
                "type": "decision",
                "project": "AIOS",
                "origin": "mixed",
                "confidence": 0.9,
                "content": "ASC-0119 closeout recorded a verified self-check repair.",
                "raw_refs": ["docs/contracts/ASC-0119-os-activity-evidence.md"],
                "captured_at": "2026-05-13T00:00:00+09:00",
            },
            {
                "id": "mem_low",
                "status": "draft",
                "type": "decision",
                "project": "AIOS",
                "origin": "mixed",
                "confidence": 0.2,
                "content": "uncertain fragment",
                "raw_refs": [],
                "captured_at": "2026-05-13T01:00:00+09:00",
            },
        ]

        batch = build_batch(ROOT, rows, limit=10)

        self.assertTrue(batch["recommendation_only"])
        self.assertFalse(batch["auto_apply"])
        self.assertEqual(batch["selected_count"], 2)
        self.assertEqual(batch["counts"]["accept"], 1)
        self.assertEqual(batch["counts"]["needs_more_evidence"], 1)
        self.assertEqual([], validate_batch(batch))

    def test_rationales_are_bounded_and_no_auto_approval_occurs(self) -> None:
        rows = [
            {
                "id": "mem_high",
                "status": "draft",
                "confidence": 0.95,
                "content": "A long but valid memory draft with enough provenance for review.",
                "raw_refs": ["source.md"],
                "captured_at": "2026-05-13T00:00:00+09:00",
            }
        ]

        batch = build_batch(ROOT, rows, limit=1)
        proposal = batch["proposals"][0]

        self.assertLessEqual(len(proposal["rationale"]), 200)
        self.assertIn("drafts approve", proposal["operator_command"])
        self.assertFalse(batch["auto_apply"])

    def test_cli_writes_batch_file_from_input_json(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            input_path = tmp_path / "drafts.json"
            output_path = tmp_path / "proposal.json"
            input_path.write_text(
                json.dumps(
                    [
                        {
                            "id": "mem_fixture",
                            "status": "draft",
                            "confidence": 0.85,
                            "content": "Fixture memory has a concrete source reference.",
                            "raw_refs": ["fixture.md"],
                            "captured_at": "2026-05-13T00:00:00+09:00",
                        }
                    ]
                ),
                encoding="utf-8",
            )

            result = subprocess.run(
                [
                    sys.executable,
                    SCRIPT.as_posix(),
                    "--root",
                    ROOT.as_posix(),
                    "--input-json",
                    input_path.as_posix(),
                    "--output",
                    output_path.as_posix(),
                    "--json",
                ],
                text=True,
                capture_output=True,
                check=False,
            )

            self.assertEqual(result.returncode, 0, result.stderr)
            payload = json.loads(result.stdout)
            self.assertTrue(output_path.exists())
            self.assertEqual(payload["selected_count"], 1)
            self.assertEqual(payload["counts"]["accept"], 1)


if __name__ == "__main__":
    unittest.main()
