"""Inter-agent packet envelope: correlation by call_id (not filename/order), threaded
lineage, typed control, and a named-exit lifecycle — the fix for the fragile file-bus.
"""
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, (Path(__file__).resolve().parents[1] / "scripts").as_posix())

import aios_packet as P


class EnvelopeTests(unittest.TestCase):
    def test_request_has_id_and_trace(self) -> None:
        r = P.new_request("claude@myworld", "hivemind", "commit_to_child_repo")
        self.assertTrue(r.id.startswith("req-"))
        self.assertTrue(r.trace_id.startswith("tr-"))

    def test_reply_correlates_and_shares_lineage(self) -> None:
        req = P.new_request("claude@myworld", "memoryOS", "accept_memory_draft")
        res = P.reply(req, "done")
        self.assertEqual(res.parent_id, req.id)        # correlated
        self.assertEqual(res.trace_id, req.trace_id)   # threaded lineage (DNA #5)

    def test_child_request_inherits_trace(self) -> None:
        parent = P.new_request("claude@myworld", "hivemind", "x")
        child = P.new_request("codex@hivemind", "memoryOS", "y", parent=parent)
        self.assertEqual(child.trace_id, parent.trace_id)
        self.assertEqual(child.parent_id, parent.id)

    def test_unknown_kind_rejected(self) -> None:
        req = P.new_request("a@b", "hivemind", "x")
        with self.assertRaises(ValueError):
            P.reply(req, "nonsense")


class CorrelationTests(unittest.TestCase):
    def test_matched_by_id_not_order(self) -> None:
        r1 = P.new_request("a@b", "hivemind", "act1", seq=1)
        r2 = P.new_request("a@b", "memoryOS", "act2", seq=2)
        res2 = P.reply(r2, "done", status="final")
        res1 = P.reply(r1, "blocked", status="pending")
        # results passed in REVERSE order — correlation must still match by id
        out = {c["request"]: c for c in P.correlate([r1, r2], [res2, res1])}
        self.assertEqual(out[r1.id]["reply"], "blocked")
        self.assertEqual(out[r2.id]["reply"], "done")

    def test_unanswered_request_is_pending(self) -> None:
        r = P.new_request("a@b", "hivemind", "act")
        self.assertEqual(P.correlate([r], [])[0]["status"], "pending")


class LifecycleTests(unittest.TestCase):
    def test_wait_status_named_exit(self) -> None:
        req = P.new_request("a@b", "hivemind", "act")
        self.assertEqual(P.wait_status(req.id, [], deadline_passed=False), "pending")
        self.assertEqual(P.wait_status(req.id, [], deadline_passed=True), "timed_out")  # not silent
        res = P.reply(req, "done", status="final")
        self.assertEqual(P.wait_status(req.id, [res]), "final")


class BusTests(unittest.TestCase):
    def test_write_read_roundtrip_keyed_by_id(self) -> None:
        with tempfile.TemporaryDirectory() as t:
            bus = Path(t)
            a = P.new_request("x@y", "hivemind", "act", seq=1)
            b = P.new_request("x@y", "hivemind", "act", seq=2)   # same action, different seq
            pa, pb = P.write_packet(a, bus=bus), P.write_packet(b, bus=bus)
            self.assertNotEqual(pa, pb)                  # collision-free filenames (vs order-clobber)
            got = {p.id for p in P.read_packets("hivemind", bus=bus)}
            self.assertEqual(got, {a.id, b.id})

    def test_packet_carries_no_inline_content(self) -> None:
        r = P.new_request("x@y", "hivemind", "act", payload_ref=".aios/run/123.json")
        self.assertNotIn("content", r.to_dict())         # only a ref, never the body
        self.assertEqual(r.payload_ref, ".aios/run/123.json")


class PerformativeTests(unittest.TestCase):
    def test_fipa_derived_and_challenge_are_valid(self) -> None:
        req = P.new_request("a@b", "GenesisOS", "propose_contract")
        for k in ("inform", "propose", "agree", "refuse", "failure", "challenge", "done"):
            self.assertEqual(P.reply(req, k).kind, k)   # all valid performatives

    def test_challenge_is_aios_novel_performative(self) -> None:
        # GenesisOS dissent as a first-class speech act — not in FIPA/A2A
        self.assertIn("challenge", P.KINDS)


class SparsityGateTests(unittest.TestCase):
    """The research's #1 finding encoded: over-communication is net-negative."""

    def test_control_always_passes(self) -> None:
        for k in ("ask", "blocked", "failure", "done", "challenge", "request"):
            self.assertTrue(P.should_communicate(k))

    def test_redundant_inform_is_suppressed(self) -> None:
        self.assertFalse(P.should_communicate("inform", redundant=True))
        self.assertFalse(P.should_communicate("inform", novel=False))

    def test_novel_inform_passes(self) -> None:
        self.assertTrue(P.should_communicate("inform", novel=True, redundant=False))


class CalibrationTests(unittest.TestCase):
    def test_with_calibration_attaches_confidence_and_provenance(self) -> None:
        req = P.new_request("codex@hivemind", "memoryOS", "accept_memory_draft")
        res = P.with_calibration(P.reply(req, "inform"), 0.7, evidence_ref=".aios/r.json")
        self.assertEqual(res.confidence, 0.7)
        self.assertEqual(res.evidence_ref, ".aios/r.json")
        self.assertNotIn("content", res.to_dict())     # still ref/scalar only, no body

    def test_default_confidence_unstated(self) -> None:
        self.assertEqual(P.new_request("a@b", "hivemind", "x").confidence, -1.0)


class A2ABridgeTests(unittest.TestCase):
    def test_bridge_field_names(self) -> None:
        req = P.new_request("claude@myworld", "hivemind", "commit_to_child_repo")
        a = P.to_a2a(req)
        self.assertEqual(a["taskId"], req.id)
        self.assertEqual(a["contextId"], req.trace_id)

    def test_blocked_maps_to_input_required(self) -> None:
        req = P.new_request("a@b", "hivemind", "x")
        self.assertEqual(P.to_a2a(P.reply(req, "blocked", status="pending"))["state"], "input_required")

    def test_final_maps_to_completed(self) -> None:
        req = P.new_request("a@b", "hivemind", "x")
        self.assertEqual(P.to_a2a(P.reply(req, "done", status="final"))["state"], "completed")


if __name__ == "__main__":
    unittest.main()
