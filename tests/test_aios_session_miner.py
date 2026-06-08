"""Session-log miner — behavioral extraction with a hard privacy invariant.

The load-bearing test: a secret embedded in a tool argument/command body must NEVER
appear anywhere in the miner's output (DNA #7). The miner reads names/timing/counts
only, never content.
"""
import json
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, (Path(__file__).resolve().parents[1] / "scripts").as_posix())

import aios_session_miner as m

SECRET = "AKIA_SUPER_SECRET_KEY_DO_NOT_LEAK_42"


def _claude_log(path: Path) -> None:
    lines = [
        {"type": "assistant", "timestamp": "t1", "message": {"content": [
            {"type": "tool_use", "name": "Bash",
             "input": {"command": f"export TOKEN={SECRET} && do_thing"}}]}},
        {"type": "user", "timestamp": "t2", "message": {"content": [
            {"type": "tool_result", "is_error": True, "content": f"failed with {SECRET}"}]}},
        {"type": "assistant", "timestamp": "t3", "message": {"content": [
            {"type": "tool_use", "name": "Edit", "input": {"file_path": f"/secret/{SECRET}.py"}}]}},
    ]
    path.write_text("\n".join(json.dumps(x) for x in lines))


class PrivacyTests(unittest.TestCase):
    def test_secret_in_args_never_appears_in_output(self) -> None:
        with tempfile.TemporaryDirectory() as t:
            log = Path(t) / "s.jsonl"
            _claude_log(log)
            events = m.parse_claude_log(log)
            prof = m.profile(events)
            blob = json.dumps(prof) + json.dumps([e.__dict__ for e in events])
            self.assertNotIn(SECRET, blob)        # the hard invariant — no content leaks
            # but behavior WAS captured (names only)
            self.assertIn("Bash", prof["tool_histogram"])
            self.assertIn("Edit", prof["tool_histogram"])


class ParseTests(unittest.TestCase):
    def test_claude_tools_and_error_extracted(self) -> None:
        with tempfile.TemporaryDirectory() as t:
            log = Path(t) / "s.jsonl"
            _claude_log(log)
            events = m.parse_claude_log(log)
            self.assertEqual(events[0].tools, ["Bash"])
            self.assertTrue(events[1].had_error)

    def test_profile_recovery_and_sequences(self) -> None:
        # error then a tool action = a recovery; sequence n-grams captured
        evs = [m.Event(role="assistant", tools=["Bash"]),
               m.Event(role="user", had_error=True),
               m.Event(role="assistant", tools=["Edit"]),
               m.Event(role="assistant", tools=["Bash"])]
        prof = m.profile(evs)
        self.assertEqual(prof["errors"], 1)
        self.assertEqual(prof["recoveries"], 1)         # Edit right after the error
        self.assertEqual(prof["recovery_rate"], 1.0)


class SystematizationTests(unittest.TestCase):
    def test_frequent_sequence_becomes_candidate(self) -> None:
        evs = [m.Event(role="assistant", tools=["Bash"]) for _ in range(10)]
        prof = m.profile(evs)
        cands = m.systematization_candidates(prof, min_count=3)
        self.assertTrue(cands)
        self.assertIn("Bash", cands[0]["pattern"])


if __name__ == "__main__":
    unittest.main()
