import sys
import unittest
from pathlib import Path

sys.path.insert(0, (Path(__file__).resolve().parents[1] / "scripts").as_posix())

import aios_tuition_copilot as t

ITEMS = [
    {"item": "등록금", "due": "2026-06-10", "amount": 3000000.0, "status": "due"},
    {"item": "기숙사비", "due": "2026-06-02", "amount": 500000.0, "status": "due"},
    {"item": "보증금", "due": "2026-05-01", "amount": 200000.0, "status": "paid"},
]


class CashflowAnalysisTests(unittest.TestCase):
    def test_totals_exclude_paid(self) -> None:
        a = t.cashflow_analysis(ITEMS, "2026-06-06")
        self.assertEqual(a["total_due"], 3500000.0)  # paid 보증금 excluded

    def test_overdue_detection_and_ordering(self) -> None:
        a = t.cashflow_analysis(ITEMS, "2026-06-06")
        # 기숙사비 due 06-02 < today 06-06 → overdue; comes first (earliest due)
        due_rows = [r for r in a["rows"] if r.get("status") in ("due", "overdue")]
        self.assertEqual(due_rows[0]["item"], "기숙사비")
        self.assertEqual(due_rows[0]["status"], "overdue")
        self.assertEqual(a["overdue_count"], 1)
        self.assertEqual(a["next_due"], "2026-06-02")

    def test_days_until(self) -> None:
        a = t.cashflow_analysis(ITEMS, "2026-06-06")
        reg = next(r for r in a["rows"] if r["item"] == "등록금")
        self.assertEqual(reg["days_until"], 4)  # 06-10 - 06-06

    def test_invalid_date_flagged(self) -> None:
        a = t.cashflow_analysis([{"item": "x", "due": "nope", "amount": 100.0, "status": "due"}], "2026-06-06")
        self.assertEqual(a["rows"][0]["status"], "invalid_date")
        self.assertEqual(a["total_due"], 0.0)


class ParseBursarTests(unittest.TestCase):
    def test_parse_and_skip_bad_amount(self) -> None:
        csv_text = "item,due,amount,status\n등록금,2026-06-10,3000000,due\nbad,2026-06-10,notnum,due\n"
        out = t.parse_bursar_csv(csv_text)
        self.assertEqual(len(out), 1)
        self.assertEqual(out[0]["amount"], 3000000.0)


if __name__ == "__main__":
    unittest.main()
