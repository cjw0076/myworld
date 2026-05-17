import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "aios_project_discovery.py"
FIXTURE = ROOT / "tests" / "fixtures" / "project_discovery" / "workspace"


class ProjectDiscoveryTest(unittest.TestCase):
    def run_cli(self, control_root: Path, *args: str) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            [sys.executable, SCRIPT.as_posix(), "--control-root", control_root.as_posix(), *args],
            cwd=ROOT,
            text=True,
            capture_output=True,
            check=False,
        )

    def test_scan_discovers_profiles_and_statuses(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            control = Path(tmp)
            result = self.run_cli(control, "scan", "--root", FIXTURE.as_posix(), "--json")
            self.assertEqual(result.returncode, 0, result.stderr)
            payload = json.loads(result.stdout)
            by_name = {Path(row["project_root"]).name: row for row in payload["projects"]}

            self.assertEqual(by_name["project_alpha"]["status"], "usable")
            self.assertEqual(by_name["project_beta"]["status"], "degraded")
            self.assertEqual(by_name["project_conflict"]["status"], "checkpoint_required")
            self.assertEqual(by_name["project_secret"]["status"], "blocked")
            self.assertNotIn("project_no_aios", by_name)

            first_id = by_name["project_alpha"]["project_id"]
            second = self.run_cli(control, "scan", "--root", FIXTURE.as_posix(), "--json")
            second_payload = json.loads(second.stdout)
            second_by_name = {Path(row["project_root"]).name: row for row in second_payload["projects"]}
            self.assertEqual(first_id, second_by_name["project_alpha"]["project_id"])

    def test_hard_bans_are_reported_not_read(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            workspace = Path(tmp) / "workspace"
            project = workspace / "project_secret"
            project.mkdir(parents=True)
            (project / "AGENTS.md").write_text("# Secret Fixture\n", encoding="utf-8")
            (project / ".env").write_text("DO_NOT_READ=fixture\n", encoding="utf-8")
            (project / "token_notes.md").write_text("fixture token notes; this file must be blocked\n", encoding="utf-8")
            control = Path(tmp) / "control"
            payload = json.loads(self.run_cli(control, "scan", "--root", workspace.as_posix(), "--json").stdout)
            blocked = {row["path"]: row["reason"] for row in payload["blocked_paths"]}

            self.assertIn("project_secret/.env", blocked)
            self.assertIn("project_secret/token_notes.md", blocked)
            secret_profile_ref = next(row for row in payload["projects"] if Path(row["project_root"]).name == "project_secret")["refs"]["profile"]
            profile = json.loads((control / secret_profile_ref).read_text(encoding="utf-8"))
            spec_paths = [row["path"] for row in profile["agent_specs"]]
            self.assertNotIn(".env", spec_paths)
            self.assertNotIn("token_notes.md", spec_paths)

    def test_symlink_escape_is_blocked(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            workspace = Path(tmp) / "workspace"
            project = workspace / "project_symlink_escape"
            outside = Path(tmp) / "outside"
            project.mkdir(parents=True)
            outside.mkdir()
            (project / "AGENTS.md").write_text("# Escape\n", encoding="utf-8")
            os.symlink(outside, project / "outside_link")

            control = Path(tmp) / "control"
            payload = json.loads(self.run_cli(control, "scan", "--root", workspace.as_posix(), "--json").stdout)
            row = payload["projects"][0]

            self.assertEqual(row["status"], "blocked")
            self.assertIn("symlink_escape", row["reasons"])

    def test_invoke_writes_plan_only_envelope(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            control = Path(tmp)
            result = self.run_cli(
                control,
                "invoke",
                "--project",
                (FIXTURE / "project_alpha").as_posix(),
                "--goal",
                "ship a local feature through AIOS",
                "--plan-only",
                "--json",
            )
            self.assertEqual(result.returncode, 0, result.stderr)
            payload = json.loads(result.stdout)
            envelope = payload["envelope"]

            self.assertEqual(envelope["requested_mode"], "plan_only")
            self.assertEqual(envelope["required_os_roles"], ["GenesisOS", "memoryOS", "CapabilityOS", "hivemind", "myworld"])
            self.assertIn("authority_ref", envelope)
            authority = json.loads((control / envelope["authority_ref"]).read_text(encoding="utf-8"))
            self.assertEqual(authority["may_write"], [])

    def test_invoke_rejects_execution_mode(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            control = Path(tmp)
            result = self.run_cli(
                control,
                "invoke",
                "--project",
                (FIXTURE / "project_alpha").as_posix(),
                "--goal",
                "run it",
                "--json",
            )
            self.assertNotEqual(result.returncode, 0)
            self.assertIn("plan-only", result.stderr)


if __name__ == "__main__":
    unittest.main()
