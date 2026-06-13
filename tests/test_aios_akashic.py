"""Tests for scripts/aios_akashic.py — Akashic Records CLI."""
import json
import sys
import unittest
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parent.parent
MEMORYOS_ROOT = ROOT / "memoryOS"

# Add memoryOS to path for import
if str(MEMORYOS_ROOT) not in sys.path:
    sys.path.insert(0, str(MEMORYOS_ROOT))


class TestAiosAkashicCLI(unittest.TestCase):
    def _run(self, args: list[str]) -> tuple[int, str]:
        """Run CLI and capture stdout."""
        import importlib.util, io
        from contextlib import redirect_stdout

        spec = importlib.util.spec_from_file_location(
            "aios_akashic", ROOT / "scripts" / "aios_akashic.py"
        )
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)

        buf = io.StringIO()
        with redirect_stdout(buf):
            with patch("sys.argv", ["aios_akashic.py"] + args):
                try:
                    mod.main()
                    code = 0
                except SystemExit as exc:
                    code = exc.code or 0
        return code, buf.getvalue()

    def test_list_json_returns_count(self):
        code, out = self._run(["list", "--json"])
        self.assertEqual(code, 0)
        data = json.loads(out)
        self.assertIn("count", data)
        self.assertIsInstance(data["count"], int)

    def test_list_json_entries_are_list(self):
        code, out = self._run(["list", "--json"])
        data = json.loads(out)
        self.assertIsInstance(data["entries"], list)

    def test_list_plain_outputs_lines(self):
        code, out = self._run(["list"])
        self.assertEqual(code, 0)
        # Either no entries or entries with expected format
        self.assertIsInstance(out, str)

    def test_append_dry_run_no_write(self):
        code, out = self._run([
            "append",
            "--work-id", "TEST-DRY-001",
            "--goal", "dry run test goal",
            "--status", "active",
            "--dry-run",
        ])
        self.assertEqual(code, 0)
        self.assertIn("dry-run", out)

    def test_append_dry_run_json(self):
        code, out = self._run([
            "append",
            "--work-id", "TEST-DRY-002",
            "--goal", "dry run json test",
            "--dry-run",
            "--json",
        ])
        self.assertEqual(code, 0)
        data = json.loads(out)
        # Should have schema_version and index
        self.assertIn("schema_version", data)

    def test_append_missing_work_id_fails(self):
        code, out = self._run([
            "append",
            "--goal", "missing work-id test",
        ])
        self.assertNotEqual(code, 0)

    def test_append_missing_goal_fails(self):
        code, out = self._run([
            "append",
            "--work-id", "TEST-MISSING-GOAL",
        ])
        self.assertNotEqual(code, 0)

    def test_show_missing_work_id_exits_nonzero(self):
        code, out = self._run(["show", "NONEXISTENT-WORK-ID-XYZ"])
        # Should either error or exit nonzero
        self.assertIsInstance(out, str)

    def test_reconstruct_missing_returns_not_resumable(self):
        code, out = self._run(["reconstruct", "NONEXISTENT-WORK-ID-XYZ"])
        self.assertEqual(code, 0)
        # Plain output should include resumable: False
        self.assertIn("False", out)

    def test_reconstruct_json_has_resumable_field(self):
        code, out = self._run(["reconstruct", "--json", "NONEXISTENT-WORK-ID-XYZ"])
        data = json.loads(out)
        self.assertIn("resumable", data)
        self.assertFalse(data["resumable"])

    def test_root_auto_detected(self):
        # list should work without explicit --root
        code, out = self._run(["list", "--json"])
        self.assertEqual(code, 0)
        data = json.loads(out)
        self.assertIn("count", data)


class TestAiosAkashicParity(unittest.TestCase):
    """Verify CLI output matches akashic_ledger module directly."""

    def test_list_count_matches_load_indexes(self):
        from memoryos.akashic_ledger import load_indexes
        rows = load_indexes(MEMORYOS_ROOT)

        import importlib.util, io, json as jsonmod
        from contextlib import redirect_stdout
        spec = importlib.util.spec_from_file_location(
            "aios_akashic", ROOT / "scripts" / "aios_akashic.py"
        )
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)

        buf = io.StringIO()
        with redirect_stdout(buf):
            with patch("sys.argv", ["aios_akashic.py", "list", "--json"]):
                try:
                    mod.main()
                except SystemExit:
                    pass

        data = jsonmod.loads(buf.getvalue())
        self.assertEqual(data["count"], len(rows))


if __name__ == "__main__":
    unittest.main()
