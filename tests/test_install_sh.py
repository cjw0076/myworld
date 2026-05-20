"""ASC-0205 CC2' — sh installer smoke test."""
from __future__ import annotations

import os
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
INSTALL_SH = REPO_ROOT / "scripts" / "install.sh"


class InstallShSmokeTest(unittest.TestCase):
    def test_install_sh_exists_and_is_executable(self):
        self.assertTrue(INSTALL_SH.exists())
        self.assertTrue(os.access(INSTALL_SH, os.X_OK),
                        f"{INSTALL_SH} must be executable")

    def test_install_sh_bash_syntax(self):
        r = subprocess.run(
            ["bash", "-n", str(INSTALL_SH)],
            capture_output=True, text=True, check=False,
        )
        self.assertEqual(r.returncode, 0, r.stderr)

    def test_install_sh_help_exits_zero(self):
        r = subprocess.run(
            ["bash", str(INSTALL_SH), "--help"],
            capture_output=True, text=True, check=False,
        )
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertIn("AIOS sh installer", r.stdout)

    def test_install_sh_against_current_repo_yields_working_aios_entry(self):
        """End-to-end smoke: install against the repo we live in, with
        AIOS_SKIP_FETCH=1 so no network, then run aios --version + aios
        contract + aios help."""
        if not shutil.which("git"):
            self.skipTest("git not on PATH in CI environment")
        with tempfile.TemporaryDirectory(prefix="aios_install_smoke_") as bin_dir:
            env = dict(os.environ)
            env["AIOS_PREFIX"] = str(REPO_ROOT)
            env["AIOS_BIN_DIR"] = bin_dir
            env["AIOS_SKIP_FETCH"] = "1"

            install = subprocess.run(
                ["bash", str(INSTALL_SH)],
                capture_output=True, text=True, env=env, check=False,
            )
            self.assertEqual(install.returncode, 0,
                             f"install failed: {install.stderr}\n{install.stdout}")
            entry = Path(bin_dir) / "aios"
            self.assertTrue(entry.exists())
            self.assertTrue(os.access(entry, os.X_OK))

            # entry must embed the install-time prefix, not rely on runtime env
            entry_body = entry.read_text()
            self.assertIn(f"AIOS_PREFIX=\"${{AIOS_PREFIX:-{REPO_ROOT}}}\"", entry_body)

            # bare invocation works without env
            no_aios_env = {k: v for k, v in env.items()
                           if not k.startswith("AIOS_")}
            ver = subprocess.run(
                [str(entry), "--version"],
                capture_output=True, text=True, env=no_aios_env, check=False,
            )
            self.assertEqual(ver.returncode, 0, ver.stderr)
            self.assertIn("aios ", ver.stdout)
            self.assertIn(str(REPO_ROOT), ver.stdout)

            # at least one operator subcommand works
            contract_ls = subprocess.run(
                [str(entry), "contract"],
                capture_output=True, text=True, env=no_aios_env, check=False,
            )
            self.assertEqual(contract_ls.returncode, 0, contract_ls.stderr)
            # we have many contracts; this just proves the path is right
            self.assertGreater(len(contract_ls.stdout.splitlines()), 50)

            # help works
            help_r = subprocess.run(
                [str(entry), "help"],
                capture_output=True, text=True, env=no_aios_env, check=False,
            )
            self.assertEqual(help_r.returncode, 0, help_r.stderr)
            self.assertIn("aios — operator CLI entrypoint", help_r.stdout)


if __name__ == "__main__":
    unittest.main()
