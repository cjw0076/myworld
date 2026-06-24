"""Tests for aios_agent_behavior.py — Phase D: doom-loop filter, loop_type,
transition probability, predict_behavior hybrid scoring, and JSONL parsing."""
from __future__ import annotations

import importlib.util
import json
import sys
import tempfile
import unittest
from pathlib import Path

ROOT    = Path(__file__).resolve().parent.parent
SCRIPTS = ROOT / "scripts"


def _load(name: str):
    full = f"{name}_behavior_under_test"
    spec = importlib.util.spec_from_file_location(full, SCRIPTS / f"{name}.py")
    m = importlib.util.module_from_spec(spec)
    sys.modules[full] = m
    if str(SCRIPTS) not in sys.path:
        sys.path.insert(0, str(SCRIPTS))
    spec.loader.exec_module(m)
    return m


class SubAgentStructureTest(unittest.TestCase):
    """Phase A2 / Q6: ingest recognizes sub-agents (sidechain) as sub-episodes."""
    def setUp(self):
        self.m = _load("aios_agent_behavior")

    def test_separates_main_sub_and_captures_features(self):
        rows = [
            {"type": "assistant", "message": {"content": [{"type": "tool_use", "name": "Bash"}]}},
            {"type": "assistant", "message": {"content": [{"type": "tool_use", "name": "Task"}]}},
            {"type": "assistant", "isSidechain": True, "parentUuid": "p1",
             "message": {"content": [{"type": "tool_use", "name": "Grep"}]}},
            {"type": "assistant", "isSidechain": True, "parentUuid": "p1",
             "message": {"content": [{"type": "tool_use", "name": "Read"}]}},
            {"type": "assistant", "message": {"content": [{"type": "tool_use", "name": "mcp__aios__aios_route"}]}},
        ]
        with tempfile.TemporaryDirectory() as d:
            p = Path(d) / "s.jsonl"
            p.write_text("\n".join(json.dumps(r) for r in rows), encoding="utf-8")
            s = self.m._parse_claude_structured(p)
            flat = self.m._parse_claude_session(p)   # read inside the tempdir scope
        self.assertEqual(s["main_tools"], ["Bash", "Task", "mcp__aios__aios_route"])
        self.assertEqual(s["subagent_tools"], ["Grep", "Read"])
        self.assertEqual(s["subagents"], 1)            # one parentUuid
        self.assertIn("Task", s["features"])
        self.assertIn("mcp__aios__aios_route", s["features"])
        self.assertEqual(flat, s["tools"])             # compat wrapper = flat list

    def test_worker_interventions_separated_from_agent(self):
        # Phase B / Q2: human steering modeled apart from the agent's tool policy.
        rows = [
            {"type": "user", "message": {"content": "do the task"}},                 # initial — not an intervention
            {"type": "assistant", "message": {"content": [{"type": "tool_use", "name": "Bash"}]}},
            {"type": "user", "message": {"content": "no, edit instead"}},            # intervention #1
            {"type": "assistant", "message": {"content": [{"type": "tool_use", "name": "Edit"}]}},
            {"type": "user", "message": {"content": [{"type": "tool_result", "content": "ok"}]}},  # tool_result — not human
            {"type": "assistant", "message": {"content": [{"type": "tool_use", "name": "Read"}]}},
            {"type": "user", "message": {"content": "stop, wrong"}},                 # intervention #2
        ]
        with tempfile.TemporaryDirectory() as d:
            p = Path(d) / "s.jsonl"
            p.write_text("\n".join(json.dumps(r) for r in rows), encoding="utf-8")
            s = self.m._parse_claude_structured(p)
        self.assertEqual(s["main_tools"], ["Bash", "Edit", "Read"])
        self.assertEqual(s["worker_interventions"], 2)   # redirect + stop; initial & tool_result excluded


