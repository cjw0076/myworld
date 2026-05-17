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
    contract_id = name.split("-", 1)[0]
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
