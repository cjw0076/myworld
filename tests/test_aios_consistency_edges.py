"""Hermetic tests for aios_consistency_edges (NO GPU / NO network).

A tmp AIOS_FS_ROOT + a deterministic MOCK judge stand in for ollama. Covers candidate-pair
selection, idempotent append-only build, the relation->sign mapping, and the degrade contract.
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


def _vec(text: str):
    """Deterministic 2D 'embedding' so candidate_pairs is testable offline."""
    t = text.lower()
    if "clusterx" in t:
        return [1.0, 0.0]
    if "clustery" in t:
        return [0.0, 1.0]
    return [0.5, 0.5]


class CandidatePairsTest(unittest.TestCase):
    def setUp(self):
        import aios_consistency_edges as CE
        self.CE = CE

    def test_only_near_pairs_and_no_embedding_skipped(self):
        nodes = [
            {"id": "x1", "embedding": [1.0, 0.0], "summary": "clusterx one"},
            {"id": "x2", "embedding": [0.9, 0.1], "summary": "clusterx two"},
            {"id": "y1", "embedding": [0.0, 1.0], "summary": "clustery one"},
            {"id": "y2", "embedding": [0.1, 0.9], "summary": "clustery two"},
            {"id": "z1", "embedding": None, "summary": "no embedding"},
        ]
        pairs = self.CE.candidate_pairs(nodes, near_k=1, max_pairs=200)
        # each node's nearest is its own-cluster partner -> only intra-cluster pairs
        self.assertIn(("x1", "x2"), pairs)
        self.assertIn(("y1", "y2"), pairs)
        self.assertNotIn(("x1", "y1"), pairs)  # distant pair excluded
        self.assertNotIn(("x2", "y2"), pairs)
        # node with no embedding never appears
        self.assertFalse(any("z1" in p for p in pairs))

    def test_pairs_unordered_and_deduped(self):
        nodes = [
            {"id": "a", "embedding": [1.0, 0.0], "summary": "a"},
            {"id": "b", "embedding": [0.99, 0.01], "summary": "b"},
        ]
        pairs = self.CE.candidate_pairs(nodes, near_k=1, max_pairs=200)
        self.assertEqual(pairs, [("a", "b")])  # one unordered pair, not (a,b)+(b,a)

    def test_max_pairs_cap_honored(self):
        nodes = [{"id": f"n{i}", "embedding": [1.0, i * 0.001], "summary": f"n{i}"} for i in range(8)]
        pairs = self.CE.candidate_pairs(nodes, near_k=7, max_pairs=3)
        self.assertLessEqual(len(pairs), 3)


def _mock_judge(text_a: str, text_b: str):
    """Sign mapping probe: contains 'CONTRA' -> contradicts, 'SUPP' -> supports, else unrelated."""
    blob = (text_a + " " + text_b).upper()
    if "CONTRA" in blob:
        return {"relation": "contradicts", "confidence": 0.8}
    if "SUPP" in blob:
        return {"relation": "supports", "confidence": 0.7}
    return {"relation": "unrelated", "confidence": 0.6}


class JudgePairTest(unittest.TestCase):
    def setUp(self):
        import aios_consistency_edges as CE
        self.CE = CE

    def test_injected_judge_sign_mapping(self):
        self.assertEqual(self.CE.judge_pair("SUPP", "x", judge=_mock_judge)["sign"], 1)
        self.assertEqual(self.CE.judge_pair("CONTRA", "x", judge=_mock_judge)["sign"], -1)
        self.assertEqual(self.CE.judge_pair("plain", "x", judge=_mock_judge)["sign"], 0)

    def test_raising_judge_returns_none_no_crash(self):
        def boom(a, b):
            raise RuntimeError("judge exploded")
        self.assertIsNone(self.CE.judge_pair("a", "b", judge=boom))

    def test_unknown_relation_returns_none(self):
        self.assertIsNone(self.CE.judge_pair("a", "b", judge=lambda a, b: {"relation": "maybe"}))


class BuildTest(unittest.TestCase):
    def setUp(self):
        import aios_consistency_edges as CE
        import aios_semantic_fs as SF
        self.CE, self.SF = CE, SF
        self.tmp = tempfile.mkdtemp(prefix="aios_ce_test_")
        os.environ["AIOS_FS_ROOT"] = self.tmp
        SF._embed = _vec  # deterministic embeddings so candidate_pairs fires

    def _seed_three(self):
        a = self.SF.put("note A", summary="clusterx SUPP A", tags=["a"])
        b = self.SF.put("note B", summary="clusterx SUPP B", tags=["b"])
        c = self.SF.put("note C", summary="clusterx CONTRA C", tags=["c"])
        return a, b, c

    def test_build_appends_and_maps_signs(self):
        self._seed_three()
        counts = self.CE.build(near_k=2, judge=_mock_judge)
        self.assertGreater(counts["judged"], 0)
        signed = self.CE.load_signed_edges()
        signs = {e["sign"] for e in signed}
        # 'SUPP' pairs -> +1; any pair containing the 'CONTRA' node -> -1
        self.assertIn(1, signs)
        self.assertIn(-1, signs)

    def test_build_idempotent_and_append_only(self):
        self._seed_three()
        path = Path(self.tmp) / "consistency_edges.jsonl"
        first = self.CE.build(near_k=2, judge=_mock_judge)
        lines_after_first = len(path.read_text().splitlines())
        self.assertGreater(lines_after_first, 0)
        second = self.CE.build(near_k=2, judge=_mock_judge)
        lines_after_second = len(path.read_text().splitlines())
        self.assertEqual(second["judged"], 0)                 # nothing re-judged
        self.assertEqual(second["skipped"], first["judged"])  # all prior pairs skipped
        self.assertEqual(lines_after_second, lines_after_first)  # append-only: file unchanged

    def test_load_signed_edges_drops_unrelated(self):
        # only-unrelated mock -> all sign 0 -> signed subgraph empty
        self._seed_three()
        self.CE.build(near_k=2, judge=lambda a, b: {"relation": "unrelated", "confidence": 0.5})
        self.assertEqual(self.CE.load_signed_edges(), [])

    def test_build_degrades_when_judge_returns_none(self):
        self._seed_three()
        counts = self.CE.build(near_k=2, judge=lambda a, b: None)  # judge always fails
        self.assertEqual(counts["judged"], 0)                      # no crash, nothing recorded
        self.assertEqual(self.CE.load_signed_edges(), [])


if __name__ == "__main__":
    unittest.main()
