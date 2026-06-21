"""Integration tests for scripts/aios_seci_pipeline.py.

Three test classes:
  1. TestPhaseEDoomLoopFilter   — phase_e skips doom_loop patterns even when memoryOS is mocked
  2. TestPatternToDraft         — _pattern_to_draft produces a valid memory_type field
  3. TestRunCycleCycleComplete  — run_cycle with all phases mocked returns cycle_complete=True
"""
import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

import aios_seci_pipeline as seci


# ── 1. phase_e doom_loop filter ───────────────────────────────────────────────

class TestPhaseEDoomLoopFilter:
    """phase_e must never forward doom_loop patterns to write_draft."""

    def _mixed_memories(self):
        return [
            {
                "id": "clean-1",
                "loop_type": "read_edit",
                "tool_freq": {"Read": 3, "Edit": 2},
                "category": "edit",
                "content": "read then edit a file",
            },
            {
                "id": "doom-1",
                "loop_type": "doom_loop",
                "tool_freq": {"Bash": 5, "Read": 4, "Edit": 3},
                "category": "debug",
                "content": "repetitive bash loop that never resolves",
            },
            {
                "id": "clean-2",
                "loop_type": "web_search",
                "tool_freq": {"WebSearch": 2, "Read": 1},
                "category": "research",
                "content": "search then read source docs",
            },
            {
                "id": "doom-2",
                "loop_type": "doom_loop",
                "tool_freq": {"Bash": 8, "Write": 1},
                "category": "debug",
                "content": "another condemned loop pattern",
            },
        ]

    def test_doom_loop_patterns_never_reach_write_draft(self):
        mock_write_draft = MagicMock(return_value={"status": "ok", "id": "draft-xyz"})

        with patch.object(seci, "_load_memoryos", return_value=mock_write_draft):
            draft_ids = seci.phase_e(self._mixed_memories(), dry_run=False)

        # Only 2 clean patterns should have been forwarded
        assert mock_write_draft.call_count == 2, (
            f"Expected write_draft called 2 times (clean patterns only), "
            f"got {mock_write_draft.call_count}"
        )

        # Confirm no doom_loop content leaked into any call
        for call in mock_write_draft.call_args_list:
            content = call.kwargs.get("content", "")
            assert "doom_loop" not in content, (
                f"doom_loop content leaked into write_draft: {content!r}"
            )

    def test_all_doom_loop_input_produces_zero_drafts(self):
        mock_write_draft = MagicMock(return_value={"status": "ok", "id": "draft-xyz"})
        doom_only = [
            {
                "id": f"doom-{i}",
                "loop_type": "doom_loop",
                "tool_freq": {"Bash": i + 1},
                "category": "debug",
                "content": "doom",
            }
            for i in range(4)
        ]

        with patch.object(seci, "_load_memoryos", return_value=mock_write_draft):
            draft_ids = seci.phase_e(doom_only, dry_run=False)

        assert draft_ids == [], (
            f"Expected empty draft list for doom_loop-only input, got {draft_ids}"
        )
        assert mock_write_draft.call_count == 0, (
            "write_draft must never be called when all patterns are doom_loop"
        )

    def test_empty_input_produces_zero_drafts(self):
        mock_write_draft = MagicMock(return_value={"status": "ok", "id": "draft-xyz"})

        with patch.object(seci, "_load_memoryos", return_value=mock_write_draft):
            draft_ids = seci.phase_e([], dry_run=False)

        assert draft_ids == []
        assert mock_write_draft.call_count == 0


# ── 2. _pattern_to_draft memory_type validation ───────────────────────────────

class TestPatternToDraft:
    """_pattern_to_draft must always produce a valid, non-empty memory_type field."""

    def test_returns_memory_type_key(self):
        pattern = {
            "id": "pat-001",
            "loop_type": "read_edit",
            "tool_freq": {"Read": 5, "Edit": 3, "Bash": 1},
            "category": "code_change",
            "content": "Typical read-then-edit agent session.",
        }
        draft = seci._pattern_to_draft(pattern)
        assert "memory_type" in draft, "_pattern_to_draft must include 'memory_type' key"

    def test_memory_type_is_non_empty_string(self):
        pattern = {
            "id": "pat-002",
            "loop_type": "web_search",
            "tool_freq": {"WebSearch": 2},
            "category": "research",
            "content": "web search session",
        }
        draft = seci._pattern_to_draft(pattern)
        mt = draft["memory_type"]
        assert isinstance(mt, str), f"memory_type must be str, got {type(mt)}"
        assert mt.strip(), "memory_type must not be blank"

    def test_memory_type_equals_capability(self):
        """Current implementation always sets memory_type='capability'."""
        pattern = {"id": "pat-003", "loop_type": "any", "tool_freq": {}, "category": "misc", "content": ""}
        draft = seci._pattern_to_draft(pattern)
        assert draft["memory_type"] == "capability", (
            f"Expected 'capability', got {draft['memory_type']!r}"
        )

    def test_memory_type_survives_sparse_pattern(self):
        """_pattern_to_draft must not raise and must still provide memory_type for a minimal dict."""
        draft = seci._pattern_to_draft({})
        assert "memory_type" in draft
        assert isinstance(draft["memory_type"], str) and draft["memory_type"]

    def test_draft_includes_required_memoryos_fields(self):
        pattern = {
            "id": "pat-004",
            "loop_type": "plan_act",
            "tool_freq": {"TaskCreate": 2, "Edit": 1},
            "category": "planning",
            "content": "task planning session",
        }
        draft = seci._pattern_to_draft(pattern)
        for field in ("memory_type", "content", "project", "origin", "confidence"):
            assert field in draft, f"_pattern_to_draft must produce field '{field}'"


