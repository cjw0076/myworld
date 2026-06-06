import sys
import unittest
from pathlib import Path

sys.path.insert(0, (Path(__file__).resolve().parents[1] / "scripts").as_posix())

import aios_star_radar as sr


class StarRadarPureTests(unittest.TestCase):
    def test_build_query(self) -> None:
        self.assertEqual(sr.build_query("2026-03-01", 2000, None), "created:>2026-03-01 stars:>2000")
        self.assertEqual(
            sr.build_query("2026-03-01", 2000, "agent OR llm"),
            "created:>2026-03-01 stars:>2000 agent OR llm",
        )

    def test_parse_repos(self) -> None:
        payload = {
            "items": [
                {
                    "full_name": "acme/agent",
                    "stargazers_count": 4200,
                    "created_at": "2026-04-15T00:00:00Z",
                    "description": "  a cool agent  ",
                    "topics": ["llm", "agent"],
                    "html_url": "https://github.com/acme/agent",
                },
                {"full_name": "x/y"},  # missing fields tolerated
            ]
        }
        repos = sr.parse_repos(payload)
        self.assertEqual(repos[0]["stars"], 4200)
        self.assertEqual(repos[0]["created_at"], "2026-04-15")
        self.assertEqual(repos[0]["description"], "a cool agent")
        self.assertEqual(repos[1]["stars"], 0)
        self.assertEqual(repos[1]["topics"], [])

    def test_parse_repos_empty(self) -> None:
        self.assertEqual(sr.parse_repos({}), [])

    def test_distill_prompt_includes_repo(self) -> None:
        p = sr.distill_prompt({"full_name": "acme/agent", "stars": 4200, "created_at": "2026-04-15",
                               "description": "a cool agent", "topics": ["llm"]})
        self.assertIn("acme/agent", p)
        self.assertIn("a cool agent", p)
        self.assertIn("AIOS", p)


    def test_load_seen(self) -> None:
        import json
        import tempfile

        with tempfile.TemporaryDirectory() as tmp:
            d = Path(tmp)
            (d / "receipt-1.json").write_text(
                json.dumps({"candidates": [{"full_name": "a/b"}, {"full_name": "c/d"}]})
            )
            (d / "receipt-2.json").write_text(json.dumps({"candidates": [{"full_name": "e/f"}]}))
            self.assertEqual(sr.load_seen(d), {"a/b", "c/d", "e/f"})

    def test_load_seen_empty_dir(self) -> None:
        import tempfile

        with tempfile.TemporaryDirectory() as tmp:
            self.assertEqual(sr.load_seen(Path(tmp) / "nope"), set())


if __name__ == "__main__":
    unittest.main()
