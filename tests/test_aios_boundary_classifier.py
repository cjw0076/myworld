import json
import subprocess
import sys
import unittest
from pathlib import Path


SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "aios_boundary_classifier.py"


class AiosBoundaryClassifierTest(unittest.TestCase):
    def classify(self, question: str) -> dict:
        result = subprocess.run(
            [sys.executable, SCRIPT.as_posix(), "--question", question, "--json"],
            text=True,
            capture_output=True,
            check=False,
        )
        if result.returncode != 0:
            self.fail(result.stderr or result.stdout)
        return json.loads(result.stdout)

    def test_routes_process_lifecycle_to_hive_execution_substrate(self) -> None:
        data = self.classify("Should AIOS daemonize local LLM background cognition with PID survival and stop receipts?")

        self.assertEqual(data["schema_version"], "aios.boundary_classifier.v1")
        self.assertEqual(data["layer"], "execution_substrate")
        self.assertEqual(data["owner_repo"], "hivemind")
        self.assertEqual(data["substrate_level"], "runtime")
        self.assertEqual(data["authority"], "execute_with_receipt")
        self.assertIn("run_receipt", data["required_receipts"])

    def test_routes_tool_and_mcp_choice_to_capabilityos_recommendation(self) -> None:
        data = self.classify("Should we install a new MCP server or plugin for browser automation?")

        self.assertEqual(data["layer"], "capability_plugin_route")
        self.assertEqual(data["owner_repo"], "CapabilityOS")
        self.assertEqual(data["surface_type"], "mcp")
        self.assertEqual(data["authority"], "recommendation_only")
        self.assertIn("plugin_executes_without_contract", data["stop_conditions"])

    def test_routes_external_research_to_memory_knowledge_evidence(self) -> None:
        data = self.classify("Research latest provider API behavior from primary web docs before changing code")

        self.assertEqual(data["layer"], "memory_knowledge_route")
        self.assertEqual(data["owner_repo"], "memoryOS")
        self.assertEqual(data["knowledge_scope"], "web_primary_sources")
        self.assertEqual(data["authority"], "speculative_only")
        self.assertIn("source_evidence_receipt", data["required_receipts"])

    def test_routes_frame_ambiguity_to_genesis_challenge(self) -> None:
        data = self.classify("The final state is ambiguous; mutate assumptions and create counter branches before execution")

        self.assertEqual(data["layer"], "genesis_challenge")
        self.assertEqual(data["owner_repo"], "GenesisOS")
        self.assertEqual(data["authority"], "speculative_only")
        self.assertIn("genesis_branch_set", data["required_receipts"])

    def test_routes_filesystem_authority_to_kernel_primitive(self) -> None:
        data = self.classify("Need safe filesystem rollback, authority checks, and syscall receipt integrity")

        self.assertEqual(data["layer"], "kernel_primitive")
        self.assertEqual(data["owner_repo"], "myworld")
        self.assertEqual(data["substrate_level"], "primitive")
        self.assertEqual(data["surface_type"], "contract")
        self.assertIn("kernel_scope_creep", data["stop_conditions"])

    def test_multi_model_review_expands_knowledge_not_execution_authority(self) -> None:
        data = self.classify("Ask Claude, Gemini, Codex, and local LLM for all available knowledge and better ideas")

        self.assertEqual(data["layer"], "capability_plugin_route")
        self.assertEqual(data["owner_repo"], "CapabilityOS")
        self.assertEqual(data["knowledge_scope"], "multi_model_review")
        self.assertEqual(data["authority"], "recommendation_only")

    def test_unknown_question_defaults_to_clarifying_contract_surface(self) -> None:
        data = self.classify("Make it better")

        self.assertEqual(data["layer"], "contract_clarification")
        self.assertEqual(data["owner_repo"], "myworld")
        self.assertEqual(data["surface_type"], "contract")
        self.assertEqual(data["authority"], "speculative_only")
        self.assertIn("scope_ambiguous", data["stop_conditions"])


if __name__ == "__main__":
    unittest.main()
