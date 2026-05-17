import json
import os
import shutil
import stat
import subprocess
import tempfile
import unittest
from pathlib import Path


SOURCE_SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "aios_pingpong.sh"


def write_executable(path: Path, body: str) -> None:
    path.write_text(body, encoding="utf-8")
    path.chmod(path.stat().st_mode | stat.S_IXUSR)


class AiosPingpongTest(unittest.TestCase):
    def make_root(self, tmp: str) -> Path:
        root = Path(tmp)
        (root / "scripts").mkdir()
        shutil.copy2(SOURCE_SCRIPT, root / "scripts" / "aios_pingpong.sh")
        (root / "scripts" / "aios_pingpong.sh").chmod(stat.S_IRUSR | stat.S_IWUSR | stat.S_IXUSR)
        (root / "docs").mkdir()
        return root

    def test_provider_access_denied_falls_back_to_other_agent(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = self.make_root(tmp)
            bin_dir = root / "bin"
            bin_dir.mkdir()
            marker = root / "fallback-ran"
            write_executable(
                bin_dir / "codex",
                "#!/usr/bin/env bash\n"
                "echo '접근 거부.' >&2\n"
                "exit 1\n",
            )
            write_executable(
                bin_dir / "claude",
                "#!/usr/bin/env bash\n"
                f"touch {marker.as_posix()}\n"
                "echo 'claude fallback completed'\n",
            )
            env = os.environ.copy()
            env["PATH"] = f"{bin_dir}{os.pathsep}{env['PATH']}"
            env["AIOS_MAX_ROUNDS"] = "1"
            env["AIOS_CONTINUE_AFTER_READY"] = "1"
            env["CODEX_TIMEOUT"] = "5"
            env["CLAUDE_TIMEOUT"] = "5"

            result = subprocess.run(
                [str(root / "scripts" / "aios_pingpong.sh"), "run"],
                cwd=root,
                env=env,
                check=False,
                capture_output=True,
                text=True,
            )

            self.assertEqual(result.returncode, 0, result.stderr or result.stdout)
            self.assertTrue(marker.exists())
            events = [
                json.loads(line)
                for line in (root / ".aios" / "state" / "aios_pingpong.jsonl").read_text(encoding="utf-8").splitlines()
            ]
            self.assertTrue(any(event["event"] == "agent_fallback_start" for event in events))
            self.assertTrue(any(event["event"] == "agent_done" and event["agent"] == "claude" for event in events))
            state = (root / ".aios" / "state" / "aios_pingpong.state").read_text(encoding="utf-8")
            self.assertIn("status=waiting", state)

    def test_provider_limit_falls_back_to_local_command(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = self.make_root(tmp)
            bin_dir = root / "bin"
            bin_dir.mkdir()
            marker = root / "local-ran"
            write_executable(
                bin_dir / "codex",
                "#!/usr/bin/env bash\n"
                "echo '접근 거부.' >&2\n"
                "exit 1\n",
            )
            write_executable(
                bin_dir / "claude",
                "#!/usr/bin/env bash\n"
                "echo \"You've hit your limit · resets 3pm (Asia/Seoul)\" >&2\n"
                "exit 1\n",
            )
            env = os.environ.copy()
            env["PATH"] = f"{bin_dir}{os.pathsep}{env['PATH']}"
            env["AIOS_MAX_ROUNDS"] = "1"
            env["AIOS_CONTINUE_AFTER_READY"] = "1"
            env["CODEX_TIMEOUT"] = "5"
            env["CLAUDE_TIMEOUT"] = "5"
            env["LOCAL_TIMEOUT"] = "5"
            env["AIOS_LOCAL_AGENT_COMMAND"] = f"touch {marker.as_posix()}; echo local fallback completed"

            result = subprocess.run(
                [str(root / "scripts" / "aios_pingpong.sh"), "run"],
                cwd=root,
                env=env,
                check=False,
                capture_output=True,
                text=True,
            )

            self.assertEqual(result.returncode, 0, result.stderr or result.stdout)
            self.assertTrue(marker.exists())
            events = [
                json.loads(line)
                for line in (root / ".aios" / "state" / "aios_pingpong.jsonl").read_text(encoding="utf-8").splitlines()
            ]
            self.assertTrue(any(event["event"] == "agent_attempt" and event["agent"] == "claude" and event["status"] == "provider_backpressure" for event in events))
            self.assertTrue(any(event["event"] == "agent_done" and event["agent"] == "local" for event in events))

    def test_pin_required_noninteractive_falls_back_without_secret_storage(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = self.make_root(tmp)
            bin_dir = root / "bin"
            bin_dir.mkdir()
            marker = root / "fallback-ran"
            write_executable(
                bin_dir / "codex",
                "#!/usr/bin/env bash\n"
                "echo '틀렸습니다. (1/3)' >&2\n"
                "echo '틀렸습니다. (2/3)' >&2\n"
                "echo '접근 거부.' >&2\n"
                "exit 1\n",
            )
            write_executable(
                bin_dir / "claude",
                "#!/usr/bin/env bash\n"
                f"touch {marker.as_posix()}\n"
                "echo 'claude fallback completed after pin-gated codex'\n",
            )
            env = os.environ.copy()
            env["PATH"] = f"{bin_dir}{os.pathsep}{env['PATH']}"
            env["AIOS_MAX_ROUNDS"] = "1"
            env["AIOS_CONTINUE_AFTER_READY"] = "1"
            env["CODEX_TIMEOUT"] = "5"
            env["CLAUDE_TIMEOUT"] = "5"

            result = subprocess.run(
                [str(root / "scripts" / "aios_pingpong.sh"), "run"],
                cwd=root,
                env=env,
                check=False,
                capture_output=True,
                text=True,
            )

            self.assertEqual(result.returncode, 0, result.stderr or result.stdout)
            self.assertTrue(marker.exists())
            events = [
                json.loads(line)
                for line in (root / ".aios" / "state" / "aios_pingpong.jsonl").read_text(encoding="utf-8").splitlines()
            ]
            self.assertTrue(
                any(
                    event["event"] == "agent_attempt"
                    and event["agent"] == "codex"
                    and event["status"] == "pin_required_noninteractive"
                    for event in events
                )
            )
            self.assertTrue(any(event["event"] == "agent_done" and event["agent"] == "claude" for event in events))


if __name__ == "__main__":
    unittest.main()
