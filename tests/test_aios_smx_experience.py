import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, (Path(__file__).resolve().parents[1] / "scripts").as_posix())

import aios_smx as smx
import aios_smx_experience as exp


def U(id, **kw):
    return smx.Universe(id, kw.pop("branch_type", "synthetic"), **kw)


class FeatureLabelTests(unittest.TestCase):
    def test_features_shape_and_bias(self) -> None:
        x = exp.universe_features(U("a", verified_ok=True, files_touched=["f"], reverts=1))
        self.assertEqual(len(x), len(exp.FEATURE_NAMES))
        self.assertEqual(x[0], 1.0)            # bias
        self.assertEqual(x[1], 1.0)            # verified

    def test_label_positive_only_when_verified_executed_unreverted(self) -> None:
        self.assertEqual(exp.universe_label(U("a", verified_ok=True, executed=True)), 1)
        self.assertEqual(exp.universe_label(U("a", verified_ok=True, executed=True), reverted=True), 0)
        self.assertEqual(exp.universe_label(U("a", verified_ok=False, executed=True)), 0)
        self.assertEqual(exp.universe_label(U("a", verified_ok=True, executed=False)), 0)


class StoreTests(unittest.TestCase):
    def test_log_then_load_roundtrip(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            store = Path(tmp) / "exp.jsonl"
            us = [U("a", verified_ok=True), U("b", verified_ok=False)]
            exp.log_experience(us, us[0], store=store)
            rows = exp.load_experience(store)
            self.assertEqual(len(rows), 2)
            self.assertEqual([y for _x, y in rows], [1, 0])


class ScorerSelectionTests(unittest.TestCase):
    def test_cold_start_falls_back_to_prior(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            store = Path(tmp) / "exp.jsonl"
            # one-class data only → must not learn
            exp.log_experience([U("a", verified_ok=True), U("b", verified_ok=True)],
                               None, store=store)
            s = exp.make_scorer(store)
            self.assertTrue(s.scorer_name.startswith("prior"))

    def test_learns_when_enough_two_class_data(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            store = Path(tmp) / "exp.jsonl"
            for _ in range(20):
                exp.log_experience([U("g", verified_ok=True, executed=True),
                                    U("b", verified_ok=False, executed=True)], None, store=store)
            s = exp.make_scorer(store, min_rows=10)
            self.assertTrue(s.scorer_name.startswith("learned"))
            # learned scorer ranks a verified universe above an unverified one
            self.assertGreater(s(U("x", verified_ok=True, executed=True)),
                               s(U("y", verified_ok=False, executed=True)))


class ExperimentTests(unittest.TestCase):
    def test_learned_adapts_better_than_prior(self) -> None:
        r = exp.run_experiment(seed=5)
        self.assertTrue(r["learned_adapts_better"])
        self.assertGreaterEqual(r["learned_top1_accuracy"], r["prior_top1_accuracy"])
        # the world heavily penalizes blast → the learned scorer must too
        self.assertLess(r["learned_weights"]["blast"], 0)

    def test_deterministic(self) -> None:
        self.assertEqual(exp.run_experiment(seed=5), exp.run_experiment(seed=5))


class LoopIntegrationTests(unittest.TestCase):
    def test_run_multiverse_logs_experience_and_uses_scorer(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            store = Path(tmp) / "exp.jsonl"
            us = [U("win", verified_ok=True, files_touched=["a"]),
                  U("lose", verified_ok=False)]
            r = smx.run_multiverse(
                us, cf_dir=Path(tmp),
                experience_sink=lambda uu, w: exp.log_experience(uu, w, store=store))
            self.assertEqual(r["winner"], "win")
            self.assertEqual(len(exp.load_experience(store)), 2)  # both universes logged


if __name__ == "__main__":
    unittest.main()
