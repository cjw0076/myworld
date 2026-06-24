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


class GlobalBoundaryPrivacyTest(unittest.TestCase):
    """Repo-wide DNA #7 guard: monkeypatch the urllib egress boundary and drive EVERY
    outbound-to-global entrypoint (not just aios_agent_system), asserting the raw goal
    never appears in any request body. Closes the false-green gap from the first fix."""

    LEAKS = ("sk-LIVE-9f3a", "ceo@corp.com", "/dain/private", "deploy prod")

    def setUp(self):
        if str(SCRIPTS) not in sys.path:
            sys.path.insert(0, str(SCRIPTS))
        self.bodies = []
        import urllib.request as ur
        self._orig = ur.urlopen

        class _Resp:
            def __enter__(self_): return self_
            def __exit__(self_, *a): return False
            def read(self_): return b'{"results":[],"predictions":[],"status":"ok"}'

        def _fake(req, *a, **k):
            try:
                url = req.full_url if hasattr(req, "full_url") else str(req)
                # only OFF-DEVICE (egress) calls matter for DNA #7; localhost embedders
                # (ollama/LM Studio/vLLM) are on-device and may see raw content.
                host = url.split("://", 1)[-1].split("/", 1)[0]
                if not any(h in host for h in ("localhost", "127.0.0.1", "0.0.0.0")):
                    self.bodies.append(getattr(req, "data", b"") or b"")
            except Exception:
                pass
            return _Resp()
        ur.urlopen = _fake
        self._ur = ur

    def tearDown(self):
        self._ur.urlopen = self._orig

    def _assert_clean(self, require_call=True):
        blob = b" ".join(self.bodies).decode("utf-8", "replace")
        if require_call:
            self.assertTrue(self.bodies, "no off-device call captured")
        for leak in self.LEAKS:
            self.assertNotIn(leak, blob, f"raw-goal leak at egress boundary: {leak}")

    def test_aios_memory_contribute_run_no_leak(self):
        import aios_memory as M
        M.contribute_run(SECRET_GOAL, {"tool_sequence": ["Bash", "Edit"], "exit": "model_finished",
                                       "loop_type": "react_code"}, api_key="k")
        self._assert_clean()

    def test_behavior_contribute_to_global_no_leak(self):
        import aios_agent_behavior as B
        # a memory whose stored content is a raw goal must still not leak (rebuilt structurally)
        mem = {"id": "x1", "content": SECRET_GOAL, "category": "code",
               "top_tools": ["Bash", "Edit"], "tool_freq": {"Bash": 2}, "loop_type": "react_code"}
        B.contribute_to_global(memories=[mem], api_key="k")
        self._assert_clean()

    def test_behavior_predict_global_query_no_leak(self):
        import aios_agent_behavior as B
        B.predict_behavior(SECRET_GOAL, ["Bash", "Edit", "Read"], use_global=True)
        self._assert_clean()


if __name__ == "__main__":
    unittest.main()
