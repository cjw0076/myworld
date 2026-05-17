import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "aios_provider_prompts.py"


class ProviderPromptBootstrapTest(unittest.TestCase):
    def run_script(self, *args: str, home: Path | None = None, cwd: Path | None = None) -> dict:
        env = os.environ.copy()
        env["AIOS_PROVIDER_PROMPTS_TIMESTAMP"] = "2026-05-13T00:00:00+09:00"
        command = [sys.executable, SCRIPT.as_posix(), "--root", ROOT.as_posix()]
        if home:
            command += ["--home", home.as_posix()]
        if cwd:
            command += ["--cwd", cwd.as_posix()]
        command += [*args, "--json"]
        result = subprocess.run(command, cwd=ROOT, env=env, text=True, capture_output=True)
        if result.returncode != 0:
            self.fail(result.stderr or result.stdout)
        return json.loads(result.stdout)

    def test_detect_reports_schema_and_claude_when_present(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            home = Path(td)
            (home / ".claude").mkdir()

            payload = self.run_script("detect", home=home)

            self.assertEqual(payload["schema_version"], "aios.provider_prompts.v1")
            self.assertIn("claude", payload["detected"])
            claude = next(row for row in payload["providers"] if row["name"] == "claude")
            self.assertTrue(claude["enabled"])
            self.assertFalse(claude["experimental"])

    def test_bootstrap_dry_run_writes_nothing(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            home = Path(td)
            (home / ".claude").mkdir()

            payload = self.run_script("bootstrap", "--dry-run", home=home)

            self.assertGreaterEqual(payload["writes_planned"], 1)
            self.assertEqual(payload["writes_performed"], 0)
            self.assertFalse((home / ".claude" / "CLAUDE.md").exists())

    def test_temp_home_bootstrap_creates_marker_block(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            home = Path(td)

            payload = self.run_script("bootstrap", home=home)

            target = home / ".claude" / "CLAUDE.md"
            self.assertEqual(payload["writes_performed"], 1)
            self.assertTrue(target.exists())
            text = target.read_text(encoding="utf-8")
            self.assertIn("<!-- AIOS BEGIN", text)
            self.assertIn("<!-- AIOS END -->", text)
            self.assertIn("AIOS Provider Contract", text)

    def test_bootstrap_is_idempotent_no_duplicate_marker(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            home = Path(td)

            self.run_script("bootstrap", home=home)
            self.run_script("bootstrap", home=home)

            text = (home / ".claude" / "CLAUDE.md").read_text(encoding="utf-8")
            self.assertEqual(text.count("<!-- AIOS BEGIN"), 1)
            self.assertEqual(text.count("<!-- AIOS END -->"), 1)

    def test_safe_merge_preserves_existing_content(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            home = Path(td)
            target = home / ".claude" / "CLAUDE.md"
            target.parent.mkdir()
            target.write_text("personal rule\n", encoding="utf-8")

            self.run_script("bootstrap", home=home)

            text = target.read_text(encoding="utf-8")
            self.assertTrue(text.startswith("personal rule\n"))
            self.assertIn("<!-- AIOS BEGIN", text)
            self.assertIn("AIOS Provider Contract", text)

    def test_status_reports_drift_for_old_marker_version(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            home = Path(td)
            target = home / ".claude" / "CLAUDE.md"
            target.parent.mkdir()
            target.write_text(
                "<!-- AIOS BEGIN v=old generated_at=2026 -->\nold\n<!-- AIOS END -->\n",
                encoding="utf-8",
            )

            payload = self.run_script("status", home=home)

            claude = next(row for row in payload["providers"] if row["name"] == "claude")
            self.assertTrue(claude["marker_present"])
            self.assertEqual(claude["installed_version"], "old")
            self.assertTrue(claude["drift"])

    def test_experimental_providers_are_not_written_by_default(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            home = Path(td)
            (home / ".gemini").mkdir()

            payload = self.run_script("bootstrap", home=home)

            gemini = next(row for row in payload["providers"] if row["name"] == "gemini")
            self.assertTrue(gemini["detected"])
            self.assertTrue(gemini["experimental"])
            self.assertEqual(gemini["action"], "skip_experimental")
            self.assertFalse((home / ".gemini" / "AIOS.md").exists())


if __name__ == "__main__":
    unittest.main()
