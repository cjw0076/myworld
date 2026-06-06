import sys
import unittest
from pathlib import Path

sys.path.insert(0, (Path(__file__).resolve().parents[1] / "scripts").as_posix())

import aios_grade_copilot as g


class GradeAnalysisTests(unittest.TestCase):
    def _one(self, current, weight_completed, target):
        return g.grade_analysis([{"course": "C", "current": current, "weight_completed": weight_completed, "target": target}])[0]

    def test_impossible(self) -> None:
        r = self._one(80, 60, 90)  # earned 48, need (90-48)/0.4 = 105
        self.assertEqual(r["needed_on_remaining"], 105.0)
        self.assertEqual(r["status"], "impossible")

    def test_at_risk(self) -> None:
        r = self._one(85, 50, 90)  # earned 42.5, need 95
        self.assertEqual(r["needed_on_remaining"], 95.0)
        self.assertEqual(r["status"], "at_risk")

    def test_on_track(self) -> None:
        r = self._one(95, 50, 90)  # need 85
        self.assertEqual(r["needed_on_remaining"], 85.0)
        self.assertEqual(r["status"], "on_track")

    def test_secured(self) -> None:
        r = self._one(100, 95, 90)  # need (90-95)/0.05 = -100 → secured
        self.assertEqual(r["status"], "secured")

    def test_final_and_missed(self) -> None:
        self.assertEqual(self._one(92, 100, 90)["status"], "final")
        self.assertEqual(self._one(80, 100, 90)["status"], "missed")
        self.assertIsNone(self._one(92, 100, 90)["needed_on_remaining"])


class ParseGradesTests(unittest.TestCase):
    def test_parse_and_skip_bad(self) -> None:
        csv_text = "course,current,weight_completed,target\n자료구조,85,50,90\nbad,notnum,50,90\n"
        out = g.parse_grades_csv(csv_text)
        self.assertEqual(len(out), 1)
        self.assertEqual(out[0]["course"], "자료구조")
        self.assertEqual(out[0]["current"], 85.0)

    def test_default_target(self) -> None:
        out = g.parse_grades_csv("course,current,weight_completed\nCS,70,40\n")
        self.assertEqual(out[0]["target"], 90)


if __name__ == "__main__":
    unittest.main()