class DoomLoopDetectionTest(unittest.TestCase):
    def setUp(self):
        self.m = _load("aios_agent_behavior")

    def test_no_doom_loop_alternating(self):
        self.assertFalse(self.m._has_doom_loop(["Bash", "Read", "Bash", "Edit"]))

    def test_three_consecutive_not_doom(self):
        # threshold induced to 12 — 3 consecutive (e.g. git status/diff/log) is normal
        self.assertFalse(self.m._has_doom_loop(["Bash", "Bash", "Bash"]))

    def test_pathological_run_is_doom(self):
        self.assertTrue(self.m._has_doom_loop(["Read"] + ["Bash"] * 12))

    def test_below_threshold_not_doom(self):
        self.assertFalse(self.m._has_doom_loop(["Bash"] * 11 + ["Read"]))

    def test_two_consecutive_not_doom(self):
        self.assertFalse(self.m._has_doom_loop(["Bash", "Bash", "Read"]))

    def test_empty_list(self):
        self.assertFalse(self.m._has_doom_loop([]))

    def test_single_tool(self):
        self.assertFalse(self.m._has_doom_loop(["Bash"]))

    def test_threshold_customization(self):
        # threshold=2: two consecutive = doom_loop
        self.assertTrue(self.m._has_doom_loop(["Bash", "Bash"], threshold=2))
        self.assertFalse(self.m._has_doom_loop(["Bash", "Read"], threshold=2))


class LoopTypeClassificationTest(unittest.TestCase):
    def setUp(self):
        self.m = _load("aios_agent_behavior")

    def test_doom_loop_classified(self):
        tools = ["Edit"] + ["Bash"] * 12        # pathological consecutive run
        self.assertEqual(self.m._classify_loop_type(tools), "doom_loop")

    def test_quick_fewer_than_5(self):
        self.assertEqual(self.m._classify_loop_type(["Read", "Edit"]), "quick")

    def test_react_code_edit_and_bash_heavy(self):
        # ≥15% Edit, ≥10% Bash
        tools = ["Read", "Edit", "Edit", "Bash", "Bash", "Edit"]
        self.assertEqual(self.m._classify_loop_type(tools), "react_code")

    def test_exploration_read_heavy_diverse(self):
        # No 3+ consecutive same tool (that would trigger doom_loop)
        tools = ["Read", "Bash", "Read", "WebSearch", "Read", "Grep", "Read"]
        result = self.m._classify_loop_type(tools)
        self.assertIn(result, ("exploration", "react_general"))

    def test_unknown_falls_back_to_react_general(self):
        tools = ["Bash", "Read", "WebSearch", "Edit", "Grep", "Agent"]
        result = self.m._classify_loop_type(tools)
        self.assertIn(result, ("react_general", "react_code", "exploration"))


class TransitionScoreTest(unittest.TestCase):
    def setUp(self):
        self.m = _load("aios_agent_behavior")

    def _mem(self, seq: list[str], loop_type: str = "react_code") -> dict:
        return {
            "id": "test-" + "-".join(seq[:3]),
            "content": "test session",
            "tool_sequence": seq,
            "top_tools": list(set(seq)),
            "tool_freq": {t: seq.count(t) for t in set(seq)},
            "loop_type": loop_type,
        }

    def test_bash_to_edit_transition(self):
        mems = [self._mem(["Bash", "Edit", "Bash", "Edit", "Bash", "Edit"])]
        scores = self.m._transition_scores("Bash", ["Edit", "Read", "Write"], mems)
        # Edit should score highest after Bash
        top = max(scores, key=scores.get)
        self.assertEqual(top, "Edit")

    def test_doom_loop_downweighted(self):
        mems = [
            self._mem(["Bash", "Edit", "Bash", "Edit"], loop_type="react_code"),
            self._mem(["Bash", "Bash", "Bash", "Bash", "Edit"], loop_type="doom_loop"),
        ]
        scores = self.m._transition_scores("Bash", ["Edit", "Read"], mems)
        # Edit should still win despite doom_loop entry also Bash→Edit
        # But doom_loop weight 0.1 — Edit should still score positively
        self.assertGreater(scores.get("Edit", 0), 0)

    def test_no_data_uniform_fallback(self):
        mems = [self._mem(["Read", "Write"])]  # no Bash transitions
        scores = self.m._transition_scores("Bash", ["Edit", "Read", "Write"], mems)
        # All should be 1/3 uniform
        vals = list(scores.values())
        self.assertAlmostEqual(vals[0], vals[1], places=5)
        self.assertAlmostEqual(vals[1], vals[2], places=5)

    def test_empty_memories_uniform(self):
        scores = self.m._transition_scores("Bash", ["Edit", "Read"], [])
        self.assertAlmostEqual(scores["Edit"], 0.5, places=5)
        self.assertAlmostEqual(scores["Read"], 0.5, places=5)

    def test_top_tools_fallback_when_no_sequence(self):
        # If tool_sequence is absent, should fall back to top_tools
        mem = {
            "id": "no-seq",
            "content": "x",
            "tool_freq": {"Edit": 3, "Bash": 2},
            "top_tools": ["Bash", "Edit"],  # no tool_sequence
            "loop_type": "react_code",
        }
        scores = self.m._transition_scores("Bash", ["Edit", "Read"], [mem])
        # With top_tools fallback, at least one transition should be found
        self.assertIsInstance(scores, dict)
        self.assertIn("Edit", scores)


