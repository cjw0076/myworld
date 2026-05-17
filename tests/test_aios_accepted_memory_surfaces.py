import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
MEMORYOS = ROOT / "memoryOS"


class AiosAcceptedMemorySurfacesTests(unittest.TestCase):
    def run_memoryos(self, memory_root: Path, *args: str) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            [sys.executable, "-m", "memoryos.cli", "--root", memory_root.as_posix(), *args],
            cwd=MEMORYOS,
            text=True,
            capture_output=True,
            check=False,
        )

    def test_approved_draft_surfaces_in_context_build(self) -> None:
        sys.path.insert(0, MEMORYOS.as_posix())
        from memoryos.schema import make_memory_object
        from memoryos.store import GraphStore

        with tempfile.TemporaryDirectory() as tmp:
            memory_root = Path(tmp) / "memory-root"
            store = GraphStore(memory_root)
            store.ensure()
            obj = make_memory_object(
                "decision",
                "ASC-TEST accepted memory should surface for retrieval probe.",
                "mixed",
                "AIOS",
                ["docs/contracts/ASC-TEST.md"],
                confidence=0.91,
                status="draft",
            )
            store.append_memory_objects([obj])

            approve = self.run_memoryos(
                memory_root,
                "drafts",
                "approve",
                obj.id,
                "--reviewer",
                "test-operator",
                "--note",
                "accepted memory surface test",
            )
            self.assertEqual(approve.returncode, 0, approve.stderr)

            context = self.run_memoryos(
                memory_root,
                "context",
                "build",
                "--task",
                "ASC-TEST retrieval probe",
                "--for",
                "hive",
                "--project",
                "AIOS",
                "--json",
            )
            self.assertEqual(context.returncode, 0, context.stderr)
            payload = json.loads(context.stdout)
            selected_ids = [
                item.get("id")
                for key in ("decisions", "constraints", "open_questions", "recent_actions", "other")
                for item in payload.get(key, [])
            ]

            self.assertEqual(payload["total_accepted"], 1)
            self.assertIn(obj.id, selected_ids)


if __name__ == "__main__":
    unittest.main()
