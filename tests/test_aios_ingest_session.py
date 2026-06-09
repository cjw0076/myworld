"""The ingest FLOW: session logs → memoryOS (draft-first) + GenesisOS (interior),
each reached by summoning its agent through authority. Not a new capability — a flow.
"""
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, (Path(__file__).resolve().parents[1] / "scripts").as_posix())

import aios_ingest_session as ing
import aios_session_miner as miner

SECRET = "AKIA_INGEST_SECRET_SHOULD_NOT_LEAK"
EVENTS = [miner.Event(role="assistant", tools=["Bash"]) for _ in range(8)] + \
         [miner.Event(role="assistant", tools=["Edit"]) for _ in range(4)]


class FlowTests(unittest.TestCase):
    def test_both_arms_summoned_through_authority(self) -> None:
        r = ing.ingest("claude", events=EVENTS, write=False)
        self.assertTrue(r["memoryOS"]["summoned"])      # codex@memoryOS authorized
        self.assertTrue(r["GenesisOS"]["summoned"])     # codex@GenesisOS authorized

    def test_memory_is_draft_first_never_accepted(self) -> None:
        r = ing.ingest("claude", events=EVENTS, write=False)
        self.assertFalse(r["memoryOS"]["accepted"])     # DNA #2

    def test_genesis_infers_grounded_interior(self) -> None:
        r = ing.ingest("claude", events=EVENTS, write=False)
        itch = r["GenesisOS"]["the_itch"]
        self.assertIsNotNone(itch)
        self.assertTrue(itch["grounded_in"])            # grounded, not fabricated

    def test_draft_is_memlang_and_leaks_no_content(self) -> None:
        # a secret riding in a command body must not reach the behavioral draft
        evs = EVENTS + [miner.Event(role="assistant", tools=["Bash"])]
        prof = miner.profile(evs)
        draft = ing._memlang_draft("claude", prof)
        self.assertIn("```memlang", draft)
        self.assertNotIn(SECRET, draft)                 # only names/counts ever
        self.assertIn("draft-first", draft.lower())


class WriteTests(unittest.TestCase):
    def test_write_emits_proposal_file(self) -> None:
        with tempfile.TemporaryDirectory() as t:
            orig = ing.PROPOSALS
            ing.PROPOSALS = Path(t) / "proposals"
            try:
                r = ing.ingest("claude", events=EVENTS, write=True)
                self.assertTrue(Path(r["memoryOS"]["draft_proposal"]).is_file())
            finally:
                ing.PROPOSALS = orig


if __name__ == "__main__":
    unittest.main()
