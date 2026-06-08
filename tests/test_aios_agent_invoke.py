"""Per-OS agent activation — head-on through the authority skeleton, not bypassing it.

The load-bearing test: an agent the registry does not authorize for its domain is
REFUSED, not waved through.
"""
import sys
import unittest
from pathlib import Path

sys.path.insert(0, (Path(__file__).resolve().parents[1] / "scripts").as_posix())

import aios_agent_invoke as inv


class SummonAuthorityTests(unittest.TestCase):
    def test_authorized_agent_is_summoned(self) -> None:
        r = inv.summon("hivemind", "run tests", "on_call",
                       identity="codex@hivemind", write_receipt=False)
        self.assertTrue(r["summoned"])
        self.assertIn("child_agent", r["citizenship"])

    def test_unauthorized_identity_is_refused_not_bypassed(self) -> None:
        # the whole point of "정면으로": an outsider cannot be summoned to an operator action
        r = inv.summon("myworld", "release dispatch", "on_call",
                       identity="test_outsider", write_receipt=False)
        self.assertFalse(r["summoned"])
        self.assertIn("requires_citizenship", r["reason"])

    def test_unknown_os_not_summoned(self) -> None:
        self.assertFalse(inv.summon("nope", "x", "on_call", write_receipt=False)["summoned"])


class RoutingTests(unittest.TestCase):
    def test_execution_task_routes_to_hivemind(self) -> None:
        r = inv.route_call("run the regression tests and apply the patch", write_receipt=False)
        self.assertEqual(r["os"], "hivemind")

    def test_no_domain_match_returns_none(self) -> None:
        self.assertIsNone(inv.route_call("xyzzy plugh", write_receipt=False))


class SelfInterventionTests(unittest.TestCase):
    def test_genesis_and_memory_raise_hands_on_their_signals(self) -> None:
        acts = inv.self_interventions("should we just assume the prior decision holds",
                                      write_receipt=False)
        by_os = {a["os"]: a for a in acts}
        self.assertIn("GenesisOS", by_os)         # 'assume' / 'should we just'
        self.assertIn("memoryOS", by_os)          # 'prior'
        self.assertTrue(by_os["GenesisOS"]["intervene_because"])

    def test_no_signal_no_intervention(self) -> None:
        self.assertEqual(inv.self_interventions("a calm neutral sentence", write_receipt=False), [])


class SessionStartTests(unittest.TestCase):
    def test_default_wakes_recall_and_challenge(self) -> None:
        woken = {a["os"] for a in inv.on_session_start("")}
        self.assertEqual(woken, {"memoryOS", "GenesisOS"})

    def test_execution_context_wakes_hivemind(self) -> None:
        woken = {a["os"] for a in inv.on_session_start("we will build and deploy the runtime")}
        self.assertIn("hivemind", woken)


if __name__ == "__main__":
    unittest.main()
