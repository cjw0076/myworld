from __future__ import annotations

import importlib.util
import json
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SCRIPTS = ROOT / "scripts"


def _load():
    spec = importlib.util.spec_from_file_location("aios_capture_args_uut", SCRIPTS / "aios_capture_args.py")
    m = importlib.util.module_from_spec(spec)
    sys.modules["aios_capture_args_uut"] = m
    spec.loader.exec_module(m)
    return m


class ScrubberPrivacyTest(unittest.TestCase):
    def setUp(self):
        self.m = _load()

    def test_sensitive_keys_redacted(self):
        for k in ("api_key", "token", "password", "authorization", "secret", "access_key"):
            sk = self.m.arg_skeleton({k: "whatever-value-here"})
            self.assertEqual(sk[k], "<redacted:sensitive-key>", k)

    def test_private_paths_redacted(self):
        for p in ("/home/u/_from_desktop/x.md", "/data/dain/notes.txt", "/x/minyoung/a", "./.env"):
            sk = self.m.arg_skeleton({"file_path": p})
            self.assertEqual(sk["file_path"], "<redacted:private>", p)

    def test_secret_looking_values_redacted(self):
        for v in ("sk-abcdefgh12345678", "ghp_abcdefgh12345678", "AKIA1234567890ABCD",
                  "eyJhbGciOiJIUzI1.eyJzdWIiOiIxMjM0"):
            sk = self.m.arg_skeleton({"note": v})
            self.assertEqual(sk["note"], "<redacted:secret>", v)

    def test_body_keys_keep_shape_not_content(self):
        sk = self.m.arg_skeleton({"command": "git push origin main && deploy.sh"})
        self.assertTrue(sk["command"].startswith("<str:"))
        self.assertNotIn("deploy", json.dumps(sk))               # body never present

    def test_short_safe_values_kept(self):
        sk = self.m.arg_skeleton({"limit": 5, "format": "json", "recursive": True, "x": None})
        self.assertEqual(sk, {"limit": 5, "format": "json", "recursive": True, "x": None})

    def test_nested_args_scrubbed(self):
        sk = self.m.arg_skeleton({"opts": {"token": "abc", "depth": 2}})
        self.assertEqual(sk["opts"]["token"], "<redacted:sensitive-key>")
        self.assertEqual(sk["opts"]["depth"], 2)

    def test_skeleton_has_no_secret_substring(self):
        sk = self.m.arg_skeleton({"api_key": "sk-SUPERSECRET", "cmd": "rm /dain/private"})
        self.assertNotIn("SUPERSECRET", json.dumps(sk))
        self.assertNotIn("private", json.dumps(sk).replace("redacted:private", ""))


class CallSignatureTest(unittest.TestCase):
    def setUp(self):
        self.m = _load()

    def test_distinct_calls_distinct_signatures(self):
        a = self.m.call_signature("Bash", {"command": "git status"})
        b = self.m.call_signature("Bash", {"command": "git diff"})
        self.assertNotEqual(a, b)

    def test_identical_calls_same_signature(self):
        a = self.m.call_signature("Bash", {"command": "git status"})
        b = self.m.call_signature("Bash", {"command": "git status"})
        self.assertEqual(a, b)

    def test_signature_is_non_reversible_hash(self):
        sig = self.m.call_signature("Bash", {"command": "echo SECRET_TOKEN_xyz"})
        self.assertNotIn("SECRET", sig)
        self.assertEqual(len(sig), 16)
        self.assertTrue(all(c in "0123456789abcdef" for c in sig))

    def test_stuck_repeat_vs_productive_repetition(self):
        a = self.m.call_signature("Bash", {"command": "git status"})
        b = self.m.call_signature("Bash", {"command": "git diff"})
        c = self.m.call_signature("Bash", {"command": "git log"})
        d = self.m.call_signature("Bash", {"command": "git show"})
        # 4 DISTINCT git commands → NOT stuck (the name-only heuristic would flag this)
        self.assertFalse(self.m.has_stuck_repeat([a, b, c, d]))
        # 4 IDENTICAL retries → stuck
        self.assertTrue(self.m.has_stuck_repeat([a, a, a, a]))


if __name__ == "__main__":
    unittest.main()
