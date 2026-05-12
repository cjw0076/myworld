import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "aios_repo_goal.py"


class AiosRepoGoalTest(unittest.TestCase):
    def run_cli(self, root: Path, *args: str, check: bool = True) -> subprocess.CompletedProcess[str]:
        result = subprocess.run(
            [sys.executable, SCRIPT.as_posix(), "--root", root.as_posix(), *args],
            text=True,
            capture_output=True,
            check=False,
        )
        if check and result.returncode != 0:
            self.fail(result.stderr or result.stdout)
        return result

    def test_submit_writes_repo_goal_packet(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)

            result = self.run_cli(
                root,
                "submit",
                "--repo",
                "hivemind",
                "--kind",
                "friction",
                "--goal",
                "Need a routed packet for watcher friction",
                "--summary",
                "Provider fallback should be visible to myworld",
                "--evidence-ref",
                "docs/AGENT_WORKLOG.md",
                "--json",
            )

            data = json.loads(result.stdout)
            self.assertEqual(data["schema_version"], "aios.repo_goal.v1")
            self.assertEqual(data["source_repo"], "hivemind")
            self.assertEqual(data["status"], "pending_route")
            packet_path = root / data["path"]
            self.assertTrue(packet_path.exists())

    def test_route_builds_recommendation_from_pending_goal(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            self.run_cli(
                root,
                "submit",
                "--repo",
                "memoryOS",
                "--kind",
                "blocker",
                "--goal",
                "Memory context provenance gap",
                "--summary",
                "Need trace evidence for selected memory",
                "--json",
            )

            result = self.run_cli(root, "route", "--repo", "memoryOS", "--json")

            data = json.loads(result.stdout)
            self.assertEqual(data["schema_version"], "aios.repo_goal_route.v1")
            self.assertEqual(data["source_repo"], "memoryOS")
            self.assertEqual(data["recommended_contract_slug"], "memory_feedback_or_provenance_followup")
            self.assertIn("memoryos", data)
            self.assertIn("capabilityos", data)
            self.assertIn("hivemind", data)
            self.assertEqual(data["next_action"], "draft_or_update_aios_smart_contract")
            self.assertTrue((root / data["path"]).exists())

    def test_route_dry_run_can_use_inline_goal_without_writing(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)

            result = self.run_cli(
                root,
                "route",
                "--repo",
                "CapabilityOS",
                "--kind",
                "observation",
                "--goal",
                "Need tool route for browser verification",
                "--dry-run",
                "--json",
            )

            data = json.loads(result.stdout)
            self.assertEqual(data["schema_version"], "aios.repo_goal_route.v1")
            self.assertEqual(data["source_repo"], "CapabilityOS")
            self.assertEqual(data["recommended_contract_slug"], "capability_provisioning_binding_plan")
            self.assertNotIn("path", data)
            self.assertFalse((root / ".aios" / "goal_routes").exists())

    def test_status_counts_goals_and_routes(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            self.run_cli(root, "submit", "--repo", "hivemind", "--goal", "Goal one", "--json")
            self.run_cli(root, "route", "--repo", "hivemind", "--json")

            result = self.run_cli(root, "status", "--repo", "hivemind", "--json")

            data = json.loads(result.stdout)
            self.assertEqual(data["repos"]["hivemind"]["pending_goals"], 1)
            self.assertEqual(data["repos"]["hivemind"]["routes"], 1)

    def test_rejects_unknown_repo(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)

            result = self.run_cli(root, "submit", "--repo", "unknown", "--goal", "bad", check=False)

            self.assertNotEqual(result.returncode, 0)
            self.assertIn("repo not allowed", result.stderr)

    def test_rejects_secret_like_or_raw_export_content(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)

            secret = self.run_cli(
                root,
                "submit",
                "--repo",
                "hivemind",
                "--goal",
                "Use token=abc123",
                check=False,
            )
            raw_path = self.run_cli(
                root,
                "submit",
                "--repo",
                "hivemind",
                "--goal",
                "Read raw_exports/chat.json",
                check=False,
            )

            self.assertNotEqual(secret.returncode, 0)
            self.assertIn("secret-like", secret.stderr)
            self.assertNotEqual(raw_path.returncode, 0)
            self.assertIn("forbidden raw/private path", raw_path.stderr)


if __name__ == "__main__":
    unittest.main()
