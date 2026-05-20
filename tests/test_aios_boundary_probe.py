"""ASC-0211 L3 routine #4 — boundary probe tests."""
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

import aios_boundary_probe as bp  # noqa: E402


class BoundaryProbeTest(unittest.TestCase):
    def test_cross_domain_drafts_emit_expected_shape(self):
        drafts = bp.cross_domain_drafts("ASC-DEMO", n=2, seed=42)
        self.assertEqual(len(drafts), 2)
        for d in drafts:
            self.assertEqual(d["schema_version"], "aios.memory_draft_review_request.v1")
            self.assertFalse(d["review_policy"]["auto_accept"])
            self.assertTrue(d["review_policy"]["draft_first"])
            self.assertEqual(d["draft"]["origin"], "aios_boundary_probe")
            self.assertEqual(d["draft"]["provenance"]["kind"], "cross_domain_probe")
            self.assertIn("domain", d["draft"]["provenance"])
            # cross-domain question should mention the target id
            self.assertIn("ASC-DEMO", d["draft"]["content"])

    def test_signature_to_draft(self):
        sig = {"signature": "assumption-silent", "description": "implicit"}
        d = bp.signature_to_draft("ASC-XYZ", sig)
        self.assertEqual(d["draft"]["provenance"]["kind"], "prison_signature")
        self.assertIn("assumption-silent", d["draft"]["content"])
        self.assertIn("ASC-XYZ", d["draft"]["content"])
        self.assertFalse(d["review_policy"]["auto_accept"])

    def test_cross_domain_n_zero(self):
        self.assertEqual(bp.cross_domain_drafts("X", n=0), [])

    def test_genesis_skip_path(self):
        # When --skip-genesis used, only cross-domain probes generated.
        # Smoke via subprocess to also cover argparse path.
        import subprocess
        with tempfile.NamedTemporaryFile("w", suffix=".txt", delete=False) as f:
            f.write("a piece of text to probe")
            tmp = f.name
        try:
            r = subprocess.run(
                [sys.executable, str(SCRIPTS / "aios_boundary_probe.py"),
                 "--text-file", tmp, "--skip-genesis", "--cross-domain-n", "1",
                 "--dry-run", "--json"],
                capture_output=True, text=True, check=False,
                cwd=str(REPO_ROOT),
            )
            self.assertEqual(r.returncode, 0, r.stderr)
            out = json.loads(r.stdout)
            self.assertEqual(out["generated"], 1)
            self.assertIsNone(out["genesis_critic"])
        finally:
            Path(tmp).unlink(missing_ok=True)


if __name__ == "__main__":
    unittest.main()
