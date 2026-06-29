"""Hermetic tests for aios_memory_hygiene (NO GPU / NO network).

A tmp AIOS_FS_ROOT + deterministic topic-vector embeddings (monkeypatched SF._embed, like
test_aios_semantic_fs) stand in for ollama. Signed edges are planted by appending directly
to the consistency-edges path. Covers dedup clustering + canonical choice + threshold,
supersession (contradicts+newer and correction-text), contradiction flags, the empty/
no-embedding degrade contract, and the DRAFT-FIRST read-only invariant over memory.
"""
from __future__ import annotations

import json
import os
import sys
import tempfile
import time
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SCRIPTS = ROOT / "scripts"
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))


# deterministic topic embeddings (no GPU/ollama). "alpha"/"beta" orthogonal; "gamma"
# sits at cosine 0.8 with alpha so a lower threshold merges it while a high one does not.
def _fake_embed(text: str):
    t = text.lower()
    if "gamma" in t:
        return [0.8, 0.6]
    if "alpha" in t:
        return [1.0, 0.0]
    if "beta" in t:
        return [0.0, 1.0]
    return [0.3, 0.3]


def _plant_signed_edge(CE, src, dst, sign, confidence=0.8):
    SF_root_edges = CE._edges_path()
    rec = {"src": src, "dst": dst,
           "relation": "contradicts" if sign == -1 else "supports",
           "sign": sign, "confidence": confidence, "ts": int(time.time())}
    # reuse the module's own append-only writer
    import aios_semantic_fs as SF
    SF._append(SF_root_edges, rec)


