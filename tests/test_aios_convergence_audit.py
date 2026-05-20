"""ASC-0211 L3 routine #1 — convergence audit unit tests."""
from __future__ import annotations

import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
SCRIPT = REPO_ROOT / "scripts" / "aios_convergence_audit.py"


CONTRACT_HIGH_CHALLENGE = """---
contract_id: ASC-9001
slug: high-challenge-fixture
status: closed
accepted: 2026-05-01 KST
closed: 2026-05-10 KST
---

# ASC-9001 High Challenge Fixture

## Genesis Escape Review

Plain language: challenge against frame.

## Stop Conditions

- if X then stop
- if Y then stop

## Named Exit

Closed when verified.

## Verification Gate

```
adversarial review
```

evidence: mem_abc123def, trace_id: 12, https://example.com/x,
supersedes_relation, prompt-prison check, cross-domain transfer.
"""


CONTRACT_FOOTPRINT = """---
contract_id: ASC-9002
slug: footprint-fixture
status: closed
accepted: 2026-05-20T18:00:00+09:00
closed: 2026-05-20T18:03:00+09:00
closeout_authority: claude@myworld operator
---

# ASC-9002

per founder said, founder 명시 frame 그대로.

evidence_refs: []
"""


class ConvergenceAuditTest(unittest.TestCase):
    def _run(self, *args: str) -> dict:
        r = subprocess.run(
            [sys.executable, str(SCRIPT), *args, "--json"],
            capture_output=True, text=True, check=False,
        )
        self.assertEqual(r.returncode, 0, r.stderr)
        return json.loads(r.stdout)

    def test_high_challenge_contract_scores_high(self):
        with tempfile.TemporaryDirectory() as td:
            p = Path(td) / "high.md"
            p.write_text(CONTRACT_HIGH_CHALLENGE, encoding="utf-8")
            out = self._run(str(p))
        self.assertEqual(out["count"], 1)
        row = out["rows"][0]
        self.assertGreaterEqual(row["challenge_score"], 6)
        self.assertIn(row["verdict"], ("real_challenge", "mixed"))
        self.assertIn("genesis_review", row["challenge_hits"])
        self.assertIn("memory_citation", row["challenge_hits"])

    def test_footprint_contract_scores_high_on_footprint(self):
        with tempfile.TemporaryDirectory() as td:
            p = Path(td) / "fp.md"
            p.write_text(CONTRACT_FOOTPRINT, encoding="utf-8")
            out = self._run(str(p))
        row = out["rows"][0]
        # accepted to closed in 3 minutes → flagged
        self.assertIn("auto_close_under_10min", row["footprint_hits"])
        self.assertIn("frame_echo", row["footprint_hits"])
        self.assertIn("no_evidence_refs", row["footprint_hits"])
        self.assertGreaterEqual(row["footprint_score"], 3)

    def test_schema_version_in_envelope(self):
        with tempfile.TemporaryDirectory() as td:
            p = Path(td) / "x.md"
            p.write_text(CONTRACT_HIGH_CHALLENGE, encoding="utf-8")
            out = self._run(str(p))
        self.assertEqual(out["schema_version"], "aios.convergence_audit.v1")
        self.assertIn("generated_at", out)

    def test_verdict_only_compact_mode(self):
        with tempfile.TemporaryDirectory() as td:
            p = Path(td) / "x.md"
            p.write_text(CONTRACT_HIGH_CHALLENGE, encoding="utf-8")
            r = subprocess.run(
                [sys.executable, str(SCRIPT), str(p), "--verdict-only"],
                capture_output=True, text=True, check=False,
            )
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertIn("ASC-9001", r.stdout)
        self.assertIn("ch=", r.stdout)


if __name__ == "__main__":
    unittest.main()
