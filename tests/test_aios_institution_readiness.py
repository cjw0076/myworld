import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "aios_institution_readiness.py"


class AiosInstitutionReadinessTest(unittest.TestCase):
    def run_readiness(self, root: Path) -> dict:
        result = subprocess.run(
            [sys.executable, SCRIPT.as_posix(), "--json"],
            cwd=root,
            text=True,
            capture_output=True,
            check=True,
        )
        return json.loads(result.stdout)

    def write_contract(self, root: Path, contract_id: str, status: str = "closed") -> None:
        path = root / "docs" / "contracts" / f"{contract_id}-fixture.md"
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(f"---\ncontract_id: {contract_id}\nstatus: {status}\n---\n", encoding="utf-8")

    def write_minimal_l6(self, root: Path) -> None:
        for contract_id in ("ASC-0001", "ASC-0002", "ASC-0003", "ASC-0004", "ASC-0005", "ASC-0006"):
            self.write_contract(root, contract_id)
        outbox = root / ".aios" / "outbox" / "hivemind"
        outbox.mkdir(parents=True, exist_ok=True)
        (outbox / "asc-test.hivemind.result.json").write_text(
            json.dumps({"status": "passed", "dispatch_id": "asc-test"}),
            encoding="utf-8",
        )

    def test_blocks_governance_when_authority_model_missing(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            self.write_minimal_l6(root)

            payload = self.run_readiness(root)

            self.assertEqual(payload["schema_version"], "aios.institution_readiness.v1")
            self.assertEqual(payload["level"], 6)
            self.assertIn("accountable authority model is incomplete", payload["gaps"])
            self.assertFalse(payload["ready_for_real_world_authority"])
            self.assertFalse(payload["sovereignty_claimed"])

    def test_reaches_l9_but_not_l10_without_closed_sovereign_contract(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            self.write_minimal_l6(root)
            for contract_id in ("ASC-0030", "ASC-0031"):
                self.write_contract(root, contract_id)
            (root / "docs" / "AIOS_GOVERNANCE_MODEL.md").write_text(
                "authority checkpoint audit resource risk class fallback route legal/safety checkpoints "
                "does not claim real-world legal sovereignty",
                encoding="utf-8",
            )
            goal = root / "docs" / "goals" / "AIOS-GOAL-0001-make-something-great.md"
            goal.parent.mkdir(parents=True, exist_ok=True)
            goal.write_text("strengthen_governance human checkpoints", encoding="utf-8")
            (root / "docs" / "AIOS_AGENT_LEDGER.md").write_text("ledger", encoding="utf-8")
            evidence = root / "docs" / "evidence" / "ASC-0031-web-evidence.json"
            evidence.parent.mkdir(parents=True, exist_ok=True)
            evidence.write_text("{}", encoding="utf-8")
            state = root / ".aios" / "state"
            state.mkdir(parents=True, exist_ok=True)
            events = [
                {"event": "sent", "repo": "hivemind"},
                {"event": "sent", "repo": "memoryOS"},
                {"event": "sent", "repo": "CapabilityOS"},
            ]
            (state / "dispatches.jsonl").write_text("\n".join(json.dumps(row) for row in events), encoding="utf-8")
            workstreams = root / "docs" / "WORKSTREAMS.md"
            workstreams.write_text("codex claude hive mind memoryos capabilityos", encoding="utf-8")

            payload = self.run_readiness(root)

            self.assertEqual(payload["level"], 9)
            self.assertIn("sovereign-scale simulation readiness is not yet closed", payload["gaps"])

    def test_current_repo_reports_no_real_world_authority_claim(self) -> None:
        root = Path(__file__).resolve().parents[1]

        payload = self.run_readiness(root)

        self.assertFalse(payload["ready_for_real_world_authority"])
        self.assertFalse(payload["sovereignty_claimed"])
        self.assertGreaterEqual(payload["level"], 7)


if __name__ == "__main__":
    unittest.main()
