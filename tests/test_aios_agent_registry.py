import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from scripts import aios_agent_registry as registry


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "aios_agent_registry.py"


class AgentRegistryTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name) / "workspace"
        (self.root / "docs").mkdir(parents=True)
        self.home = Path(self.tmp.name) / "agent-home"
        self.env = {**os.environ, "AIOS_AGENT_HOME": self.home.as_posix()}

    def run_cli(self, *args: str, check: bool = True,
                env: dict[str, str] | None = None) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            [sys.executable, SCRIPT.as_posix(), "--root", self.root.as_posix(), *args],
            cwd=ROOT,
            env=env if env is not None else self.env,
            text=True,
            capture_output=True,
            check=check,
        )

    def test_register_list_verify_and_doc_mirror(self) -> None:
        registered = self.run_cli(
            "register",
            "--id",
            "claude@myworld",
            "--substrate",
            "claude_code",
            "--capabilities",
            "operator,reviewer",
            "--json",
        )

        payload = json.loads(registered.stdout)
        self.assertTrue(payload["ok"])
        self.assertTrue((self.home / "agents.json").exists())
        doc = (self.root / "docs" / "AIOS_AGENTS_REGISTRY.md").read_text(encoding="utf-8")
        self.assertIn("claude@myworld", doc)
        self.assertIn("operator", doc)

        listed = json.loads(self.run_cli("list", "--json").stdout)
        self.assertEqual(listed["agents"][0]["agent_id"], "claude@myworld")

        verified = json.loads(self.run_cli("verify", "claude@myworld", "--json").stdout)
        self.assertTrue(verified["valid"])
        self.assertEqual(verified["reason"], "registered")

    def test_verify_unknown_agent_is_warning_not_error(self) -> None:
        completed = self.run_cli("verify", "unknown@myworld", "--json")
        payload = json.loads(completed.stdout)
        self.assertFalse(payload["valid"])
        self.assertEqual(payload["reason"], "unknown_agent")

    def test_invalid_agent_id_fails(self) -> None:
        completed = self.run_cli(
            "register",
            "--id",
            "bad id",
            "--substrate",
            "codex_cli",
            "--capabilities",
            "operator",
            check=False,
        )

        self.assertEqual(completed.returncode, 2)
        self.assertIn("agent id", completed.stderr)

    def test_current_infers_codex_by_default(self) -> None:
        # Isolate the env: the default-inference path is only exercised when
        # no agent-detection variable is set. Without this, the test passes
        # under codex and fails under claude — a brittle environment leak.
        clean_env = {k: v for k, v in self.env.items()
                     if k not in ("CLAUDECODE", "CLAUDE_CODE", "AIOS_AGENT_ID")}
        payload = json.loads(self.run_cli("current", "--json", env=clean_env).stdout)
        self.assertEqual(payload["agent_id"], "codex@myworld")
        self.assertTrue(payload["inferred"])

    def test_current_infers_claude_when_claudecode_set(self) -> None:
        env = {**self.env, "CLAUDECODE": "1"}
        env.pop("AIOS_AGENT_ID", None)
        payload = json.loads(self.run_cli("current", "--json", env=env).stdout)
        self.assertEqual(payload["agent_id"], "claude@myworld")
        self.assertTrue(payload["inferred"])

    def test_parse_capabilities_deduplicates(self) -> None:
        self.assertEqual(registry.parse_capabilities("operator,reviewer,operator"), ["operator", "reviewer"])


if __name__ == "__main__":
    unittest.main()
