import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from scripts.aios_desktop_app import desktop_status, display_unavailable_message, load_or_build_snapshot, view_model


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "aios_desktop_app.py"
CONTROL_SNAPSHOT = ROOT / "scripts" / "aios_control_snapshot.py"


class AiosDesktopAppTest(unittest.TestCase):
    def test_view_model_extracts_control_fields(self) -> None:
        snapshot = {
            "generated_at": "2026-05-12T19:30:00+09:00",
            "goals": {"active": {"id": "AIOS-GOAL-1"}, "evolution": {"recommendation": "goal:next", "readiness": "L6"}},
            "monitor": {"health": "clear"},
            "round_controller": {"running": True},
            "contracts": {"counts": {"closed": 1}, "latest": [{"id": "ASC-1", "status": "closed"}]},
            "dispatches": {"counts": {"released": 1}, "latest": [{"dispatch_id": "asc-1", "status": "released"}]},
            "repos": {"items": [{"repo": "hivemind", "dirty": False}]},
            "next_actions": [{"owner": "myworld", "action": "continue", "reason": "ok"}],
        }

        model = view_model(snapshot)

        self.assertEqual(model["monitor_health"], "clear")
        self.assertEqual(model["recommendation"], "goal:next")
        self.assertTrue(model["round_running"])
        self.assertEqual(model["latest_contracts"][0]["id"], "ASC-1")
        self.assertIn("myworld: continue", model["next_action"])

    def test_status_json_declares_non_web_desktop_mode(self) -> None:
        status = desktop_status(ROOT)

        self.assertEqual(status["schema_version"], "aios.desktop_app.v1")
        self.assertEqual(status["mode"], "native_desktop")
        self.assertFalse(status["uses_http_server"])
        self.assertFalse(status["uses_browser"])

    def test_display_unavailable_message_points_to_headless_checks(self) -> None:
        message = display_unavailable_message(Exception("no display name and no $DISPLAY environment variable"))

        self.assertIn("graphical display", message)
        self.assertIn("status --json", message)
        self.assertIn("snapshot --json", message)

    def test_snapshot_refresh_writes_snapshot_without_gui(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            self.write_fixture(root)

            snapshot = load_or_build_snapshot(root, refresh=True)

            self.assertEqual(snapshot["schema_version"], "aios.control_snapshot.v1")
            self.assertTrue((root / "apps" / "control" / "aios-control-snapshot.json").exists())

    def test_cli_snapshot_json_is_headless(self) -> None:
        result = subprocess.run(
            [sys.executable, SCRIPT.as_posix(), "--root", ROOT.as_posix(), "snapshot", "--json"],
            cwd=ROOT,
            text=True,
            capture_output=True,
            check=False,
        )

        self.assertEqual(result.returncode, 0, result.stderr)
        payload = json.loads(result.stdout)
        self.assertEqual(payload["schema_version"], "aios.desktop_app.v1")
        self.assertIn("view_model", payload)

    def write_fixture(self, root: Path) -> None:
        (root / "scripts").mkdir()
        (root / "apps" / "control").mkdir(parents=True)
        (root / "docs" / "contracts").mkdir(parents=True)
        (root / "docs" / "goals").mkdir(parents=True)
        (root / "scripts" / CONTROL_SNAPSHOT.name).write_text(CONTROL_SNAPSHOT.read_text(encoding="utf-8"), encoding="utf-8")
        (root / "docs" / "contracts" / "ASC-0001-demo.md").write_text(
            "---\ncontract_id: ASC-0001\nstatus: closed\ngoal: demo\n---\n# Demo\n",
            encoding="utf-8",
        )
        (root / "docs" / "goals" / "AIOS-GOAL-0001-make-something-great.md").write_text(
            "---\ngoal_id: AIOS-GOAL-0001\nslug: demo\nstatus: active\n---\n# Demo\n\n## North Star\n\nRun.\n",
            encoding="utf-8",
        )


if __name__ == "__main__":
    unittest.main()