# ── 3. run_cycle cycle_complete with all phases mocked ───────────────────────

class TestRunCycleCycleComplete:
    """run_cycle must return cycle_complete=True when all four phase functions are mocked."""

    def _patch_all_phases(self, *, memories=None, draft_ids=None, review=None, prediction=None):
        memories = memories if memories is not None else []
        draft_ids = draft_ids if draft_ids is not None else []
        review = review if review is not None else {"accepted": [], "rejected": [], "queued": []}
        prediction = prediction if prediction is not None else {"ranked": [], "method": "none"}
        return (
            patch.object(seci, "phase_s", return_value=memories),
            patch.object(seci, "phase_e", return_value=draft_ids),
            patch.object(seci, "phase_c", return_value=review),
            patch.object(seci, "phase_i", return_value=prediction),
        )

    def test_cycle_complete_is_true(self):
        # run_cycle indexes prediction["ranked"][0] unconditionally, so we must
        # supply at least one entry — an empty list would raise IndexError in the source.
        patches = self._patch_all_phases(
            prediction={"ranked": [{"action": "Read", "score": 0.5}], "method": "stub"}
        )
        with patches[0], patches[1], patches[2], patches[3]:
            result = seci.run_cycle(provider="claude", dry_run=True)
        assert result.get("cycle_complete") is True, (
            f"Expected cycle_complete=True, got {result.get('cycle_complete')!r}"
        )

    def test_cycle_complete_true_with_realistic_phase_outputs(self):
        fake_memories = [
            {"id": "m1", "loop_type": "read_edit", "tool_freq": {"Read": 2, "Edit": 1}, "category": "edit", "content": "stub"},
        ]
        fake_draft_ids = ["draft-001", "draft-002"]
        fake_review = {"accepted": ["draft-001"], "rejected": ["draft-002"], "queued": []}
        fake_prediction = {
            "ranked": [{"action": "Edit", "score": 0.85}, {"action": "Read", "score": 0.72}],
            "method": "freq_weighted",
        }
        patches = self._patch_all_phases(
            memories=fake_memories,
            draft_ids=fake_draft_ids,
            review=fake_review,
            prediction=fake_prediction,
        )
        with patches[0], patches[1], patches[2], patches[3]:
            result = seci.run_cycle(provider="claude", dry_run=False)
        assert result["cycle_complete"] is True

    def test_cycle_report_contains_all_schema_fields(self):
        patches = self._patch_all_phases(
            prediction={"ranked": [{"action": "Bash", "score": 0.6}], "method": "fallback"},
        )
        with patches[0], patches[1], patches[2], patches[3]:
            result = seci.run_cycle()

        required = {
            "schema_version",
            "s_patterns_ingested",
            "e_drafts_created",
            "e_draft_ids",
            "c_accepted",
            "c_rejected",
            "c_queued",
            "i_top_action",
            "i_top_score",
            "i_method",
            "cycle_complete",
        }
        missing = required - result.keys()
        assert not missing, f"run_cycle result is missing fields: {missing}"
        assert result["cycle_complete"] is True

    def test_cycle_complete_true_with_single_ranked_entry(self):
        """Minimal non-empty ranked list — the minimum required by the current source."""
        # Note: run_cycle does `prediction.get("ranked", [{}])[0]` which raises IndexError
        # when ranked is explicitly [] (the default fallback only triggers when the key is
        # absent entirely).  This test documents the minimum-viable prediction shape.
        patches = self._patch_all_phases(
            prediction={"ranked": [{"action": "Edit", "score": 0.9}], "method": "freq"},
        )
        with patches[0], patches[1], patches[2], patches[3]:
            result = seci.run_cycle(dry_run=True)
        assert result["cycle_complete"] is True
        assert result.get("i_top_action") == "Edit"
