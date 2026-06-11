import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from scripts.aios_dna_lint import lint_contract


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "aios_dna_lint.py"
DNA = ROOT / "docs" / "AIOS_DNA.md"


class AiosDnaLintTests(unittest.TestCase):
    def test_dna_spec_contains_required_sections(self) -> None:
        text = DNA.read_text(encoding="utf-8")

        self.assertEqual(text.count("### Invariant "), 8)
        self.assertIn("## Preamble", text)
        self.assertIn("## Invariant Interaction Map", text)
        self.assertIn("## Amendment Clause", text)
        self.assertIn("## Dissent Register", text)
        self.assertIn("D1: Detection-first security model is forensic, not protective", text)
        self.assertIn("D4: Decision granularity will force early amendment", text)

    def test_lint_requires_citation_for_cross_repo_scope(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "ASC-9999-demo.md"
            path.write_text(
                """---
contract_id: ASC-9999
status: accepted
goal: Touch Hive execution.
---

# Demo

## Scope

repos:

- `myworld`
- `hivemind`
""",
                encoding="utf-8",
            )

            result = lint_contract(path)

        self.assertTrue(result["required"])
        self.assertTrue(result["missing"])
        self.assertIn("cross_repo_scope", result["reasons"])

    def test_lint_accepts_explicit_invariant_citation(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "ASC-9998-demo.md"
            path.write_text(
                """---
contract_id: ASC-9998
status: accepted
goal: Route private capability work.
---

# Demo

Reference: DNA Invariant 7.

## Scope

repos: `myworld`, `CapabilityOS`
""",
                encoding="utf-8",
            )

            result = lint_contract(path)

        self.assertTrue(result["required"])
        self.assertFalse(result["missing"])
        self.assertEqual(result["citations"], [7])

    def test_lint_marks_simple_myworld_doc_as_not_required(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "ASC-9997-demo.md"
            path.write_text(
                """---
contract_id: ASC-9997
status: accepted
goal: Rename a local note.
---

# Demo

## Scope

repos: `myworld`
""",
                encoding="utf-8",
            )

            result = lint_contract(path)

        self.assertFalse(result["required"])
        self.assertFalse(result["missing"])

    def test_dogfood_contracts_match_expected_baseline(self) -> None:
        dna_result = lint_contract(ROOT / "docs" / "_history" / "contracts" / "ASC-0105-aios-dna-canonical-spec.md")
        old_result = lint_contract(ROOT / "docs" / "_history" / "contracts" / "ASC-0091-memoryos-auto-writeback.md")

        self.assertTrue(dna_result["required"])
        self.assertFalse(dna_result["missing"])
        self.assertTrue(dna_result["citations"])
        self.assertTrue(old_result["required"])
        self.assertTrue(old_result["missing"])

    def test_cli_emits_json_and_never_fails_for_missing_citation(self) -> None:
        result = subprocess.run(
            [
                sys.executable,
                SCRIPT.as_posix(),
                "docs/_history/contracts/ASC-0091-memoryos-auto-writeback.md",
                "--json",
            ],
            cwd=ROOT,
            text=True,
            capture_output=True,
            check=False,
        )

        self.assertEqual(result.returncode, 0, result.stderr)
        payload = json.loads(result.stdout)
        self.assertTrue(payload["missing"])
        self.assertEqual(payload["contract_id"], "ASC-0091")


if __name__ == "__main__":
    unittest.main()
