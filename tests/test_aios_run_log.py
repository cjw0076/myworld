"""Resumable run log (blueprint step 5): a kernel run becomes reconstructible, not
just auditable. Load-bearing: reconstruct after an interruption, and no content leaks.
"""
import json
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, (Path(__file__).resolve().parents[1] / "scripts").as_posix())

import aios_run_log as RL
import aios_tools as tools
import aios_turn_loop as L


def scripted(steps):
    it = iter(steps)
    return lambda h: next(it)


class RunLogTests(unittest.TestCase):
    def test_open_and_reconstruct_resumable(self) -> None:
        with tempfile.TemporaryDirectory() as t:
            rl = RL.RunLog("r1", runs_dir=Path(t))
            rl.open()
            L.run_loop("g", scripted([
                {"tool_calls": [L.ToolCall("self.audit", {"claims": []}, call_id="c1")]},
                {"tool_calls": []},
            ]), tools.build_registry(), gate=tools.gate_for("codex@myworld"), turn_sink=rl.sink)
            r = RL.reconstruct(rl.path)
            self.assertTrue(r["resumable"])
            self.assertEqual(r["run_id"], "r1")
            self.assertEqual(r["tool_calls_so_far"], 1)
            self.assertGreaterEqual(r["resume_at_turn"], 2)

    def test_reconstruct_after_interruption_points_to_next_turn(self) -> None:
        # simulate a crash: log only the first 2 turn_contexts, then reconstruct
        with tempfile.TemporaryDirectory() as t:
            rl = RL.RunLog("r2", runs_dir=Path(t))
            rl.open()
            rl.sink({"kind": "turn_context", "turn": 1})
            rl.sink({"kind": "trajectory", "turn": 1, "tool": "fs.read", "status": "ok"})
            rl.sink({"kind": "turn_context", "turn": 2})
            # crash here — turn 2 never finished
            r = RL.reconstruct(rl.path)
            self.assertTrue(r["resumable"])
            self.assertEqual(r["resume_at_turn"], 3)        # resume AFTER the last seen turn
            self.assertEqual(r["tool_calls_so_far"], 1)

    def test_compacted_checkpoint_dropped(self) -> None:
        with tempfile.TemporaryDirectory() as t:
            rl = RL.RunLog("r3", runs_dir=Path(t), compact_every=1)
            rl.open()
            rl.sink({"kind": "turn_context", "turn": 1})
            rl.sink({"kind": "turn_context", "turn": 2})
            recs = [json.loads(x) for x in rl.path.read_text().splitlines() if x.strip()]
            self.assertTrue(any(r["kind"] == "compacted" for r in recs))

    def test_missing_log_not_resumable(self) -> None:
        self.assertFalse(RL.reconstruct("/no/such/run.jsonl")["resumable"])

    def test_log_leaks_no_content(self) -> None:
        with tempfile.TemporaryDirectory() as t:
            rl = RL.RunLog("r4", runs_dir=Path(t))
            rl.open()
            L.run_loop("g", scripted([
                {"tool_calls": [L.ToolCall("fs.write", {"body": "AKIA_RUNLOG_SECRET"}, call_id="c1")]},
                {"tool_calls": []},
            ]), tools.build_registry(), gate=lambda n, a: L.ALLOW, turn_sink=rl.sink)
            self.assertNotIn("AKIA_RUNLOG_SECRET", rl.path.read_text())   # names/status only


if __name__ == "__main__":
    unittest.main()
