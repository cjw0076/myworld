import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "aios_instruction_index.py"


class AiosInstructionIndexTest(unittest.TestCase):
    def run_cli(self, root: Path, *args: str) -> subprocess.CompletedProcess[str]:
        result = subprocess.run(
            [sys.executable, SCRIPT.as_posix(), "--root", root.as_posix(), *args],
            text=True,
            capture_output=True,
            check=False,
        )
        if result.returncode != 0:
            self.fail(result.stderr or result.stdout)
        return result

    def test_indexes_instruction_files_and_excludes_runtime_paths(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "hivemind").mkdir()
            (root / "hivemind" / "AGENTS.md").write_text(
                "# Hive Agent\n\nMust run tests. Do not edit memoryOS.\n",
                encoding="utf-8",
            )
            (root / ".ai-runs").mkdir()
            (root / ".ai-runs" / "AGENTS.md").write_text("# Runtime noise\n", encoding="utf-8")

            result = self.run_cli(root, "--json")
            data = json.loads(result.stdout)

            paths = [entry["path"] for entry in data["entries"]]
            self.assertEqual(data["schema_version"], "aios.instruction_index.v1")
            self.assertIn("hivemind/AGENTS.md", paths)
            self.assertNotIn(".ai-runs/AGENTS.md", paths)
            self.assertEqual(data["counts"]["by_domain"]["hivemind"], 1)

    def test_writes_markdown_index(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "docs").mkdir()
            (root / "docs" / "README.md").write_text("# Docs\n\nRequired reading.\n", encoding="utf-8")
            output = root / "index.md"

            self.run_cli(root, "--write", output.as_posix())

            text = output.read_text(encoding="utf-8")
            self.assertIn("# AIOS Instruction Index", text)
            self.assertIn("docs/README.md", text)


if __name__ == "__main__":
    unittest.main()
