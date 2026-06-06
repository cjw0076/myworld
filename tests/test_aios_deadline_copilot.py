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


class InputAdapterTests(unittest.TestCase):
    def test_parse_ical(self) -> None:
        ics = (
            "BEGIN:VCALENDAR\r\n"
            "BEGIN:VEVENT\r\n"
            "SUMMARY:과제 3: 이진탐색트리\r\n"
            "DTSTART;VALUE=DATE:20260608\r\n"
            "CATEGORIES:자료구조\r\n"
            "END:VEVENT\r\n"
            "BEGIN:VEVENT\r\n"
            "SUMMARY:중간고사\r\n"
            "DTSTART:20260610T090000Z\r\n"
            "CATEGORIES:선형대수,exam\r\n"
            "END:VEVENT\r\n"
            "END:VCALENDAR\r\n"
        )
        out = c.parse_ical(ics)
        self.assertEqual(len(out), 2)
        self.assertEqual(out[0], {"title": "과제 3: 이진탐색트리", "due": "2026-06-08", "course": "자료구조"})
        self.assertEqual(out[1]["due"], "2026-06-10")
        self.assertEqual(out[1]["course"], "선형대수")  # first category only

    def test_parse_ical_unfolds_long_summary(self) -> None:
        # RFC5545 fold = CRLF + a single space; unfolding removes exactly that space.
        ics = "BEGIN:VEVENT\nSUMMARY:매우 긴 과제\n 제목이어짐\nDTSTART:20260612\nEND:VEVENT\n"
        out = c.parse_ical(ics)
        self.assertEqual(out[0]["title"], "매우 긴 과제제목이어짐")
        self.assertEqual(out[0]["due"], "2026-06-12")

    def test_parse_csv(self) -> None:
        csv_text = "course,title,due\n자료구조,과제3,2026-06-08\n선형대수,중간고사,2026-06-10\n"
        out = c.parse_csv(csv_text)
        self.assertEqual(len(out), 2)
        self.assertEqual(out[0], {"course": "자료구조", "title": "과제3", "due": "2026-06-08"})

    def test_parse_csv_case_insensitive_and_skips_incomplete(self) -> None:
        csv_text = "Course,Assignment,Deadline\nCS,HW1,2026-06-09\n,Orphan,\n"
        out = c.parse_csv(csv_text)
        self.assertEqual(len(out), 1)
        self.assertEqual(out[0]["title"], "HW1")
        self.assertEqual(out[0]["due"], "2026-06-09")


class NormDateAndSecurityTests(unittest.TestCase):
    def test_norm_date(self) -> None:
        self.assertEqual(c.norm_date("2026-6-2"), "2026-06-02")
        self.assertEqual(c.norm_date("20260608"), "2026-06-08")
        self.assertEqual(c.norm_date("20260610T090000Z"), "2026-06-10")
        self.assertIsNone(c.norm_date("2026-13-40"))
        self.assertIsNone(c.norm_date("garbage"))
        self.assertIsNone(c.norm_date(""))

    def test_verify_normalizes_nonpadded(self) -> None:
        v = c.verify_schedule(
            [{"date": "2026-6-7", "course": "자료구조"}],
            [{"course": "자료구조", "title": "x", "due": "2026-6-8"}],
            "2026-6-5",
        )
        self.assertTrue(v["ok"])  # 06-07 within [06-05, 06-08] after normalization

    def test_verify_flags_invalid_due(self) -> None:
        v = c.verify_schedule(
            [{"date": "2026-06-07", "course": "c"}],
            [{"course": "c", "title": "x", "due": "nope"}],
            "2026-06-05",
        )
        self.assertFalse(v["ok"])
        self.assertTrue(any("invalid due" in x["issue"] for x in v["violations"]))

    def test_ical_prefers_due_over_dtstart(self) -> None:
        ics = "BEGIN:VTODO\nSUMMARY:HW\nDTSTART:20260601\nDUE:20260610\nCATEGORIES:CS\nEND:VTODO\n"
        out = c.parse_ical(ics)
        self.assertEqual(out[0]["due"], "2026-06-10")

    def test_student_dir_blocks_traversal(self) -> None:
        base = (c.ROOT / ".aios" / "copilot").resolve()
        d = c.student_dir("../../etc/passwd").resolve()
        self.assertTrue(str(d).startswith(str(base)))
        self.assertEqual(d.parent, base)  # exactly one safe segment under copilot


class PerStudentMemoryTests(unittest.TestCase):
    def test_empty_dir_no_context(self) -> None:
        import tempfile

        with tempfile.TemporaryDirectory() as t:
            self.assertEqual(c.load_prior_context(Path(t)), "")

    def test_summarizes_prior_courses(self) -> None:
        import json
        import tempfile

        with tempfile.TemporaryDirectory() as t:
            d = Path(t)
            (d / "receipt-1.json").write_text(
                json.dumps({"generated_at": "2026-06-01",
                            "assignments": [{"course": "자료구조"}, {"course": "선형대수"}]})
            )
            ctx = c.load_prior_context(d)
            self.assertIn("자료구조", ctx)
            self.assertIn("선형대수", ctx)
            self.assertIn("2026-06-01", ctx)

    def test_student_dir_isolation(self) -> None:
        self.assertNotEqual(c.student_dir("kim"), c.student_dir("lee"))
        self.assertTrue(c.student_dir("kim").name == "kim")


if __name__ == "__main__":
    unittest.main()
