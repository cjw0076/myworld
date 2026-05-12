import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "aios_semantic_handshake.py"


GLOSSARY = """# AIOS Shared Language

AIOS
AIOS smart contract
dispatch packet
memory draft
capability route
hive execution
stop condition
semantic handshake
"""


AGENT_TEXT = """# Agent

Read ../docs/AIOS_SHARED_LANGUAGE.md before cross-repo work.

Terms: AIOS, AIOS smart contract, dispatch packet, memory draft,
capability route, hive execution, stop condition, semantic handshake.
"""


class AiosSemanticHandshakeTest(unittest.TestCase):
    def run_cli(self, root: Path, *args: str, check: bool = True) -> subprocess.CompletedProcess[str]:
        result = subprocess.run(
            [sys.executable, SCRIPT.as_posix(), "--root", root.as_posix(), *args],
            text=True,
            capture_output=True,
            check=False,
        )
        if check and result.returncode != 0:
            self.fail(result.stderr or result.stdout)
        return result

    def make_root(self, tmp: str) -> Path:
        root = Path(tmp)
        (root / "docs").mkdir()
        (root / "docs" / "AIOS_SHARED_LANGUAGE.md").write_text(GLOSSARY, encoding="utf-8")
        for repo in ("hivemind", "memoryOS", "CapabilityOS"):
            (root / repo).mkdir()
            (root / repo / "AGENTS.md").write_text(AGENT_TEXT, encoding="utf-8")
        return root

    def test_passes_when_all_repo_agents_reference_shared_language(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = self.make_root(tmp)

            result = self.run_cli(root, "--json")

            data = json.loads(result.stdout)
            self.assertEqual(data["schema_version"], "aios.semantic_handshake.v1")
            self.assertEqual(data["status"], "pass")
            self.assertTrue(all(row["has_glossary_ref"] for row in data["repos"]))

    def test_fails_when_repo_agent_misses_contract_terms(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = self.make_root(tmp)
            (root / "memoryOS" / "AGENTS.md").write_text("# Agent\n\nAIOS only.\n", encoding="utf-8")

            result = self.run_cli(root, "--json", check=False)

            self.assertNotEqual(result.returncode, 0)
            data = json.loads(result.stdout)
            memory = next(row for row in data["repos"] if row["repo"] == "memoryOS")
            self.assertEqual(memory["status"], "fail")
            self.assertIn("dispatch packet", memory["missing_terms"])

    def test_writes_markdown_report(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = self.make_root(tmp)
            output = root / "docs" / "AIOS_SEMANTIC_HANDSHAKE.md"

            self.run_cli(root, "--write", output.as_posix())

            text = output.read_text(encoding="utf-8")
            self.assertIn("# AIOS Semantic Handshake Report", text)
            self.assertIn("| hivemind | pass | True | - |", text)


if __name__ == "__main__":
    unittest.main()
