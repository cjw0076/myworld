import json
import subprocess
import sys
import tempfile
import unittest
from argparse import Namespace
from pathlib import Path
from unittest import mock


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "aios_ask.py"


def load_module():
    import importlib.util

    spec = importlib.util.spec_from_file_location("aios_ask", SCRIPT)
    module = importlib.util.module_from_spec(spec)
    assert spec and spec.loader
    sys.path.insert(0, str(ROOT / "scripts"))
    try:
        spec.loader.exec_module(module)
    finally:
        try:
            sys.path.remove(str(ROOT / "scripts"))
        except ValueError:
            pass
    return module


class AiosAskTests(unittest.TestCase):
    def fake_invocation(self, root: Path, ask_id: str) -> dict:
        inv_dir = root / ".aios" / "invocations" / ask_id
        genesis = inv_dir / "genesis" / "branches.json"
        capability = inv_dir / "capability" / "route.json"
        hive = inv_dir / "hive" / "execution_plan.json"
        memory = inv_dir / "memory" / "context_pack.md"
        request = inv_dir / "memory" / "context_request.json"
        for path in [genesis, capability, hive, memory, request]:
            path.parent.mkdir(parents=True, exist_ok=True)
        genesis.write_text(
            json.dumps(
                {
                    "authority": "speculative_only",
                    "branches": [
                        {
                            "premise": "Treat ask as city planning, not a command.",
                            "contract_seed": "Explore ask as control-plane zoning.",
                        },
                        {
                            "premise": "Treat missing friction as the product signal.",
                            "contract_seed": "Explore ask as discomfort capture.",
                        },
                    ],
                }
            ),
            encoding="utf-8",
        )
        capability.write_text(
            json.dumps(
                {
                    "recommendation_only": True,
                    "recommendations": [
                        {"id": "cap_hivemind_execution_harness"},
                        {"id": "cap_memoryos_context_build"},
                    ],
                }
            ),
            encoding="utf-8",
        )
        hive.write_text(
            json.dumps({"verification_gate": ["python -m unittest tests/test_aios_ask.py"]}),
            encoding="utf-8",
        )
        memory.write_text("# Context\n", encoding="utf-8")
        request.write_text(json.dumps({"auto_accept": False}), encoding="utf-8")
        return {
            "schema_version": "aios.invocation_receipt.v1",
            "invocation_id": ask_id,
            "overall_status": "passed",
            "role_statuses": {"genesis": "passed", "memory": "passed", "capability": "passed", "hive": "passed"},
            "artifact_paths": {
                "genesis": f".aios/invocations/{ask_id}/genesis/branches.json",
                "capability": f".aios/invocations/{ask_id}/capability/route.json",
                "hive": f".aios/invocations/{ask_id}/hive/execution_plan.json",
                "memory_context_pack": f".aios/invocations/{ask_id}/memory/context_pack.md",
                "memory_request": f".aios/invocations/{ask_id}/memory/context_request.json",
                "receipt": f".aios/invocations/{ask_id}/receipt.json",
            },
            "next_action": "dispatch_ready",
        }

    def test_build_ask_writes_instruction_and_valid_praxis(self) -> None:
        module = load_module()
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            goal = "Build AIOS ask interface"
            ask_id = "ask-test"
            args = Namespace(goal_text=goal, write=f".aios/asks/{ask_id}", draft_contract=True)

            def fake_build_invocation(root_arg, invocation_args):
                self.assertEqual(root_arg, root)
                return self.fake_invocation(root, ask_id)

            with mock.patch.object(module.aios_invoke, "build_invocation", side_effect=fake_build_invocation):
                receipt = module.build_ask(root, args)

            self.assertEqual(receipt["schema_version"], "aios.ask.receipt.v1")
            self.assertEqual(receipt["status"], "passed")
            praxis = json.loads((root / ".aios" / "asks" / ask_id / "praxis.json").read_text(encoding="utf-8"))
            self.assertEqual(praxis["memory_context"]["status"], "used")
            self.assertIn("aios://capability/cap_hivemind_execution_harness", praxis["capability_routes"]["routes"])
            self.assertIn("Explore ask as control-plane zoning.", praxis["genesis_reframe"]["alternative_frames"])
            self.assertIn("python -m unittest tests/test_aios_ask.py", praxis["hive_execution_plan"]["verification_gate"])
            instruction = (root / ".aios" / "asks" / ask_id / "instruction.md").read_text(encoding="utf-8")
            self.assertIn("Operator Next Step", instruction)
            seed = (root / ".aios" / "asks" / ask_id / "contract_seed.md").read_text(encoding="utf-8")
            self.assertIn("contract_id: ASC-XXXX", seed)
            self.assertIn("praxis_required: true", seed)
            self.assertIn("## AIOS Role Evidence", seed)
            self.assertIn("### MemoryOS", seed)
            self.assertIn("### CapabilityOS", seed)
            self.assertIn("### GenesisOS", seed)
            self.assertIn("### Hive Mind", seed)
            self.assertEqual(receipt["artifact_paths"]["contract_seed"], ".aios/asks/ask-test/contract_seed.md")

    def test_output_cannot_escape_ask_dir(self) -> None:
        result = subprocess.run(
            [sys.executable, SCRIPT.as_posix(), "--root", ROOT.as_posix(), "--write", "tmp/outside", "escape", "--json"],
            cwd=ROOT,
            text=True,
            capture_output=True,
            check=False,
        )
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("ask output must stay", result.stderr)


if __name__ == "__main__":
    unittest.main()
