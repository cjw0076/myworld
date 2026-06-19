import sys
import unittest
from pathlib import Path

sys.path.insert(0, (Path(__file__).resolve().parents[1] / "scripts").as_posix())

import aios_demo as d


class RunDemoTests(unittest.TestCase):
    def test_good_plan_passes(self) -> None:
        good = next(c for c in d.run_demo()["checks"] if c["plan"] == "good")
        self.assertTrue(good["verification"]["ok"])
        self.assertEqual(good["verification"]["violations"], [])

    def test_slipped_plan_is_caught_with_specific_violation(self) -> None:
        slipped = next(c for c in d.run_demo()["checks"] if c["plan"] == "slipped")
        v = slipped["verification"]
        self.assertFalse(v["ok"])
        # the demo's whole point: the checker names exactly what's wrong
        self.assertEqual(len(v["violations"]), 1)
        viol = v["violations"][0]
        self.assertEqual(viol["course"], "Database Systems")
        self.assertIn("AFTER", viol["issue"])

    def test_demo_ok_is_the_honesty_gate(self) -> None:
        # demo_ok must be True ONLY when good passes AND slipped is caught
        self.assertTrue(d.run_demo()["demo_ok"])

    def test_deterministic_no_clock(self) -> None:
        # same fixed scenario every run — no Date.now / randomness
        self.assertEqual(d.run_demo(), d.run_demo())

    def test_no_network_or_model_in_run_demo(self) -> None:
        # run_demo must not import/route through the LLM substrate — pure verifier
        result = d.run_demo()
        self.assertIn("no model", result["provenance"])


class CliTests(unittest.TestCase):
    def test_main_json_returns_zero_and_skips_receipt(self) -> None:
        rc = d.main(["--json", "--no-receipt"])
        self.assertEqual(rc, 0)

    def test_main_human_returns_zero(self) -> None:
        rc = d.main(["--no-receipt"])
        self.assertEqual(rc, 0)


class ChatModeUnitTests(unittest.TestCase):
    """Unit tests for run_chat / narrate_chat that never touch a live provider."""

    def test_narrate_chat_ok_path(self) -> None:
        fake = {
            "ok": True,
            "goal": "Test goal",
            "provider_used": "test_provider",
            "final_answer": "A test answer.",
            "memory_hits": 2,
            "memory_status": "hit",
            "turns": 3,
            "exit": "max_turns",
        }
        out = d.narrate_chat(fake)
        self.assertIn("AIOS demo --chat", out)
        self.assertIn("test_provider", out)
        self.assertIn("2 hit(s)", out)
        self.assertIn("A test answer.", out)
        self.assertIn("preamble → loop → synthesis", out)

    def test_narrate_chat_error_path(self) -> None:
        fake = {"ok": False, "error": "No provider available."}
        out = d.narrate_chat(fake)
        self.assertIn("ERROR", out)
        self.assertIn("No provider available.", out)

    def test_chat_goal_constant_is_non_empty(self) -> None:
        self.assertIsInstance(d.CHAT_GOAL, str)
        self.assertGreater(len(d.CHAT_GOAL), 10)

    def test_import_head_returns_module_with_run_organic_goal(self) -> None:
        head = d._import_head()
        self.assertTrue(callable(getattr(head, "run_organic_goal", None)))

    def test_build_parser_has_chat_and_goal_flags(self) -> None:
        p = d.build_parser()
        parsed = p.parse_args(["--chat", "--goal", "hello?"])
        self.assertTrue(parsed.chat)
        self.assertEqual(parsed.goal, "hello?")

    def test_main_chat_json_no_provider(self) -> None:
        """When no provider is available, main --chat exits 1 gracefully."""
        import os, unittest.mock as mock
        # Patch all three availability checks to return False
        head = d._import_head()
        adapters_mod = head._load("aios_adapters")
        with mock.patch.object(adapters_mod, "_ollama_rest_available", return_value=False), \
             mock.patch.object(adapters_mod, "_gemini_rest_available", return_value=False), \
             mock.patch.object(adapters_mod, "_anthropic_rest_available", return_value=False):
            result = d.run_chat()
        self.assertFalse(result.get("ok"))
        self.assertIn("No provider available", result.get("error", ""))


if __name__ == "__main__":
    unittest.main()
