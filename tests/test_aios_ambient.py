"""Ambient wiring (the moat): a download wires AIOS alongside each provider via their
published seams — idempotent, non-destructive, reversible, backed-up, JSON-validated.

Durability finding (2026-06-10): Claude Code regenerates ~/.claude/settings.json on launch
and strips externally-injected mcpServers/hooks. So the load-bearing MCP server lands in
~/.claude.json (app-canonical, durable); settings.json hooks are best-effort only. These
tests lock that in: claude durability is decided by ~/.claude.json, not settings.json.
"""
import json, sys, tempfile, unittest
from pathlib import Path
sys.path.insert(0, (Path(__file__).resolve().parents[1] / "scripts").as_posix())
import aios_ambient as A

ROOT = Path(__file__).resolve().parents[1]


class AmbientTests(unittest.TestCase):
    def _home(self):
        h = Path(tempfile.mkdtemp())
        (h / ".claude").mkdir()
        # a user settings.json the app owns (theme + an unrelated mcp the user may have set)
        (h / ".claude" / "settings.json").write_text('{"theme":"dark","mcpServers":{"other":{"command":"x"}}}')
        return h

    def test_dry_run_does_not_write(self):
        h = self._home()
        A.wire_all(h, ROOT, apply=False)
        self.assertFalse((h / ".claude.json").exists())          # durable seam untouched
        self.assertNotIn("aios", json.loads((h/".claude"/"settings.json").read_text()).get("mcpServers", {}))

    def test_durable_mcp_goes_to_claude_json(self):
        h = self._home()
        A.wire_all(h, ROOT, apply=True)
        durable = json.loads((h / ".claude.json").read_text())
        self.assertIn("aios", durable["mcpServers"])             # MCP server in the seam that persists

    def test_wire_is_non_destructive(self):
        h = self._home()
        A.wire_all(h, ROOT, apply=True)
        settings = json.loads((h/".claude"/"settings.json").read_text())
        self.assertEqual(settings["theme"], "dark")             # user key preserved
        self.assertIn("other", settings["mcpServers"])          # user's own mcp preserved
        self.assertIn("SessionStart", settings["hooks"])        # best-effort hooks added

    def test_backup_created(self):
        h = self._home()
        A.wire_all(h, ROOT, apply=True)
        self.assertTrue((h/".claude"/"settings.json.aios-bak").exists())

    def test_idempotent(self):
        h = self._home()
        A.wire_all(h, ROOT, apply=True)
        A.wire_all(h, ROOT, apply=True)
        settings = json.loads((h/".claude"/"settings.json").read_text())
        self.assertEqual(len(settings["hooks"]["SessionStart"]), 1)   # no double-add
        durable = json.loads((h/".claude.json").read_text())
        self.assertEqual(len([k for k in durable["mcpServers"] if k == "aios"]), 1)

    def test_reversible_keeps_user_config(self):
        h = self._home()
        A.wire_all(h, ROOT, apply=True)
        A.unwire_claude(h, apply=True)
        durable = json.loads((h/".claude.json").read_text())
        self.assertNotIn("aios", durable.get("mcpServers", {}))  # aios removed from durable seam
        settings = json.loads((h/".claude"/"settings.json").read_text())
        self.assertEqual(settings["theme"], "dark")             # user config intact
        self.assertIn("other", settings["mcpServers"])

    def test_codex_and_gemini_wired(self):
        h = self._home()
        A.wire_all(h, ROOT, apply=True)
        st = A.status(h)
        self.assertTrue(st["codex"] and st["gemini"])

    def test_status_is_decided_by_durable_seam_not_settings(self):
        h = self._home()
        self.assertFalse(A.status(h)["claude"])
        A.wire_all(h, ROOT, apply=True)
        self.assertTrue(A.status(h)["claude"])                  # true because ~/.claude.json has it
        # simulate the app stripping settings.json hooks on relaunch — durability must survive
        (h/".claude"/"settings.json").write_text('{"theme":"dark"}')
        self.assertTrue(A.status(h)["claude"])                  # still wired: the MCP seam persisted

    def test_atomic_write_leaves_no_tmp(self):
        h = self._home()
        A.wire_all(h, ROOT, apply=True)
        self.assertEqual(list((h).glob("**/*.aios-tmp")), [])    # no leftover temp files


if __name__ == "__main__":
    unittest.main()
