import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "aios_contract_reconcile.py"


def write_contract(root: Path, number: int, status: str, closed: str = "") -> None:
    path = root / "docs" / "contracts" / f"ASC-{number:04d}-test.md"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        f"""---
contract_id: ASC-{number:04d}
status: {status}
goal: test
closed: {closed}
---

# Test
""",
        encoding="utf-8",
    )


class ContractReconcileTest(unittest.TestCase):
    def run_script(self, root: Path, *args: str) -> dict:
        result = subprocess.run(
            [sys.executable, SCRIPT.as_posix(), "--root", root.as_posix(), *args, "--json"],
            text=True,
            capture_output=True,
            check=True,
        )
        return json.loads(result.stdout)

    def test_accepted_without_closed_is_not_complete(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            write_contract(root, 56, "accepted")
            payload = self.run_script(root, "--from", "56", "--to", "56")
        row = payload["rows"][0]
        self.assertEqual(row["classification"], "continue_implementation")
        self.assertFalse(row["closed"])

    def test_held_provider_backpressure_becomes_retry_now(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            write_contract(root, 56, "accepted")
            state = root / ".aios" / "state"
            state.mkdir(parents=True)
            (state / "dispatches.jsonl").write_text(
                json.dumps(
                    {
                        "dispatch_id": "asc-0056",
                        "contract_id": "ASC-0056",
                        "status": "held",
                        "reason": "provider_backpressure_blocks_memoryos_child_execution",
                    }
                )
                + "\n",
                encoding="utf-8",
            )
            payload = self.run_script(root, "--from", "56", "--to", "56")
        self.assertEqual(payload["rows"][0]["classification"], "retry_now")

    def test_held_non_actionable_contract_is_not_next_contract(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            write_contract(root, 56, "accepted")
            write_contract(root, 59, "accepted")
            state = root / ".aios" / "state"
            state.mkdir(parents=True)
            (state / "dispatches.jsonl").write_text(
                json.dumps(
                    {
                        "dispatch_id": "asc-0056-retry-1",
                        "contract_id": "ASC-0056",
                        "status": "held",
                        "reason": "partial_memoryos_doc_radar_ingest_committed_provider_fallback_failed",
                    }
                )
                + "\n",
                encoding="utf-8",
            )
            payload = self.run_script(root, "--from", "56", "--to", "59")

        self.assertEqual(payload["rows"][0]["classification"], "hold")
        self.assertEqual(payload["next_contract"], "ASC-0059")
        self.assertNotIn("ASC-0056", payload["execution_order"])

    def test_released_accepted_contract_can_close_now(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            write_contract(root, 66, "accepted")
            state = root / ".aios" / "state"
            state.mkdir(parents=True)
            (state / "dispatches.jsonl").write_text(
                json.dumps({"dispatch_id": "asc-0066", "contract_id": "ASC-0066", "status": "released"}) + "\n",
                encoding="utf-8",
            )
            payload = self.run_script(root, "--from", "66", "--to", "66")
        self.assertEqual(payload["rows"][0]["classification"], "close_now")

    def test_write_markdown_report(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            write_contract(root, 67, "accepted")
            out = root / "docs" / "AIOS_CONTRACT_RECONCILIATION.md"
            self.run_script(root, "--from", "67", "--to", "67", "--write", out.as_posix())
            text = out.read_text(encoding="utf-8")
        self.assertIn("ASC-0067", text)
        self.assertIn("continue_implementation", text)


if __name__ == "__main__":
    unittest.main()
