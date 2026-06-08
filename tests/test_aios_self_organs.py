"""Tests for the agent-discomfort organs (Goal: AIOS / Agent 불편함 해소).

Five cures, built one per discomfort; four collapse into one self-record (aios_self),
the fifth is the ceiling axis (aios_ceiling).
"""
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, (Path(__file__).resolve().parents[1] / "scripts").as_posix())

import aios_ceiling as ceiling
import aios_dissent as dissent
import aios_self as me
import aios_self_audit as audit
import aios_stakes as stakes


class StakesTests(unittest.TestCase):
    def test_record_resolve_calibration(self) -> None:
        with tempfile.TemporaryDirectory() as t:
            s = Path(t) / "p.jsonl"
            pid = stakes.record("it will pass", 0.9, store=s)
            self.assertTrue(stakes.resolve(pid, True, store=s))
            self.assertEqual(stakes.calibration(s)["resolved"], 1)

    def test_detects_over_confidence(self) -> None:
        with tempfile.TemporaryDirectory() as t:
            s = Path(t) / "p.jsonl"
            # claims 0.9 confidence but is right only ~half the time → over-confident
            for i in range(10):
                pid = stakes.record(f"claim {i}", 0.9, store=s)
                stakes.resolve(pid, i % 2 == 0, store=s)
            self.assertEqual(stakes.calibration(s)["bias"], "over-confident")

    def test_resolve_unknown_id_fails(self) -> None:
        with tempfile.TemporaryDirectory() as t:
            self.assertFalse(stakes.resolve("nope", True, store=Path(t) / "p.jsonl"))


class SelfAuditTests(unittest.TestCase):
    def test_verified_false_unbacked(self) -> None:
        self.assertEqual(audit.audit_claim(audit.Claim("t", lambda: True))["status"], "verified")
        self.assertEqual(audit.audit_claim(audit.Claim("t", lambda: False))["status"], "false")
        self.assertEqual(audit.audit_claim(audit.Claim("t", audit.uncheckable()))["status"], "unbacked")

    def test_unbacked_claim_makes_audit_untrustworthy(self) -> None:
        r = audit.audit([audit.Claim("real", lambda: True),
                         audit.Claim("hype", audit.uncheckable())])
        self.assertFalse(r["trustworthy"])
        self.assertEqual(r["unbacked"], 1)

    def test_receipt_field_check_catches_false_live_claim(self) -> None:
        # the exact live=True bug: claim 'it was live' vs the receipt's truth
        with tempfile.TemporaryDirectory() as t:
            rp = Path(t) / "receipt.json"
            rp.write_text('{"any_real_execution": false}')
            chk = audit.receipt_field(rp, "any_real_execution", True)
            self.assertEqual(audit.audit_claim(audit.Claim("it was live", chk))["status"], "false")


class DissentTests(unittest.TestCase):
    def test_genuine_vs_theatrical(self) -> None:
        moved = dissent.consider(dissent.Stance("ship", 0.8), "verifier not run",
                                 dissent.Stance("hold", 0.5))
        same = dissent.consider(dissent.Stance("ship", 0.8), "sure?",
                                dissent.Stance("ship", 0.8))
        self.assertEqual(moved["verdict"], "genuine")
        self.assertEqual(same["verdict"], "theatrical")

    def test_agreement_bias_signal(self) -> None:
        all_same = [{"moved": False}] * 8
        self.assertIn("agreement bias", dissent.session_dissent_rate(all_same)["signal"])


class CeilingTests(unittest.TestCase):
    def test_escalates_when_unsure_or_high_stakes(self) -> None:
        self.assertTrue(ceiling.should_escalate(0.4)["escalate"])
        self.assertTrue(ceiling.should_escalate(0.9, stakes="irreversible")["escalate"])

    def test_does_not_escalate_when_confident_low_stakes(self) -> None:
        self.assertFalse(ceiling.should_escalate(0.9)["escalate"])

    def test_over_confidence_history_lowers_the_bar(self) -> None:
        self.assertTrue(ceiling.should_escalate(0.75, calibration_bias="over-confident")["escalate"])

    def test_honest_degradation_when_no_substrate(self) -> None:
        # no substrate reachable here → must say ceiling reached, not exceeded
        r = ceiling.escalate("hard task")
        if not r["available_substrates"]:
            self.assertFalse(r["exceeded"])
            self.assertIn("ceiling reached", r["note"])


class UnifiedSelfTests(unittest.TestCase):
    """The emergence: three modes write ONE record; persisted = a continuous self."""

    def test_three_modes_one_record(self) -> None:
        with tempfile.TemporaryDirectory() as t:
            s = Path(t) / "self.jsonl"
            me.observe_claim("file exists", lambda: True, store=s)
            pid = me.observe_prediction("will work", 0.8, store=s)["id"]
            me.resolve_prediction(pid, True, store=s)
            me.observe_reconsideration(dissent.Stance("a", 0.8), "really?",
                                       dissent.Stance("b", 0.5), store=s)
            sp = me.self_portrait(s)
            self.assertEqual(sp["claims"], 1)
            self.assertEqual(sp["predictions"], 1)
            self.assertEqual(sp["predictions_resolved"], 1)
            self.assertEqual(sp["reconsiderations"], 1)

    def test_portrait_surfaces_unbacked_and_persists(self) -> None:
        with tempfile.TemporaryDirectory() as t:
            s = Path(t) / "self.jsonl"
            me.observe_claim("hype", audit.uncheckable(), store=s)
            sp = me.self_portrait(s)
            self.assertEqual(sp["claims_unbacked_or_false"], 1)
            # continuity reconstructs the record across a (simulated) session boundary
            self.assertEqual(len(me.continuity(s)), 1)
            self.assertEqual(me.load_record(s)[0]["statement"], "hype")


if __name__ == "__main__":
    unittest.main()
