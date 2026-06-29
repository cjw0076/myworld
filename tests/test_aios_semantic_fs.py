from __future__ import annotations

import importlib.util
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SCRIPTS = ROOT / "scripts"


def _load():
    spec = importlib.util.spec_from_file_location("aios_semantic_fs_uut", SCRIPTS / "aios_semantic_fs.py")
    m = importlib.util.module_from_spec(spec)
    sys.modules["aios_semantic_fs_uut"] = m
    if str(SCRIPTS) not in sys.path:
        sys.path.insert(0, str(SCRIPTS))
    spec.loader.exec_module(m)
    return m


# deterministic topic embeddings (no GPU/ollama) — 3 orthogonal axes
def _fake_embed(text: str):
    t = text.lower()
    if any(w in t for w in ("solar", "sun", "photovolt", "energy")):
        return [1.0, 0.0, 0.0]
    if any(w in t for w in ("lean", "proof", "theorem", "tactic")):
        return [0.0, 1.0, 0.0]
    if any(w in t for w in ("pasta", "carbonara", "recipe", "pecorino")):
        return [0.0, 0.0, 1.0]
    return [0.3, 0.3, 0.3]


SEEDS = {
    "solar": "Photovoltaic panels convert sunlight into electricity; perovskite tandem cells.",
    "lean": "Lean 4 is a theorem prover; the omega tactic discharges arithmetic proof goals.",
    "pasta": "Carbonara uses guanciale, egg yolk, pecorino; never cream in the recipe.",
}


class SemanticFsTest(unittest.TestCase):
    def setUp(self):
        self.m = _load()
        self.tmp = tempfile.mkdtemp(prefix="aios_fs_test_")
        import os
        os.environ["AIOS_FS_ROOT"] = self.tmp

    def _seed(self):
        return {k: self.m.put(v, summary=v, tags=[k]) for k, v in SEEDS.items()}

    def test_put_get_pointer_integrity(self):
        self.m._embed = lambda t: None  # no embed needed here
        node = self.m.put("the quick brown fox jumps", tags=["t"])
        self.assertTrue(Path(node["path"]).exists())            # pointed-to file on disk
        self.assertIn("quick brown fox", self.m.get(node))      # get returns on-disk content
        self.assertIn("quick brown fox", self.m.get(node["id"]))  # by id too

    def test_search_semantic_top1_by_meaning(self):
        self.m._embed = _fake_embed                              # deterministic semantic vectors
        self._seed()
        hits = self.m.search("how do we capture power from the sun", k=1)
        self.assertEqual(len(hits), 1)
        self.assertEqual(hits[0]["_method"], "semantic")
        self.assertIn("solar", hits[0]["tags"])                 # topically right, not insertion order

    def test_search_keyword_fallback_when_no_embeddings(self):
        self.m._embed = lambda t: None                          # ollama down → fallback
        self._seed()
        hits = self.m.search("carbonara recipe", k=1)
        self.assertTrue(hits)
        self.assertEqual(hits[0]["_method"], "keyword")
        self.assertIn("pasta", hits[0]["tags"])
        # must not crash and must return the relevant one

    def test_link_and_neighbors(self):
        self.m._embed = lambda t: None
        a = self.m.put(SEEDS["solar"], tags=["solar"])
        b = self.m.put(SEEDS["lean"], tags=["lean"])
        self.m.link(a, b, "cites")
        nb = self.m.neighbors(a)
        self.assertEqual(len(nb), 1)
        self.assertEqual(nb[0]["id"], b["id"])
        self.assertEqual(nb[0]["_relation"], "cites")

    def test_rm_is_append_only_tombstone(self):
        self.m._embed = lambda t: None
        node = self.m.put(SEEDS["pasta"], tags=["pasta"])
        index = Path(self.tmp) / "index.jsonl"
        lines_before = len(index.read_text().splitlines())
        self.m.rm(node)
        lines_after = len(index.read_text().splitlines())
        self.assertGreater(lines_after, lines_before)           # append-only: grew, not shrank
        self.assertEqual([n for n in self.m.ls() if n["id"] == node["id"]], [])  # gone from live set
        self.assertEqual(self.m.search("pasta carbonara"), [])  # excluded from search

    def test_privacy_index_holds_pointer_and_capped_summary_only(self):
        self.m._embed = lambda t: None
        big = "SECRET_BODY " * 500                                # long content (500 repeats)
        node = self.m.put(big, tags=["x"])
        self.assertLessEqual(len(node["summary"]), 200)          # summary CAPPED, not full body
        rec = self.m._live_nodes()[node["id"]]
        # the index record holds a capped summary (~16 repeats), NOT the full 500-repeat body
        self.assertLess(rec.get("summary", "").count("SECRET_BODY"), 50)
        self.assertIn("path", rec)                               # pointer present
        # the full body lives only in the on-disk blob the pointer references (local-only)
        self.assertEqual(self.m.get(node).count("SECRET_BODY"), 500)


if __name__ == "__main__":
    unittest.main()