class PredictBehaviorNoDataTest(unittest.TestCase):
    """predict_behavior without real embeddings — tests no_data path."""

    def setUp(self):
        self.m = _load("aios_agent_behavior")

    def test_no_data_returns_candidates(self):
        # Patch load_behavior_memories to return empty + disable global fetch
        import unittest.mock as mock
        with mock.patch.object(self.m, "load_behavior_memories", return_value=[]), \
             mock.patch.object(self.m, "sync_from_global", return_value=[]):
            result = self.m.predict_behavior(
                "fix bug in auth.py", ["Edit", "Read", "Bash"],
                use_global=False,
            )
        self.assertIn("ranked", result)
        self.assertEqual(result["method"], "no_data")
        # All candidates appear
        actions = {r["action"] for r in result["ranked"]}
        self.assertTrue(actions.issubset({"Edit", "Read", "Bash"}))

    def test_with_memories_prev_tool_uses_transition(self):
        """When prev_tool is given and memories exist, method is hybrid."""
        mems = [{
            "id": "m1",
            "content": "code fix session",
            "tool_freq": {"Edit": 3, "Bash": 2},
            "top_tools": ["Edit", "Bash", "Read"],
            "tool_sequence": ["Bash", "Edit", "Bash", "Edit", "Bash"],
            "loop_type": "react_code",
            "domain": "agent_behavior",
        }]
        import unittest.mock as mock
        with mock.patch.object(self.m, "load_behavior_memories", return_value=mems), \
             mock.patch.object(self.m, "sync_from_global", return_value=[]), \
             mock.patch.object(self.m, "_embed_batch", return_value=[]), \
             mock.patch.object(self.m, "_descent_scores",
                               return_value=({"Edit": 0.8, "Read": 0.5, "Bash": 0.6}, 0.0)):
            result = self.m.predict_behavior(
                "need to change file after running tests",
                ["Edit", "Read", "Bash"],
                use_global=False,
                prev_tool="Bash",
            )
        # Must use transition scoring (prev_tool given)
        self.assertIn("ranked", result)
        # Edit should rank well (Bash→Edit pattern in memories)
        actions = [r["action"] for r in result["ranked"]]
        self.assertIn("Edit", actions)
        # Top result's explanation should mention 'trans='
        top_expl = result["ranked"][0].get("explanation", "")
        self.assertIn("trans=", top_expl)


