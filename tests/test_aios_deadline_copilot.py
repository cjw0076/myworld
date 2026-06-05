import sys
import unittest
from pathlib import Path

sys.path.insert(0, (Path(__file__).resolve().parents[1] / "scripts").as_posix())

import aios_deadline_copilot as c

ASSIGNMENTS = [
    {"course": "자료구조", "title": "과제3", "due": "2026-06-08"},
    {"course": "선형대수", "title": "중간고사", "due": "2026-06-10"},
]


class VerifyScheduleTests(unittest.TestCase):
    def test_clean_schedule_passes(self) -> None:
        sched = [
            {"date": "2026-06-05", "course": "자료구조"},
            {"date": "2026-06-08", "course": "자료구조"},
            {"date": "2026-06-09", "course": "선형대수"},
        ]
        v = c.verify_schedule(sched, ASSIGNMENTS, "2026-06-05")
        self.assertTrue(v["ok"])
        self.assertEqual(v["violations"], [])

    def test_work_after_due_is_flagged(self) -> None:
        sched = [{"date": "2026-06-09", "course": "자료구조"},  # due 06-08
                 {"date": "2026-06-09", "course": "선형대수"}]
        v = c.verify_schedule(sched, ASSIGNMENTS, "2026-06-05")
        self.assertFalse(v["ok"])
        self.assertTrue(any("AFTER due" in x["issue"] and x["course"] == "자료구조" for x in v["violations"]))

    def test_unscheduled_course_is_flagged(self) -> None:
        sched = [{"date": "2026-06-06", "course": "자료구조"}]
        v = c.verify_schedule(sched, ASSIGNMENTS, "2026-06-05")
        self.assertTrue(any(x["course"] == "선형대수" and x["issue"] == "not scheduled" for x in v["violations"]))

    def test_work_before_today_is_flagged(self) -> None:
        sched = [{"date": "2026-06-01", "course": "자료구조"},
                 {"date": "2026-06-09", "course": "선형대수"}]
        v = c.verify_schedule(sched, ASSIGNMENTS, "2026-06-05")
        self.assertTrue(any("BEFORE today" in x["issue"] for x in v["violations"]))


class ExtractScheduleTests(unittest.TestCase):
    def test_extracts_inline_json_array(self) -> None:
        text = 'blah\n[{"date":"2026-06-05","course":"자료구조","task":"x"}]\nmore prose'
        out = c.extract_schedule(text)
        self.assertEqual(len(out), 1)
        self.assertEqual(out[0]["course"], "자료구조")

    def test_missing_array_returns_empty(self) -> None:
        self.assertEqual(c.extract_schedule("no json here"), [])

    def test_entries_missing_fields_dropped(self) -> None:
        text = '[{"date":"2026-06-05"},{"course":"x","date":"2026-06-06"}]'
        out = c.extract_schedule(text)
        self.assertEqual(len(out), 1)  # first dropped (no course)


if __name__ == "__main__":
    unittest.main()
