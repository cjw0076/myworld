import sys
import unittest
from pathlib import Path

sys.path.insert(0, (Path(__file__).resolve().parents[1] / "scripts").as_posix())

import aios_copilot_serve as serve
import aios_deadline_copilot as copilot


class PlanRequestTests(unittest.TestCase):
    def setUp(self) -> None:
        self._run = copilot.run

    def tearDown(self) -> None:
        copilot.run = self._run

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
