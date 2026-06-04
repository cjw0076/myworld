import json
import subprocess
import sys
import time
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, (ROOT / "scripts").as_posix())

import aios_ritual_gate as gate

HOOK = ROOT / "scripts" / "aios_guard_hook.py"


def run_hook(payload: dict) -> str:
    r = subprocess.run(
        [sys.executable, HOOK.as_posix()],
        input=json.dumps(payload),
        text=True,
        capture_output=True,
        cwd=ROOT,
    )
    return r.stdout.strip()


class RitualGateTests(unittest.TestCase):
    def setUp(self) -> None:
        self._orig = gate.TOKEN

    def tearDown(self) -> None:
        gate.TOKEN = self._orig

    def test_freshness(self) -> None:
        import tempfile

        with tempfile.TemporaryDirectory() as tmp:
            gate.TOKEN = Path(tmp) / "decide.token"
            self.assertFalse(gate.is_fresh(60))  # missing
            gate.record("x")
            self.assertTrue(gate.is_fresh(60))  # fresh
            gate.TOKEN.write_text(json.dumps({"ts": time.time() - 7200}))
            self.assertFalse(gate.is_fresh(60))  # 2h old > 60min


class GuardHookSafetyTests(unittest.TestCase):
    def test_allows_normal_bash(self) -> None:
        self.assertEqual(run_hook({"tool_name": "Bash", "tool_input": {"command": "ls -la"}}), "")

    def test_allows_normal_write(self) -> None:
        self.assertEqual(
            run_hook({"tool_name": "Write", "tool_input": {"file_path": "scripts/foo.py"}}), ""
        )

    def test_fails_open_on_malformed_stdin(self) -> None:
        r = subprocess.run(
            [sys.executable, HOOK.as_posix()], input="not json", text=True, capture_output=True, cwd=ROOT
        )
        self.assertEqual(r.stdout.strip(), "")
        self.assertEqual(r.returncode, 0)

    def test_denies_contract_write_without_token(self) -> None:
        # Ensure no fresh token, then a contract Write must be denied.
        if gate.TOKEN.exists():
            gate.TOKEN.unlink()
        out = run_hook(
            {"tool_name": "Write", "tool_input": {"file_path": "docs/contracts/ASC-0000-probe.md"}}
        )
        self.assertIn('"permissionDecision": "deny"', out)

    def test_denies_bash_contract_write_without_token(self) -> None:
        # codex review #3: a contract created via shell write must also be gated.
        if gate.TOKEN.exists():
            gate.TOKEN.unlink()
        out = run_hook(
            {"tool_name": "Bash", "tool_input": {"command": "echo x > docs/contracts/ASC-0000-probe.md"}}
        )
        self.assertIn('"permissionDecision": "deny"', out)

    def test_allows_bash_contract_read(self) -> None:
        # Reading a contract (no write verb) must NOT be gated.
        self.assertEqual(
            run_hook({"tool_name": "Bash", "tool_input": {"command": "cat docs/contracts/ASC-0000-probe.md"}}),
            "",
        )


if __name__ == "__main__":
    unittest.main()
