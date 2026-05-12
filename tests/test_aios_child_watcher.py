import json
import os
import shutil
import stat
import subprocess
import tempfile
import unittest
from pathlib import Path


SOURCE_SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "aios_child_watcher.sh"


def write_executable(path: Path, body: str) -> None:
    path.write_text(body, encoding="utf-8")
    path.chmod(path.stat().st_mode | stat.S_IXUSR)


class AiosChildWatcherTest(unittest.TestCase):
    def make_root(self, tmp: str) -> Path:
        root = Path(tmp)
        (root / "scripts").mkdir()
        script = root / "scripts" / "aios_child_watcher.sh"
        shutil.copy2(SOURCE_SCRIPT, script)
        script.chmod(script.stat().st_mode | stat.S_IXUSR)
        (root / "memoryOS").mkdir()
        (root / "CapabilityOS" / "capabilityos").mkdir(parents=True)
        (root / ".aios" / "inbox" / "memoryOS").mkdir(parents=True)
        (root / ".aios" / "outbox" / "memoryOS").mkdir(parents=True)
        return root

    def write_packet(self, root: Path, dispatch_id: str, agent: str = "codex") -> Path:
        packet = {
            "schema_version": "aios.dispatch.v1",
            "dispatch_id": dispatch_id,
            "contract_id": "ASC-0996",
            "contract_path": "docs/contracts/ASC-0996-test.md",
            "target_repo": "memoryOS",
            "agent": agent,
            "goal": "prove child watcher fallback behavior",
            "return_to": f".aios/outbox/memoryOS/{dispatch_id}.memoryOS.result.json",
            "scope": {"allowed_files": ["memoryOS/docs/AGENT_WORKLOG.md"], "forbidden_files": [".env"]},
        }
        path = root / ".aios" / "inbox" / "memoryOS" / f"{dispatch_id}.memoryOS.json"
        path.write_text(json.dumps(packet), encoding="utf-8")
        return path

    def run_watcher(self, root: Path, bin_dir: Path) -> subprocess.CompletedProcess[str]:
        env = os.environ.copy()
        env["PATH"] = f"{bin_dir}{os.pathsep}{env['PATH']}"
        env["CODEX_TIMEOUT"] = "10"
        env["CLAUDE_TIMEOUT"] = "10"
        env["AIOS_CHILD_AGENT_FALLBACKS"] = "1"
        return subprocess.run(
            [str(root / "scripts" / "aios_child_watcher.sh"), "once", "--repo", "memoryOS"],
            cwd=root,
            env=env,
            text=True,
            capture_output=True,
            check=False,
        )

    def write_capabilityos_route_cli(self, root: Path, fallback_agent: str) -> Path:
        package = root / "CapabilityOS" / "capabilityos"
        (package / "__init__.py").write_text("", encoding="utf-8")
        marker = root / "capability-route-called"
        (package / "cli.py").write_text(
            "\n".join(
                [
                    "from __future__ import annotations",
                    "import json",
                    "from pathlib import Path",
                    f"Path({marker.as_posix()!r}).write_text('called', encoding='utf-8')",
                    "print(json.dumps({",
                    "  'contract': 'capabilityos.provider_route.v1',",
                    "  'recommendation_only': True,",
                    f"  'fallback_agents': [{fallback_agent!r}],",
                    "  'routes': [],",
                    "}))",
                ]
            ),
            encoding="utf-8",
        )
        return marker

    def test_provider_access_denied_falls_back_once(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = self.make_root(tmp)
            marker = self.write_capabilityos_route_cli(root, "claude")
            bin_dir = root / "bin"
            bin_dir.mkdir()
            write_executable(
                bin_dir / "codex",
                "#!/usr/bin/env bash\n"
                "echo 'provider access denied: account lacks this model' >&2\n"
                "exit 1\n",
            )
            write_executable(
                bin_dir / "claude",
                "#!/usr/bin/env bash\n"
                "echo 'fallback agent completed bounded turn'\n"
                "exit 0\n",
            )
            self.write_packet(root, "asc-0996")

            result = self.run_watcher(root, bin_dir)

            self.assertEqual(result.returncode, 0, result.stderr or result.stdout)
            result_path = root / ".aios" / "outbox" / "memoryOS" / "asc-0996.memoryOS.result.json"
            data = json.loads(result_path.read_text(encoding="utf-8"))
            self.assertEqual(data["status"], "passed")
            self.assertTrue(data["fallback_used"])
            self.assertEqual(data["final_agent"], "claude")
            self.assertEqual(data["failure_category"], "provider_access_denied")
            self.assertEqual([item["agent"] for item in data["agent_attempts"]], ["codex", "claude"])
            self.assertEqual(data["agent_attempts"][0]["failure_category"], "provider_access_denied")
            self.assertEqual(data["agent_attempts"][1]["failure_category"], "none")
            self.assertFalse(data["stop_conditions_triggered"])
            self.assertTrue(marker.exists())
            self.assertTrue((root / ".aios" / "logs" / "asc-0996.memoryOS.provider_route.json").exists())

    def test_unknown_child_failure_does_not_fallback(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = self.make_root(tmp)
            bin_dir = root / "bin"
            bin_dir.mkdir()
            marker = root / "fallback-called"
            write_executable(
                bin_dir / "codex",
                "#!/usr/bin/env bash\n"
                "echo 'ordinary implementation failure' >&2\n"
                "exit 1\n",
            )
            write_executable(
                bin_dir / "claude",
                "#!/usr/bin/env bash\n"
                f"touch {marker.as_posix()}\n"
                "exit 0\n",
            )
            self.write_packet(root, "asc-0995")

            result = self.run_watcher(root, bin_dir)

            self.assertEqual(result.returncode, 0, result.stderr or result.stdout)
            self.assertFalse(marker.exists())
            result_path = root / ".aios" / "outbox" / "memoryOS" / "asc-0995.memoryOS.result.json"
            data = json.loads(result_path.read_text(encoding="utf-8"))
            self.assertEqual(data["status"], "failed")
            self.assertFalse(data["fallback_used"])
            self.assertEqual(data["final_agent"], "codex")
            self.assertEqual(data["failure_category"], "child_agent_failed")
            self.assertEqual([item["agent"] for item in data["agent_attempts"]], ["codex"])
            self.assertEqual(data["stop_conditions_triggered"], ["child_agent_failed"])

    def test_korean_access_denied_falls_back_once(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = self.make_root(tmp)
            self.write_capabilityos_route_cli(root, "claude")
            bin_dir = root / "bin"
            bin_dir.mkdir()
            write_executable(
                bin_dir / "codex",
                "#!/usr/bin/env bash\n"
                "echo '접근 거부.' >&2\n"
                "exit 1\n",
            )
            write_executable(
                bin_dir / "claude",
                "#!/usr/bin/env bash\n"
                "echo 'fallback agent completed bounded turn'\n"
                "exit 0\n",
            )
            self.write_packet(root, "asc-0994")

            result = self.run_watcher(root, bin_dir)

            self.assertEqual(result.returncode, 0, result.stderr or result.stdout)
            result_path = root / ".aios" / "outbox" / "memoryOS" / "asc-0994.memoryOS.result.json"
            data = json.loads(result_path.read_text(encoding="utf-8"))
            self.assertEqual(data["status"], "passed")
            self.assertTrue(data["fallback_used"])
            self.assertEqual(data["failure_category"], "provider_access_denied")
            self.assertEqual([item["agent"] for item in data["agent_attempts"]], ["codex", "claude"])


if __name__ == "__main__":
    unittest.main()
