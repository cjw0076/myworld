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

    def test_parse_raw_line_add_gitlink(self) -> None:
        e = guard.parse_raw_line(":000000 160000 0000000 d732431 A\t_tmp_embed")
        self.assertEqual(e, {"dst_mode": "160000", "status": "A", "path": "_tmp_embed", "size": None})

    def test_parse_raw_line_deletion_not_gitlink(self) -> None:
        # codex review #1: a gitlink DELETION has dst_mode 000000, so it must NOT
        # be flagged as a bad gitlink.
        e = guard.parse_raw_line(":160000 000000 d732431 0000000 D\toldmod")
        self.assertEqual(e["dst_mode"], "000000")
        self.assertEqual(e["status"], "D")
        self.assertEqual(guard.analyze([e], submodule_paths=set()), [])

    def test_parse_raw_line_rename_gitlink_takes_dest(self) -> None:
        # codex review #2: rename row (R100) with two paths → keep destination,
        # still detect a renamed unregistered gitlink.
        e = guard.parse_raw_line(":160000 160000 aaaaaaa bbbbbbb R100\toldname\tnewname")
        self.assertEqual(e["status"], "R")
        self.assertEqual(e["dst_mode"], "160000")
        self.assertEqual(e["path"], "newname")
        findings = guard.analyze([e], submodule_paths=set())
        self.assertEqual(findings[0]["rule"], "gitlink_without_submodule")

    def test_gitmodules_paths_strips_quotes(self) -> None:
        # codex review #4: a quoted path must still match the bare git path.
        import tempfile

        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / ".gitmodules").write_text(
                '[submodule "GenesisOS"]\n\tpath = "GenesisOS"\n\turl = x\n'
                '[submodule "hivemind"]\n\tpath = hivemind\n\turl = y\n'
            )
            self.assertEqual(guard.gitmodules_paths(root), {"GenesisOS", "hivemind"})

    def test_is_junk_name(self) -> None:
        self.assertTrue(guard.is_junk_name("0"))
        self.assertTrue(guard.is_junk_name("dir/12"))
        self.assertTrue(guard.is_junk_name(".3"))
        # broadened (gemini review #3): editor/OS temp + untitled scratch
        self.assertTrue(guard.is_junk_name("foo.swp"))
        self.assertTrue(guard.is_junk_name("app.js~"))
        self.assertTrue(guard.is_junk_name("notes.orig"))
        self.assertTrue(guard.is_junk_name("Untitled.md"))
        self.assertTrue(guard.is_junk_name("dir/.DS_Store"))
        self.assertFalse(guard.is_junk_name("app.js"))
        self.assertFalse(guard.is_junk_name("README"))
        self.assertFalse(guard.is_junk_name("untitled_form.tsx"))


if __name__ == "__main__":
    unittest.main()
