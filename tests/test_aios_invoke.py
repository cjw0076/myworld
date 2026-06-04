import json
import shutil
import subprocess
import sys
import unittest
from pathlib import Path
from unittest import mock


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "aios_invoke.py"


def load_module():
    import importlib.util

    spec = importlib.util.spec_from_file_location("aios_invoke", SCRIPT)
    module = importlib.util.module_from_spec(spec)
    assert spec and spec.loader
    spec.loader.exec_module(module)
    return module


class AiosInvokeTest(unittest.TestCase):
    def setUp(self) -> None:
        self.out = ROOT / ".aios" / "invocations" / "test-asc-0067"
        shutil.rmtree(self.out, ignore_errors=True)

    def tearDown(self) -> None:
        shutil.rmtree(self.out, ignore_errors=True)

    def run_cli(self, *args: str) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            [sys.executable, SCRIPT.as_posix(), "--root", ROOT.as_posix(), *args],
            cwd=ROOT,
            text=True,
            capture_output=True,
            check=False,
        )

    def test_happy_path_writes_all_artifacts_with_mocked_roles(self) -> None:
        module = load_module()
        genesis = {"schema_version": "genesisos.v1", "authority": "speculative_only", "branches": [{}, {}, {}, {}, {}]}
        capability = {"contract": "capabilityos.recommendations.v1", "recommendation_only": True, "recommendations": []}
        memory = {"decisions": [{"id": "mem-1"}], "retrieval_trace_id": "rtrace_fixture", "signal_coverage": 1.0}

        def fake_run_json(command, *, cwd, timeout=60):
            text = " ".join(command)
            if "genesisos.cli" in text:
                return "passed", genesis, ""
            if "memoryos.cli" in text:
                return "passed", memory, ""
            if "capabilityos.cli" in text:
                return "passed", capability, ""
            return "failed", None, "unexpected"

        with mock.patch.object(module, "run_json", side_effect=fake_run_json):
            args = module.build_parser().parse_args([
                "--root", ROOT.as_posix(),
                "--goal", "AIOS should route one task",
                "--write", ".aios/invocations/test-asc-0067",
                "--json",
            ])
            receipt = module.build_invocation(ROOT, args)

        self.assertEqual(receipt["schema_version"], "aios.invocation_receipt.v1")
        self.assertEqual(receipt["overall_status"], "passed")
        for rel in receipt["artifact_paths"].values():
            self.assertTrue((ROOT / rel).exists(), rel)
        envelope = json.loads((ROOT / receipt["session_envelope"]).read_text(encoding="utf-8"))
        self.assertEqual(envelope["schema_version"], "aios.session_envelope.v1")
        self.assertTrue(envelope["required_before_execution"])
        self.assertEqual(envelope["executor_assignment"]["default_executor"], "codex")
        self.assertEqual(envelope["role_statuses"]["memory"], "passed")
        self.assertEqual(envelope["role_artifacts"]["hive_execution_plan"], receipt["artifact_paths"]["hive"])
        context_pack = (ROOT / receipt["artifact_paths"]["memory_context_pack"]).read_text(encoding="utf-8")
        self.assertIn("trace_id: rtrace_fixture", context_pack)
        self.assertIn("signal_coverage: 1.0", context_pack)

    def test_missing_genesis_cli_fails_receipt(self) -> None:
        module = load_module()
        with mock.patch.object(module, "run_json", return_value=("failed", None, "missing")):
            args = module.build_parser().parse_args([
                "--root", ROOT.as_posix(),
                "--goal", "missing genesis",
                "--write", ".aios/invocations/test-asc-0067",
            ])
            receipt = module.build_invocation(ROOT, args)
        self.assertEqual(receipt["role_statuses"]["genesis"], "failed")
        envelope = json.loads((ROOT / receipt["session_envelope"]).read_text(encoding="utf-8"))
        self.assertIn("genesis", envelope["failed_roles"])
        self.assertEqual(envelope["degraded_receipt"]["status"], "degraded")
        self.assertIn("missing_genesis_artifact", receipt["stop_conditions_triggered"])
        self.assertNotEqual(receipt["overall_status"], "passed")

    def test_memory_unavailable_writes_degraded_context_pack(self) -> None:
        module = load_module()
        with mock.patch.object(module, "run_json", return_value=("failed", None, "provider blocked")):
            status, request, context, stops = module.memory_artifacts(ROOT, "memory degraded")
        self.assertEqual(status, "degraded")
        self.assertFalse(request["auto_accept"])
        self.assertEqual(stops, [])
        self.assertIn("auto_accept: false", context)

    def test_capability_executes_tools_is_blocked(self) -> None:
        module = load_module()
        with mock.patch.object(module, "run_json", return_value=("passed", {"recommendation_only": True, "recommendations": [{"executes_tools": True}]}, "")):
            status, payload, stops = module.capability_artifact(ROOT, "bad route")
        self.assertEqual(status, "failed")
        self.assertIn("capability_executes_tool", stops)

    def test_hive_plan_requires_contract_for_execution(self) -> None:
        module = load_module()
        _, plan, _ = module.hive_plan(ROOT, "goal", contract_id=None, plan_only=True)
        self.assertFalse(plan["execute_allowed"])
        self.assertEqual(plan["user_patterns"]["status"], "draft")
        _, plan, _ = module.hive_plan(ROOT, "goal", contract_id="ASC-0067", plan_only=False)
        self.assertTrue(plan["execute_allowed"])

    def test_output_cannot_escape_invocation_dir(self) -> None:
        result = self.run_cli("--goal", "escape", "--write", "tmp/outside", "--json")
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("invocation output must stay", result.stderr)

    def test_plan_only_does_not_modify_child_source_mtime(self) -> None:
        target = ROOT / "GenesisOS" / "genesisos" / "cli.py"
        before = target.stat().st_mtime_ns
        result = self.run_cli("--goal", "mtime smoke", "--write", ".aios/invocations/test-asc-0067", "--plan-only", "--json")
        self.assertIn(result.returncode, (0, 1), result.stderr)
        after = target.stat().st_mtime_ns
        self.assertEqual(before, after)


if __name__ == "__main__":
    unittest.main()
