import sys
import unittest
from pathlib import Path

sys.path.insert(0, (Path(__file__).resolve().parents[1] / "scripts").as_posix())

import aios_commit_guard as guard


class CommitGuardTests(unittest.TestCase):
    def test_gitlink_without_submodule_is_error(self) -> None:
        entries = [{"dst_mode": "160000", "status": "A", "path": "GenesisOS", "size": None}]
        findings = guard.analyze(entries, submodule_paths=set())
        self.assertEqual(len(findings), 1)
        self.assertEqual(findings[0]["level"], "error")
        self.assertEqual(findings[0]["rule"], "gitlink_without_submodule")

    def test_registered_submodule_is_clean(self) -> None:
        entries = [{"dst_mode": "160000", "status": "M", "path": "hivemind", "size": None}]
        findings = guard.analyze(entries, submodule_paths={"hivemind", "uri"})
        self.assertEqual(findings, [])

    def test_empty_junk_file_is_warn(self) -> None:
        entries = [{"dst_mode": "100644", "status": "A", "path": "0", "size": 0}]
        findings = guard.analyze(entries, submodule_paths=set())
        self.assertEqual(len(findings), 1)
        self.assertEqual(findings[0]["level"], "warn")
        self.assertEqual(findings[0]["rule"], "empty_junk_file")

    def test_normal_file_is_clean(self) -> None:
        entries = [
            {"dst_mode": "100644", "status": "A", "path": "scripts/x.py", "size": 1200},
            {"dst_mode": "100644", "status": "M", "path": "README.md", "size": 50},
        ]
        self.assertEqual(guard.analyze(entries, submodule_paths=set()), [])

    def test_empty_named_file_is_not_junk(self) -> None:
        # A real (if empty) file with a meaningful name should not warn.
        entries = [{"dst_mode": "100644", "status": "A", "path": "pkg/__init__.py", "size": 0}]
        self.assertEqual(guard.analyze(entries, submodule_paths=set()), [])

    def test_is_junk_name(self) -> None:
        self.assertTrue(guard.is_junk_name("0"))
        self.assertTrue(guard.is_junk_name("dir/12"))
        self.assertTrue(guard.is_junk_name(".3"))
        self.assertFalse(guard.is_junk_name("app.js"))
        self.assertFalse(guard.is_junk_name("README"))


if __name__ == "__main__":
    unittest.main()
