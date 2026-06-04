import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "aios_repair_dispatch_log.py"


class AiosRepairDispatchLogTest(unittest.TestCase):
    def test_dry_run_reports_malformed_without_writing(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            state = root / ".aios" / "state"
            state.mkdir(parents=True)
            log = state / "dispatches.jsonl"
            log.write_text('{"event": "created"}\n{"event": "broken"\n', encoding="utf-8")

            result = subprocess.run(
                [sys.executable, SCRIPT.as_posix(), "--json"],
                cwd=root,
                text=True,
                capture_output=True,
                check=True,
            )

            payload = json.loads(result.stdout)
            self.assertFalse(payload["apply"])
            self.assertEqual(1, payload["valid_lines"])
            self.assertEqual(1, payload["malformed_lines"])
            self.assertEqual('{"event": "created"}\n{"event": "broken"\n', log.read_text(encoding="utf-8"))
            self.assertEqual([], list(state.glob("*.backup.*")))

    def test_apply_quarantines_raw_line_and_rewrites_valid_jsonl(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            state = root / ".aios" / "state"
            state.mkdir(parents=True)
            log = state / "dispatches.jsonl"
            good = {"event": "created", "dispatch_id": "asc-good"}
            bad = '{"event": "created", "dispatch_id": "broken'
            log.write_text(json.dumps(good) + "\n" + bad + "\n", encoding="utf-8")

            result = subprocess.run(
                [sys.executable, SCRIPT.as_posix(), "--apply", "--json"],
                cwd=root,
                text=True,
                capture_output=True,
                check=True,
            )

            payload = json.loads(result.stdout)
            self.assertTrue(payload["apply"])
            self.assertEqual(1, payload["valid_lines_preserved"])
            self.assertEqual(1, payload["malformed_lines_quarantined"])
            self.assertEqual(json.dumps(good) + "\n", log.read_text(encoding="utf-8"))
            backup_paths = list(state.glob("dispatches.jsonl.backup.*"))
            quarantine_paths = list(state.glob("dispatches.jsonl.malformed.*"))
            receipt_paths = list(state.glob("dispatches.jsonl.repair.*.json"))
            self.assertEqual(1, len(backup_paths))
            self.assertEqual(1, len(quarantine_paths))
            self.assertEqual(1, len(receipt_paths))
            self.assertIn(bad, quarantine_paths[0].read_text(encoding="utf-8"))
            receipt = json.loads(receipt_paths[0].read_text(encoding="utf-8"))
            self.assertNotIn(bad, json.dumps(receipt))
            self.assertEqual("aios.dispatch_log_repair.v1", receipt["schema_version"])


if __name__ == "__main__":
    unittest.main()