class MemoryHygieneTest(unittest.TestCase):
    def setUp(self):
        import aios_memory_hygiene as MH
        import aios_consistency_edges as CE
        import aios_semantic_fs as SF
        self.MH, self.CE, self.SF = MH, CE, SF
        self.tmp = tempfile.mkdtemp(prefix="aios_hygiene_test_")
        os.environ["AIOS_FS_ROOT"] = self.tmp
        SF._embed = _fake_embed  # deterministic vectors so dedup is testable offline

    # ── dedup ────────────────────────────────────────────────────────────────
    def test_dedup_clusters_groups_near_identical_with_canonical(self):
        # 3 near-identical "alpha" nodes (cosine 1.0) + 1 distinct "beta" node
        a1 = self.SF.put("alpha short", summary="alpha short", tags=["a"])
        a2 = self.SF.put("alpha medium length note", summary="alpha medium length note", tags=["a"])
        a3 = self.SF.put("alpha the longest summary of the cluster by far indeed",
                         summary="alpha the longest summary of the cluster by far indeed", tags=["a"])
        beta = self.SF.put("beta distinct", summary="beta distinct", tags=["b"])

        clusters = self.MH.dedup_clusters(threshold=0.92)
        self.assertEqual(len(clusters), 1)
        c = clusters[0]
        self.assertEqual(set(c["cluster"]), {a1["id"], a2["id"], a3["id"]})
        self.assertEqual(c["canonical"], a3["id"])              # longest summary is canonical
        self.assertEqual(set(c["duplicates"]), {a1["id"], a2["id"]})
        self.assertNotIn(beta["id"], c["cluster"])              # distinct node not clustered
        self.assertAlmostEqual(c["max_cosine"], 1.0, places=3)

    def test_dedup_threshold_respected_lower_merges_more(self):
        # alpha [1,0] and gamma [0.8,0.6] -> cosine 0.8
        self.SF.put("alpha note", summary="alpha note", tags=["a"])
        self.SF.put("gamma note", summary="gamma note", tags=["g"])
        self.assertEqual(self.MH.dedup_clusters(threshold=0.92), [])   # 0.8 < 0.92 -> no cluster
        merged = self.MH.dedup_clusters(threshold=0.7)                 # 0.8 >= 0.7 -> merged
        self.assertEqual(len(merged), 1)
        self.assertEqual(len(merged[0]["cluster"]), 2)

    # ── supersession ───────────────────────────────────────────────────────────
    def test_supersession_contradicts_plus_newer(self):
        older = self.SF.put("alpha older claim", summary="alpha older claim", tags=["o"])
        newer = self.SF.put("alpha newer claim", summary="alpha newer claim", tags=["n"])
        # force a clearly-newer ts on `newer`
        rec = self.SF._live_nodes()[newer["id"]]
        self.SF._append(self.SF._paths()[2],
                        {**rec, "ts": rec["ts"] + 1000})
        _plant_signed_edge(self.CE, older["id"], newer["id"], sign=-1, confidence=0.85)

        sug = self.MH.supersession_suggestions()
        hit = [s for s in sug if s["reason"] == "contradicts+newer"]
        self.assertEqual(len(hit), 1)
        self.assertEqual(hit[0]["supersedes"], newer["id"])
        self.assertEqual(hit[0]["superseded"], older["id"])
        self.assertAlmostEqual(hit[0]["confidence"], 0.85, places=3)

    def test_supersession_correction_text_pattern(self):
        node = self.SF.put("CORRECTION to earlier alpha estimate: value is 42",
                           summary="CORRECTION to earlier alpha estimate: value is 42", tags=["c"])
        sug = self.MH.supersession_suggestions()
        hit = [s for s in sug if s["reason"] == "correction-text"]
        self.assertEqual(len(hit), 1)
        self.assertEqual(hit[0]["supersedes"], node["id"])     # the correcting note

    # ── contradiction flags ──────────────────────────────────────────────────
    def test_contradiction_flags_returns_only_minus_one_edges(self):
        a = self.SF.put("alpha one", summary="alpha one", tags=["a"])
        b = self.SF.put("alpha two", summary="alpha two", tags=["a"])
        c = self.SF.put("beta one", summary="beta one", tags=["b"])
        _plant_signed_edge(self.CE, a["id"], b["id"], sign=-1, confidence=0.7)
        _plant_signed_edge(self.CE, a["id"], c["id"], sign=1, confidence=0.6)  # support, excluded

        flags = self.MH.contradiction_flags()
        self.assertEqual(len(flags), 1)
        self.assertEqual({flags[0]["a"], flags[0]["b"]}, {a["id"], b["id"]})
        self.assertAlmostEqual(flags[0]["confidence"], 0.7, places=3)

    # ── draft-first invariant (read-only over memory) ─────────────────────────
    def test_draft_first_invariant_memory_unchanged(self):
        a = self.SF.put("alpha one", summary="alpha one", tags=["a"])
        self.SF.put("alpha two", summary="alpha two", tags=["a"])
        b = self.SF.put("beta one", summary="beta one", tags=["b"])
        _plant_signed_edge(self.CE, a["id"], b["id"], sign=-1, confidence=0.7)

        index = Path(self.tmp) / "index.jsonl"
        lines_before = len(index.read_text().splitlines())
        live_before = {n["id"] for n in self.SF.ls()}

        # exercise every function + the CLI report
        self.MH.dedup_clusters()
        self.MH.supersession_suggestions()
        self.MH.contradiction_flags()
        self.MH.hygiene_report()
        self.MH.main(["report"])

        lines_after = len(index.read_text().splitlines())
        live_after = {n["id"] for n in self.SF.ls()}
        self.assertEqual(lines_after, lines_before)             # index untouched (read-only)
        self.assertEqual(live_after, live_before)               # nothing deleted/tombstoned

    def test_report_shape_and_draft_note(self):
        self.SF.put("alpha one", summary="alpha one", tags=["a"])
        rep = self.MH.hygiene_report()
        for key in ("fs_root", "n_nodes", "dedup_clusters",
                    "supersession_suggestions", "contradiction_flags", "summary", "note"):
            self.assertIn(key, rep)
        self.assertIn("DRAFT", rep["note"].upper())
        self.assertEqual(rep["fs_root"], self.SF._root().as_posix())

    # ── degrade contracts ──────────────────────────────────────────────────────
    def test_empty_fs_degrades_cleanly(self):
        self.assertEqual(self.MH.dedup_clusters(), [])
        self.assertEqual(self.MH.supersession_suggestions(), [])
        self.assertEqual(self.MH.contradiction_flags(), [])
        rep = self.MH.hygiene_report()
        self.assertEqual(rep["n_nodes"], 0)
        self.assertEqual(rep["summary"]["dedup_clusters"], 0)

    def test_no_embedding_degrades_to_empty_dedup(self):
        self.SF._embed = lambda t: None                          # ollama down -> no embeddings
        self.SF.put("alpha one", summary="alpha one", tags=["a"])
        self.SF.put("alpha two", summary="alpha two", tags=["a"])
        self.assertEqual(self.MH.dedup_clusters(), [])           # no embeddings -> no clusters


if __name__ == "__main__":
    unittest.main()
