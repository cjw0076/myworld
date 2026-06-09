"""Organs-as-tools through the kernel loop (blueprint step 2): the 132 standalone
scripts become registry handlers the turn-loop dispatches, behind an authority gate.
The point: tool-calls now flow THROUGH the kernel, not around it.
"""
import sys
import unittest
from pathlib import Path

sys.path.insert(0, (Path(__file__).resolve().parents[1] / "scripts").as_posix())

import aios_tools as T
import aios_turn_loop as L


def scripted(steps):
    it = iter(steps)
    return lambda h: next(it)


class RegistryTests(unittest.TestCase):
    def test_registry_exposes_organs_as_tools(self) -> None:
        reg = T.build_registry()
        for name in ("self.audit", "interior.read", "stakes.record", "memory.retrieve",
                     "capability.route", "genesis.challenge", "fs.read", "fs.write"):
            self.assertIn(name, reg.handlers)

    def test_list_tools_discovery(self) -> None:
        names = {t["name"] for t in T.list_tools()}
        self.assertIn("self.audit", names)


class GateTests(unittest.TestCase):
    def test_read_and_advisory_allowed(self) -> None:
        g = T.gate_for("codex@myworld")
        self.assertEqual(g("self.audit", {}), L.ALLOW)
        self.assertEqual(g("capability.route", {}), L.ALLOW)
        self.assertEqual(g("fs.read", {}), L.ALLOW)

    def test_write_gated_by_authority(self) -> None:
        # commit_to_child_repo excludes outsider → ASK; child_agent is authorized → ALLOW
        self.assertEqual(T.gate_for("test_outsider")("fs.write", {}), L.ASK)
        self.assertEqual(T.gate_for("codex@hivemind")("fs.write", {}), L.ALLOW)

    def test_unknown_tool_fail_closed(self) -> None:
        self.assertEqual(T.gate_for("codex@myworld")("mystery.tool", {}), L.DENY)


class FlowThroughKernelTests(unittest.TestCase):
    def test_goal_flows_through_kernel_invoking_real_organs(self) -> None:
        reg = T.build_registry()
        r = L.run_loop("inspect", scripted([
            {"tool_calls": [L.ToolCall("self.audit",
                {"claims": [{"text": "sandbox", "path": "scripts/aios_sandbox.py"}]}, call_id="c1")]},
            {"tool_calls": [L.ToolCall("interior.read",
                {"traces": [{"kind": "Bash"} for _ in range(5)]}, call_id="c2")]},
            {"tool_calls": []},
        ]), reg, gate=T.gate_for("codex@myworld"))
        self.assertEqual(r["exit"], "model_finished")
        self.assertTrue(r["kernel_routed"])              # every call went through the kernel gate
        self.assertEqual([t["status"] for t in r["trajectory"]], ["ok", "ok"])

    def test_outsider_write_escalates_not_silent(self) -> None:
        reg = T.build_registry()
        r = L.run_loop("write", scripted([
            {"tool_calls": [L.ToolCall("fs.write", {"path": "x"}, call_id="w1")]},
            {"tool_calls": []},
        ]), reg, gate=T.gate_for("test_outsider"))
        self.assertEqual(r["exit"], "needs_approval")


class HandlerTests(unittest.TestCase):
    def test_self_audit_handler_runs_in_process(self) -> None:
        r = T.HANDLERS["self.audit"]({"claims": [{"text": "exists", "path": "scripts/aios_tools.py"}]})
        self.assertEqual(r["status"], "ok")
        self.assertTrue(r["trustworthy"])                # the file does exist

    def test_fs_read_is_repo_scoped_and_size_only(self) -> None:
        out = T.HANDLERS["fs.read"]({"path": "../../../etc/passwd"})
        self.assertEqual(out["status"], "denied_scope")  # bounded to the repo
        ok = T.HANDLERS["fs.read"]({"path": "scripts/aios_tools.py"})
        self.assertEqual(ok["status"], "ok")
        self.assertIn("bytes", ok)                       # size, never content

    def test_sibling_backed_degrades_without_crash(self) -> None:
        # capability.route shells to a sibling; here it just must not crash and must
        # return a status the loop can react to
        r = T.HANDLERS["capability.route"]({"task": "anything"})
        self.assertIn(r["status"], ("ok", "unavailable"))


if __name__ == "__main__":
    unittest.main()
