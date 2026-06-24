from __future__ import annotations

import importlib.util
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SCRIPTS = ROOT / "scripts"


def _load():
    spec = importlib.util.spec_from_file_location("aios_agent_system_uut", SCRIPTS / "aios_agent_system.py")
    m = importlib.util.module_from_spec(spec)
    sys.modules["aios_agent_system_uut"] = m
    if str(SCRIPTS) not in sys.path:
        sys.path.insert(0, str(SCRIPTS))
    spec.loader.exec_module(m)
    return m


SECRET_GOAL = "deploy prod with token sk-LIVE-9f3a and email me at ceo@corp.com about /dain/private"


class GlobalPayloadPrivacyTest(unittest.TestCase):
    """P0: the raw goal/prompt must NEVER reach the global Akashic worker."""

    def setUp(self):
        self.m = _load()
        self.captured = []
        # intercept the network boundary
        self.m._akashic_post = lambda path, payload, *a, **k: (
            self.captured.append((path, payload)) or {"results": [], "predictions": []})

    def _assert_no_goal(self, payload):
        blob = str(payload)
        for leak in ("sk-LIVE-9f3a", "ceo@corp.com", "/dain/private", "deploy prod"):
            self.assertNotIn(leak, blob, f"raw-goal leak in global payload: {leak}")

    def test_contribute_sends_no_raw_goal(self):
        self.m.contribute(SECRET_GOAL, ["Bash", "Edit"], "claude", 1.0)
        path, payload = self.captured[-1]
        self.assertEqual(path, "/contribute")
        self._assert_no_goal(payload)
        self.assertIn("category:", payload["content"])      # structural summary only
        self.assertIn("tools:", payload["content"])

    def test_recall_sends_no_raw_goal(self):
        self.m.recall(SECRET_GOAL)
        path, payload = self.captured[-1]
        self.assertEqual(path, "/sync")
        self._assert_no_goal(payload)

    def test_predict_sends_no_raw_goal(self):
        self.m.predict(SECRET_GOAL)
        path, payload = self.captured[-1]
        self.assertEqual(path, "/predict")
        self._assert_no_goal(payload)

    def test_safe_summary_is_structural_only(self):
        s = self.m._safe_summary("code", ["Bash", "Read"], "react_code")
        self.assertEqual(s, "category:code tools:Bash,Read pattern:react_code")


if __name__ == "__main__":
    unittest.main()
