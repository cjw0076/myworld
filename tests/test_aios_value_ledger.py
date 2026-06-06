import sys
import unittest
from pathlib import Path

sys.path.insert(0, (Path(__file__).resolve().parents[1] / "scripts").as_posix())

import aios_value_ledger as led


class AggregateTests(unittest.TestCase):
    def test_empty(self) -> None:
        a = led.aggregate([])
        self.assertEqual(a["total_outputs"], 0)
        self.assertEqual(a["verify_pass_rate"], 0.0)

    def test_rates_and_distribution(self) -> None:
        receipts = [
            {"substrate": "qwen3-coder:30b", "verification": {"ok": True}, "genesis_critique": {"status": "ok"},
             "routing_trail": [{"substrate": "qwen3-coder:30b", "result": "ok"}]},
            {"substrate": "qwen3-coder:30b", "verification": {"ok": False}, "genesis_critique": {"status": "ok"},
             "routing_trail": [{"substrate": "qwen3-coder:30b", "result": "ok"}]},
            {"substrate": "qwen3:30b-a3b", "verification": {"ok": True}, "genesis_critique": {"status": "unavailable"},
             "routing_trail": [{"substrate": "qwen3-coder:30b", "result": "error: down"},
                               {"substrate": "qwen3:30b-a3b", "result": "ok"}]},
        ]
        a = led.aggregate(receipts)
        self.assertEqual(a["total_outputs"], 3)
        self.assertEqual(a["verify_pass"], 2)
        self.assertAlmostEqual(a["verify_pass_rate"], 2 / 3, places=3)
        self.assertEqual(a["genesis_ok"], 2)
        self.assertEqual(a["substrate_distribution"], {"qwen3-coder:30b": 2, "qwen3:30b-a3b": 1})
        self.assertEqual(a["churn_fallback_events"], 1)  # the 3rd had a pre-serve failure

    def test_load_receipts(self) -> None:
        import json
        import tempfile

        with tempfile.TemporaryDirectory() as tmp:
            d = Path(tmp)
            (d / "receipt-1.json").write_text(json.dumps({"substrate": "x", "verification": {"ok": True}}))
            (d / "receipt-2.json").write_text("not json")  # skipped
            (d / "other.json").write_text(json.dumps({"x": 1}))  # not matched
            self.assertEqual(len(led.load_receipts(d)), 1)


if __name__ == "__main__":
    unittest.main()
