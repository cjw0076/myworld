import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "aios_sprint_loop.py"


class AiosSprintLoopTest(unittest.TestCase):
    def run_loop(self, *args: str, cwd: Path = ROOT, check: bool = True) -> subprocess.CompletedProcess[str]:
        result = subprocess.run(
            [sys.executable, SCRIPT.as_posix(), *args],
            cwd=cwd,
            text=True,
            capture_output=True,
        )
        if check and result.returncode != 0:
            self.fail(result.stderr or result.stdout)
        return result

    def test_init_and_status_read_pending_task(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            sprint = root / ".aios" / "sprints" / "uri" / "current.md"
            self.run_loop(
                "--root",
                root.as_posix(),
                "init",
                "--sprint-file",
                sprint.as_posix(),
                "--repo",
                "uri",
                "--repo-path",
                "uri",
                "--goal",
                "Test sprint",
                "--task",
                "first task",
                "--json",
            )

            result = self.run_loop("--root", root.as_posix(), "status", "--sprint-file", sprint.as_posix(), "--json")
            payload = json.loads(result.stdout)

            self.assertEqual(payload["schema_version"], "aios.sprint_loop.v1")
            self.assertEqual(payload["status"], "continue")
            self.assertEqual(payload["pending_tasks"], 1)
            self.assertEqual(payload["next_task"], "first task")

    def test_tick_dry_run_builds_codex_workspace_write_command(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            repo = root / "uri"
            repo.mkdir()
            sprint = root / "current.md"
            sprint.write_text(
                "\n".join(
                    [
                        "---",
                        "repo: uri",
                        "repo_path: uri",
                        "provider: codex",
                        "goal: Test sprint",
                        "verification: npm test",
                        "---",
                        "",
                        "## Queue",
                        "",
                        "- [ ] implement feature",
                        "",
                    ]
                ),
                encoding="utf-8",
            )

            result = self.run_loop("--root", root.as_posix(), "tick", "--sprint-file", sprint.as_posix(), "--json")
            payload = json.loads(result.stdout)

            self.assertEqual(payload["status"], "dry_run")
            self.assertEqual(payload["provider"], "codex")
            self.assertIn("--sandbox", payload["command"])
            self.assertIn("workspace-write", payload["command"])
            self.assertEqual(payload["task"], "implement feature")
            self.assertTrue(Path(payload["receipt"]).exists())

    def test_tick_can_mark_complete_after_fake_provider_success(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            repo = root / "uri"
            repo.mkdir()
            sprint = root / "current.md"
            sprint.write_text(
                "---\nrepo: uri\nrepo_path: uri\nprovider: local\ngoal: Test sprint\n---\n\n## Queue\n\n- [ ] close loop\n",
                encoding="utf-8",
            )

            result = self.run_loop(
                "--root",
                root.as_posix(),
                "tick",
                "--sprint-file",
                sprint.as_posix(),
                "--execute",
                "--mark-complete-on-success",
                "--json",
                "--provider-command",
                sys.executable,
                "-c",
                "print('ok')",
            )
            payload = json.loads(result.stdout)

            self.assertEqual(payload["status"], "passed")
            self.assertTrue(payload["marked_complete"])
            self.assertIn("- [x] close loop", sprint.read_text(encoding="utf-8"))

    def test_status_stops_when_no_pending_tasks(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            sprint = root / "current.md"
            sprint.write_text("---\nrepo: uri\nrepo_path: uri\n---\n\n- [x] done\n", encoding="utf-8")

            result = self.run_loop("--root", root.as_posix(), "status", "--sprint-file", sprint.as_posix(), "--json")
            payload = json.loads(result.stdout)

            self.assertEqual(payload["status"], "stop")
            self.assertEqual(payload["pending_tasks"], 0)


if __name__ == "__main__":
    unittest.main()
