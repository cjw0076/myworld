import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "aios_work_view.py"


def make_root() -> tempfile.TemporaryDirectory:
    return tempfile.TemporaryDirectory()


def write_contract(root: Path) -> None:
    path = root / "docs" / "contracts" / "ASC-0067-test.md"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        """---
contract_id: ASC-0067
status: accepted
goal: visible work
closed:
---

# Test
""",
        encoding="utf-8",
    )


class AiosWorkViewTest(unittest.TestCase):
    def run_view(self, root: Path, *args: str) -> dict:
        result = subprocess.run(
            [sys.executable, SCRIPT.as_posix(), "--root", root.as_posix(), *args, "--json"],
            text=True,
            capture_output=True,
            check=True,
        )
        return json.loads(result.stdout)

    def test_status_includes_active_contract_and_blocked_dispatch(self) -> None:
        with make_root() as td:
            root = Path(td)
            write_contract(root)
            state = root / ".aios" / "state"
            state.mkdir(parents=True)
            (state / "dispatches.jsonl").write_text(
                json.dumps({"dispatch_id": "asc-0056", "contract_id": "ASC-0056", "status": "held", "reason": "provider"}) + "\n",
                encoding="utf-8",
            )
            payload = self.run_view(root, "status")
        self.assertEqual(payload["schema_version"], "aios.work_view.v1")
        self.assertEqual(payload["active_contracts"][0]["contract_id"], "ASC-0067")
        self.assertEqual(payload["blocked"][0]["status"], "held")

    def test_latest_result_packet_is_summarized_without_raw_output(self) -> None:
        with make_root() as td:
            root = Path(td)
            outbox = root / ".aios" / "outbox" / "myworld"
            outbox.mkdir(parents=True)
            (outbox / "asc-0067.myworld.result.json").write_text(
                json.dumps({"status": "failed", "stdout": "secret raw output", "evidence": ["cmd"]}),
                encoding="utf-8",
            )
            payload = self.run_view(root, "status")
        result = payload["latest_results"][0]
        self.assertEqual(result["status"], "failed")
        self.assertNotIn("stdout", result)

    def test_contract_view_returns_related_contract(self) -> None:
        with make_root() as td:
            root = Path(td)
            write_contract(root)
            payload = self.run_view(root, "contract", "ASC-0067")
        self.assertTrue(payload["found"])
        self.assertEqual(payload["status"], "accepted")

    def test_missing_runtime_files_degrade_gracefully(self) -> None:
        with make_root() as td:
            payload = self.run_view(Path(td), "status")
        self.assertEqual(payload["health"]["health"], "unknown")
        self.assertEqual(payload["dispatch_summary"]["total"], 0)


if __name__ == "__main__":
    unittest.main()
