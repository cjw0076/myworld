import sys
import unittest
from pathlib import Path

sys.path.insert(0, (Path(__file__).resolve().parents[1] / "scripts").as_posix())

import aios_exam_copilot as e

EXAMS = [
    {"course": "자료구조", "title": "기말", "due": "2026-06-10"},
    {"course": "선형대수", "title": "기말", "due": "2026-06-12"},
]


class VerifyPrepTests(unittest.TestCase):
    def test_clean_passes(self) -> None:
        prep = [
            {"date": "2026-06-08", "course": "자료구조"},
            {"date": "2026-06-09", "course": "자료구조"},
            {"date": "2026-06-11", "course": "선형대수"},
        ]
        v = e.verify_prep(prep, EXAMS, "2026-06-07")
        self.assertTrue(v["ok"])

    def test_prep_on_or_after_exam_flagged(self) -> None:
        prep = [{"date": "2026-06-10", "course": "자료구조"}, {"date": "2026-06-11", "course": "선형대수"}]
        v = e.verify_prep(prep, EXAMS, "2026-06-07")
        self.assertFalse(v["ok"])
        self.assertTrue(any("not before exam" in x["issue"] and x["course"] == "자료구조" for x in v["violations"]))

    def test_missing_prep_flagged(self) -> None:
        prep = [{"date": "2026-06-08", "course": "자료구조"}]
        v = e.verify_prep(prep, EXAMS, "2026-06-07")
        self.assertTrue(any(x["course"] == "선형대수" and x["issue"] == "no prep scheduled" for x in v["violations"]))

    def test_prep_before_today_flagged(self) -> None:
        prep = [{"date": "2026-06-01", "course": "자료구조"}, {"date": "2026-06-11", "course": "선형대수"}]
        v = e.verify_prep(prep, EXAMS, "2026-06-07")
        self.assertTrue(any("before today" in x["issue"] for x in v["violations"]))

    def test_reuses_parse_ical(self) -> None:
        # the factory reuse: exam dates come from the shared .ics parser
        exams = e.parse_ical("BEGIN:VEVENT\nSUMMARY:중간\nDTSTART:20260610\nCATEGORIES:OS\nEND:VEVENT\n")
        self.assertEqual(exams[0]["due"], "2026-06-10")
        self.assertEqual(exams[0]["course"], "OS")


class RepairLoopTests(unittest.TestCase):
    def setUp(self) -> None:
        self._gp = e.generate_prep

    def tearDown(self) -> None:
        e.generate_prep = self._gp

    def test_repairs_until_valid(self) -> None:
        calls = {"n": 0}

        def gp(exams, today, feedback=""):
            calls["n"] += 1
            if calls["n"] == 1:  # prep after the exam (06-10)
                return "bad", [{"date": "2026-06-15", "course": "자료구조"}], "x", []
            return "good", [{"date": "2026-06-08", "course": "자료구조"}], "x", []

        e.generate_prep = gp
        r = e.run([{"course": "자료구조", "title": "기말", "due": "2026-06-10"}], "2026-06-06")
        self.assertTrue(r["verification"]["ok"])
        self.assertEqual(r["verify_attempts"], 2)
        self.assertEqual(r["plan"], "good")

    def test_stops_at_max_tries(self) -> None:
        e.generate_prep = lambda ex, t, f="": ("bad", [{"date": "2026-06-15", "course": "자료구조"}], "x", [])
        r = e.run([{"course": "자료구조", "title": "기말", "due": "2026-06-10"}], "2026-06-06", max_tries=2)
        self.assertFalse(r["verification"]["ok"])
        self.assertEqual(r["verify_attempts"], 2)


if __name__ == "__main__":
    unittest.main()
