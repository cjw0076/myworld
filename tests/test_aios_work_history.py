import json
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, (Path(__file__).resolve().parents[1] / "scripts").as_posix())

import aios_work_history as w


class SummarizeTests(unittest.TestCase):
    def test_copilot_receipt(self) -> None:
        s = w.summarize({"schema_version": "aios.deadline_copilot.v1", "generated_at": "2026-06-07",
                         "verification": {"ok": True}, "items": [1, 2], "substrate": "qwen3-coder:30b"})
        self.assertEqual(s["organ"], "deadline_copilot")
        self.assertEqual(s["status"], "ok")
        self.assertEqual(s["what"], "2 items planned")
        self.assertEqual(s["substrate"], "qwen3-coder:30b")

    def test_radar_receipt(self) -> None:
        s = w.summarize({"schema_version": "aios.star_radar.v1", "generated_at": "2026-06-07",
                         "candidates": [{}, {}, {}]})
        self.assertEqual(s["organ"], "star_radar")
        self.assertEqual(s["what"], "3 absorption candidates")

    def test_tuition_rows_in_dict(self) -> None:
        s = w.summarize({"schema_version": "aios.tuition_copilot.v1", "analysis": {"rows": [1, 2, 3]}})
        self.assertEqual(s["what"], "3 rows analyzed")


class LoadHistoryTests(unittest.TestCase):
    def test_aggregates_sorted_newest_first(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            d = Path(tmp)
            (d / "a").mkdir()
            (d / "b").mkdir()
            (d / "a" / "receipt-1.json").write_text(json.dumps({"schema_version": "aios.x.v1", "generated_at": "2026-06-05"}))
            (d / "b" / "receipt-2.json").write_text(json.dumps({"schema_version": "aios.y.v1", "generated_at": "2026-06-07"}))
            (d / "a" / "receipt-3.json").write_text("not json")  # skipped
            hist = w.load_history(d)
            self.assertEqual([h["when"] for h in hist], ["2026-06-07", "2026-06-05"])  # newest first

    def test_missing_generated_at_falls_back_to_mtime(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            d = Path(tmp)
            (d / "x").mkdir()
            (d / "x" / "receipt-1.json").write_text(json.dumps({"schema_version": "aios.z.v1"}))  # no generated_at
            hist = w.load_history(d)
            self.assertEqual(len(hist), 1)
            self.assertNotEqual(hist[0]["when"], "?")  # mtime fallback applied
            self.assertRegex(hist[0]["when"], r"^\d{4}-\d{2}-\d{2}$")


if __name__ == "__main__":
    unittest.main()
