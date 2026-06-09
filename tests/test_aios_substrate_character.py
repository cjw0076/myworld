"""Substrate character + automatic complementation (자가 공진): each substrate's weak
axis is auto-covered by whoever is strong, and who-is-strong is LEARNED from outcomes.
"""
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, (Path(__file__).resolve().parents[1] / "scripts").as_posix())

import aios_substrate_character as C


class ComplementTests(unittest.TestCase):
    def test_claude_weak_vision_is_covered_by_genesisos(self) -> None:
        # the founder's example: claude is weak at vision → GenesisOS compensates
        self.assertEqual(C.complement("claude", "vision"), "genesisos")

    def test_claude_strong_completion_needs_no_complement(self) -> None:
        self.assertIsNone(C.complement("claude", "completion"))

    def test_strongest_on_vision_is_the_divergence_organ(self) -> None:
        self.assertEqual(C.strongest("vision"), "genesisos")


class ResonancePlanTests(unittest.TestCase):
    def test_vision_task_auto_injects_compensator(self) -> None:
        plan = C.resonance_plan("claude", C.needed_dimensions("give me a big-picture vision and ideas"))
        self.assertIn("vision", plan["injected"])
        self.assertEqual(plan["injected"]["vision"], "genesisos")
        self.assertFalse(plan["self_sufficient"])

    def test_execution_task_is_self_sufficient_for_claude(self) -> None:
        plan = C.resonance_plan("claude", C.needed_dimensions("implement and finish the parser"))
        self.assertTrue(plan["self_sufficient"])

    def test_signal_to_dimension_mapping(self) -> None:
        self.assertIn("vision", C.needed_dimensions("what should our strategy be"))
        self.assertIn("rigor", C.needed_dimensions("verify and audit this"))
        self.assertIn("speed", C.needed_dimensions("a fast bulk pass"))


class SelfResonanceTests(unittest.TestCase):
    def test_failures_lower_and_successes_raise_the_profile(self) -> None:
        with tempfile.TemporaryDirectory() as t:
            store = Path(t) / "p.json"
            before = C.load_profiles(store)["claude"]["vision"]
            for _ in range(5):
                C.update_from_outcome("claude", "vision", False, store=store)
            after_fail = C.load_profiles(store)["claude"]["vision"]
            self.assertLess(after_fail, before)             # learned down
            for _ in range(8):
                C.update_from_outcome("local", "vision", True, store=store)
            self.assertGreater(C.load_profiles(store)["local"]["vision"], C.SEED["local"]["vision"])

    def test_learned_profiles_persist_over_seed(self) -> None:
        with tempfile.TemporaryDirectory() as t:
            store = Path(t) / "p.json"
            C.update_from_outcome("claude", "vision", True, store=store)
            # saved value (learned) must win over the seed on reload
            reloaded = C.load_profiles(store)["claude"]["vision"]
            self.assertNotEqual(reloaded, C.SEED["claude"]["vision"])

    def test_resonance_can_become_self_sufficient_after_learning(self) -> None:
        # if claude learns to be strong at vision, it stops needing the compensator
        with tempfile.TemporaryDirectory() as t:
            store = Path(t) / "p.json"
            for _ in range(30):
                C.update_from_outcome("claude", "vision", True, store=store)
            profiles = C.load_profiles(store)
            self.assertIsNone(C.complement("claude", "vision", profiles=profiles))


if __name__ == "__main__":
    unittest.main()
