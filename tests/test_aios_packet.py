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


if __name__ == "__main__":
    unittest.main()
