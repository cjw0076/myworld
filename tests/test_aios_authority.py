import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from scripts import aios_authority as authority


ROOT = Path(__file__).resolve().parents[1]
AUTH = ROOT / "scripts" / "aios_authority.py"
REGISTRY = ROOT / "scripts" / "aios_agent_registry.py"


class AuthorityTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name) / "workspace"
        (self.root / "docs").mkdir(parents=True)
        self.home = Path(self.tmp.name) / "agent-home"
        self.env = {**os.environ, "AIOS_AGENT_HOME": self.home.as_posix()}

    def run_registry(self, *args: str) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            [sys.executable, REGISTRY.as_posix(), "--root", self.root.as_posix(), *args],
            cwd=ROOT,
            env=self.env,
            text=True,
            capture_output=True,
            check=True,
        )

    def run_auth(self, *args: str) -> dict:
        completed = subprocess.run(
            [sys.executable, AUTH.as_posix(), "--root", self.root.as_posix(), *args, "--json"],
            cwd=ROOT,
            env=self.env,
            text=True,
            capture_output=True,
            check=True,
        )
        return json.loads(completed.stdout)

    def seed(self) -> None:
        self.run_registry("register", "--id", "operator@myworld", "--substrate", "codex_cli", "--capabilities", "operator")
        self.run_registry("register", "--id", "reviewer@memoryOS", "--substrate", "codex_cli", "--capabilities", "reviewer")
        self.run_registry("register", "--id", "outsider_peer", "--substrate", "ollama", "--capabilities", "outsider")

    def test_classes_include_all_six_citizenships(self) -> None:
        payload = self.run_auth("classes")
        self.assertEqual(payload["classes"], list(authority.CITIZENSHIP_CLASSES))

    def test_operator_can_release_but_outsider_cannot(self) -> None:
        self.seed()
        allowed = self.run_auth("verify", "--agent", "operator@myworld", "--action", "release_dispatch")
        denied = self.run_auth("verify", "--agent", "outsider_peer", "--action", "release_dispatch")

        self.assertTrue(allowed["allowed"])
        self.assertFalse(denied["allowed"])
        self.assertIn("requires_citizenship:operator", denied["reason"])

    def test_outsider_can_propose_contract(self) -> None:
        self.seed()
        payload = self.run_auth("verify", "--agent", "outsider_peer", "--action", "propose_contract")
        self.assertTrue(payload["allowed"])

    def test_reviewer_can_accept_memory_draft(self) -> None:
        self.seed()
        payload = self.run_auth("verify", "--agent", "reviewer@memoryOS", "--action", "accept_memory_draft")
        self.assertTrue(payload["allowed"])

    def test_bind_capability_is_forbidden(self) -> None:
        self.seed()
        payload = self.run_auth("verify", "--agent", "operator@myworld", "--action", "bind_capability")
        self.assertFalse(payload["allowed"])
        self.assertEqual(payload["reason"], "forbidden_action:bind_capability")

    def test_missing_registry_degrades_to_warning_allow(self) -> None:
        payload = self.run_auth("verify", "--agent", "unknown", "--action", "release_dispatch")
        self.assertFalse(payload["allowed"])
        self.assertEqual(payload["reason"], "requires_citizenship:operator")


if __name__ == "__main__":
    unittest.main()
