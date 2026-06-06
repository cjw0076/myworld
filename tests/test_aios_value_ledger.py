import sys
import unittest
from pathlib import Path

sys.path.insert(0, (Path(__file__).resolve().parents[1] / "scripts").as_posix())

import aios_value_ledger as led


class AggregateTests(unittest.TestCase):
    def test_empty(self) -> None:
        a = led.aggregate([])
        self.assertEqual(a["total_outputs"], 0)
        self.assertEqual(a["capabilities"], {})

    def test_groups_by_capability(self) -> None:
        receipts = [
            {"schema_version": "aios.deadline_copilot.v1", "substrate": "qwen3-coder:30b",
             "verification": {"ok": True}, "genesis_critique": {"status": "ok"}, "verify_attempts": 2,
             "routing_trail": [{"substrate": "qwen3-coder:30b", "result": "ok"}]},
            {"schema_version": "aios.deadline_copilot.v1", "substrate": "qwen3:30b-a3b",
             "verification": {"ok": False}, "genesis_critique": {"status": "ok"}, "verify_attempts": 1,
             "routing_trail": [{"substrate": "qwen3-coder:30b", "result": "error: down"},
                               {"substrate": "qwen3:30b-a3b", "result": "ok"}]},
            # a different capability with no verification/genesis fields (grade-shaped)
            {"schema_version": "aios.grade_copilot.v1", "substrate": "qwen3-coder:30b",
             "routing_trail": [{"substrate": "qwen3-coder:30b", "result": "ok"}]},
        ]
        a = led.aggregate(receipts)
        self.assertEqual(a["total_outputs"], 3)
        self.assertEqual(set(a["capabilities"]), {"aios.deadline_copilot.v1", "aios.grade_copilot.v1"})
        dl = a["capabilities"]["aios.deadline_copilot.v1"]
        self.assertEqual(dl["outputs"], 2)
        self.assertEqual((dl["verify_pass"], dl["verify_of"]), (1, 2))
        self.assertEqual((dl["repaired"], dl["repaired_of"]), (1, 2))  # one needed a re-gen
        self.assertEqual(dl["churn_fallback_events"], 1)
        gr = a["capabilities"]["aios.grade_copilot.v1"]
        self.assertEqual((gr["verify_pass"], gr["verify_of"]), (0, 0))  # no verify gate → not counted
        self.assertEqual(gr["substrate_distribution"], {"qwen3-coder:30b": 1})

    def test_load_receipts_recurses(self) -> None:
        import json
        import tempfile

        with tempfile.TemporaryDirectory() as tmp:
            d = Path(tmp)
            (d / "copilot").mkdir()
            (d / "grade").mkdir()
            (d / "copilot" / "receipt-1.json").write_text(json.dumps({"schema_version": "x"}))
            (d / "grade" / "receipt-2.json").write_text(json.dumps({"schema_version": "y"}))
            (d / "copilot" / "other.json").write_text("ignored")
            self.assertEqual(len(led.load_receipts(d)), 2)  # rglob finds both subdirs


if __name__ == "__main__":
    unittest.main()
