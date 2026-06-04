from __future__ import annotations

import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from scripts.aios_persona_audit import build_report


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "aios_persona_audit.py"


def write_contract(root: Path, name: str, body: str, *, accepted: str = "codex@myworld operator") -> None:
    path = root / "docs" / "contracts" / name
    path.parent.mkdir(parents=True, exist_ok=True)
    contract_id = "-".join(name.split("-")[:2])
    path.write_text(
        "\n".join(
            [
                "---",
                f"contract_id: {contract_id}",
                "status: closed",
                "goal: persona audit fixture",
                f"acceptance_authority: {accepted}",
                "---",
                "",
                body,
                "",
            ]
        ),
        encoding="utf-8",
    )


class PersonaAuditTest(unittest.TestCase):
    def test_scores_each_persona_signal(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            write_contract(
                root,
                "ASC-0001-rich.md",
                "Claude Codex providers. Memory trace rtrace_abc123 signal_coverage=1.0. "
                "CapabilityOS recommend top route followed. GenesisOS critic alternatives. "
                "Founder approved cognitive architecture decision.",
            )

            report = build_report(root, window=20)

        self.assertEqual(1, report["contracts_scored"])
        self.assertEqual(1.0, report["scores"]["wrapper_score"])
        self.assertEqual(1.0, report["scores"]["retriever_score"])
        self.assertEqual(1.0, report["scores"]["router_score"])
        self.assertEqual(1.0, report["scores"]["philosophy_score"])
        self.assertEqual(1.0, report["scores"]["sovereign_score"])
        self.assertEqual(1.0, report["scores"]["persona_composite"])

    def test_retriever_signal_accepts_markdown_backticked_coverage(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            write_contract(
                root,
                "ASC-0003-backtick.md",
                "Claude Codex providers. retrieval_trace: `rtrace_backtick123`. "
                "signal_coverage: `1.0`. CapabilityOS recommend top route followed. "
                "GenesisOS critic alternatives. Founder approved.",
            )

            report = build_report(root, window=20)

        self.assertEqual(1.0, report["scores"]["retriever_score"])

    def test_bypassed_personas_score_zero_except_sovereign(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            write_contract(root, "ASC-0002-thin.md", "Only normal tests and ledger records.")

            report = build_report(root, window=20)

        self.assertEqual(0.0, report["scores"]["wrapper_score"])
        self.assertEqual(0.0, report["scores"]["retriever_score"])
        self.assertEqual(0.0, report["scores"]["router_score"])
        self.assertEqual(0.0, report["scores"]["philosophy_score"])
        self.assertEqual(1.0, report["scores"]["sovereign_score"])
        weak = {row["score_key"] for row in report["weak_personas"]}
        self.assertIn("retriever_score", weak)
        self.assertIn("philosophy_score", weak)
        self.assertEqual("ASC-0002", report["contract_gaps"][0]["contract_id"])
        self.assertIn("retriever_score", report["contract_gaps"][0]["missing_personas"])
        self.assertTrue(report["contract_gaps"][0]["recommendations"])

    def test_explicit_role_evidence_and_justified_absence_count_as_handled(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            write_contract(
                root,
                "ASC-0004-role-evidence.md",
                "\n".join(
                    [
                        "## AIOS Role Evidence",
                        "",
                        "### 5-Persona Use",
                        "",
                        "- Hive / Wrapper: codex@myworld single-provider justified.",
                        "- MemoryOS / Retriever: no retrieval trace required;",
                        "  repo-local fixture.",
                        "- CapabilityOS / Router: no new tool route required; local pytest only.",
                        "- GenesisOS / Philosophy: discomfort identified before closure.",
                        "- MyWorld / Sovereign: operator retains override for cognitive architecture.",
                    ]
                ),
            )

            report = build_report(root, window=20)

        self.assertEqual(1.0, report["scores"]["wrapper_score"])
        self.assertEqual(1.0, report["scores"]["retriever_score"])
        self.assertEqual(1.0, report["scores"]["router_score"])
        self.assertEqual(1.0, report["scores"]["philosophy_score"])
        self.assertEqual(1.0, report["scores"]["sovereign_score"])
        self.assertEqual(0.0, report["evidence_scores"]["retriever_score"])
        self.assertEqual(0.0, report["evidence_scores"]["router_score"])
        self.assertEqual([], report["contract_gaps"])
        signals = report["per_contract"][0]["signals"]
        self.assertIn("retriever_score", signals["justified_absences"])
        self.assertIn("router_score", signals["justified_absences"])
        self.assertIn("repo-local fixture", signals["justified_absences"]["retriever_score"])
        self.assertIn("philosophy_score", signals["role_evidence"])
        self.assertIn("sovereign_score", signals["role_evidence"])

    def test_cli_assert_keys(self) -> None:
        result = subprocess.run(
            [
                sys.executable,
                SCRIPT.as_posix(),
                "--root",
                ROOT.as_posix(),
                "--window",
                "5",
                "--json",
                "--assert-keys",
                "wrapper_score,retriever_score,router_score,philosophy_score,sovereign_score,persona_composite",
            ],
            text=True,
            capture_output=True,
            check=False,
        )

        self.assertEqual(result.returncode, 0, result.stderr)
        payload = json.loads(result.stdout)
        self.assertIn("persona_composite", payload["scores"])


if __name__ == "__main__":
    unittest.main()
