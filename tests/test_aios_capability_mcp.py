"""ASC-0212 — CapabilityOS MCP wrapper tests."""
from __future__ import annotations

import json
import subprocess
import sys
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
SCRIPT = REPO_ROOT / "scripts" / "aios_capability_mcp.py"


class CapabilityMcpTest(unittest.TestCase):
    def test_list_tools(self):
        r = subprocess.run(
            [sys.executable, str(SCRIPT), "list-tools"],
            capture_output=True, text=True, check=False,
            cwd=str(REPO_ROOT),
        )
        self.assertEqual(r.returncode, 0, r.stderr)
        tools = json.loads(r.stdout)
        names = {t["name"] for t in tools}
        self.assertIn("capability.recommend", names)
        self.assertIn("capability.audit", names)
        self.assertIn("capability.show", names)
        self.assertIn("capability.list", names)

    def test_unknown_tool_returns_error(self):
        r = subprocess.run(
            [sys.executable, str(SCRIPT), "call", "capability.nonexistent"],
            capture_output=True, text=True, check=False,
            cwd=str(REPO_ROOT),
        )
        self.assertEqual(r.returncode, 0, r.stderr)
        out = json.loads(r.stdout)
        self.assertIn("error", out)
        self.assertIn("available", out)

    def test_private_path_in_task_rejected(self):
        r = subprocess.run(
            [sys.executable, str(SCRIPT), "call", "capability.recommend",
             "--kwargs", '{"task":"_from_desktop/secrets.txt"}'],
            capture_output=True, text=True, check=False,
            cwd=str(REPO_ROOT),
        )
        self.assertEqual(r.returncode, 0, r.stderr)
        out = json.loads(r.stdout)
        self.assertIn("error", out)
        self.assertIn("private", out["error"])

    def test_audit_returns_catalog_state(self):
        r = subprocess.run(
            [sys.executable, str(SCRIPT), "call", "capability.audit"],
            capture_output=True, text=True, check=False,
            cwd=str(REPO_ROOT),
        )
        self.assertEqual(r.returncode, 0, r.stderr)
        out = json.loads(r.stdout)
        self.assertTrue(out.get("ok"), out)
        self.assertIn("catalog_complete", out["result"])


if __name__ == "__main__":
    unittest.main()
