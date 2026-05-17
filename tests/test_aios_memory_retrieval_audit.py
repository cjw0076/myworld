import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
MEMORYOS = ROOT / "memoryOS"
SCRIPT = ROOT / "scripts" / "aios_memory_retrieval_audit.py"


class AiosMemoryRetrievalAuditTests(unittest.TestCase):
    def make_store(self, root: Path) -> tuple[str, str]:
        sys.path.insert(0, MEMORYOS.as_posix())
        from memoryos.schema import make_memory_object
        from memoryos.store import GraphStore

        store = GraphStore(root)
        store.ensure()
        first = make_memory_object(
            "decision",
            "Founder wants AIOS완성 공진화 memoryOS capabilityOS hive mind.",
            "founder_directive",
            "AIOS",
            ["docs/contracts/ASC-TEST.md:1"],
            confidence=0.9,
            status="accepted",
        )
        second = make_memory_object(
            "decision",
            "Founder wants 작업방식 few shot pattern extraction.",
            "founder_directive",
            "AIOS",
            ["docs/contracts/ASC-TEST.md:2"],
            confidence=0.9,
            status="accepted",
        )
        store.append_memory_objects([first, second])
        return first.id, second.id

    def run_audit(self, memory_root: Path, *case_args: str) -> dict:
        command = [
            sys.executable,
            SCRIPT.as_posix(),
            "--memoryos-dir",
            MEMORYOS.as_posix(),
            "--root",
            memory_root.as_posix(),
            "--json",
            *case_args,
        ]
        result = subprocess.run(command, cwd=ROOT, text=True, capture_output=True, check=False)
        self.assertEqual(result.returncode, 0, result.stderr)
        return json.loads(result.stdout)

    def test_audit_reports_hit_rate_and_trace_ids(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            memory_root = Path(tmp) / "memory-root"
            first_id, second_id = self.make_store(memory_root)

            payload = self.run_audit(
                memory_root,
                "--case",
                f"AIOS완성 공진화::{first_id}",
                "--case",
                f"few shot 작업방식::{second_id}",
            )

            self.assertEqual(payload["schema_version"], "aios.memory_retrieval_audit.v1")
            self.assertEqual(payload["retrieval_rate"], 1.0)
            self.assertTrue(payload["passed"])
            self.assertEqual(payload["hits"], 2)
            self.assertTrue(all(case.get("trace_id") for case in payload["cases"]))

    def test_audit_explains_task_filtered_miss(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            memory_root = Path(tmp) / "memory-root"
            first_id, second_id = self.make_store(memory_root)

            payload = self.run_audit(
                memory_root,
                "--case",
                f"AIOS완성 공진화::{first_id}",
                "--case",
                f"AIOS완성 공진화::{second_id}",
            )

            self.assertEqual(payload["retrieval_rate"], 0.5)
            missed = [case for case in payload["cases"] if not case["hit"]]
            self.assertEqual(len(missed), 1)
            self.assertEqual(missed[0]["expected_ids"], [second_id])
            self.assertEqual(missed[0]["drop_at_stage"], "excluded:task_no_match")


if __name__ == "__main__":
    unittest.main()
