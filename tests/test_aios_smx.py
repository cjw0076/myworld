import json
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, (Path(__file__).resolve().parents[1] / "scripts").as_posix())

import aios_smx as smx


def U(id, **kw):
    return smx.Universe(id, kw.pop("branch_type", "baseline"), **kw)


class ScoreTests(unittest.TestCase):
    def test_verified_beats_unverified(self) -> None:
        self.assertGreater(smx.score_universe(U("a", verified_ok=True)),
                           smx.score_universe(U("b", verified_ok=False)))

    def test_smaller_blast_radius_wins(self) -> None:
        small = U("a", verified_ok=True, files_touched=["x"])
        big = U("b", verified_ok=True, files_touched=["x", "y", "z", "w"])
        self.assertGreater(smx.score_universe(small), smx.score_universe(big))

    def test_fewer_reverts_wins(self) -> None:
        self.assertGreater(smx.score_universe(U("a", verified_ok=True, reverts=0)),
                           smx.score_universe(U("b", verified_ok=True, reverts=3)))

    def test_dryrun_cannot_outrank_real_verified(self) -> None:
        dry = U("dry", verified_ok=True, files_touched=[], executed=False)
        real = U("real", verified_ok=True, files_touched=["a"], executed=True)
        self.assertGreater(smx.score_universe(real), smx.score_universe(dry))


class SelectTests(unittest.TestCase):
    def test_picks_highest(self) -> None:
        us = [U("a", verified_ok=False),
              U("b", verified_ok=True, files_touched=["x"]),
              U("c", verified_ok=True, files_touched=["x", "y", "z"])]
        self.assertEqual(smx.select_winner(us).id, "b")

    def test_empty_returns_none(self) -> None:
        self.assertIsNone(smx.select_winner([]))

    def test_deterministic_tiebreak(self) -> None:
        us = [U("a", verified_ok=True), U("b", verified_ok=True)]
        self.assertEqual(smx.select_winner(us).id, smx.select_winner(list(reversed(us))).id)


class MultiverseTests(unittest.TestCase):
    def test_winner_applied_losers_to_counterfactual(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            applied = []
            us = [U("win", verified_ok=True, files_touched=["a"]),
                  U("lose1", verified_ok=False),
                  U("lose2", verified_ok=True, files_touched=["a", "b", "c", "d"])]
            r = smx.run_multiverse(us, apply_fn=lambda u: applied.append(u.id),
                                   cf_dir=Path(tmp))
            self.assertEqual(r["winner"], "win")
            self.assertEqual(applied, ["win"])          # ONLY the winner applied
            self.assertTrue(r["winner_applied"])
            self.assertEqual(r["counterfactuals"], 2)    # both losers kept
            cf = json.loads(Path(r["counterfactual_ref"]).read_text())
            ids = {e["id"] for e in cf["episodes"]}
            self.assertEqual(ids, {"lose1", "lose2"})
            # the unverified loser records the honest reason
            byid = {e["id"]: e for e in cf["episodes"]}
            self.assertIn("failed verification", byid["lose1"]["why_not_chosen"])

    def test_unverified_winner_not_applied(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            applied = []
            us = [U("a", verified_ok=False), U("b", verified_ok=False)]
            r = smx.run_multiverse(us, apply_fn=lambda u: applied.append(u.id), cf_dir=Path(tmp))
            self.assertFalse(r["winner_applied"])        # nothing verified → nothing applied
            self.assertEqual(applied, [])

    def test_dryrun_universe_not_applied(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            applied = []
            us = [U("dry", verified_ok=True, executed=False)]  # isolation unavailable
            r = smx.run_multiverse(us, apply_fn=lambda u: applied.append(u.id), cf_dir=Path(tmp))
            self.assertEqual(applied, [])                 # dry-run never silently applied
            self.assertFalse(r["any_real_execution"])


class SandboxExecutorTests(unittest.TestCase):
    def test_executor_degrades_gracefully_when_isolation_unavailable(self) -> None:
        # uses the real sandbox; in this env isolation is blocked → must dry-run,
        # never silently run unsandboxed
        with tempfile.TemporaryDirectory() as ws:
            execute = smx.sandboxed_universe_executor(ws, lambda u: ["sh", "-c", "echo hi"])
            u = execute(U("x", verified_ok=True))
            import aios_sandbox as sb
            if sb.sandbox_self_test().get("isolated"):
                self.assertTrue(u.executed)               # capable host: really ran
            else:
                self.assertFalse(u.executed)              # restricted: honest dry-run
                self.assertIn("dry-run", u.note)


if __name__ == "__main__":
    unittest.main()
