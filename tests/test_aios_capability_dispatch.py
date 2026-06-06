import sys
import unittest
from pathlib import Path

sys.path.insert(0, (Path(__file__).resolve().parents[1] / "scripts").as_posix())

import aios_capability_dispatch as d
import aios_deadline_copilot as deadline
import aios_exam_copilot as exam
import aios_grade_copilot as grade
import aios_tuition_copilot as tuition


class DetectTests(unittest.TestCase):
    def test_ics_is_deadline_or_exam(self) -> None:
        self.assertEqual(d.detect_capability({"ical": "X"}), "deadline")
        self.assertEqual(d.detect_capability({"ical": "X", "kind": "exam"}), "exam")

    def test_csv_grade(self) -> None:
        self.assertEqual(d.detect_capability({"csv": "course,current,weight_completed,target\n"}), "grade")

    def test_csv_tuition(self) -> None:
        self.assertEqual(d.detect_capability({"csv": "item,due,amount,status\n"}), "tuition")

    def test_csv_deadline(self) -> None:
        self.assertEqual(d.detect_capability({"csv": "course,title,due\n"}), "deadline")

    def test_unknown(self) -> None:
        self.assertIsNone(d.detect_capability({"csv": "a,b,c\n"}))
        self.assertIsNone(d.detect_capability({}))


class DispatchTests(unittest.TestCase):
    def setUp(self) -> None:
        self._runs = (deadline.run, exam.run, grade.run, tuition.run)

    def tearDown(self) -> None:
        deadline.run, exam.run, grade.run, tuition.run = self._runs

    def test_routes_grade(self) -> None:
        grade.run = lambda courses, today: {"cap": "grade", "n": len(courses)}
        cap, receipt = d.dispatch({"csv": "course,current,weight_completed,target\nCS,80,50,90\n"}, "2026-06-06")
        self.assertEqual(cap, "grade")
        self.assertEqual(receipt["n"], 1)

    def test_routes_tuition(self) -> None:
        tuition.run = lambda items, today: {"cap": "tuition", "n": len(items)}
        cap, receipt = d.dispatch({"csv": "item,due,amount,status\n등록금,2026-06-10,3000000,due\n"}, "2026-06-06")
        self.assertEqual(cap, "tuition")
        self.assertEqual(receipt["n"], 1)

    def test_unknown_returns_error(self) -> None:
        cap, receipt = d.dispatch({"csv": "x,y,z\n"}, "2026-06-06")
        self.assertIsNone(cap)
        self.assertIn("error", receipt)


if __name__ == "__main__":
    unittest.main()
