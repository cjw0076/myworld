"""ASC-0213 closure_gate tests."""
from __future__ import annotations

import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
SCRIPT = REPO_ROOT / "scripts" / "aios_closure_gate.py"


def _fixture(td: Path, contract_id: str, body: str, *, override: str = "",
             accepted: str = "", closed: str = "") -> Path:
    overr = f"closure_gate_override: {override}\n" if override else ""
    acc_line = f"accepted: {accepted}\n" if accepted else ""
    cls_line = f"closed: {closed}\n" if closed else ""
    p = td / f"{contract_id}.md"
    p.write_text(
        f"---\ncontract_id: {contract_id}\nslug: fx\nstatus: closed\n"
        f"{acc_line}{cls_line}{overr}---\n\n{body}\n",
        encoding="utf-8",
    )
    return p


def _run(contract_path: Path, *extra: str) -> tuple[int, dict]:
    r = subprocess.run(
        [sys.executable, str(SCRIPT), str(contract_path), "--json", *extra],
        capture_output=True, text=True, check=False, cwd=str(REPO_ROOT),
    )
    return r.returncode, (json.loads(r.stdout) if r.stdout else {})


class ClosureGateTest(unittest.TestCase):
    def test_block_on_footprint_consensus(self):
        with tempfile.TemporaryDirectory() as td:
            # 2-min close + frame echo + no evidence + closeout claude self
            # → footprint_score≥3, audit_verdict=footprint_consensus → block.
            p = _fixture(Path(td), "ASC-9001",
                         "per founder said. evidence_refs: []. quick close. "
                         "closeout_authority: claude@myworld.",
                         accepted="2026-05-20T18:00:00+09:00",
                         closed="2026-05-20T18:02:00+09:00")
            rc, out = _run(p)
        self.assertEqual(out.get("verdict"), "block")
        self.assertEqual(out.get("effective"), "block")
        self.assertEqual(rc, 1)

    def test_pass_on_real_challenge(self):
        # Force high challenge score with rich evidence markers
        rich = (
            "## Genesis Escape Review\n"
            "## Stop Conditions\n"
            "## Named Exit\n"
            "## Verification Gate\n"
            "evidence: mem_abc123def4 mem_def4567890 trace_id: 12 "
            "https://example.com/a https://arxiv.org/abs/x.y "
            "superseded_by relationship, prompt-prison check, "
            "cross-domain transfer, adversarial review pass.\n"
        )
        with tempfile.TemporaryDirectory() as td:
            p = _fixture(Path(td), "ASC-9002", rich)
            rc, out = _run(p)
        self.assertIn(out.get("verdict"), ("pass", "warn"))
        self.assertEqual(rc, 0)

    def test_override_promotes_block_to_pass_with_override(self):
        with tempfile.TemporaryDirectory() as td:
            p = _fixture(Path(td), "ASC-9003",
                         "per founder said. evidence_refs: []. quick close. "
                         "closeout_authority: claude@myworld.",
                         accepted="2026-05-20T18:00:00+09:00",
                         closed="2026-05-20T18:02:00+09:00",
                         override="L3 routines enacted; gate textual evidence is incomplete signal")
            rc, out = _run(p)
        # Underlying verdict still block, but effective should be pass_with_override
        self.assertEqual(out.get("verdict"), "block")
        self.assertEqual(out.get("effective"), "pass_with_override")
        self.assertEqual(rc, 0)
        self.assertIn("L3 routines", out.get("override_reason", ""))

    def test_allow_block_flag_returns_zero_even_on_block(self):
        with tempfile.TemporaryDirectory() as td:
            p = _fixture(Path(td), "ASC-9004",
                         "per founder said. evidence_refs: []. "
                         "closeout_authority: claude@myworld.",
                         accepted="2026-05-20T18:00:00+09:00",
                         closed="2026-05-20T18:02:00+09:00")
            rc, _ = _run(p, "--allow-block")
        self.assertEqual(rc, 0)


if __name__ == "__main__":
    unittest.main()
