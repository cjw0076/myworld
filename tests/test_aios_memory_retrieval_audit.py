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

    def add_product_object(self, root: Path) -> str:
        sys.path.insert(0, MEMORYOS.as_posix())
        from memoryos.schema import make_memory_object
        from memoryos.store import GraphStore

        store = GraphStore(root)
        store.ensure()
        product = make_memory_object(
            "decision",
            "URI public-content sourcing: clean-room pointer-first, zero fabrication.",
            "claude",
            "URI",
            ["uri/docs/CAMPUS_WIKI_SEED.md:1"],
            confidence=0.8,
            status="accepted",
        )
        store.append_memory_objects([product])
        return product.id

    def test_is_internal_classification(self) -> None:
        sys.path.insert(0, (ROOT / "scripts").as_posix())
        import aios_memory_retrieval_audit as audit

        self.assertTrue(audit._is_internal("AIOS"))
        self.assertTrue(audit._is_internal("hivemind"))
        self.assertTrue(audit._is_internal("Hive Mind"))
        self.assertTrue(audit._is_internal("memoryOS"))
        self.assertFalse(audit._is_internal("URI"))
        self.assertFalse(audit._is_internal(None))

    def test_domain_coverage_alarm_when_only_internal(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            memory_root = Path(tmp) / "memory-root"
            first_id, _ = self.make_store(memory_root)

            payload = self.run_audit(memory_root, "--case", f"AIOS완성 공진화::{first_id}")

            cov = payload["domain_coverage"]
            self.assertEqual(cov["status"], "ok")
            self.assertEqual(cov["product"], 0)
            self.assertEqual(cov["internal"], cov["total_accepted"])
            self.assertTrue(cov["inward_growth_alarm"])

    def test_domain_coverage_counts_product(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            memory_root = Path(tmp) / "memory-root"
            self.make_store(memory_root)
            product_id = self.add_product_object(memory_root)

            # project filter on --case defaults to AIOS, so the URI object need
            # not be retrieved here — this test asserts coverage, not the hit.
            payload = self.run_audit(
                memory_root,
                "--min-rate",
                "0",
                "--case",
                f"uri clean-room sourcing::{product_id}",
            )

            cov = payload["domain_coverage"]
            self.assertEqual(cov["product"], 1)
            self.assertFalse(cov["inward_growth_alarm"])
            self.assertAlmostEqual(cov["product_coverage"], 1 / cov["total_accepted"], places=3)
            self.assertIn("URI", cov["by_project"])

    def test_durable_ref_path(self) -> None:
        sys.path.insert(0, (ROOT / "scripts").as_posix())
        import aios_memory_retrieval_audit as audit

        # skipped: urls, ids, ephemeral run artifacts, non-paths
        self.assertIsNone(audit.durable_ref_path("aios://memory-draft/123"))
        self.assertIsNone(audit.durable_ref_path("src_f007c0049be329e5"))
        self.assertIsNone(audit.durable_ref_path("mem_517caac18c12b2b0"))
        self.assertIsNone(audit.durable_ref_path(".runs/run_x/final_report.md"))
        self.assertIsNone(audit.durable_ref_path(".agent/pingpong/logs/claude.log"))
        self.assertIsNone(audit.durable_ref_path("README"))  # no slash
        # durable: suffixes stripped
        self.assertEqual(
            audit.durable_ref_path("myworld/memoryOS/docs/TODO.md#L1-L9;signals=a,b"),
            "myworld/memoryOS/docs/TODO.md",
        )
        self.assertEqual(audit.durable_ref_path("docs/contracts/ASC-TEST.md:12"), "docs/contracts/ASC-TEST.md")
        self.assertEqual(audit.durable_ref_path("uri/src/lib/festival-data.ts"), "uri/src/lib/festival-data.ts")

    def test_ref_exists(self) -> None:
        sys.path.insert(0, (ROOT / "scripts").as_posix())
        import aios_memory_retrieval_audit as audit

        self.assertTrue(audit.ref_exists("scripts/aios_commit_guard.py", [ROOT]))
        self.assertFalse(audit.ref_exists("docs/THIS_DOES_NOT_EXIST_zzz.md", [ROOT]))

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
