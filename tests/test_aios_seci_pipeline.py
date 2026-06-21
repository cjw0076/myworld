"""Tests for aios_seci_pipeline — SECI knowledge cycle."""
import sys
import unittest
from pathlib import Path
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))

import aios_seci_pipeline as seci


class TestPhaseSFallback(unittest.TestCase):
    def test_phase_s_returns_list(self):
        """phase_s always returns a list even if sessions produce nothing."""
        result = seci.phase_s(provider="claude")
        self.assertIsInstance(result, list)

    def test_phase_s_unknown_provider_returns_empty(self):
        result = seci.phase_s(provider="nonexistent_provider_xyz")
        self.assertIsInstance(result, list)


class TestPhaseEPatternToDraft(unittest.TestCase):
    def test_pattern_to_draft_structure(self):
        pat = {
            "id": "abc123",
            "loop_type": "react_code",
            "category": "code",
            "tool_freq": {"Edit": 3, "Bash": 2, "Read": 1},
            "content": "edited files and ran tests",
        }
        draft = seci._pattern_to_draft(pat)
        self.assertEqual(draft["memory_type"], "capability")
        self.assertEqual(draft["project"], "aios")
        self.assertIn("Edit", draft["content"])
        self.assertEqual(draft["confidence"], 0.55)

    def test_pattern_to_draft_empty_tools(self):
        pat = {"id": "x", "tool_freq": {}}
        draft = seci._pattern_to_draft(pat)
        self.assertIn("none", draft["content"])

    def test_doom_loop_excluded_from_e(self):
        """doom_loop patterns should not become drafts."""
        mems = [
            {"id": "a", "loop_type": "doom_loop", "tool_freq": {"Bash": 10}},
            {"id": "b", "loop_type": "react_code", "tool_freq": {"Edit": 3, "Read": 2}},
        ]
        with mock.patch("aios_seci_pipeline._load_memoryos", return_value=None):
            ids = seci.phase_e(mems, dry_run=False)
        self.assertEqual(ids, [])  # no memoryos available → empty

    def test_phase_e_dry_run_no_memoryos_call(self):
        """dry_run with memoryos available returns dry: prefixed IDs."""
        fake_write = mock.Mock(return_value={"status": "ok", "id": "mem-123"})
        with mock.patch("aios_seci_pipeline._load_memoryos", return_value=fake_write):
            mems = [{"id": "p1", "loop_type": "react_code",
                     "tool_freq": {"Edit": 2, "Read": 1}, "content": "test"}]
            ids = seci.phase_e(mems, dry_run=True)
        self.assertTrue(all(i.startswith("dry:") for i in ids))
        fake_write.assert_not_called()

    def test_phase_e_live_calls_write_draft(self):
        fake_write = mock.Mock(return_value={"status": "ok", "id": "mem-xyz"})
        with mock.patch("aios_seci_pipeline._load_memoryos", return_value=fake_write):
            mems = [{"id": "p1", "loop_type": "react_code",
                     "tool_freq": {"Edit": 2, "Read": 1, "Bash": 1}, "content": "test ctx"}]
            ids = seci.phase_e(mems, dry_run=False)
        self.assertEqual(ids, ["mem-xyz"])
        fake_write.assert_called_once()


class TestPhaseCFallback(unittest.TestCase):
    def test_phase_c_returns_dict_when_unavailable(self):
        with mock.patch("aios_seci_pipeline._load_auto_reviewer", return_value=None):
            result = seci.phase_c(dry_run=True)
        self.assertIn("accepted", result)
        self.assertIn("rejected", result)
        self.assertIn("queued", result)


class TestPhaseI(unittest.TestCase):
    def test_phase_i_returns_dict(self):
        result = seci.phase_i("read a file then need to edit", ["Edit", "Read", "Bash"])
        self.assertIsInstance(result, dict)

    def test_phase_i_top_action_in_candidates(self):
        cands = ["Edit", "Read", "Bash"]
        result = seci.phase_i("fix a bug in the code", cands)
        ranked = result.get("ranked", [])
        if ranked:
            self.assertIn(ranked[0]["action"], cands)


class TestRunCycleDryRun(unittest.TestCase):
    def test_cycle_schema(self):
        result = seci.run_cycle(provider="claude", dry_run=True)
        self.assertEqual(result.get("schema_version"), "aios.seci.v1")
        self.assertIn("s_patterns_ingested", result)
        self.assertIn("e_drafts_created", result)
        self.assertIn("c_accepted", result)
        self.assertIn("i_top_action", result)
        self.assertTrue(result.get("cycle_complete"))

    def test_cycle_returns_numeric_counts(self):
        result = seci.run_cycle(dry_run=True)
        for key in ("s_patterns_ingested", "e_drafts_created", "c_accepted", "c_rejected"):
            self.assertIsInstance(result[key], int, f"{key} should be int")


if __name__ == "__main__":
    unittest.main()
