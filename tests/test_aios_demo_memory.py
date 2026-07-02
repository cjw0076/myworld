"""Tests for the MEMORY ACT of `aios demo` (scripts/aios_demo.py).

Hermetic: no network, no GPU, no ollama, no API key. The demo pins the real
behavioral-memory engine to its offline keyword/frequency fallback and points its
store at an isolated temp AIOS_HOME, so these tests exercise the REAL ingest →
record → predict path with nothing mocked. The headline they protect: run 1 starts
from zero, run 2 carries forward what the recorded run did.
"""
from __future__ import annotations

import os
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, (Path(__file__).resolve().parents[1] / "scripts").as_posix())

import aios_demo as d


class MemoryActTests(unittest.TestCase):
    def setUp(self) -> None:
        self._td = tempfile.TemporaryDirectory()
        self.home = Path(self._td.name)
        self.mem = d.run_memory_act(home=self.home)

    def tearDown(self) -> None:
        self._td.cleanup()

    def test_run1_starts_from_zero(self) -> None:
        # (a) with an empty ledger the predictor honestly reports no prior data
        r1 = self.mem["run1"]
        self.assertEqual(r1["method"], "no_data")
        self.assertEqual(r1["memories_used"], 0)

    def test_run_recorded_into_isolated_tmp_ledger(self) -> None:
        rec = self.mem["recorded"]
        self.assertGreaterEqual(rec["written"], 1)
        self.assertTrue(rec["id"].startswith("beh-"))
        # the record really landed in the tmp ledger (real write path)
        store = self.home / "memory" / "objects.jsonl"
        self.assertTrue(store.exists())
        self.assertIn(rec["id"], store.read_text(encoding="utf-8"))

    def test_run2_is_grounded_in_the_recorded_run(self) -> None:
        # (b) after recording, run 2 is non-empty and derives from the recorded entry
        r2 = self.mem["run2"]
        self.assertGreaterEqual(r2["memories_used"], 1)
        self.assertTrue(r2["ranked"])
        # a real frequency signal from the recorded run actually contributed
        self.assertTrue(any(r.get("freq_score", 0) > 0 for r in r2["ranked"]))
        # and the top suggestion is a tool the recorded run genuinely used
        self.assertIn(r2["top"], self.mem["recorded"]["top_tools"])

    def test_delta_zero_to_learned(self) -> None:
        # the whole point: run 1 empty, run 2 informed by exactly the recorded run
        self.assertEqual(self.mem["run1"]["memories_used"], 0)
        self.assertEqual(self.mem["run2"]["memories_used"], 1)

    def test_memory_ok_is_the_honesty_gate(self) -> None:
        self.assertTrue(self.mem["memory_ok"])


class IsolationTests(unittest.TestCase):
    """The stranger's real ~/.aios must never be touched (env points at tmp)."""

    def setUp(self) -> None:
        self._prev = os.environ.get("AIOS_HOME")

    def tearDown(self) -> None:
        if self._prev is None:
            os.environ.pop("AIOS_HOME", None)
        else:
            os.environ["AIOS_HOME"] = self._prev

    def test_store_points_at_tmp_home_not_real_aios(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            home = Path(td)
            beh = d._load_behavior(home)
            self.assertEqual(beh.AIOS_HOME, home.resolve())
            self.assertEqual(beh.MEMORY_STORE, home.resolve() / "memory" / "objects.jsonl")
            # (c) never the stranger's real ledger
            self.assertNotEqual(beh.MEMORY_STORE, Path.home() / ".aios" / "memory" / "objects.jsonl")

    def test_offline_pins_no_embeddings_no_descentnet(self) -> None:
        # deterministic no-GPU/no-network fallback: the real machinery, held offline
        with tempfile.TemporaryDirectory() as td:
            beh = d._load_behavior(Path(td))
            self.assertIsNone(beh.DESCENTNET)
            self.assertIsNone(beh._embed_batch(["anything"]))

    def test_env_restored_after_run(self) -> None:
        before = os.environ.get("AIOS_HOME")
        with tempfile.TemporaryDirectory() as td:
            d.run_memory_act(home=Path(td))
        self.assertEqual(os.environ.get("AIOS_HOME"), before)


class DemoMainTests(unittest.TestCase):
    def test_main_human_exits_zero(self) -> None:
        # (d) full demo (memory act + verify act) exits 0
        self.assertEqual(d.main(["--no-receipt"]), 0)

    def test_main_json_exits_zero(self) -> None:
        self.assertEqual(d.main(["--json", "--no-receipt"]), 0)


if __name__ == "__main__":
    unittest.main()
