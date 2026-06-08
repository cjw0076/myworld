import json
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, (Path(__file__).resolve().parents[1] / "scripts").as_posix())

import aios_smx_deadline as smd

ASSIGN = [
    {"course": "Database Systems", "due": "2026-06-15"},
    {"course": "Linear Algebra", "due": "2026-06-12"},
]
TODAY = "2026-06-08"

# Canned planner outputs (the DI seam — tests the wiring, not a live model).
# baseline = a valid plan; inversion = schedules work AFTER a deadline (must lose).
GOOD = [{"date": "2026-06-10", "course": "Database Systems", "task": "x"},
        {"date": "2026-06-11", "course": "Linear Algebra", "task": "y"}]
BAD = [{"date": "2026-06-17", "course": "Database Systems", "task": "x"},  # after 06-15 due
       {"date": "2026-06-11", "course": "Linear Algebra", "task": "y"}]


def fake_planner(_assign, _today, framing):
    # the baseline framing returns a valid plan; everything else a deadline-violating one
    return GOOD if framing == smd.FRAMINGS["baseline"] else BAD


class WiringTests(unittest.TestCase):
    def test_real_verifier_scores_universes(self) -> None:
        us = smd.build_universes(ASSIGN, TODAY, planner=fake_planner)
        byid = {u.id: u for u in us}
        self.assertTrue(byid["u-baseline"].verified_ok)        # valid plan verified
        self.assertFalse(byid["u-inversion"].verified_ok)      # deadline-violating caught

    def test_multiverse_picks_the_verified_survivor(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            r = smd.run(ASSIGN, TODAY, planner=fake_planner, cf_dir=Path(tmp))
            self.assertEqual(r["winner"], "u-baseline")        # only verified universe wins
            self.assertGreaterEqual(r["counterfactuals"], 1)   # losers kept
            cf = json.loads(Path(r["counterfactual_ref"]).read_text())
            reasons = {e["id"]: e["why_not_chosen"] for e in cf["episodes"]}
            self.assertIn("failed verification", reasons["u-inversion"])

    def test_planner_failure_does_not_fabricate(self) -> None:
        def boom(_a, _t, _f):
            raise RuntimeError("substrate unreachable")
        us = smd.build_universes(ASSIGN, TODAY, planner=boom)
        self.assertTrue(all(not u.verified_ok and not u.executed for u in us))
        self.assertTrue(all("planner failed" in u.note for u in us))

    def test_empty_schedule_marks_dryrun_not_live(self) -> None:
        # substrate produced nothing (unreachable) → executed must be False (evidence,
        # not the dataclass default) so the run is not falsely reported as live
        us = smd.build_universes(ASSIGN, TODAY, planner=lambda a, t, f: [])
        self.assertTrue(all(not u.executed for u in us))

    def test_all_violating_means_no_winner_applied(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            r = smd.run(ASSIGN, TODAY, planner=lambda a, t, f: BAD, cf_dir=Path(tmp))
            self.assertFalse(r["winner_applied"])              # nothing verified → nothing applied


if __name__ == "__main__":
    unittest.main()
