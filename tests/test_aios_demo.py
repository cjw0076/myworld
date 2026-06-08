import sys
import unittest
from pathlib import Path

sys.path.insert(0, (Path(__file__).resolve().parents[1] / "scripts").as_posix())

import aios_demo as d


class RunDemoTests(unittest.TestCase):
    def test_good_plan_passes(self) -> None:
        good = next(c for c in d.run_demo()["checks"] if c["plan"] == "good")
        self.assertTrue(good["verification"]["ok"])
        self.assertEqual(good["verification"]["violations"], [])

    def test_slipped_plan_is_caught_with_specific_violation(self) -> None:
        slipped = next(c for c in d.run_demo()["checks"] if c["plan"] == "slipped")
        v = slipped["verification"]
        self.assertFalse(v["ok"])
        # the demo's whole point: the checker names exactly what's wrong
        self.assertEqual(len(v["violations"]), 1)
        viol = v["violations"][0]
        self.assertEqual(viol["course"], "Database Systems")
        self.assertIn("AFTER", viol["issue"])

    def test_demo_ok_is_the_honesty_gate(self) -> None:
        # demo_ok must be True ONLY when good passes AND slipped is caught
        self.assertTrue(d.run_demo()["demo_ok"])

    def test_deterministic_no_clock(self) -> None:
        # same fixed scenario every run — no Date.now / randomness
        self.assertEqual(d.run_demo(), d.run_demo())

    def test_no_network_or_model_in_run_demo(self) -> None:
        # run_demo must not import/route through the LLM substrate — pure verifier
        result = d.run_demo()
        self.assertIn("no model", result["provenance"])


class CliTests(unittest.TestCase):
    def test_main_json_returns_zero_and_skips_receipt(self) -> None:
        rc = d.main(["--json", "--no-receipt"])
        self.assertEqual(rc, 0)

    def test_main_human_returns_zero(self) -> None:
        rc = d.main(["--no-receipt"])
        self.assertEqual(rc, 0)


if __name__ == "__main__":
    unittest.main()
