"""MCP gateway: external agents discover + invoke ALL AIOS organs through the
authority gate (deferred-loading — 2 gateway tools, not 150 schemas)."""
import json, sys, unittest
from pathlib import Path
sys.path.insert(0, (Path(__file__).resolve().parents[1] / "scripts").as_posix())
import aios_mcp_server as M

ROOT = Path(__file__).resolve().parents[1]

class GatewayTests(unittest.TestCase):
    def test_tools_list_advertises_gateway(self):
        names = {t["name"] for t in M.tool_specs()}
        self.assertIn("aios_list_tools", names)
        self.assertIn("aios_invoke", names)

    def test_discovery_returns_organ_catalog(self):
        ok, out = M.call_list_tools(ROOT, {})
        self.assertTrue(ok)
        tools = json.loads(out)["tools"]
        self.assertTrue(any(t["name"] == "self.audit" for t in tools))

    def test_invoke_read_organ_runs(self):
        ok, out = M.call_invoke(ROOT, {"tool": "self.audit",
            "arguments": {"claims": [{"text": "x", "path": "scripts/aios_mcp_server.py"}]},
            "agent": "codex@myworld"})
        self.assertTrue(ok)
        self.assertEqual(json.loads(out)["status"], "ok")

    def test_invoke_write_by_outsider_is_gated(self):
        ok, out = M.call_invoke(ROOT, {"tool": "fs.write", "arguments": {"path": "x"},
                                       "agent": "test_outsider"})
        self.assertEqual(json.loads(out)["status"], "needs_approval")  # not silently run

    def test_invoke_requires_tool_name(self):
        ok, _ = M.call_invoke(ROOT, {})
        self.assertFalse(ok)

if __name__ == "__main__":
    unittest.main()
