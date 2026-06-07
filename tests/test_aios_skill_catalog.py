import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, (Path(__file__).resolve().parents[1] / "scripts").as_posix())

import aios_skill_catalog as c

INLINE = "---\nname: foo\ndescription: a short skill desc\n---\n# body"
FOLDED = "---\nname: bar\ndescription: >-\n  first line\n  second line\n---\n# body"


class ParseSkillTests(unittest.TestCase):
    def test_inline_description(self) -> None:
        s = c.parse_skill(INLINE)
        self.assertEqual(s["name"], "foo")
        self.assertEqual(s["description"], "a short skill desc")

    def test_folded_description(self) -> None:
        s = c.parse_skill(FOLDED)
        self.assertEqual(s["name"], "bar")
        self.assertEqual(s["description"], "first line second line")

    def test_no_frontmatter(self) -> None:
        self.assertIsNone(c.parse_skill("# just a heading"))

    def test_no_name(self) -> None:
        self.assertIsNone(c.parse_skill("---\ndescription: x\n---"))


class ScanSkillsTests(unittest.TestCase):
    def test_scans_and_tags_repo(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / ".claude" / "skills" / "alpha").mkdir(parents=True)
            (root / ".claude" / "skills" / "alpha" / "SKILL.md").write_text(INLINE)
            (root / "uri" / ".claude" / "skills" / "beta").mkdir(parents=True)
            (root / "uri" / ".claude" / "skills" / "beta" / "SKILL.md").write_text(FOLDED)
            (root / "node_modules" / "pkg").mkdir(parents=True)
            (root / "node_modules" / "pkg" / "SKILL.md").write_text(INLINE)  # excluded
            skills = c.scan_skills(root)
            names = {s["name"]: s["repo"] for s in skills}
            self.assertEqual(names, {"foo": "myworld", "bar": "uri"})  # node_modules skipped

    def test_live_catalog_has_harness_skills(self) -> None:
        # against the real repo: the operator harness skills must be indexed
        skills = c.scan_skills(c.ROOT)
        names = {s["name"] for s in skills}
        self.assertIn("aios-decide", names)
        self.assertIn("absorption-probe", names)


if __name__ == "__main__":
    unittest.main()
