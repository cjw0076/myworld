"""Ambient wiring (the moat): a download wires AIOS alongside each provider via their
published seams — idempotent, non-destructive, reversible, backed-up, JSON-validated."""
import json, sys, tempfile, unittest
from pathlib import Path
sys.path.insert(0, (Path(__file__).resolve().parents[1] / "scripts").as_posix())
import aios_ambient as A

ROOT = Path(__file__).resolve().parents[1]

class AmbientTests(unittest.TestCase):
    def _home(self):
        h = Path(tempfile.mkdtemp())
        (h / ".claude").mkdir()
        (h / ".claude" / "settings.json").write_text('{"theme":"dark","mcpServers":{"other":{"command":"x"}}}')
        return h

    def test_dry_run_does_not_write(self):
        h = self._home()
        A.wire_all(h, ROOT, apply=False)
        self.assertNotIn("aios", json.loads((h/".claude"/"settings.json").read_text())["mcpServers"])

    def test_wire_is_non_destructive(self):
        h = self._home()
        A.wire_all(h, ROOT, apply=True)
        cfg = json.loads((h/".claude"/"settings.json").read_text())
        self.assertEqual(cfg["theme"], "dark")              # user key preserved
        self.assertIn("other", cfg["mcpServers"])            # user mcp preserved
        self.assertIn("aios", cfg["mcpServers"])             # aios added alongside
        self.assertIn("SessionStart", cfg["hooks"])

    def test_backup_created(self):
        h = self._home()
        A.wire_all(h, ROOT, apply=True)
        self.assertTrue((h/".claude"/"settings.json.aios-bak").exists())

    def test_idempotent(self):
        h = self._home()
        A.wire_all(h, ROOT, apply=True)
        A.wire_all(h, ROOT, apply=True)
        cfg = json.loads((h/".claude"/"settings.json").read_text())
        self.assertEqual(len(cfg["hooks"]["SessionStart"]), 1)   # no double-add

    def test_reversible_keeps_user_config(self):
        h = self._home()
        A.wire_all(h, ROOT, apply=True)
        A.unwire_claude(h, apply=True)
        cfg = json.loads((h/".claude"/"settings.json").read_text())
        self.assertNotIn("aios", cfg["mcpServers"])          # aios removed
        self.assertEqual(cfg["theme"], "dark")               # user config intact
        self.assertIn("other", cfg["mcpServers"])

    def test_codex_and_gemini_wired(self):
        h = self._home()
        A.wire_all(h, ROOT, apply=True)
        st = A.status(h)
        self.assertTrue(st["codex"] and st["gemini"])

    def test_status_reflects_wiring(self):
        h = self._home()
        self.assertFalse(A.status(h)["claude"])
        A.wire_all(h, ROOT, apply=True)
        self.assertTrue(A.status(h)["claude"])

if __name__ == "__main__":
    unittest.main()
