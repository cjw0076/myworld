"""Hermetic instrument-validity tests for aios_h1_agent_edges (NO GPU / NO network).

The two KEY tests are the gate:
  (a) a KNOWN frustrated triangle is DETECTED as NON_TRIVIAL_H1 (no false negative),
  (b) a fully CONSISTENT graph is reported TRIVIAL_H1 (no false positive).
Both go end-to-end through aios_consistency_edges.build with a deterministic MOCK judge.
"""
from __future__ import annotations

import os
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SCRIPTS = ROOT / "scripts"
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))


def _near_vec(text: str):
    """All three seeds mutually near so every pair becomes a candidate."""
    return [1.0, 0.01, 0.0]


class FrustrationUnitTest(unittest.TestCase):
    def setUp(self):
        import aios_h1_agent_edges as HA
        self.HA = HA

    def test_empty_graph_is_trivial(self):
        r = self.HA.frustration_h1([])
        self.assertEqual(r["verdict"], "TRIVIAL_H1")
        self.assertEqual(r["frustrated_cycle_count"], 0)
        self.assertEqual(r["n_independent_cycles"], 0)

    def test_direct_frustrated_triangle(self):
        edges = [
            {"src": "A", "dst": "B", "sign": 1},
            {"src": "B", "dst": "C", "sign": 1},
            {"src": "A", "dst": "C", "sign": -1},  # product = +1*+1*-1 = -1 -> frustrated
        ]
        r = self.HA.frustration_h1(edges)
        self.assertEqual(r["verdict"], "NON_TRIVIAL_H1")
        self.assertGreaterEqual(r["frustrated_cycle_count"], 1)
        self.assertEqual(r["n_independent_cycles"], 1)
        self.assertIn(["A", "B", "C"], r["frustrated_triangles"])

    def test_direct_balanced_triangle(self):
        # +1,-1,-1 -> product = +1 -> balanced, no frustration (no false positive)
        edges = [
            {"src": "A", "dst": "B", "sign": 1},
            {"src": "B", "dst": "C", "sign": -1},
            {"src": "A", "dst": "C", "sign": -1},
        ]
        r = self.HA.frustration_h1(edges)
        self.assertEqual(r["verdict"], "TRIVIAL_H1")
        self.assertEqual(r["frustrated_cycle_count"], 0)
        self.assertEqual(r["frustrated_triangles"], [])

    def test_sign_zero_edges_ignored(self):
        edges = [
            {"src": "A", "dst": "B", "sign": 1},
            {"src": "B", "dst": "C", "sign": 0},   # unrelated -> not in signed subgraph
            {"src": "A", "dst": "C", "sign": -1},
        ]
        r = self.HA.frustration_h1(edges)
        self.assertEqual(r["n_signed_edges"], 2)       # the sign-0 edge is dropped
        self.assertEqual(r["n_independent_cycles"], 0)  # path, no cycle
        self.assertEqual(r["verdict"], "TRIVIAL_H1")


class EndToEndGateTest(unittest.TestCase):
    """The instrument-validity gate: build edges via mock judge, then run frustration_h1."""

    def setUp(self):
        import aios_consistency_edges as CE
        import aios_h1_agent_edges as HA
        import aios_semantic_fs as SF
        self.CE, self.HA, self.SF = CE, HA, SF
        self.tmp = tempfile.mkdtemp(prefix="aios_h1a_test_")
        os.environ["AIOS_FS_ROOT"] = self.tmp
        SF._embed = _near_vec

    def _seed(self, sa: str, sb: str, sc: str):
        a = self.SF.put("node a", summary=sa, tags=["a"])
        b = self.SF.put("node b", summary=sb, tags=["b"])
        c = self.SF.put("node c", summary=sc, tags=["c"])
        return a["id"], b["id"], c["id"]

    def test_a_frustrated_triangle_detected(self):
        """A supports B (+1), B supports C (+1), A contradicts C (-1) -> NON_TRIVIAL_H1."""
        ida, idb, idc = self._seed("alpha", "beta", "gamma")

        def judge(ta, tb):
            pair = frozenset((ta, tb))
            if pair == frozenset(("alpha", "beta")):
                return {"relation": "supports", "confidence": 0.9}
            if pair == frozenset(("beta", "gamma")):
                return {"relation": "supports", "confidence": 0.9}
            if pair == frozenset(("alpha", "gamma")):
                return {"relation": "contradicts", "confidence": 0.9}
            return {"relation": "unrelated", "confidence": 0.5}

        self.CE.build(near_k=2, judge=judge)
        r = self.HA.frustration_h1(self.CE.load_signed_edges())
        self.assertEqual(r["verdict"], "NON_TRIVIAL_H1")
        self.assertGreaterEqual(r["frustrated_cycle_count"], 1)
        self.assertIn(tuple(sorted((ida, idb, idc))),
                      {tuple(t) for t in r["frustrated_triangles"]})

    def test_b_consistent_graph_no_false_positive(self):
        """All-supports (+1,+1,+1) -> balanced -> TRIVIAL_H1, zero frustration."""
        self._seed("alpha", "beta", "gamma")
        r = self.HA.frustration_h1(
            self._built_all_supports())
        self.assertEqual(r["verdict"], "TRIVIAL_H1")
        self.assertEqual(r["frustrated_cycle_count"], 0)
        self.assertEqual(r["frustrated_triangles"], [])

    def _built_all_supports(self):
        self.CE.build(near_k=2, judge=lambda ta, tb: {"relation": "supports", "confidence": 0.9})
        return self.CE.load_signed_edges()


if __name__ == "__main__":
    unittest.main()
