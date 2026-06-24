from __future__ import annotations

import importlib.util
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SCRIPTS = ROOT / "scripts"


def _load():
    spec = importlib.util.spec_from_file_location("aios_sources_uut", SCRIPTS / "aios_sources.py")
    m = importlib.util.module_from_spec(spec)
    sys.modules["aios_sources_uut"] = m
    if str(SCRIPTS) not in sys.path:
        sys.path.insert(0, str(SCRIPTS))
    spec.loader.exec_module(m)
    return m


class SourceFrameworkTest(unittest.TestCase):
    def setUp(self):
        self.m = _load()

    def test_filesource_pulls_human_native_notes(self):
        with tempfile.TemporaryDirectory() as d:
            (Path(d) / "a.md").write_text("a diary line about figma", encoding="utf-8")
            (Path(d) / "b.txt").write_text("a note", encoding="utf-8")
            (Path(d) / "skip.png").write_text("binary-ish", encoding="utf-8")
            src = self.m.FileSource("diary", d, category="personal")
            self.assertTrue(src.available())
            items = src.pull()
            self.assertEqual(len(items), 2)            # .md + .txt, not .png
            self.assertTrue(all("content" in i and "ref" in i for i in items))

    def test_ingest_dry_run_and_opt_in_gate(self):
        with tempfile.TemporaryDirectory() as d:
            (Path(d) / "n.md").write_text("note one", encoding="utf-8")
            self.m.register(self.m.FileSource("tsrc", d, category="personal"))
            # dry-run: found, nothing written
            dry = self.m.ingest_source("tsrc", ROOT, frozenset(["personal"]), apply=False)
            self.assertEqual(dry["status"], "ok")
            self.assertEqual(dry["found"], 1)
            self.assertEqual(dry["written"], 0)
            # opt-in privacy gate: category not allowed → skipped, nothing pulled to ledger
            blk = self.m.ingest_source("tsrc", ROOT, frozenset(["code"]))
            self.assertEqual(blk["status"], "skipped_opt_in")

    def test_unknown_source_is_honest(self):
        out = self.m.ingest_source("nope", ROOT, frozenset(["personal"]))
        self.assertEqual(out["status"], "unknown_source")

    def test_harvest_registers_provider_mcp_adapters(self):
        # harvest reads the providers' wired MCP configs and auto-registers adapters
        summary = self.m.harvest_provider_adapters()
        self.assertIn("mcp", summary)
        self.assertIsInstance(summary["mcp"], list)
        # whatever was harvested is registered + flagged harvested with an origin
        for nm in summary["mcp"]:
            a = self.m.SOURCES[nm]
            self.assertTrue(a.available())            # wired into a provider
            self.assertEqual(a.kind, "mcp")
            self.assertIn(getattr(a, "origin", ""), ("claude", "codex"))
            self.assertEqual(a.pull(), [])            # honest: protocol harvested, pull binds later

    def test_harvested_adapter_listed_with_origin(self):
        self.m.register(self.m._HarvestedMcp("notion", origin="claude"))
        row = next(r for r in self.m.list_sources() if r["name"] == "notion")
        self.assertTrue(row["harvested"])
        self.assertEqual(row["origin"], "claude")


if __name__ == "__main__":
    unittest.main()
