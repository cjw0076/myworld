"""The turn-loop spine — proves AIOS can now run a model-in-the-loop agent loop
(react to results), gated and loop-safe, instead of a single-pass batch executor.
"""
import sys
import unittest
from pathlib import Path

sys.path.insert(0, (Path(__file__).resolve().parents[1] / "scripts").as_posix())

import aios_turn_loop as L


def scripted(steps):
    it = iter(steps)
    return lambda history: next(it)


class TurnLoopTests(unittest.TestCase):
    def setUp(self) -> None:
        self.reg = L.Registry()
        self.reg.register("aios_read", lambda a: "data")
        self.reg.register("aios_write", lambda a: "written")

    def test_decondition_history_elides_old_errors_keeps_recent_and_success(self) -> None:
        # Renewal pillar 1 (self-conditioning defense, arXiv 2509.09677): old error
        # traces are compressed so the model doesn't self-condition; the most recent
        # error and all successful observations survive verbatim.
        hist = [
            {"role": "user"},
            {"role": "tool", "tool": "Bash", "status": "error",
             "result": {"status": "error", "output": "OLD-ERR-1"}},
            {"role": "tool", "tool": "Read", "status": "no_results",
             "result": {"status": "no_results", "output": "OLD-ERR-2"}},
            {"role": "tool", "tool": "Edit", "status": "ok",
             "result": {"status": "ok", "output": "GOOD"}},
            {"role": "tool", "tool": "Bash", "status": "timeout",
             "result": {"status": "timeout", "output": "RECENT-ERR"}},
        ]
        out = L.decondition_history(hist)
        elided = [h for h in out if (h.get("result") or {}).get("_deconditioned")]
        self.assertEqual(len(elided), 2)                         # both old errors compressed
        self.assertEqual(out[-1]["result"]["output"], "RECENT-ERR")  # recent error kept
        self.assertTrue(any((h.get("result") or {}).get("output") == "GOOD" for h in out))
        self.assertEqual(hist[1]["result"]["output"], "OLD-ERR-1")   # input not mutated

    def test_plan_repair_injected_on_stall(self) -> None:
        # Renewal pillar 3 (arXiv 2604.11978): when the loop makes no progress for
        # repair_threshold turns, a plan_repair note is injected and the sampler sees it.
        self.reg.register("flaky", lambda a: (_ for _ in ()).throw(RuntimeError("boom")))
        repairs = []
        seen = {"v": False}

        def sampler(history):
            if any(h.get("kind") == "plan_repair" for h in history):
                seen["v"] = True
            return {"tool_calls": [L.ToolCall("flaky", {}, call_id="c")]}

        L.run_loop("goal", sampler, self.reg, gate=lambda n, a: L.ALLOW,
                   max_turns=6, repair_threshold=2,
                   turn_sink=lambda r: repairs.append(r) if r.get("kind") == "plan_repair" else None)
        self.assertGreaterEqual(len(repairs), 1)
        self.assertTrue(seen["v"])

    def test_constraint_provider_resurfaces_into_context(self) -> None:
        # Renewal pillar 4 (arXiv 2604.11978, catastrophic forgetting): the loop
        # periodically re-injects long-range constraints so they stay in context.
        self.reg.register("noop", lambda a: "ok")
        seen = {"v": False}
        events = []
        calls = {"n": 0}

        def provider(goal, traj):
            return ["never touch prod DB", "keep PII local"]

        def sampler(history):
            if any(h.get("kind") == "constraint" for h in history):
                seen["v"] = True
            calls["n"] += 1
            if calls["n"] >= 5:
                return {"tool_calls": []}
            # vary args so the loop-detector doesn't fire before re-surfacing
            return {"tool_calls": [L.ToolCall("noop", {"i": calls["n"]}, call_id=f"c{calls['n']}")]}

        L.run_loop("task", sampler, self.reg, gate=lambda n, a: L.ALLOW, max_turns=8,
                   constraint_provider=provider, resurface_every=2,
                   turn_sink=lambda r: events.append(r) if r.get("kind") == "constraint_resurfaced" else None)
        self.assertGreaterEqual(len(events), 1)
        self.assertTrue(seen["v"])

    def test_finishes_when_model_emits_no_tool_call(self) -> None:
        r = L.run_loop("x", scripted([
            {"tool_calls": [L.ToolCall("aios_read", {"p": "1"}, call_id="c1")]},
            {"tool_calls": []},
        ]), self.reg)
        self.assertEqual(r["exit"], "model_finished")
        self.assertEqual(r["tool_calls"], 1)

    def test_reacts_to_a_failed_result_THE_difference_from_a_batch_executor(self) -> None:
        # tool errors on turn 1; the loop feeds the result back; the model (sampler)
        # SEES the error in history and changes course on turn 2 — impossible for a
        # single-pass step executor.
        self.reg.register("flaky", lambda a: (_ for _ in ()).throw(RuntimeError("boom")))
        seen_error = {"v": False}

        def sampler(history):
            last = history[-1]
            if last.get("role") == "user":
                return {"tool_calls": [L.ToolCall("flaky", {}, call_id="c1")]}
            if last.get("role") == "tool" and last.get("status") == "error":
                seen_error["v"] = True                       # the model observed the failure
                return {"tool_calls": [L.ToolCall("aios_read", {"p": "fallback"}, call_id="c2")]}
            return {"tool_calls": []}

        r = L.run_loop("recover", sampler, self.reg, gate=lambda n, a: L.ALLOW)
        self.assertTrue(seen_error["v"])                     # result was fed back
        self.assertEqual(r["exit"], "model_finished")
        tools = [t["tool"] for t in r["trajectory"]]
        self.assertEqual(tools, ["flaky", "aios_read"])      # it recovered

    def test_loop_detector_trips_on_repetition_named_exit(self) -> None:
        same = {"tool_calls": [L.ToolCall("aios_read", {"p": "same"}, call_id="c")]}
        r = L.run_loop("x", lambda h: same, self.reg, loop_threshold=3)
        self.assertEqual(r["exit"], "loop_detected")
        self.assertEqual(r["repeated"], "aios_read")

    def test_max_turns_cap(self) -> None:
        # distinct calls each turn (so the loop-detector does not trip first)
        n = {"i": 0}

        def sampler(h):
            n["i"] += 1
            return {"tool_calls": [L.ToolCall("aios_read", {"p": str(n["i"])}, call_id=f"c{n['i']}")]}
        r = L.run_loop("x", sampler, self.reg, max_turns=4)
        self.assertEqual(r["exit"], "max_turns")

    def test_gate_deny_blocks_dispatch(self) -> None:
        dispatched = {"v": False}
        self.reg.register("danger", lambda a: dispatched.__setitem__("v", True))
        r = L.run_loop("x", scripted([
            {"tool_calls": [L.ToolCall("danger", {}, call_id="c1")]},
            {"tool_calls": []},
        ]), self.reg, gate=lambda name, args: L.DENY)
        self.assertFalse(dispatched["v"])                    # never ran
        self.assertEqual(r["trajectory"][0]["status"], "denied")

    def test_gate_ask_escalates_as_typed_control(self) -> None:
        r = L.run_loop("x", scripted([
            {"tool_calls": [L.ToolCall("aios_write", {}, call_id="c1")]},
        ]), self.reg, gate=lambda name, args: L.ASK)
        self.assertEqual(r["exit"], "needs_approval")        # structured escalation, not prose
        self.assertEqual(r["pending"]["tool"], "aios_write")

    def test_unknown_tool_is_a_result_not_a_crash(self) -> None:
        r = L.run_loop("x", scripted([
            {"tool_calls": [L.ToolCall("nope", {}, call_id="c1")]},
            {"tool_calls": []},
        ]), self.reg, gate=lambda n, a: L.ALLOW)
        self.assertEqual(r["trajectory"][0]["status"], "unknown_tool")

    def test_trajectory_carries_no_content_only_names_and_status(self) -> None:
        import json
        r = L.run_loop("secret-goal", scripted([
            {"tool_calls": [L.ToolCall("aios_write", {"body": "AKIA_SECRET"}, call_id="c1")]},
            {"tool_calls": []},
        ]), self.reg, gate=lambda n, a: L.ALLOW)
        self.assertNotIn("AKIA_SECRET", json.dumps(r["trajectory"]))   # args never logged

    # -- GenesisOS direction hook tests --

    def test_needs_direction_on_loop_detected(self) -> None:
        outcome = {"exit": "loop_detected", "loop_type": "quick"}
        self.assertTrue(L.needs_direction(outcome))

    def test_needs_direction_on_doom_loop_type(self) -> None:
        outcome = {"exit": "max_turns", "loop_type": "doom_loop"}
        self.assertTrue(L.needs_direction(outcome))

    def test_needs_direction_false_on_react_code(self) -> None:
        outcome = {"exit": "max_turns", "loop_type": "react_code"}
        self.assertFalse(L.needs_direction(outcome))

    def test_needs_direction_false_on_model_finished(self) -> None:
        outcome = {"exit": "model_finished", "loop_type": "react_general"}
        self.assertFalse(L.needs_direction(outcome))

    # -- completion_audit tests (absorbed from OMX ralph.js) --

    def test_completion_audit_passes_when_write_tool_ok(self) -> None:
        """ralph pattern: model_finished + Write ok → audit.passed=True."""
        self.reg.register("Write", lambda a: "written")
        r = L.run_loop("write a file", scripted([
            {"tool_calls": [L.ToolCall("Write", {"path": "x"}, call_id="c1")]},
            {"tool_calls": []},
        ]), self.reg, gate=lambda n, a: L.ALLOW)
        self.assertEqual(r["exit"], "model_finished")
        audit = r.get("completion_audit", {})
        self.assertTrue(audit.get("passed"))
        self.assertEqual(audit["evidence_writes"], 1)
        self.assertEqual(audit["checklist_note"], "artifacts_produced")

    def test_completion_audit_fails_when_no_tools_used(self) -> None:
        r = L.run_loop("nothing", scripted([{"tool_calls": []}]), self.reg)
        audit = r.get("completion_audit", {})
        self.assertFalse(audit.get("passed"))
        self.assertEqual(audit["checklist_note"], "no_tool_evidence")

    def test_completion_audit_only_on_model_finished(self) -> None:
        """max_turns exit should not have completion_audit."""
        n = {"i": 0}
        def s(h):
            n["i"] += 1
            return {"tool_calls": [L.ToolCall("aios_read", {"p": str(n["i"])}, call_id=f"c{n['i']}")]}
        r = L.run_loop("x", s, self.reg, max_turns=2)
        self.assertEqual(r["exit"], "max_turns")
        self.assertNotIn("completion_audit", r)

    def test_loop_detected_injects_genesis_direction(self) -> None:
        """When doom-loop triggers, genesis_direction must appear in outcome."""
        r = L.run_loop("find bugs", scripted([
            {"tool_calls": [L.ToolCall("Bash", {"cmd": "ls"}, call_id="c1")]},
            {"tool_calls": [L.ToolCall("Bash", {"cmd": "ls"}, call_id="c2")]},
            {"tool_calls": [L.ToolCall("Bash", {"cmd": "ls"}, call_id="c3")]},
        ]), self.reg, gate=lambda n, a: L.ALLOW)
        self.assertEqual(r["exit"], "loop_detected")
        gd = r.get("genesis_direction")
        self.assertIsNotNone(gd, "genesis_direction must be injected on loop_detected")
        self.assertIn("branch", gd)
        self.assertIn("first_move", gd)
        self.assertEqual(gd.get("authority"), "advisory_only")


if __name__ == "__main__":
    unittest.main()
