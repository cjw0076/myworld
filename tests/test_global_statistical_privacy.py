"""Tests for the statistical fingerprint / k-anonymity privacy closure.

The global payload (sent to /contribute on the Akashic worker) must NOT
contain:
  (a) a numeric tool_freq distribution (tool: count dict) — that distribution
      is a per-tenant fingerprint re-identifiable via joint frequency analysis.
  (b) more than 3 tool names (top-3 names only, presence-only).
  (c) arg_skeletons (already forbidden by the lexical guard, confirmed here).

These tests cover all three global contribute paths:
  1. aios_agent_behavior.contribute_to_global
  2. aios_agent_system.contribute
  3. aios_memory.contribute_run
"""
from __future__ import annotations

import importlib.util
import json
import sys
import unittest
import urllib.request
from pathlib import Path

ROOT    = Path(__file__).resolve().parent.parent
SCRIPTS = ROOT / "scripts"


def _load(name: str, alias: str | None = None):
    alias = alias or name
    if str(SCRIPTS) not in sys.path:
        sys.path.insert(0, str(SCRIPTS))
    spec = importlib.util.spec_from_file_location(alias, SCRIPTS / f"{name}.py")
    m = importlib.util.module_from_spec(spec)
    sys.modules[alias] = m
    spec.loader.exec_module(m)
    return m


class _NetworkCapture:
    """Context manager that intercepts urllib.request.urlopen and records
    the decoded body of every off-device (non-localhost) POST."""

    def __init__(self):
        self.bodies: list[dict] = []

    def __enter__(self):
        import urllib.request as ur
        self._orig = ur.urlopen
        capture = self.bodies

        class _Resp:
            def __enter__(self_): return self_
            def __exit__(self_, *a): return False
            def read(self_):
                return b'{"results":[],"predictions":[],"status":"ok","earned_akr":0}'

        def _fake(req, *a, **k):
            try:
                url = req.full_url if hasattr(req, "full_url") else str(req)
                host = url.split("://", 1)[-1].split("/", 1)[0]
                if not any(h in host for h in ("localhost", "127.0.0.1", "0.0.0.0")):
                    raw = getattr(req, "data", b"") or b""
                    try:
                        capture.append(json.loads(raw))
                    except Exception:
                        capture.append({"_raw": raw.decode("utf-8", "replace")})
            except Exception:
                pass
            return _Resp()

        ur.urlopen = _fake
        self._ur = ur
        return self

    def __exit__(self, *a):
        self._ur.urlopen = self._orig

    def contribute_payloads(self) -> list[dict]:
        """Return all captured payloads whose path would be /contribute."""
        return self.bodies