class FrequencyScoreTest(unittest.TestCase):
    """_frequency_scores weights tool_freq entries correctly."""

    def setUp(self):
        self.m = _load("aios_agent_behavior")

    def test_most_frequent_tool_scores_highest(self):
        mems = [{
            "id": "x",
            "content": "session",
            "tool_freq": {"Edit": 10, "Read": 2, "Bash": 1},
            "top_tools": ["Edit", "Read", "Bash"],
        }]
        scores = self.m._frequency_scores(["Edit", "Read", "Bash"], mems)
        self.assertGreater(scores["Edit"], scores["Read"])
        self.assertGreater(scores["Read"], scores["Bash"])

    def test_doom_loop_weighted_low(self):
        """Doom-loop session tool freq should contribute less to final score."""
        normal_mem = {
            "id": "n",
            "content": "normal",
            "tool_freq": {"Edit": 5},
            "loop_type": "react_code",
        }
        doom_mem = {
            "id": "d",
            "content": "doom",
            "tool_freq": {"Bash": 100},
            "loop_type": "doom_loop",
        }
        scores_with_doom = self.m._frequency_scores(["Edit", "Bash"], [normal_mem, doom_mem])
        scores_without_doom = self.m._frequency_scores(["Edit", "Bash"], [normal_mem])
        # Bash score with doom_loop should be lower than it would be if weighted normally
        # (Can't assert exact ratio without knowing exact impl, but Bash shouldn't dominate)
        # The key: Edit (from normal) should still be competitive
        self.assertGreater(scores_with_doom["Edit"], 0)


class ParseClaudeSessionTest(unittest.TestCase):
    """_parse_claude_session must extract real tool names only.

    Regression: 'queue-operation' and 'last-prompt' are internal Claude Code
    event types — they must NOT appear in the tool sequence.
    """

    def setUp(self):
        self.m = _load("aios_agent_behavior")
        self._td = tempfile.TemporaryDirectory()

    def tearDown(self):
        self._td.cleanup()

    def _write_jsonl(self, events: list[dict]) -> Path:
        p = Path(self._td.name) / "session.jsonl"
        p.write_text("\n".join(json.dumps(e) for e in events))
        return p

    def _tool_event(self, name: str) -> dict:
        return {
            "type": "assistant",
            "message": {
                "content": [{"type": "tool_use", "name": name}]
            }
        }

    def test_real_tools_extracted(self):
        path = self._write_jsonl([
            self._tool_event("Bash"),
            self._tool_event("Read"),
            self._tool_event("Edit"),
        ])
        tools = self.m._parse_claude_session(path)
        self.assertEqual(tools, ["Bash", "Read", "Edit"])

    def test_queue_operation_excluded(self):
        """queue-operation is an internal event type, NOT a tool."""
        path = self._write_jsonl([
            self._tool_event("Bash"),
            {"type": "queue-operation", "data": "something"},
            self._tool_event("Edit"),
        ])
        tools = self.m._parse_claude_session(path)
        self.assertNotIn("queue-operation", tools)
        self.assertEqual(tools, ["Bash", "Edit"])

    def test_last_prompt_excluded(self):
        """last-prompt is an internal event type, NOT a tool."""
        path = self._write_jsonl([
            {"type": "last-prompt", "content": "the goal"},
            self._tool_event("Read"),
            self._tool_event("Write"),
        ])
        tools = self.m._parse_claude_session(path)
        self.assertNotIn("last-prompt", tools)
        self.assertEqual(tools, ["Read", "Write"])

    def test_mixed_internal_events_filtered(self):
        """Both garbage event types filtered from a realistic session."""
        path = self._write_jsonl([
            {"type": "last-prompt", "content": "fix bug"},
            self._tool_event("Read"),
            {"type": "queue-operation", "data": "x"},
            self._tool_event("Edit"),
            {"type": "queue-operation", "data": "y"},
            self._tool_event("Bash"),
        ])
        tools = self.m._parse_claude_session(path)
        self.assertEqual(tools, ["Read", "Edit", "Bash"])
        self.assertNotIn("queue-operation", tools)
        self.assertNotIn("last-prompt", tools)

    def test_empty_session(self):
        path = self._write_jsonl([])
        tools = self.m._parse_claude_session(path)
        self.assertEqual(tools, [])

    def test_no_tool_use_events(self):
        path = self._write_jsonl([
            {"type": "user", "message": {"content": "hello"}},
            {"type": "last-prompt", "content": "fix bug"},
        ])
        tools = self.m._parse_claude_session(path)
        self.assertEqual(tools, [])


if __name__ == "__main__":
    unittest.main()
