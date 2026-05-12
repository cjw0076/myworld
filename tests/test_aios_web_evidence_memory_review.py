import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from scripts.aios_web_evidence_memory_review import build_review_packet, validate_review_packet


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "aios_web_evidence_memory_review.py"
RECEIPT = ROOT / "docs" / "evidence" / "ASC-0031-web-evidence.json"
MEMORYOS_ROOT = ROOT / "memoryOS"


class AiosWebEvidenceMemoryReviewTest(unittest.TestCase):
    def test_build_review_packet_keeps_candidates_draft_only(self) -> None:
        packet = build_review_packet(RECEIPT, ROOT)

        self.assertEqual(packet["schema_version"], "aios.web_evidence_memory_review.v1")
        self.assertFalse(packet["auto_accept"])
        self.assertEqual(packet["memoryos_target_status"], "draft")
        self.assertTrue(packet["review_required"])
        self.assertEqual(packet["candidate_count"], len(packet["candidates"]))
        self.assertGreater(packet["candidate_count"], 0)
        for candidate in packet["candidates"]:
            self.assertEqual(candidate["status"], "draft")
            self.assertEqual(candidate["evidence_state"], "unreviewed")
            self.assertTrue(candidate["review_required"])
            self.assertFalse(candidate["auto_accept"])
            self.assertEqual(candidate["raw_refs"], ["docs/evidence/ASC-0031-web-evidence.json"])
            self.assertTrue(candidate["provenance"]["sources"])

    def test_validate_rejects_auto_accept_candidate(self) -> None:
        packet = build_review_packet(RECEIPT, ROOT)
        packet["candidates"][0]["auto_accept"] = True

        errors = validate_review_packet(packet)

        self.assertIn("candidates[0].auto_accept must be false", errors)

    def test_cli_build_writes_candidate_and_hive_run_bundle(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            output = Path(tmp) / "candidates.json"
            run_bundle = Path(tmp) / "run_bundle"

            result = subprocess.run(
                [
                    sys.executable,
                    SCRIPT.as_posix(),
                    "--root",
                    ROOT.as_posix(),
                    "build",
                    "docs/evidence/ASC-0031-web-evidence.json",
                    "--output",
                    output.as_posix(),
                    "--run-bundle",
                    run_bundle.as_posix(),
                    "--json",
                ],
                cwd=ROOT,
                text=True,
                capture_output=True,
                check=False,
            )

            self.assertEqual(result.returncode, 0, result.stderr)
            payload = json.loads(output.read_text(encoding="utf-8"))
            self.assertEqual(payload["candidate_count"], 3)
            self.assertTrue((run_bundle / "run_state.json").exists())
            drafts = json.loads((run_bundle / "memory_drafts.json").read_text(encoding="utf-8"))
            self.assertEqual(len(drafts["memory_drafts"]), payload["candidate_count"])
            self.assertTrue(all(draft["status"] == "draft" for draft in drafts["memory_drafts"]))

    def test_memoryos_import_run_dry_run_accepts_generated_bundle(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            run_bundle = Path(tmp) / "run_bundle"
            subprocess.run(
                [
                    sys.executable,
                    SCRIPT.as_posix(),
                    "--root",
                    ROOT.as_posix(),
                    "build",
                    "docs/evidence/ASC-0031-web-evidence.json",
                    "--run-bundle",
                    run_bundle.as_posix(),
                ],
                cwd=ROOT,
                text=True,
                capture_output=True,
                check=True,
            )

            result = subprocess.run(
                [
                    sys.executable,
                    "-m",
                    "memoryos.cli",
                    "--root",
                    ROOT.as_posix(),
                    "import-run",
                    run_bundle.as_posix(),
                    "--dry-run",
                    "--json",
                ],
                cwd=MEMORYOS_ROOT,
                text=True,
                capture_output=True,
                check=False,
            )

            self.assertEqual(result.returncode, 0, result.stderr)
            payload = json.loads(result.stdout)
            self.assertEqual(payload["schema_version"], "K43.2")
            self.assertEqual(payload["status"], "dry_run_ok")
            self.assertTrue(payload["dry_run"])
            self.assertEqual(payload["counts"]["planned"]["memory_objects"], 3)
            self.assertEqual(payload["counts"]["imported"]["memory_objects"], 3)
            self.assertFalse(payload["run_refs"]["raw_refs_included"])


if __name__ == "__main__":
    unittest.main()
