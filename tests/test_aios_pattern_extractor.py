import json
import subprocess
import sys
import unittest
from pathlib import Path

from scripts.aios_pattern_extractor import build_patterns


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "aios_pattern_extractor.py"


class AiosPatternExtractorTest(unittest.TestCase):
    def test_current_corpus_extracts_five_draft_patterns_with_refs(self) -> None:
        payload = build_patterns(ROOT)

        self.assertEqual(payload["schema_version"], "aios.user_pattern.v1")
        self.assertGreaterEqual(len(payload["patterns"]), 5)
        self.assertTrue(all(row["status"] == "draft" for row in payload["patterns"]))
        self.assertTrue(all(row["evidence_refs"] for row in payload["patterns"][:5]))
        as_text = json.dumps(payload, ensure_ascii=False)
        self.assertNotIn("_from_desktop", as_text)
        self.assertNotIn("q1q1e3e3", as_text.lower())
        self.assertEqual(payload["memory_drafts"]["memory_drafts"][0]["type"], "user_pattern")
        self.assertEqual(payload["memory_drafts"]["memory_drafts"][0]["origin"], "pattern_extracted")

    def test_cli_write_outputs_patterns(self) -> None:
        out = ROOT / ".aios" / "patterns" / "founder" / "patterns.json"
        result = subprocess.run(
            [sys.executable, SCRIPT.as_posix(), "--root", ROOT.as_posix(), "--write", ".aios/patterns/founder/patterns.json", "--json"],
            cwd=ROOT,
            text=True,
            capture_output=True,
            check=False,
        )

        self.assertEqual(result.returncode, 0, result.stderr)
        payload = json.loads(result.stdout)
        self.assertTrue(out.exists())
        self.assertGreaterEqual(len(payload["patterns"]), 5)


if __name__ == "__main__":
    unittest.main()
