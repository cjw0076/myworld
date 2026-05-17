import importlib.util
import json
import subprocess
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch


SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "aios_dream.py"


def load_dream_module():
    spec = importlib.util.spec_from_file_location("aios_dream_under_test", SCRIPT)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class AiosDreamTest(unittest.TestCase):
    def test_graph_control_stage_summarizes_persisted_memoryos_run(self) -> None:
        module = load_dream_module()
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "memoryOS").mkdir()
            payload = {
                "contract_id": "ASC-0194",
                "stage": "graph_control_model",
                "report_id": "gcr_demo",
                "persisted": True,
                "bound_ratio": 1.25,
                "raw_ingest_count": 4,
                "reclaimed_count": 5,
                "queryable_surface_count": 3,
                "stop_conditions": [],
                "halt_auto_consolidation": False,
                "filters": {"project": "AIOS", "limit": 10},
            }
            completed = subprocess.CompletedProcess(
                args=["memoryos"], returncode=0, stdout=json.dumps(payload), stderr=""
            )

            with patch.object(module.subprocess, "run", return_value=completed) as run_mock:
                result = module.run_memory_graph_control(root, timeout_seconds=7)

        self.assertEqual(result["status"], "ok")
        self.assertEqual(result["report_id"], "gcr_demo")
        self.assertTrue(result["persisted"])
        self.assertEqual(result["bound_ratio"], 1.25)
        self.assertIn("review-gated", result["boundary"])
        command = run_mock.call_args.args[0]
        self.assertIn("graph-control", command)
        self.assertIn("--persist", command)
        self.assertEqual(run_mock.call_args.kwargs["timeout"], 7)

    def test_graph_control_stage_degrades_on_timeout(self) -> None:
        module = load_dream_module()
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "memoryOS").mkdir()
            with patch.object(
                module.subprocess,
                "run",
                side_effect=subprocess.TimeoutExpired(cmd=["memoryos"], timeout=3),
            ):
                result = module.run_memory_graph_control(root, timeout_seconds=3)

        self.assertEqual(result["status"], "degraded")
        self.assertEqual(result["reason"], "graph_control_timeout")
        self.assertTrue(result["timed_out"])
        self.assertIn("no closeout claim", result["boundary"])

    def test_consolidation_helper_is_bounded(self) -> None:
        module = load_dream_module()
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            with patch.object(
                module.subprocess,
                "run",
                side_effect=subprocess.TimeoutExpired(cmd=["helper"], timeout=5),
            ):
                ok, message = module.call_consolidation_helper(root, "digest", timeout_seconds=5)

        self.assertFalse(ok)
        self.assertIn("timed out after 5s", message)

    def test_embedding_coverage_degrades_on_stats_timeout(self) -> None:
        module = load_dream_module()
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "memoryOS").mkdir()
            with patch.object(
                module.subprocess,
                "run",
                side_effect=subprocess.TimeoutExpired(cmd=["memoryos", "stats"], timeout=2),
            ):
                result = module.embedding_coverage(root, timeout_seconds=2)

        self.assertEqual(result["status"], "unavailable")
        self.assertEqual(result["reason"], "stats_timeout")


if __name__ == "__main__":
    unittest.main()
