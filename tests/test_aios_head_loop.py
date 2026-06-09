"""The kernel head can now run a reactive agent TURN-LOOP (organs as kernel tools,
authority-gated) — additive to the existing single-pass plan path. This is what keeps
the turn-loop from being an orphan: the head actually drives it.
"""
import sys
import unittest
from pathlib import Path

sys.path.insert(0, (Path(__file__).resolve().parents[1] / "scripts").as_posix())

import aios_head as H
import aios_turn_loop as L


def scripted(steps):
    it = iter(steps)
    return lambda h: next(it)


class HeadLoopTests(unittest.TestCase):
    def test_head_runs_the_loop_routing_organs_through_kernel(self) -> None:
        r = H.run_loop_goal("inspect", agent_id="codex@myworld", sampler=scripted([
            {"tool_calls": [L.ToolCall("self.audit",
                {"claims": [{"text": "head", "path": "scripts/aios_head.py"}]})]},
            {"tool_calls": []},
        ]))
        self.assertEqual(r["exit"], "model_finished")
        self.assertTrue(r["kernel_routed"])

    def test_no_sampler_is_honest(self) -> None:
        self.assertEqual(H.run_loop_goal("x")["exit"], "no_sampler")

    def test_provider_sampler_degrades_when_provider_unreachable(self) -> None:
        # a provider adapter that raises → sampler ends the loop cleanly, no fabrication
        def boom(_prompt):
            raise RuntimeError("provider down")
        sampler = H.make_provider_sampler("claude", {"claude": boom})
        r = H.run_loop_goal("x", sampler=sampler)
        self.assertEqual(r["exit"], "model_finished")   # ended, did not invent a tool call
        self.assertEqual(r["tool_calls"], 0)

    def test_provider_sampler_parses_a_tool_call(self) -> None:
        # a provider returning a JSON move → one tool call, then done
        replies = iter(['{"tool":"fs.read","arguments":{"path":"scripts/aios_head.py"}}',
                        '{"done":true}'])
        sampler = H.make_provider_sampler("claude", {"claude": lambda p: next(replies)})
        r = H.run_loop_goal("read head", agent_id="codex@myworld", sampler=sampler)
        self.assertEqual([t["tool"] for t in r["trajectory"]], ["fs.read"])


if __name__ == "__main__":
    unittest.main()
