"""Outcome bridge: Uri Ledger reputation → substrate profiles (self-resonance loop).
Honesty gates: unmapped contributors are reported not guessed; NPS passives carry no
signal; profiles only move when a real outcome was observed."""
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, (Path(__file__).resolve().parents[1] / "scripts").as_posix())

import aios_outcome_bridge as B
import aios_substrate_character as C


def rec(cid="agent:poster-v2", quality=0.95, jobs=3, **kw):
    return {"contributorId": cid, "kind": "agent", "jobs": jobs,
            "totalCredit": 1.5, "paidKrw": 30000, "avgQuality": quality, **kw}


class ClassifyTests(unittest.TestCase):
    def test_nps_standard_cutpoints(self) -> None:
        self.assertTrue(B.classify(0.9))     # promoter (nps 9)
        self.assertFalse(B.classify(0.6))    # detractor (nps 6)
        self.assertIsNone(B.classify(0.75))  # passive (nps 7-8) — no signal
        self.assertIsNone(B.classify(None))  # never observed — no signal


class IngestTests(unittest.TestCase):
    def test_unmapped_contributor_is_reported_never_guessed(self) -> None:
        report = B.ingest([rec()], mapping={}, apply=False)
        self.assertEqual(report["updated"], [])
        self.assertIn("agent:poster-v2", report["unmapped"])

    def test_promoter_outcome_moves_the_profile(self) -> None:
        with tempfile.TemporaryDirectory() as t:
            store = Path(t) / "p.json"
            before = C.load_profiles(store)["local"]["completion"]
            report = B.ingest([rec(quality=0.9)],
                              mapping={"agent:poster-v2": "local"}, apply=True, store=store)
            self.assertEqual(len(report["updated"]), 1)
            self.assertTrue(report["updated"][0]["success"])
            self.assertGreater(C.load_profiles(store)["local"]["completion"], before)

    def test_detractor_outcome_lowers_the_profile(self) -> None:
        with tempfile.TemporaryDirectory() as t:
            store = Path(t) / "p.json"
            before = C.load_profiles(store)["local"]["completion"]
            B.ingest([rec(quality=0.4)], mapping={"agent:poster-v2": "local"},
                     apply=True, store=store)
            self.assertLess(C.load_profiles(store)["local"]["completion"], before)

    def test_passive_and_unobserved_do_not_touch_profiles(self) -> None:
        with tempfile.TemporaryDirectory() as t:
            store = Path(t) / "p.json"
            before = C.load_profiles(store)["local"]["completion"]
            report = B.ingest([rec(quality=0.75), rec(cid="agent:x", quality=None)],
                              mapping={"agent:poster-v2": "local", "agent:x": "local"},
                              apply=True, store=store)
            self.assertEqual(report["updated"], [])
            self.assertEqual(report["passive"], ["agent:poster-v2"])
            self.assertEqual(report["no_outcome"], ["agent:x"])
            self.assertEqual(C.load_profiles(store)["local"]["completion"], before)

    def test_dry_run_reports_but_does_not_apply(self) -> None:
        with tempfile.TemporaryDirectory() as t:
            store = Path(t) / "p.json"
            before = C.load_profiles(store)["local"]["completion"]
            report = B.ingest([rec(quality=0.95)], mapping={"agent:poster-v2": "local"},
                              apply=False, store=store)
            self.assertEqual(len(report["updated"]), 1)
            self.assertFalse(report["updated"][0]["applied"])
            self.assertEqual(C.load_profiles(store)["local"]["completion"], before)

    def test_dimension_override_is_respected(self) -> None:
        report = B.ingest([rec(quality=0.95, dimension="vision")],
                          mapping={"agent:poster-v2": "local"}, apply=False)
        self.assertEqual(report["updated"][0]["dimension"], "vision")


if __name__ == "__main__":
    unittest.main()
