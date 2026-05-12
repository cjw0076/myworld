import json
import subprocess
import sys
import tempfile
import time
import unittest
from pathlib import Path


SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "aios_local_app.py"
SNAPSHOT = Path(__file__).resolve().parents[1] / "scripts" / "aios_control_snapshot.py"
MONITOR = Path(__file__).resolve().parents[1] / "scripts" / "aios_monitor.py"
ROUND = Path(__file__).resolve().parents[1] / "scripts" / "aios_round_controller.py"


class AiosLocalAppTest(unittest.TestCase):
    def write_fixture(self, root: Path) -> None:
        (root / "scripts").mkdir()
        (root / "apps" / "control").mkdir(parents=True)
        (root / "apps" / "control" / "index.html").write_text("<!doctype html><div>AIOS</div>\n", encoding="utf-8")
        (root / "apps" / "control" / "app.js").write_text(
            "window.AIOS_CONTROL_SNAPSHOT; function renderContracts(){} function renderDispatches(){} function renderRepos(){} function renderRoutes(){}\n",
            encoding="utf-8",
        )
        for source in (SCRIPT, SNAPSHOT, MONITOR, ROUND):
            (root / "scripts" / source.name).write_text(source.read_text(encoding="utf-8"), encoding="utf-8")
        (root / "docs" / "contracts").mkdir(parents=True)
        (root / "docs" / "contracts" / "ASC-0001-demo.md").write_text(
            "---\ncontract_id: ASC-0001\nstatus: closed\ngoal: demo\n---\n# Demo\n",
            encoding="utf-8",
        )
        (root / "docs" / "goals").mkdir(parents=True)
        (root / "docs" / "goals" / "AIOS-GOAL-0001-make-something-great.md").write_text(
            "---\ngoal_id: AIOS-GOAL-0001\nslug: demo\nstatus: active\n---\n# Demo\n\n## North Star\n\nRun.\n",
            encoding="utf-8",
        )

    def run_cli(self, root: Path, *args: str) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            [sys.executable, SCRIPT.as_posix(), "--root", root.as_posix(), *args],
            text=True,
            capture_output=True,
            check=False,
        )

    def test_refresh_writes_snapshot_and_reports_monitor(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            self.write_fixture(root)

            result = self.run_cli(root, "refresh", "--json")

            self.assertEqual(result.returncode, 0, result.stderr)
            data = json.loads(result.stdout)
            self.assertTrue(data["ok"])
            self.assertTrue((root / "apps" / "control" / "aios-control-snapshot.json").exists())
            self.assertTrue((root / "apps" / "control" / "aios-control-data.js").exists())

    def test_start_status_and_stop_server(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            self.write_fixture(root)
            port = "9876"

            start = self.run_cli(root, "start", "--port", port, "--json")
            try:
                self.assertEqual(start.returncode, 0, start.stderr)
                start_data = json.loads(start.stdout)
                self.assertTrue(start_data["server"]["running"])

                status = self.run_cli(root, "status", "--json")
                status_data = json.loads(status.stdout)
                self.assertTrue(status_data["server"]["running"])
                self.assertEqual(status_data["server"]["url"], f"http://127.0.0.1:{port}/")
            finally:
                stop = self.run_cli(root, "stop", "--json")
                self.assertEqual(stop.returncode, 0, stop.stderr)
                time.sleep(0.1)

            status_after = self.run_cli(root, "status", "--json")
            self.assertFalse(json.loads(status_after.stdout)["server"]["running"])


if __name__ == "__main__":
    unittest.main()
