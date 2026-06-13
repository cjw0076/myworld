import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "aios_serving_session.py"


class AiosServingSessionTest(unittest.TestCase):
    def run_session(self, root: Path, *args: str) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            [sys.executable, SCRIPT.as_posix(), *args],
            cwd=root,
            text=True,
            capture_output=True,
            check=False,
        )

    def test_create_writes_deterministic_session_under_serving_root(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            result = self.run_session(
                root,
                "create",
                "--root",
                root.as_posix(),
                "--user-id",
                "user1",
                "--session-id",
                "sess1",
                "--json",
            )

            self.assertEqual(result.returncode, 0, result.stderr)
            payload = json.loads(result.stdout)
            record = payload["record"]
            self.assertTrue(payload["ok"])
            self.assertEqual(record["schema_version"], "aios.serving_session.v1")
            self.assertEqual(record["user_id"], "user1")
            self.assertEqual(record["session_id"], "sess1")
            self.assertEqual(record["workspace_path"], ".aios/serving/workspaces/user1/sess1")
            self.assertEqual(
                record["artifact_path"],
                ".aios/serving/workspaces/user1/sess1/serving_session.json",
            )
            artifact = root / record["artifact_path"]
            self.assertTrue(artifact.exists())
            self.assertEqual(json.loads(artifact.read_text(encoding="utf-8")), record)
            written = [path.relative_to(root).as_posix() for path in root.rglob("*") if path.is_file()]
            self.assertEqual(written, [record["artifact_path"]])

    def test_create_includes_approval_and_draft_memory_policy(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            result = self.run_session(
                root,
                "create",
                "--root",
                root.as_posix(),
                "--user-id",
                "user_2",
                "--session-id",
                "session-2",
                "--json",
            )

            self.assertEqual(result.returncode, 0, result.stderr)
            record = json.loads(result.stdout)["record"]
            self.assertTrue(record["approval_policy"]["sensitive_actions_require_approval"])
            self.assertEqual(record["approval_policy"]["default_sensitive_action"], "hold_for_user_approval")
            self.assertEqual(record["memory_policy"]["write_policy"], "draft_only")
            self.assertEqual(record["memory_policy"]["accepted_memory_writes"], "forbidden")
            self.assertEqual(record["privacy_policy"]["credential_values"], "forbidden")
            self.assertEqual(record["privacy_policy"]["raw_provider_logs"], "forbidden")

    def test_rejects_path_traversal_user_or_session_ids(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            bad_user = self.run_session(
                root,
                "create",
                "--root",
                root.as_posix(),
                "--user-id",
                "../user",
                "--session-id",
                "sess1",
                "--json",
            )
            bad_session = self.run_session(
                root,
                "create",
                "--root",
                root.as_posix(),
                "--user-id",
                "user1",
                "--session-id",
                "../sess",
                "--json",
            )

            self.assertEqual(bad_user.returncode, 2)
            self.assertEqual(bad_session.returncode, 2)
            self.assertFalse((root / ".aios").exists())


if __name__ == "__main__":
    unittest.main()

