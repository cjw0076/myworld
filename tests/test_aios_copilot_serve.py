import sys
import unittest
from pathlib import Path

sys.path.insert(0, (Path(__file__).resolve().parents[1] / "scripts").as_posix())

import aios_copilot_serve as serve
import aios_deadline_copilot as copilot
import aios_grade_copilot as grade
import aios_tuition_copilot as tuition


class PlanRequestTests(unittest.TestCase):
    def setUp(self) -> None:
        self._run = copilot.run
        self._grade_run = grade.run
        self._tuition_run = tuition.run

    def tearDown(self) -> None:
        copilot.run = self._run
        grade.run = self._grade_run
        tuition.run = self._tuition_run

    def test_routes_grade_csv_to_grade_capability(self) -> None:
        grade.run = lambda courses, today: {"schema_version": "aios.grade_copilot.v1", "n": len(courses)}
        status, body = serve.plan_request(
            {"csv": "course,current,weight_completed,target\n자료구조,80,50,90\n"}
        )
        self.assertEqual(status, 200)
        self.assertEqual(body["capability"], "grade")
        self.assertEqual(body["n"], 1)

    def test_routes_tuition_csv(self) -> None:
        tuition.run = lambda items, today: {"schema_version": "aios.tuition_copilot.v1", "n": len(items)}
        status, body = serve.plan_request(
            {"csv": "item,due,amount,status\n등록금,2026-06-10,3000000,due\n"}
        )
        self.assertEqual(status, 200)
        self.assertEqual(body["capability"], "tuition")

    def test_no_assignments_is_400(self) -> None:
        status, body = serve.plan_request({})
        self.assertEqual(status, 400)
        self.assertIn("error", body)

    def test_happy_path(self) -> None:
        copilot.run = lambda a, t, p="": {"plan": "PLAN", "assignments": a, "prior_context": p}
        status, body = serve.plan_request(
            {"assignments": [{"course": "c", "title": "t", "due": "2026-06-08"}], "student": "unit_probe"}
        )
        self.assertEqual(status, 200)
        self.assertEqual(body["plan"], "PLAN")

    def test_ical_body_is_parsed(self) -> None:
        copilot.run = lambda a, t, p="": {"got": a}
        status, body = serve.plan_request(
            {"ical": "BEGIN:VEVENT\nSUMMARY:HW1\nDTSTART:20260608\nCATEGORIES:CS\nEND:VEVENT\n"}
        )
        self.assertEqual(status, 200)
        self.assertEqual(len(body["got"]), 1)
        self.assertEqual(body["got"][0]["course"], "CS")


if __name__ == "__main__":
    unittest.main()
