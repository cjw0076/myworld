import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "aios_doc_scout.py"


class AiosDocScoutTest(unittest.TestCase):
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

    def test_scans_markdown_signals_and_excludes_private_or_dependency_paths(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "myworld" / "docs").mkdir(parents=True)
            (root / "myworld" / "docs" / "TODO.md").write_text(
                "# Plan\n\nP0: AIOS next contract TODO needs verification.\n",
                encoding="utf-8",
            )
            (root / "myworld" / "node_modules" / "pkg").mkdir(parents=True)
            (root / "myworld" / "node_modules" / "pkg" / "README.md").write_text(
                "# TODO dependency noise\n",
                encoding="utf-8",
            )
            (root / "myworld" / "memoryOS" / "data").mkdir(parents=True)
            (root / "myworld" / "memoryOS" / "data" / "private.md").write_text(
                "# TODO private raw data\n",
                encoding="utf-8",
            )
            (root / "myworld" / "docs" / "secret-plan.md").write_text(
                "# TODO secret plan\n",
                encoding="utf-8",
            )
            (root / "myworld" / "docs" / "AIOS_TASK_RADAR.md").write_text(
                "# AIOS Task Radar\n\nTODO generated self-feedback\n",
                encoding="utf-8",
            )
            (root / "myworld" / ".env.docs.md").write_text(
                "# TODO env-shaped file\n",
                encoding="utf-8",
            )

            result = self.run_cli(root, "--json")
            data = json.loads(result.stdout)

            paths = [task["path"] for task in data["top_tasks"]]
            self.assertIn("myworld/docs/TODO.md", paths)
            self.assertNotIn("myworld/node_modules/pkg/README.md", paths)
            self.assertNotIn("myworld/memoryOS/data/private.md", paths)
            self.assertNotIn("myworld/docs/secret-plan.md", paths)
            self.assertNotIn("myworld/docs/AIOS_TASK_RADAR.md", paths)
            self.assertNotIn("myworld/.env.docs.md", paths)
            self.assertEqual(data["schema_version"], "aios.doc_scout.v1")
            self.assertIn("p0", data["top_tasks"][0]["signals"]["counts"])

    def test_writes_markdown_task_radar(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "CapabilityOS").mkdir()
            (root / "CapabilityOS" / "README.md").write_text(
                "# CapabilityOS\n\nNEXT: add fallback plan verification.\n",
                encoding="utf-8",
            )
            output = root / "radar.md"

            self.run_cli(root, "--write", output.as_posix())

            text = output.read_text(encoding="utf-8")
            self.assertIn("# AIOS Task Radar", text)
            self.assertIn("CapabilityOS/README.md", text)
            self.assertIn("ASC-0008", text)

    def test_proposed_contract_ids_follow_existing_contract_index(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "myworld" / "docs" / "contracts").mkdir(parents=True)
            (root / "myworld" / "docs" / "contracts" / "ASC-0012-existing.md").write_text(
                "---\ncontract_id: ASC-0012\nstatus: closed\n---\n",
                encoding="utf-8",
            )
            (root / "myworld" / "docs" / "TODO.md").write_text(
                "# AIOS TODO\n\nTODO next verification.\n",
                encoding="utf-8",
            )

            result = self.run_cli(root, "--json")
            data = json.loads(result.stdout)

            self.assertEqual(data["proposed_contracts"][0]["contract_id"], "ASC-0013")


if __name__ == "__main__":
    unittest.main()
