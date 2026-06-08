import sys
import unittest
from pathlib import Path

sys.path.insert(0, (Path(__file__).resolve().parents[1] / "scripts").as_posix())

import aios_smx_learn as L

ASSIGN = [
    {"course": "Database Systems", "due": "2026-06-15"},
    {"course": "Linear Algebra", "due": "2026-06-12"},
    {"course": "Operating Systems", "due": "2026-06-20"},
]
TODAY = "2026-06-08"


class LogRegTests(unittest.TestCase):
    def test_fits_a_separable_problem(self) -> None:
        # y=1 iff x1>0 — a trivially separable set; the fitter must recover it
        rows = [([1.0, 1.0], 1), ([1.0, 2.0], 1), ([1.0, 3.0], 1),
                ([1.0, -1.0], 0), ([1.0, -2.0], 0), ([1.0, -3.0], 0)]
        w = L.fit_logreg(rows, epochs=500)
        self.assertEqual(L.accuracy(w, rows), 1.0)
        self.assertGreater(w[1], 0)  # positive weight on the discriminating feature

    def test_sigmoid_bounds(self) -> None:
        self.assertAlmostEqual(L._sigmoid(0), 0.5)
        self.assertLess(L._sigmoid(-100), 1e-6)
        self.assertGreater(L._sigmoid(100), 1 - 1e-6)


class ExperimentTests(unittest.TestCase):
    def test_deterministic_per_seed(self) -> None:
        a = L.run_experiment(ASSIGN, TODAY, n=200, seed=7)
        b = L.run_experiment(ASSIGN, TODAY, n=200, seed=7)
        self.assertEqual(a["induced_weights"], b["induced_weights"])

    def test_balanced_population_has_signal(self) -> None:
        r = L.run_experiment(ASSIGN, TODAY, n=400, seed=7)
        # the population must be reasonably balanced (the fix the first run forced)
        self.assertGreater(r["label_balance"], 0.3)
        self.assertLess(r["label_balance"], 0.7)
        # and the induced model must beat the majority-class baseline
        self.assertTrue(r["beats_baseline"])
        self.assertGreater(r["test_accuracy"], r["majority_baseline"])

    def test_lateness_is_the_dominant_learned_predictor(self) -> None:
        # the experiment should INDUCE that scheduling work far out predicts failure
        # (the deadline-violation rule), not because we coded it — because the data shows it
        r = L.run_experiment(ASSIGN, TODAY, n=400, seed=7)
        w = r["induced_weights"]
        self.assertLess(w["max_out"], 0)  # later reach → less likely to pass
        # max_out should be among the strongest-magnitude non-bias signals
        non_bias = {k: abs(v) for k, v in w.items() if k != "bias"}
        self.assertEqual(max(non_bias, key=non_bias.get), "max_out")


if __name__ == "__main__":
    unittest.main()
