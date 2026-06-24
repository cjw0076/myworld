from __future__ import annotations

import importlib.util
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SCRIPTS = ROOT / "scripts"


def _load():
    spec = importlib.util.spec_from_file_location("aios_cls_gate_uut", SCRIPTS / "aios_cls_gate.py")
    m = importlib.util.module_from_spec(spec)
    sys.modules["aios_cls_gate_uut"] = m
    if str(SCRIPTS) not in sys.path:
        sys.path.insert(0, str(SCRIPTS))
    spec.loader.exec_module(m)
    return m


def _mem(rid, loop_type, freq, ir=0.0):
    return {"id": rid, "domain": "agent_behavior", "loop_type": loop_type,
            "tool_freq": freq, "intervention_rate": ir, "category": "code"}


class CorpusGateTest(unittest.TestCase):
    def setUp(self):
        self.m = _load()

    def test_excludes_doom_loop_and_thin_runs(self):
        mems = [
            _mem("a", "react_code", {"Edit": 4, "Bash": 4}),       # ok, 8 tools
            _mem("b", "doom_loop", {"Bash": 9}),                    # excluded: doom
            _mem("c", "quick", {"Read": 2}),                        # excluded: <5 signal
        ]
        elig, man = self.m.select_corpus(mems)
        self.assertEqual(man["selected"], 1)
        self.assertEqual(elig[0]["ref"], "a")
        self.assertEqual(man["from"], 3)

    def test_intervention_runs_weighted_up(self):
        plain = self.m.select_corpus([_mem("p", "react_code", {"Edit": 6}, ir=0.0)])[0][0]
        steered = self.m.select_corpus([_mem("s", "react_code", {"Edit": 6}, ir=0.5)])[0][0]
        self.assertEqual(plain["weight"], 1.0)
        self.assertGreater(steered["weight"], plain["weight"])   # human supervision worth more

    def test_diversity_cap_per_bucket(self):
        mems = [_mem(f"r{i}", "react_code", {"Edit": 6}) for i in range(5)]
        elig, man = self.m.select_corpus(mems, max_per_bucket=2)
        self.assertEqual(man["selected"], 2)                     # capped

    def test_provenance_hash_is_stable_and_order_independent(self):
        a = self.m.select_corpus([_mem("x", "react_code", {"Edit": 6}),
                                  _mem("y", "exploration", {"Read": 6})])[1]["provenance"]
        b = self.m.select_corpus([_mem("y", "exploration", {"Read": 6}),
                                  _mem("x", "react_code", {"Edit": 6})])[1]["provenance"]
        self.assertEqual(a, b)


class EvalGateTest(unittest.TestCase):
    def setUp(self):
        self.m = _load()

    def test_split_is_deterministic(self):
        corpus = [{"ref": str(i), "tool_freq": {"Edit": 6}, "weight": 1.0} for i in range(10)]
        t1, h1 = self.m.split_holdout(corpus, frac=0.2)
        t2, h2 = self.m.split_holdout(corpus, frac=0.2)
        self.assertEqual([c["ref"] for c in h1], [c["ref"] for c in h2])
        self.assertEqual(len(h1), 2)

    def test_eval_returns_accuracy(self):
        train = [{"ref": "t", "tool_freq": {"Edit": 10}, "weight": 1.0}]
        holdout = [{"ref": "h1", "tool_freq": {"Edit": 5}}, {"ref": "h2", "tool_freq": {"Bash": 5}}]
        r = self.m.eval_behavior(train, holdout)
        self.assertEqual(r["n"], 2)
        self.assertEqual(r["predicts"], "Edit")
        self.assertEqual(r["acc"], 0.5)              # Edit hit, Bash miss

    def test_promotion_is_draft_first(self):
        # no trained adapter yet → not promotable, awaiting founder GO
        none = self.m.gate_promote(0.5, None)
        self.assertFalse(none["promote"])
        self.assertIn("awaiting_training", none["status"])
        # candidate must beat baseline by margin
        self.assertFalse(self.m.gate_promote(0.5, 0.51, margin=0.02)["promote"])
        self.assertTrue(self.m.gate_promote(0.5, 0.55, margin=0.02)["promote"])


if __name__ == "__main__":
    unittest.main()
