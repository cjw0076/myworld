import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "aios_launcher.py"
BIN = ROOT / "bin" / "aios"


class AiosLauncherTest(unittest.TestCase):
    def run_launcher(self, *args: str, cwd: Path = ROOT, check: bool = True) -> subprocess.CompletedProcess[str]:
        result = subprocess.run(
            [sys.executable, SCRIPT.as_posix(), *args],
            cwd=cwd,
            text=True,
            capture_output=True,
        )
        if check and result.returncode != 0:
            self.fail(result.stderr or result.stdout)
        return result

    def test_root_prefers_explicit_root(self) -> None:
        result = self.run_launcher("--root", ROOT.as_posix(), "root", "--json")
        payload = json.loads(result.stdout)

        self.assertEqual(payload["schema_version"], "aios.launcher.v1")
        self.assertEqual(payload["root"], ROOT.as_posix())
        self.assertEqual(payload["source"], "explicit")

    def test_root_finds_nearest_aios_ancestor(self) -> None:
        nested = ROOT / "docs" / "contracts"

        result = self.run_launcher("root", "--json", cwd=nested)
        payload = json.loads(result.stdout)

        self.assertEqual(payload["root"], ROOT.as_posix())
        self.assertEqual(payload["source"], "nearest_ancestor")

    def test_root_uses_aios_home_when_no_ancestor_exists(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            env = os.environ.copy()
            env["AIOS_HOME"] = ROOT.as_posix()
            result = subprocess.run(
                [sys.executable, SCRIPT.as_posix(), "root", "--json"],
                cwd=td,
                env=env,
                text=True,
                capture_output=True,
                check=True,
            )
        payload = json.loads(result.stdout)
        self.assertEqual(payload["root"], ROOT.as_posix())
        self.assertEqual(payload["source"], "AIOS_HOME")

    def test_runtime_command_constructs_aios_runtime_delegation(self) -> None:
        import importlib.util

        spec = importlib.util.spec_from_file_location("aios_launcher", SCRIPT)
        module = importlib.util.module_from_spec(spec)
        assert spec and spec.loader
        spec.loader.exec_module(module)

        command = module.runtime_command(ROOT, ["status", "--json"])

        self.assertEqual(command[0], sys.executable)
        self.assertEqual(command[1], (ROOT / "scripts" / "aios_runtime.py").as_posix())
        self.assertEqual(command[2:5], ["--root", ROOT.as_posix(), "status"])
        self.assertEqual(command[-1], "--json")

    def test_ask_command_constructs_aios_ask_delegation(self) -> None:
        import importlib.util

        spec = importlib.util.spec_from_file_location("aios_launcher", SCRIPT)
        module = importlib.util.module_from_spec(spec)
        assert spec and spec.loader
        spec.loader.exec_module(module)

        command = module.ask_command(ROOT, ["Build", "AIOS", "interface", "--json"])

        self.assertEqual(command[0], sys.executable)
        self.assertEqual(command[1], (ROOT / "scripts" / "aios_ask.py").as_posix())
        self.assertEqual(command[2:4], ["--root", ROOT.as_posix()])
        self.assertEqual(command[-1], "--json")

    def test_sprint_loop_uses_runtime_delegation(self) -> None:
        import importlib.util

        spec = importlib.util.spec_from_file_location("aios_launcher", SCRIPT)
        module = importlib.util.module_from_spec(spec)
        assert spec and spec.loader
        spec.loader.exec_module(module)

        command = module.runtime_command(ROOT, ["sprint-loop", "status", "--sprint-file", "current.md", "--json"])

        self.assertEqual(command[1], (ROOT / "scripts" / "aios_runtime.py").as_posix())
        self.assertEqual(command[2:5], ["--root", ROOT.as_posix(), "sprint-loop"])
        self.assertEqual(command[-1], "--json")

    def test_provider_loop_command_constructs_hive_delegation(self) -> None:
        import importlib.util

        spec = importlib.util.spec_from_file_location("aios_launcher", SCRIPT)
        module = importlib.util.module_from_spec(spec)
        assert spec and spec.loader
        spec.loader.exec_module(module)

        command, cwd = module.provider_loop_command(ROOT, ["status", "--json"])

        self.assertEqual(cwd, ROOT / "hivemind")
        self.assertEqual(command[:3], [sys.executable, "-m", "hivemind.hive"])
        self.assertEqual(command[3:6], ["--root", (ROOT / "hivemind").as_posix(), "provider-loop"])
        self.assertEqual(command[-2:], ["status", "--json"])

    def test_discover_command_constructs_project_discovery_delegation(self) -> None:
        import importlib.util

        spec = importlib.util.spec_from_file_location("aios_launcher", SCRIPT)
        module = importlib.util.module_from_spec(spec)
        assert spec and spec.loader
        spec.loader.exec_module(module)

        command = module.discover_command(ROOT, ["scan", "--root", "workspace", "--json"])

        self.assertEqual(command[0], sys.executable)
        self.assertEqual(command[1], (ROOT / "scripts" / "aios_project_discovery.py").as_posix())
        self.assertEqual(command[2:5], ["--control-root", ROOT.as_posix(), "scan"])

    def test_install_command_constructs_aios_install_delegation(self) -> None:
        import importlib.util

        spec = importlib.util.spec_from_file_location("aios_launcher", SCRIPT)
        module = importlib.util.module_from_spec(spec)
        assert spec and spec.loader
        spec.loader.exec_module(module)

        command = module.install_command(ROOT, ["--json", "--enable-now"])

        self.assertEqual(command[0], sys.executable)
        self.assertEqual(command[1], (ROOT / "scripts" / "aios_install.py").as_posix())
        self.assertEqual(command[2:5], ["--root", ROOT.as_posix(), "install"])
        self.assertEqual(command[-2:], ["--json", "--enable-now"])

    def test_local_app_command_constructs_control_app_delegation(self) -> None:
        import importlib.util

        spec = importlib.util.spec_from_file_location("aios_launcher", SCRIPT)
        module = importlib.util.module_from_spec(spec)
        assert spec and spec.loader
        spec.loader.exec_module(module)

        command = module.local_app_command(ROOT, ["up", "--json"])

        self.assertEqual(command[0], sys.executable)
        self.assertEqual(command[1], (ROOT / "scripts" / "aios_local_app.py").as_posix())
        self.assertEqual(command[2:5], ["--root", ROOT.as_posix(), "up"])

    def test_bin_aios_smoke_root_json(self) -> None:
        result = subprocess.run(
            [BIN.as_posix(), "--root", ROOT.as_posix(), "root", "--json"],
            cwd=ROOT,
            text=True,
            capture_output=True,
            check=True,
        )
        payload = json.loads(result.stdout)
        self.assertEqual(payload["root"], ROOT.as_posix())


if __name__ == "__main__":
    unittest.main()
