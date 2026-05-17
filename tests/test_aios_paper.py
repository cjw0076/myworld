import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
PAPER = ROOT / "docs" / "papers" / "AIOS_AGENT_OPERATING_LAYER_DRAFT.md"
CLAIMS = ROOT / "docs" / "papers" / "AIOS_MYWORLD_CLAIM_LEDGER.md"
REFINEMENT = ROOT / "docs" / "papers" / "AIOS_AGENT_OPERATING_LAYER_REFINEMENT.md"
RELATED = ROOT / "docs" / "papers" / "AIOS_RELATED_WORK_SOURCE_RECEIPT.md"
INVOCATION = ROOT / ".aios" / "invocations" / "asc-0160-paper-refinement"
NEGATIVE_EVIDENCE = ROOT / "docs" / "AIOS_NEGATIVE_EVIDENCE_AND_COMBINATORIAL_CREATIVITY.md"
CREATIVITY_INVOCATION = ROOT / ".aios" / "invocations" / "asc-0163-negative-evidence-creativity"


class AiosPaperDraftTest(unittest.TestCase):
    def test_operating_layer_claim_is_present(self) -> None:
        text = PAPER.read_text(encoding="utf-8")

        self.assertIn("AIOS: An Agent Operating Layer for Reliable Long-Running AI Work", text)
        self.assertIn("AIOS does not replace provider CLIs", text)
        self.assertIn("Direct provider CLI workflow", text)
        self.assertIn("stateful operating loop", text)
        self.assertIn("operational overhead", text)

    def test_evaluation_does_not_conflate_provider_and_layer(self) -> None:
        text = PAPER.read_text(encoding="utf-8")

        self.assertIn("The provider must be held constant", text)
        self.assertIn("operating layer improves the management of long-running work", text)
        self.assertIn("Baseline:", text)
        self.assertIn("System:", text)

    def test_claim_ledger_tracks_new_paper_claims(self) -> None:
        text = CLAIMS.read_text(encoding="utf-8")

        for claim_id in (
            "C-011",
            "C-012",
            "C-013",
            "C-014",
            "C-015",
            "C-016",
            "C-017",
            "C-018",
            "C-019",
            "C-020",
            "C-021",
            "C-022",
        ):
            self.assertIn(claim_id, text)

    def test_refinement_loop_artifacts_are_recorded(self) -> None:
        for rel in (
            "receipt.json",
            "memory/context_pack.md",
            "capability/route.json",
            "genesis/branches.json",
            "hive/execution_plan.json",
        ):
            self.assertTrue((INVOCATION / rel).exists(), rel)

        text = REFINEMENT.read_text(encoding="utf-8")
        self.assertIn("rtrace_7124ea1c1fee8eff", text)
        self.assertIn("cap_memoryos_context_build", text)
        self.assertIn("failure_as_feature", text)

    def test_paper_contains_evidence_tightening_loop(self) -> None:
        text = PAPER.read_text(encoding="utf-8")

        self.assertIn("Evidence-Tightening Loop", text)
        self.assertIn("claim ledger update", text)
        self.assertIn("paper edit or claim downgrade", text)

    def test_related_work_is_source_grounded(self) -> None:
        paper = PAPER.read_text(encoding="utf-8")
        receipt = RELATED.read_text(encoding="utf-8")

        for label in ("AutoGen", "LangGraph", "SWE-agent", "OpenHands", "Temporal", "CrewAI", "OpenAI Swarm", "Cloudflare"):
            self.assertIn(label, receipt)
        for url in (
            "https://arxiv.org/abs/2308.08155",
            "https://docs.langchain.com/oss/python/langgraph/overview",
            "https://arxiv.org/abs/2405.15793",
            "https://arxiv.org/abs/2407.16741",
            "https://docs.temporal.io/",
            "https://docs.crewai.com/en/introduction",
            "https://github.com/openai/swarm",
            "https://developers.cloudflare.com/agents/concepts/long-running-agents/",
        ):
            self.assertIn(url, receipt)
        self.assertIn("AIOS_RELATED_WORK_SOURCE_RECEIPT.md", paper)
        self.assertIn("not a new foundation model", paper)
        self.assertIn("not a replacement", paper)

    def test_benchmark_protocol_tracks_negative_evidence(self) -> None:
        protocol = (ROOT / "docs" / "papers" / "AIOS_BENCHMARK_PROTOCOL.md").read_text(encoding="utf-8")
        paper = PAPER.read_text(encoding="utf-8")

        self.assertIn("negative_evidence_captured", protocol)
        self.assertIn("Negative Evidence Policy", protocol)
        self.assertIn("bad route", protocol)
        self.assertIn("bad routes", paper)

    def test_negative_evidence_and_combinatorial_creativity_spec(self) -> None:
        spec = NEGATIVE_EVIDENCE.read_text(encoding="utf-8")
        protocol = (ROOT / "docs" / "papers" / "AIOS_BENCHMARK_PROTOCOL.md").read_text(encoding="utf-8")
        paper = PAPER.read_text(encoding="utf-8")

        for term in (
            "failure_memory",
            "bad_tool_observation",
            "genesis_recombination_candidate",
            "draft-first",
            "provenance",
            "verification_seed",
            "human combination ability",
        ):
            self.assertIn(term, spec)
        self.assertIn("genesis_recombination_count", protocol)
        self.assertIn("Negative Evidence And Creativity Trace", protocol)
        self.assertIn("combinatorial creativity layer", paper)
        self.assertIn("AIOS_NEGATIVE_EVIDENCE_AND_COMBINATORIAL_CREATIVITY.md", paper)

    def test_asc0163_role_artifacts_are_recorded(self) -> None:
        for rel in (
            "receipt.json",
            "memory/context_pack.md",
            "capability/route.json",
            "genesis/branches.json",
            "hive/execution_plan.json",
        ):
            self.assertTrue((CREATIVITY_INVOCATION / rel).exists(), rel)

        spec = NEGATIVE_EVIDENCE.read_text(encoding="utf-8")
        self.assertIn("rtrace_0fa028fc49623cad", spec)
        self.assertIn("failure_as_feature", spec)
        self.assertIn("execute_allowed=false", spec)


if __name__ == "__main__":
    unittest.main()
