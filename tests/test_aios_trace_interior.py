"""Tests for GenesisOS's reframed job: infer the grounded interior behind data traces.

The load-bearing test is anti-fabrication: an imagined inference that cites no real
trace evidence MUST be quarantined as speculative, never asserted as interior.
"""
import sys
import unittest
from pathlib import Path

sys.path.insert(0, (Path(__file__).resolve().parents[1] / "scripts").as_posix())

import aios_trace_interior as ti


def traces(seq):
    return [{"t": i, "kind": k, "detail": f"{k}-{i}", "status": s}
            for i, (k, s) in enumerate(seq)]


class SignalTests(unittest.TestCase):
    def test_grind_detected(self) -> None:
        ts = traces([("a", "ok")] * 4 + [("b", "ok")])
        names = {s.name for s in ti.extract_signals(ts)}
        self.assertIn("grind", names)

    def test_distress_detected_with_evidence(self) -> None:
        ts = traces([("a", "ok"), ("b", "flagged"), ("c", "failed")])
        sig = [s for s in ti.extract_signals(ts) if s.name == "distress"]
        self.assertTrue(sig)
        self.assertTrue(sig[0].evidence)              # carries the offending traces

    def test_absence_detected(self) -> None:
        ts = traces([("x", "ok"), ("x", "ok"), ("x", "ok"), ("y", "ok"), ("y", "ok"), ("y", "ok")])
        names = {s.name for s in ti.extract_signals(ts)}
        self.assertIn("absence", names)

    def test_empty_traces_no_signals(self) -> None:
        self.assertEqual(ti.extract_signals([]), [])


class GroundingTests(unittest.TestCase):
    def test_deterministic_inferences_are_all_grounded(self) -> None:
        r = ti.report(traces([("a", "ok")] * 5 + [("b", "ok")]))
        for dim in ("need", "discomfort", "want"):
            for h in r["interior"][dim]:
                self.assertTrue(h["grounded_in"])     # every asserted inference cites evidence

    def test_ungrounded_imagination_is_quarantined_not_asserted(self) -> None:
        # an LLM that invents an inference citing NO real signal must be quarantined
        def hallucinating_llm(signals):
            return [{"dimension": "want", "text": "secretly wants to move to Paris",
                     "grounded_in": ["a feeling I had"]}]   # not in any signal's evidence
        sigs = ti.extract_signals(traces([("a", "ok")] * 4))
        r = ti.infer_interior(sigs, generate_fn=hallucinating_llm)
        # it must NOT appear in interior; it must be flagged speculative
        asserted = [h["text"] for dim in r["interior"].values() for h in dim]
        self.assertNotIn("secretly wants to move to Paris", asserted)
        self.assertEqual(len(r["speculative"]), 1)
        self.assertIn("ungrounded", r["speculative"][0]["flag"])

    def test_the_itch_is_the_most_grounded_inference(self) -> None:
        r = ti.report(traces([("grindy", "ok")] * 8 + [("x", "ok"), ("y", "ok")]))
        self.assertIsNotNone(r["the_itch"])
        # the itch should be grounded in more evidence than a minimal inference
        self.assertGreaterEqual(len(r["the_itch"]["grounded_in"]), 3)

    def test_thin_data_yields_no_false_itch(self) -> None:
        r = ti.report(traces([("a", "ok")]))   # one event → nothing to infer
        self.assertIsNone(r["the_itch"])


class DivergentReadingTests(unittest.TestCase):
    def test_same_evidence_opposite_interiors(self) -> None:
        sig = [s for s in ti.extract_signals(traces([("a", "ok")] * 5)) if s.name == "grind"][0]
        dr = ti.divergent_readings(sig)
        self.assertTrue(dr["ambiguous"])
        kinds = {r["kind"] for r in dr["readings"]}
        self.assertEqual(kinds, {"obvious", "inverted"})
        # the two readings sit on opposite interior dimensions, same evidence
        dims = {r["dimension"] for r in dr["readings"]}
        self.assertNotEqual(len(dims), 1)
        for r in dr["readings"]:
            self.assertEqual(r["grounded_in"], sig.evidence)

    def test_report_surfaces_ambiguities(self) -> None:
        r = ti.report(traces([("a", "ok")] * 5))
        self.assertTrue(r["divergent_readings"])
        self.assertTrue(r["ambiguities"])           # held, not collapsed

    def test_unknown_signal_has_no_reading(self) -> None:
        self.assertEqual(ti.divergent_readings(ti.Signal("mystery", "x"))["readings"], [])


if __name__ == "__main__":
    unittest.main()
