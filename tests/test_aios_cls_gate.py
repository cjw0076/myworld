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

    def test_aggregate_imports_excluded_by_default(self):
        agg = {"id": "ds1", "dataset": "agentbank", "tool_freq": {"Bash": 999, "Edit": 50}}
        sess = _mem("s1", "react_code", {"Edit": 6, "Bash": 6})
        elig, man = self.m.select_corpus([agg, sess])
        self.assertEqual(man["selected"], 1)                 # only the session-derived run
        self.assertEqual(elig[0]["ref"], "s1")
        q = man["corpus_quality"]
        self.assertEqual(q["aggregate_import"], 1)
        self.assertEqual(q["session_derived"], 1)
        # opt-in to include aggregates
        elig2, _ = self.m.select_corpus([agg, sess], include_aggregates=True)
        self.assertEqual(len(elig2), 2)

    def test_infers_loop_type_for_stale_records(self):
        # session-derived record with NO loop_type (predates the field) gets labeled
        stale = {"id": "old1", "tool_freq": {"Edit": 5, "Bash": 4, "Read": 2}}  # react_code shape
        elig, man = self.m.select_corpus([stale])
        self.assertEqual(elig[0]["loop_type"], "react_code")     # inferred, not 'unknown'
        self.assertEqual(man["corpus_quality"]["labeled_loop_type"], 1)
        self.assertTrue(man["training_ready"])

    def test_infer_loop_type_shapes(self):
        self.assertEqual(self.m._infer_loop_type({"Read": 1, "Bash": 1}), "quick")  # <5
        self.assertEqual(self.m._infer_loop_type({"Edit": 5, "Bash": 4, "Read": 2}), "react_code")
        # exploration needs read>0.30 AND unique_ratio>0.5
        self.assertEqual(self.m._infer_loop_type({"Read": 3, "Grep": 2, "Glob": 1, "WebFetch": 1}), "exploration")

    def test_training_ready_flag_is_honest(self):
        # empty / no-eligible corpus → not training-ready
        _, man0 = self.m.select_corpus([])
        self.assertFalse(man0["training_ready"])
        # eligible session corpus (label inferred) → training-ready
        labeled = _mem("l1", "react_code", {"Edit": 6, "Bash": 6})
        _, man2 = self.m.select_corpus([labeled])
        self.assertTrue(man2["training_ready"])
        # unknown-bucket aggregates (opted in) are not enough on their own
        agg = {"id": "a1", "dataset": "x", "loop_type": "unknown", "tool_freq": {"Bash": 9}}
        _, man3 = self.m.select_corpus([agg], include_aggregates=True)
        self.assertFalse(man3["training_ready"])             # all 'unknown'

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


class ReplayPolicyTest(unittest.TestCase):
    def setUp(self):
        self.m = _load()

    def _c(self, ref, loop_type, freq, weight=1.0):
        return {"ref": ref, "loop_type": loop_type, "tool_freq": freq, "weight": weight}

    def test_rare_mode_replayed_more_than_dominant(self):
        # 3 react_code runs (same dominant tool Edit) + 1 rare exploration run
        corpus = [self._c(f"r{i}", "react_code", {"Edit": 6}) for i in range(3)]
        corpus.append(self._c("x", "exploration", {"Read": 6}))
        sched, summary = self.m.replay_schedule(corpus)
        top = sched[0]
        self.assertEqual(top["ref"], "x")                 # rarest mode replayed most
        self.assertEqual(summary["items"], 4)

    def test_intervention_weight_carries_into_replay(self):
        corpus = [self._c("plain", "react_code", {"Edit": 6}, weight=1.0),
                  self._c("steered", "react_code", {"Edit": 6}, weight=3.0)]
        sched, _ = self.m.replay_schedule(corpus)
        self.assertEqual(sched[0]["ref"], "steered")      # supervision → replayed more

    def test_epoch_counts_emitted(self):
        corpus = [self._c("a", "react_code", {"Edit": 6}),
                  self._c("b", "exploration", {"Read": 6})]
        sched, summary = self.m.replay_schedule(corpus, epoch_size=10)
        self.assertEqual(summary["epoch_size"], 10)
        self.assertTrue(all("replay_count" in s and s["replay_count"] >= 1 for s in sched))

    def test_empty_corpus_is_safe(self):
        sched, summary = self.m.replay_schedule([])
        self.assertEqual(sched, [])
        self.assertEqual(summary["items"], 0)


class CycleTest(unittest.TestCase):
    def setUp(self):
        self.m = _load()

    def test_cycle_closes_loop_and_awaits_training(self):
        mems = [_mem(f"r{i}", "react_code", {"Edit": 6, "Bash": 4, "Read": 2}) for i in range(6)]
        mems += [_mem(f"e{i}", "exploration", {"Read": 6, "Grep": 3, "Glob": 2, "WebFetch": 1}) for i in range(4)]
        rep = self.m.run_cycle(mems, at="2026-06-24T00:00:00+00:00")
        self.assertEqual(rep["schema"], "aios.cls_cycle.v1")
        self.assertTrue(rep["corpus"]["training_ready"])
        self.assertTrue(rep["loop_closed"])
        self.assertFalse(rep["gate"]["promote"])             # no trained adapter yet
        self.assertIn("awaiting_training", rep["gate"]["status"])
        self.assertIn("QLoRA", rep["open_step"])

    def test_cycle_with_candidate_makes_real_decision(self):
        # supplying a trained-adapter score moves the gate OUT of 'awaiting' into a
        # real promote/stays-draft decision (the value depends on the held-out baseline).
        mems = [_mem(f"r{i}", "react_code", {"Edit": 6, "Bash": 4}) for i in range(6)]
        rep = self.m.run_cycle(mems, candidate_acc=0.9)
        self.assertEqual(rep["gate"]["candidate"], 0.9)
        self.assertNotIn("awaiting_training", rep["gate"]["status"])
        self.assertIn(rep["gate"]["status"], ("promote", "stays_draft (eval not beaten)"))
        # gate decision is consistent with the margin rule
        g = rep["gate"]
        self.assertEqual(g["promote"], g["candidate"] >= g["base"] + g["margin"])

    def test_cycle_empty_corpus_not_closed(self):
        rep = self.m.run_cycle([])
        self.assertFalse(rep["loop_closed"])


if __name__ == "__main__":
    unittest.main()
