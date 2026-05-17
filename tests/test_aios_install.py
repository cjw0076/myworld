import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "aios_install.py"


class AiosInstallTests(unittest.TestCase):
    def run_install(self, *args: str, env: dict[str, str] | None = None) -> subprocess.CompletedProcess[str]:
        merged_env = os.environ.copy()
        merged_env["AIOS_INSTALL_SKIP_SYSTEMCTL"] = "1"
        if env:
            merged_env.update(env)
        return subprocess.run(
            [sys.executable, SCRIPT.as_posix(), "--root", ROOT.as_posix(), *args],
            cwd=ROOT,
            text=True,
            capture_output=True,
            check=False,
            env=merged_env,
        )

    def test_plan_reports_targets_without_writing(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            home = Path(tmp) / "home"
            result = self.run_install("plan", "--home", home.as_posix(), "--json")
            self.assertEqual(result.returncode, 0, result.stderr)
            payload = json.loads(result.stdout)
            self.assertEqual(payload["schema_version"], "aios.install.v1")
            self.assertEqual(payload["status"], "planned")
            self.assertIn((home / ".local" / "bin" / "aios").as_posix(), payload["would_write"])
            self.assertFalse((home / ".local" / "bin" / "aios").exists())
            self.assertEqual(payload["service_model"]["restart"], "always")

    def test_install_writes_managed_launcher_service_and_desktop_entry(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            home = Path(tmp) / "home"
            result = self.run_install("install", "--home", home.as_posix(), "--json")
            self.assertEqual(result.returncode, 0, result.stderr)
            launcher = home / ".local" / "bin" / "aios"
            service = home / ".config" / "systemd" / "user" / "aios.service"
            desktop = home / ".config" / "autostart" / "aios-control.desktop"
            self.assertTrue(launcher.exists())
            self.assertTrue(service.exists())
            self.assertTrue(desktop.exists())
            self.assertIn("AIOS_INSTALLER_MANAGED", launcher.read_text())
            self.assertIn("exec", launcher.read_text())
            service_text = service.read_text()
            self.assertIn("scripts/aios_local_app.py", service_text)
            self.assertIn("scripts/aios_round_controller.py run", service_text)
            self.assertIn("--execute-children", service_text)
            self.assertIn("Restart=always", service_text)
            self.assertIn(f"Environment=AIOS_HOME={ROOT.as_posix()}", service_text)
            self.assertIn("xdg-open http://127.0.0.1:8765/", desktop.read_text())

    def test_status_reports_installed_targets(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            home = Path(tmp) / "home"
            self.assertEqual(self.run_install("install", "--home", home.as_posix(), "--json").returncode, 0)
            result = self.run_install("status", "--home", home.as_posix(), "--json")
            self.assertEqual(result.returncode, 0, result.stderr)
            payload = json.loads(result.stdout)
            self.assertEqual(payload["status"], "installed")
            self.assertTrue(payload["targets"]["launcher"]["managed_by_aios_install"])
            self.assertFalse(payload["systemd_user_service"]["available"])

    def test_uninstall_removes_only_managed_files(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            home = Path(tmp) / "home"
            self.assertEqual(self.run_install("install", "--home", home.as_posix(), "--json").returncode, 0)
            unmanaged = home / ".local" / "bin" / "other"
            unmanaged.parent.mkdir(parents=True, exist_ok=True)
            unmanaged.write_text("do not remove\n")
            result = self.run_install("uninstall", "--home", home.as_posix(), "--json")
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertFalse((home / ".local" / "bin" / "aios").exists())
            self.assertFalse((home / ".config" / "systemd" / "user" / "aios.service").exists())
            self.assertTrue(unmanaged.exists())

    def test_unmanaged_aios_target_blocks_install_without_force(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            home = Path(tmp) / "home"
            launcher = home / ".local" / "bin" / "aios"
            launcher.parent.mkdir(parents=True, exist_ok=True)
            launcher.write_text("# existing user command\n")
            result = self.run_install("install", "--home", home.as_posix(), "--json")
            self.assertEqual(result.returncode, 1)
            payload = json.loads(result.stdout)
            self.assertEqual(payload["status"], "blocked")
            self.assertEqual(payload["writes"][0]["stop_condition"], "unmanaged_target_exists")
            self.assertEqual(launcher.read_text(), "# existing user command\n")


if __name__ == "__main__":
    unittest.main()