class BehaviorGlobalPayloadCoarseTest(unittest.TestCase):
    """aios_agent_behavior.contribute_to_global: no numeric tool_freq, <=3 tool names."""

    def setUp(self):
        self.B = _load("aios_agent_behavior", "aios_agent_behavior_gsp")

    def _run(self, mem: dict) -> list[dict]:
        with _NetworkCapture() as cap:
            self.B.contribute_to_global(memories=[mem], api_key="test-key")
        return cap.contribute_payloads()

    def test_no_numeric_tool_freq_in_global_payload(self):
        mem = {
            "id": "beh-test1",
            "content": "category:code",
            "category": "code",
            "top_tools": ["Bash", "Edit", "Read", "Grep", "Write"],
            "tool_freq": {"Bash": 42, "Edit": 17, "Read": 8, "Grep": 5, "Write": 3},
            "loop_type": "react_code",
        }
        payloads = self._run(mem)
        self.assertTrue(payloads, "no off-device payload captured")
        payload = payloads[0]
        # (a) no numeric tool_freq distribution
        self.assertNotIn("tool_freq", payload,
                         "tool_freq (numeric counts) must not be sent globally")

    def test_at_most_3_tool_names_egress(self):
        mem = {
            "id": "beh-test2",
            "content": "category:code",
            "category": "code",
            "top_tools": ["Bash", "Edit", "Read", "Grep", "Write"],
            "tool_freq": {"Bash": 42, "Edit": 17, "Read": 8, "Grep": 5, "Write": 3},
            "loop_type": "react_code",
        }
        payloads = self._run(mem)
        self.assertTrue(payloads)
        top_tools = payloads[0].get("top_tools", [])
        self.assertLessEqual(len(top_tools), 3,
                             f"at most 3 tool names allowed globally, got {len(top_tools)}: {top_tools}")

    def test_no_arg_skeletons_in_global_payload(self):
        mem = {
            "id": "beh-test3",
            "content": "category:code",
            "category": "code",
            "top_tools": ["Bash"],
            "tool_freq": {"Bash": 5},
            "arg_skeletons": [{"tool": "Bash", "args": {"command": "<str:20>"}}],
            "loop_type": "react_code",
        }
        payloads = self._run(mem)
        self.assertTrue(payloads)
        blob = json.dumps(payloads)
        self.assertNotIn("arg_skeleton", blob,
                         "arg_skeletons must never egress to the global endpoint")

    def test_top_tools_are_names_not_counts(self):
        """top_tools must be a list of strings, not a dict of {name: count}."""
        mem = {
            "id": "beh-test4",
            "content": "category:code",
            "category": "code",
            "top_tools": ["Bash", "Edit"],
            "tool_freq": {"Bash": 10, "Edit": 5},
            "loop_type": "react_code",
        }
        payloads = self._run(mem)
        self.assertTrue(payloads)
        top_tools = payloads[0].get("top_tools", [])
        self.assertIsInstance(top_tools, list,
                              "top_tools must be a list of name strings, not a dict")
        for item in top_tools:
            self.assertIsInstance(item, str,
                                  f"each top_tools entry must be a string, got {type(item)}: {item!r}")


class AgentSystemGlobalPayloadCoarseTest(unittest.TestCase):
    """aios_agent_system.contribute: no numeric tool_freq, <=3 tool names."""

    def setUp(self):
        self.M = _load("aios_agent_system", "aios_agent_system_gsp")

    def _run(self, tools: list[str]) -> list[dict]:
        with _NetworkCapture() as cap:
            self.M.contribute("fix the auth bug", tools, "claude", 1.0, api_key="k")
        return cap.contribute_payloads()

    def test_no_numeric_tool_freq(self):
        payloads = self._run(["Bash", "Edit", "Read", "Grep", "Write"])
        self.assertTrue(payloads)
        self.assertNotIn("tool_freq", payloads[0],
                         "tool_freq must not be sent globally from aios_agent_system.contribute")

    def test_at_most_3_tool_names(self):
        payloads = self._run(["Bash", "Edit", "Read", "Grep", "Write"])
        self.assertTrue(payloads)
        top_tools = payloads[0].get("top_tools", [])
        self.assertLessEqual(len(top_tools), 3,
                             f"at most 3 tool names allowed globally, got {len(top_tools)}: {top_tools}")


class MemoryContributeRunGlobalPayloadCoarseTest(unittest.TestCase):
    """aios_memory.contribute_run: no numeric tool_freq, <=3 tool names."""

    def setUp(self):
        self.R = _load("aios_memory", "aios_memory_gsp")

    def _run(self, tools: list[str]) -> list[dict]:
        with _NetworkCapture() as cap:
            self.R.contribute_run("analyze the dataset",
                                  {"tool_sequence": tools, "exit": "model_finished",
                                   "loop_type": "react_code"},
                                  api_key="k")
        return cap.contribute_payloads()

    def test_no_numeric_tool_freq(self):
        payloads = self._run(["Bash", "Edit", "Read", "Grep", "Write"])
        self.assertTrue(payloads)
        self.assertNotIn("tool_freq", payloads[0],
                         "tool_freq must not be sent globally from aios_memory.contribute_run")

    def test_at_most_3_tool_names(self):
        payloads = self._run(["Bash", "Edit", "Read", "Grep", "Write"])
        self.assertTrue(payloads)
        top_tools = payloads[0].get("top_tools", [])
        self.assertLessEqual(len(top_tools), 3,
                             f"at most 3 tool names allowed globally, got {len(top_tools)}: {top_tools}")


if __name__ == "__main__":
    unittest.main()
