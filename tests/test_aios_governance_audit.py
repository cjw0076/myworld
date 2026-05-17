import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from scripts.aios_governance_audit import audit_contract, build_audit, render_markdown


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "aios_governance_audit.py"


def write_contract(path: Path, *, contract_id: str, status: str, body: str) -> None:
    path.write_text(
        f"""---
contract_id: {contract_id}
status: {status}
goal: Test contract
---

# {contract_id}

{body}
""",
        encoding="utf-8",
    )


class AiosGovernanceAuditTests(unittest.TestCase):
    def test_scores_closed_contract_with_evidence(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "ASC-9999-demo.md"
            write_contract(
                path,
                contract_id="ASC-9999",
                status="closed",
                body="""DNA reference: Invariant 5.

## Scope

repos: `myworld`

## Receipts

- Verification passed: `python -m unittest tests/test_demo.py`
- Dispatch result: `.aios/outbox/myworld/demo.result.json`
- Dogfood smoke produced a result packet.
""",
            )

            result = audit_contract(path)

        self.assertEqual(result["scores"]["closure_evidence"], 1)
        self.assertEqual(result["scores"]["verification_evidence"], 1)
        self.assertEqual(result["scores"]["dogfood_evidence"], 1)
        self.assertGreater(result["governance_score"], 0.8)

    def test_reports_zero_score_contracts(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "ASC-9998-empty.md"
            write_contract(
                path,
                contract_id="ASC-9998",
                status="accepted",
                body="""## Scope

repos:

- `myworld`
- `hivemind`

## Receipts

Pending.
""",
            )

            result = audit_contract(path)

        self.assertLess(result["governance_score"], 0.5)
        self.assertEqual(result["scores"]["closure_evidence"], 0)
        self.assertEqual(result["scores"]["cross_repo_evidence"], 0)

    def test_build_audit_is_deterministic_and_counts_contracts(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            contracts = root / "docs" / "contracts"
            contracts.mkdir(parents=True)
            write_contract(contracts / "ASC-0001-a.md", contract_id="ASC-0001", status="closed", body="## Receipts\n\n- Verification passed: `python test.py`\n")
            write_contract(contracts / "ASC-0002-b.md", contract_id="ASC-0002", status="accepted", body="## Receipts\n\nPending.\n")

            first = build_audit(root, "docs/contracts/ASC-*.md")
            second = build_audit(root, "docs/contracts/ASC-*.md")

        self.assertEqual(first, second)
        self.assertEqual(first["aggregate"]["contract_count"], 2)
        self.assertEqual(len(first["per_contract"]), 2)

    def test_markdown_report_contains_baseline_and_lowest_contracts(self) -> None:
        audit = build_audit(ROOT, "docs/contracts/ASC-0105*.md")

        report = render_markdown(audit)

        self.assertIn("# AIOS Governance Audit", report)
        self.assertIn("## Baseline", report)
        self.assertIn("## Lowest Contracts", report)

    def test_cli_json_and_write(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            output = Path(tmp) / "audit.md"
            result = subprocess.run(
                [
                    sys.executable,
                    SCRIPT.as_posix(),
                    "--root",
                    ROOT.as_posix(),
                    "--glob",
                    "docs/contracts/ASC-0105*.md",
                    "--write",
                    output.as_posix(),
                    "--json",
                ],
                text=True,
                capture_output=True,
                check=False,
            )
            output_exists = output.exists()

        self.assertEqual(result.returncode, 0, result.stderr)
        payload = json.loads(result.stdout)
        self.assertGreaterEqual(payload["aggregate"]["contract_count"], 1)
        self.assertTrue(output_exists)

    def test_self_check_contains_governance_theater_tripwire(self) -> None:
        text = (ROOT / "scripts" / "aios_self_check.sh").read_text(encoding="utf-8")

        self.assertIn("aios_governance_audit.py --json", text)
        self.assertIn("GOVERNANCE_THEATER", text)
        self.assertIn("governance_theater=true", text)


if __name__ == "__main__":
    unittest.main()
