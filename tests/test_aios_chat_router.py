import json
import os
import subprocess
import sys
import tempfile
import unittest
import importlib.util
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "aios_chat_router.py"


def write_executable(path: Path, body: str) -> None:
    path.write_text(body, encoding="utf-8")
    path.chmod(path.stat().st_mode | 0o100)


class AiosChatRouterTest(unittest.TestCase):
    def load_router_module(self):
        scripts_dir = (ROOT / "scripts").as_posix()
        if scripts_dir not in sys.path:
            sys.path.insert(0, scripts_dir)
        spec = importlib.util.spec_from_file_location("aios_chat_router_test_module", SCRIPT)
        module = importlib.util.module_from_spec(spec)
        assert spec and spec.loader
        spec.loader.exec_module(module)
        return module

    def run_router(self, root: Path, message: str, conversation: str = "demo", env: dict[str, str] | None = None) -> dict:
        run_env = os.environ.copy()
        if env:
            run_env.update(env)
        result = subprocess.run(
            [
                sys.executable,
                SCRIPT.as_posix(),
                "--root",
                root.as_posix(),
                "--conversation",
                conversation,
                "--message",
                message,
                "--json",
            ],
            cwd=ROOT,
            text=True,
            capture_output=True,
            env=run_env,
            check=True,
        )
        return json.loads(result.stdout)

    def install_fake_memoryos(self, root: Path) -> None:
        package = root / "memoryOS" / "memoryos"
        package.mkdir(parents=True)
        (package / "__init__.py").write_text("", encoding="utf-8")
        (package / "cli.py").write_text(
            "import json\n"
            "print(json.dumps({\n"
            "  'trace_id': 'rtrace_test_memory',\n"
            "  'decisions': [\n"
            "    {'id': 'mem_founder_1', 'type': 'decision', 'content': 'Founder wants AIOS to absorb provider CLIs behind one operating interface.', 'confidence': 0.9, 'raw_refs': ['docs/contracts/ASC-0052.md:8']},\n"
            "    {'id': 'mem_founder_2', 'type': 'decision', 'content': 'Founder delegated operator role to AIOS and expects continuous coevolution.', 'confidence': 0.9, 'raw_refs': ['docs/contracts/ASC-0051.md:9']}\n"
            "  ],\n"
            "  'constraints': [], 'open_questions': [], 'recent_actions': [], 'other': []\n"
            "}, ensure_ascii=False))\n",
            encoding="utf-8",
        )

    def install_fake_negative_memoryos(self, root: Path) -> None:
        package = root / "memoryOS" / "memoryos"
        package.mkdir(parents=True)
        (package / "__init__.py").write_text("", encoding="utf-8")
        (package / "cli.py").write_text(
            "import json\n"
            "print(json.dumps({\n"
            "  'trace_id': 'rtrace_negative_memory',\n"
            "  'decisions': [], 'constraints': [], 'open_questions': [], 'recent_actions': [],\n"
            "  'other': [\n"
            "    {'id': 'mem_fail_1', 'type': 'failure_memory', 'content': 'Codex provider failed with pin_required_noninteractive; route fallback instead of waiting.', 'confidence': 0.88, 'raw_refs': ['docs/contracts/ASC-0166.md:12']},\n"
            "    {'id': 'mem_bad_tool_1', 'type': 'bad_tool', 'content': 'Cheap local model gave generic completion for schema-critical JSON; require verifier before acceptance.', 'confidence': 0.77, 'raw_refs': ['docs/contracts/ASC-0081.md:20']}\n"
            "  ]\n"
            "}, ensure_ascii=False))\n",
            encoding="utf-8",
        )

    def write_memory_review_gap(self, root: Path) -> None:
        result = root / ".aios" / "outbox" / "memoryOS" / "mdrev-gap.memoryOS.result.json"
        result.parent.mkdir(parents=True)
        result.write_text(
            json.dumps(
                {
                    "schema_version": "aios.dispatch.result.v1",
                    "status": "passed",
                    "dispatch_id": "mdrev-gap",
                    "target_repo": "memoryOS",
                    "executed_at": "2026-05-17T00:00:00+09:00",
                    "review_request": {
                        "request_id": "mdrev-gap",
                        "source_artifact": ".aios/chat/demo/memory_drafts.json",
                        "draft_id": "demo:1",
                        "draft_type": "genesis_friction_signal",
                        "review_decision": "needs_more_evidence",
                        "memory_object_id": "mem_gap",
                        "review_id": "review_gap",
                    },
                }
            ),
            encoding="utf-8",
        )

    def test_cheap_turn_routes_local_and_persists_evidence(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            payload = self.run_router(root, "summarize this short text", "cli-test")

            self.assertEqual(payload["schema_version"], "aios.chat.turn.v1")
            self.assertIn(payload["chosen_substrate"], {"local_llm", "ollama_qwen"})
            self.assertEqual(payload["route_reason"], "cheap_local_first")
            self.assertEqual(payload["memory_draft"]["status"], "draft")
            self.assertIn("pattern_injection_audit", payload["artifact_paths"])
            self.assertGreaterEqual(payload["cost"]["turn_tokens_in"], 1)
            self.assertTrue((root / ".aios" / "chat" / "cli-test" / "messages.jsonl").exists())
            self.assertTrue((root / ".aios" / "chat" / "cli-test" / "cost.json").exists())
            self.assertTrue((root / ".aios" / "chat" / "cli-test" / "run_state.json").exists())
            drafts = json.loads((root / ".aios" / "chat" / "cli-test" / "memory_drafts.json").read_text(encoding="utf-8"))
            self.assertIn("memory_drafts", drafts)
            self.assertEqual(drafts["memory_drafts"][0]["origin"], "aios_chat")
            self.assertIn("messages.jsonl", drafts["memory_drafts"][0]["raw_refs"])

    def test_operator_override_forces_substrate(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            payload = self.run_router(root, "@claude explain this", "override-test")

            self.assertEqual(payload["chosen_substrate"], "claude")
            self.assertEqual(payload["operator_override"], "claude")
            self.assertEqual(payload["route_reason"], "operator_override")
            cost = json.loads((root / ".aios" / "chat" / "override-test" / "cost.json").read_text(encoding="utf-8"))
            self.assertGreaterEqual(cost["total_cost_usd"], 0)

    def test_multi_step_routes_to_hive_flow(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            payload = self.run_router(root, "build a new AIOS contract and dispatch plan", "flow-test")

            self.assertEqual(payload["chosen_substrate"], "hive_flow")
            self.assertEqual(payload["intent"], "multi_step")
            self.assertIn("Hive orchestration", payload["response"])
            self.assertIn("promote this conversation", payload["operating_receipt"]["next_step"])

    def test_action_turn_projects_genesis_friction_when_available(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            (root / "GenesisOS").symlink_to(ROOT / "GenesisOS", target_is_directory=True)

            payload = self.run_router(root, "build a new AIOS contract and dispatch plan", "genesis-friction-test")

            self.assertEqual(payload["chosen_substrate"], "hive_flow")
            self.assertIsInstance(payload["genesis_friction"], dict)
            self.assertIn("GenesisOS가 먼저 건드린 불편함", payload["response"])
            self.assertIn("genesis_summary", payload["operating_receipt"])
            self.assertIn("genesis_branches", payload["artifact_paths"])

    def test_provider_word_does_not_steal_action_turn_from_hive(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            (root / "GenesisOS").symlink_to(ROOT / "GenesisOS", target_is_directory=True)

            payload = self.run_router(root, "AIOS web chat을 더 provider급으로 개선하는 작업 진행해", "provider-action-test")

            self.assertEqual(payload["chosen_substrate"], "hive_flow")
            self.assertEqual(payload["route_reason"], "multi_step_orchestration")
            self.assertIn("GenesisOS가 먼저 건드린 불편함", payload["response"])
            self.assertNotIn("..", payload["response"])

    def test_genesis_friction_question_answers_without_provider_turn(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            (root / "GenesisOS").symlink_to(ROOT / "GenesisOS", target_is_directory=True)

            payload = self.run_router(root, "이 대화에서 불편함과 숨은 필요성을 찾아줘", "genesis-question-test")

            self.assertEqual(payload["provider_turn"], None)
            self.assertIsInstance(payload["genesis_friction"], dict)
            self.assertIn("GenesisOS가 이 질문에서 불편함/필요성 후보", payload["response"])
            self.assertIn("speculative signal", payload["response"])
            self.assertIn("chatdraft_", payload["memory_draft"]["id"])
            self.assertTrue(payload["memory_draft"]["extra_draft_ids"])
            self.assertIn("friction_contract_seed", payload["artifact_paths"])
            self.assertIn("friction_contract_seed.md", payload["operating_receipt"]["next_step"])
            seed_text = (root / payload["artifact_paths"]["friction_contract_seed"]).read_text(encoding="utf-8")
            self.assertIn("status: proposed", seed_text)
            self.assertIn("origin: AIOS chat GenesisOS friction", seed_text)
            self.assertIn("This file is not execution authority", seed_text)
            self.assertIn("genesis_branches", seed_text)
            drafts = json.loads((root / ".aios" / "chat" / "genesis-question-test" / "memory_drafts.json").read_text(encoding="utf-8"))
            self.assertEqual(drafts["memory_drafts"][1]["type"], "genesis_friction_signal")
            self.assertEqual(drafts["memory_drafts"][1]["origin"], "aios_chat_genesis")
            self.assertIn("genesis/branches.json", " ".join(drafts["memory_drafts"][1]["raw_refs"]))

    def test_conversation_response_reflects_greeting_and_receipts(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            payload = self.run_router(root, "hey 안녕", "hello-test")

            self.assertIn("안녕", payload["response"])
            self.assertIn("AIOS", payload["response"])
            self.assertNotIn("Session preparation status", payload["response"])
            self.assertIn("MemoryOS", payload["operating_receipt"]["memory_summary"])
            self.assertIn("session_status", payload["operating_receipt"])
            self.assertNotEqual(
                payload["response"],
                "AIOS handled this as a low-cost local turn and recorded the context for continuation.",
            )

    def test_identity_question_answers_as_aios_before_receipt(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            payload = self.run_router(root, "너는 누구니", "identity-test")

            response = payload["response"]
            self.assertTrue(response.startswith("나는 AIOS야."))
            self.assertIn("myworld control plane", response)
            self.assertIn("Hive Mind", response)
            self.assertIn("MemoryOS", response)
            self.assertIn("CapabilityOS", response)
            self.assertIn("GenesisOS", response)
            self.assertIn("provider substrate", response)
            self.assertNotIn("I routed this as a lightweight conversation turn", response)
            self.assertIn("lightweight conversation", payload["operating_receipt"]["route_summary"])
            self.assertNotIn("받았어. 이 대화 턴을 AIOS 라우터로 처리했어.", response)

    def test_weather_question_is_held_by_gate_for_location(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            payload = self.run_router(root, "오늘 날씨는 ?", "weather-test")

            self.assertEqual(payload["chosen_substrate"], "gate_clarification")
            self.assertEqual(payload["intent"], "current_info")
            self.assertEqual(payload["route_reason"], "gate_requires_input")
            self.assertEqual(payload["cost"]["turn_cost_usd"], 0.0)
            self.assertEqual(payload["gate_decision"]["decision"], "clarify_location")
            self.assertIn("location", payload["gate_decision"]["missing_inputs"])
            self.assertIn("현재 날씨 정보", payload["response"])
            self.assertIn("어느 지역", payload["response"])
            self.assertIn("CapabilityOS", payload["response"])
            gate_path = root / payload["artifact_paths"]["gate_decision"]
            self.assertTrue(gate_path.exists())

    def test_aios_self_diagnosis_now_is_not_current_info_hold(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            payload = self.run_router(
                root,
                "AIOS 완성을 위해 지금 가장 불편한 점과 다음 필요성을 하나만 골라줘",
                "self-diagnosis-test",
            )

            self.assertNotEqual(payload["intent"], "current_info")
            self.assertNotEqual(payload["chosen_substrate"], "capability_route_required")
            self.assertNotEqual(payload["gate_decision"]["decision"], "require_current_info_route")
            self.assertNotIn("외부 근거 route가 필요", payload["response"])

    def test_provider_chatbot_question_answers_gate_architecture(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            payload = self.run_router(
                root,
                "provided chatbot들도 AIOS에 연결할 수 있나? codex(CLI)의 역할을 대신하는 gate 역할의 Agent가 붙어있어야해.",
                "gate-architecture-test",
            )

            self.assertEqual(payload["gate_decision"]["decision"], "answer_architecture")
            self.assertEqual(payload["chosen_substrate"], "aios_gate")
            self.assertEqual(payload["route_reason"], "gate_answer")
            self.assertEqual(payload["gate_decision"]["provider_execution"], "not_required")
            self.assertIn("가능해", payload["response"])
            self.assertIn("provider substrate", payload["response"])
            self.assertIn("Gate/Chair Agent", payload["response"])
            self.assertIn("Gate Chair runtime 상태", payload["response"])
            self.assertIn("MemoryOS", payload["response"])
            self.assertIn("CapabilityOS", payload["response"])
            self.assertIn("GenesisOS", payload["response"])
            self.assertIn("Hive", payload["response"])

    def test_korean_gate_question_does_not_fall_through_to_generic_provider(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            payload = self.run_router(
                root,
                "AIOS에는 너처럼 routing 해주는 Gate Agent가 있나, 아니면 시스템 답변밖에 못하나?",
                "korean-gate-question-test",
                env={"AIOS_LOCAL_AGENT_COMMAND": "printf 'provider should not be used for this gate question'"},
            )

            self.assertEqual(payload["gate_decision"]["decision"], "answer_architecture")
            self.assertEqual(payload["chosen_substrate"], "aios_gate")
            self.assertEqual(payload["provider_turn"], None)
            self.assertNotIn("provider should not be used", payload["response"])
            self.assertIn("Gate/Chair Agent", payload["response"])

    def test_gate_architecture_answer_explains_internal_chair_runtime(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)

            payload = self.run_router(
                root,
                "AIOS에는 gate 역할의 Agent가 있나? 아니면 시스템 답변밖에 못하나?",
                "gate-runtime-architecture-test",
                env={"PATH": str(root / "empty-bin")},
            )

            self.assertEqual(payload["chosen_substrate"], "aios_gate")
            self.assertEqual(payload["route_reason"], "gate_answer")
            self.assertIn("internal_evidence_synthesizer", payload["response"])
            self.assertIn("Chair runtime", payload["response"])
            self.assertIn("품질 평가 루프", payload["response"])

    def test_memory_question_surfaces_selected_memory_content(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            self.install_fake_memoryos(root)

            payload = self.run_router(root, "나에 대한 기억은?", "memory-question-test")

            self.assertEqual(payload["memory_context"]["trace_id"], "rtrace_test_memory")
            self.assertEqual(payload["provider_turn"], None)
            self.assertIn("MemoryOS가", payload["response"])
            self.assertIn("provider CLIs", payload["response"])
            self.assertIn("continuous coevolution", payload["response"])
            self.assertIn("자동 승인되지는 않아", payload["response"])

    def test_memory_question_projects_memory_review_gap(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            self.install_fake_memoryos(root)
            self.write_memory_review_gap(root)

            payload = self.run_router(root, "나에 대한 기억은?", "memory-review-gap-test")

            self.assertEqual(payload["memory_context"]["memory_review_gap_count"], 1)
            self.assertEqual(payload["memory_context"]["memory_review_gaps"][0]["draft_id"], "demo:1")
            self.assertIn("needs_more_evidence", payload["response"])
            self.assertIn("보강 증거", payload["response"])
            self.assertIn("MemoryOS returned 2 relevant context item(s)", payload["operating_receipt"]["memory_summary"])
            self.assertIn("review gap", payload["operating_receipt"]["memory_summary"])

    def test_negative_evidence_question_surfaces_failure_memories(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            self.install_fake_negative_memoryos(root)

            payload = self.run_router(root, "provider 실패 기억과 bad tool evidence는?", "negative-memory-test")

            self.assertEqual(payload["memory_context"]["trace_id"], "rtrace_negative_memory")
            self.assertEqual(payload["provider_turn"], None)
            self.assertEqual(payload["memory_context"]["negative_evidence_count"], 2)
            self.assertEqual(payload["memory_context"]["negative_evidence"][0]["id"], "mem_fail_1")
            self.assertIn("negative evidence", payload["response"])
            self.assertIn("pin_required_noninteractive", payload["response"])
            self.assertIn("schema-critical JSON", payload["response"])
            self.assertIn("fallback", payload["response"])
            self.assertIn("chatdraft_", payload["memory_draft"]["extra_draft_ids"][0])
            drafts = json.loads((root / ".aios" / "chat" / "negative-memory-test" / "memory_drafts.json").read_text(encoding="utf-8"))
            negative_drafts = [item for item in drafts["memory_drafts"] if item["type"] == "negative_evidence_signal"]
            self.assertEqual(negative_drafts[0]["origin"], "aios_chat_negative_evidence")
            self.assertEqual(negative_drafts[0]["status"], "draft")
            self.assertIn("pin_required_noninteractive", negative_drafts[0]["content"])
            self.assertEqual(negative_drafts[0]["provenance"]["memory_trace_id"], "rtrace_negative_memory")

    def test_negative_evidence_demotes_bad_capability_provider_candidate(self) -> None:
        module = self.load_router_module()
        capability = {"recommendations": ["use local ollama for low cost", "fallback to claude for synthesis"]}
        memory = {
            "status": "available",
            "negative_evidence_source": "memoryos",
            "negative_evidence": [
                {
                    "id": "mem_bad_tool_1",
                    "type": "bad_tool",
                    "content": "Cheap local model gave generic completion for schema-critical JSON; require verifier before acceptance.",
                    "failure_class": "bad_tool",
                    "raw_refs": ["docs/contracts/ASC-0081.md:20"],
                }
            ],
        }

        substrate, intent, reason, audit = module.choose_substrate(
            "summarize this short text",
            None,
            capability,
            {"input_class": "cheap_single_turn"},
            memory,
        )

        self.assertEqual(substrate, "claude")
        self.assertEqual(intent, "cheap_single_turn")
        self.assertEqual(reason, "negative_evidence_avoids_bad_provider")
        self.assertEqual(audit["skipped_provider_candidates"], ["ollama_qwen"])
        self.assertIn("ollama_qwen", audit["bad_provider_signals"])

    def test_gate_chair_command_can_synthesize_memory_answer(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            self.install_fake_memoryos(root)

            payload = self.run_router(
                root,
                "나에 대한 기억은?",
                "gate-chair-test",
                env={"AIOS_GATE_AGENT_COMMAND": "printf 'Gate Chair synthesized from MemoryOS context'"},
            )

            self.assertEqual(payload["provider_turn"], None)
            self.assertIn("Gate Chair synthesized", payload["response"])
            self.assertIn("gate_chair_turns", payload["artifact_paths"])
            self.assertEqual(payload["gate_chair_turn"], ".aios/chat/gate-chair-test/gate_chair_turns.jsonl")
            self.assertEqual(payload["gate_chair_status"]["status"], "success")
            self.assertTrue(payload["gate_chair_status"]["executed"])
            chair_rows = (root / ".aios" / "chat" / "gate-chair-test" / "gate_chair_turns.jsonl").read_text(encoding="utf-8")
            self.assertIn("aios.chat.gate_chair_turn.v1", chair_rows)

    def test_gate_chair_prompt_redacts_private_context_and_stays_compact(self) -> None:
        module = self.load_router_module()
        memory = {
            "trace_id": "rtrace_private",
            "context_items": 12,
            "selected_memory_ids": [f"mem_{idx}" for idx in range(12)],
            "selected_memories": [
                {
                    "id": f"mem_{idx}",
                    "type": "decision",
                    "content": "Founder email cjw070690@example.com and pin q1q1e3e3 must not leave AIOS. " * 8,
                    "confidence": 0.9,
                    "raw_refs": ["docs/private.md:1", "token=abc123"],
                }
                for idx in range(8)
            ],
            "negative_evidence": [
                {
                    "id": "neg_1",
                    "type": "provider_failure",
                    "failure_class": "provider_access_denied",
                    "content": "Gemini key AIzaSyFAKE-TEST-KEY-NOT-A-REAL-SECRET-00 failed.",
                    "raw_refs": ["secret/api_key=demo"],
                }
            ],
            "memory_review_gaps": [],
        }

        prompt = module.gate_chair_prompt(
            "나에 대한 기억은? cjw070690@example.com",
            "MemoryOS가 기억을 찾았어. q1q1e3e3",
            memory,
            {"decision": "route_normally", "input_class": "cheap_single_turn", "route": "standard_chat_router"},
            {"schema_version": "aios.chat.genesis_friction.v1", "authority": "speculative_only", "frictions": []},
        )
        payload = json.loads(prompt)

        self.assertLess(len(prompt), 5000)
        self.assertNotIn("cjw070690@example.com", prompt)
        self.assertNotIn("q1q1e3e3", prompt)
        self.assertNotIn("AIzaSyFAKE-TEST-KEY-NOT-A-REAL-SECRET-00", prompt)
        self.assertIn("[REDACTED_PRIVATE]", prompt)
        self.assertEqual(len(payload["memory_context"]["selected_memories"]), 5)
        self.assertEqual(len(payload["memory_context"]["selected_memory_ids"]), 8)

    def test_gate_chair_output_is_redacted_before_persistence(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            self.install_fake_memoryos(root)

            payload = self.run_router(
                root,
                "나에 대한 기억은?",
                "gate-chair-output-redaction-test",
                env={"AIOS_GATE_AGENT_COMMAND": "printf 'private email cjw070690@example.com and pin q1q1e3e3'"},
            )

            self.assertNotIn("cjw070690@example.com", payload["response"])
            self.assertNotIn("q1q1e3e3", payload["response"])
            self.assertIn("[REDACTED_PRIVATE]", payload["response"])
            messages = (root / payload["artifact_paths"]["messages"]).read_text(encoding="utf-8")
            turns = (root / payload["artifact_paths"]["gate_chair_turns"]).read_text(encoding="utf-8")
            self.assertNotIn("cjw070690@example.com", messages)
            self.assertNotIn("q1q1e3e3", messages)
            self.assertNotIn("cjw070690@example.com", turns)
            self.assertNotIn("q1q1e3e3", turns)

    def test_gate_chair_force_internal_overrides_configured_command(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)

            payload = self.run_router(
                root,
                "AIOS에는 gate 역할의 Agent가 있나?",
                "gate-chair-force-internal-test",
                env={
                    "AIOS_GATE_AGENT_COMMAND": "printf 'external chair should not run'",
                    "AIOS_GATE_CHAIR_FORCE_INTERNAL": "1",
                },
            )

            self.assertEqual(payload["chosen_substrate"], "aios_gate")
            self.assertEqual(payload["gate_chair_status"]["mode"], "internal_evidence_synthesizer")
            self.assertEqual(payload["gate_chair_status"]["model"], "deterministic")
            self.assertNotIn("external chair should not run", payload["response"])
            self.assertIn("AIOS_GATE_CHAIR_FORCE_INTERNAL", payload["response"])

    def test_gate_chair_runtime_config_can_force_internal(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            config = root / ".aios" / "gate" / "founder" / "chair_runtime.json"
            config.parent.mkdir(parents=True)
            config.write_text(
                json.dumps(
                    {
                        "schema_version": "aios.gate.chair_runtime.v1",
                        "status": "active",
                        "mode": "internal_evidence_synthesizer",
                    }
                ),
                encoding="utf-8",
            )

            payload = self.run_router(
                root,
                "AIOS에는 gate 역할의 Agent가 있나?",
                "gate-chair-config-internal-test",
                env={"AIOS_GATE_AGENT_COMMAND": "printf 'external chair should not run'"},
            )

            self.assertEqual(payload["chosen_substrate"], "aios_gate")
            self.assertEqual(payload["gate_chair_status"]["mode"], "internal_evidence_synthesizer")
            self.assertNotIn("external chair should not run", payload["response"])
            self.assertIn("chair_runtime.json", payload["response"])

    def test_gate_chair_runtime_config_can_select_ollama_model(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            config = root / ".aios" / "gate" / "founder" / "chair_runtime.json"
            config.parent.mkdir(parents=True)
            config.write_text(
                json.dumps(
                    {
                        "schema_version": "aios.gate.chair_runtime.v1",
                        "status": "active",
                        "mode": "ollama",
                        "model": "chair-test-model",
                    }
                ),
                encoding="utf-8",
            )
            bin_dir = root / "bin"
            bin_dir.mkdir()
            write_executable(
                bin_dir / "ollama",
                "#!/usr/bin/env bash\n"
                "printf 'configured ollama chair model=%s' \"$2\"\n",
            )

            payload = self.run_router(
                root,
                "AIOS에는 gate 역할의 Agent가 있나?",
                "gate-chair-config-ollama-test",
                env={"PATH": f"{bin_dir}{os.pathsep}{os.environ['PATH']}"},
            )

            self.assertEqual(payload["chosen_substrate"], "aios_gate")
            self.assertEqual(payload["gate_chair_status"]["mode"], "ollama")
            self.assertEqual(payload["gate_chair_status"]["model"], "chair-test-model")
            self.assertIn("configured ollama chair", payload["response"])

    def test_gate_chair_runtime_config_can_select_provider_cli(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            config = root / ".aios" / "gate" / "founder" / "chair_runtime.json"
            config.parent.mkdir(parents=True)
            config.write_text(
                json.dumps(
                    {
                        "schema_version": "aios.gate.chair_runtime.v1",
                        "status": "active",
                        "mode": "claude",
                        "model": "chair-test-model",
                    }
                ),
                encoding="utf-8",
            )
            bin_dir = root / "bin"
            bin_dir.mkdir()
            write_executable(
                bin_dir / "claude",
                "#!/usr/bin/env bash\n"
                "printf 'configured claude chair model=%s' \"$4\"\n",
            )

            payload = self.run_router(
                root,
                "AIOS에는 gate 역할의 Agent가 있나?",
                "gate-chair-config-claude-test",
                env={"PATH": f"{bin_dir}{os.pathsep}{os.environ['PATH']}"},
            )

            self.assertEqual(payload["chosen_substrate"], "aios_gate")
            self.assertEqual(payload["gate_chair_status"]["mode"], "claude")
            self.assertEqual(payload["gate_chair_status"]["model"], "chair-test-model")
            self.assertIn("configured claude chair", payload["response"])

    def test_active_gate_chair_runtime_demotes_after_repeated_failures(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            config = root / ".aios" / "gate" / "founder" / "chair_runtime.json"
            config.parent.mkdir(parents=True)
            config.write_text(
                json.dumps(
                    {
                        "schema_version": "aios.gate.chair_runtime.v1",
                        "status": "active",
                        "mode": "claude",
                        "model": "chair-test-model",
                    }
                ),
                encoding="utf-8",
            )
            report = root / ".aios" / "evals" / "gate_chair" / "eval-demote" / "report.json"
            report.parent.mkdir(parents=True)
            report.write_text(
                json.dumps(
                    {
                        "schema_version": "aios.gate_chair_eval.v1",
                        "eval_id": "eval-demote",
                        "promotion_ready": False,
                        "modes": [
                            {
                                "mode": "current",
                                "runs": [
                                    {
                                        "prompt_preview": "나에 대한 기억은?",
                                        "gate_chair_status": {
                                            "status": "gate_chair_timeout",
                                            "mode": "claude",
                                            "model": "chair-test-model",
                                        },
                                    },
                                    {
                                        "prompt_preview": "provider 실패 기억은?",
                                        "gate_chair_status": {
                                            "status": "provider_access_denied",
                                            "mode": "claude",
                                            "model": "chair-test-model",
                                        },
                                    },
                                ],
                            }
                        ],
                    }
                ),
                encoding="utf-8",
            )
            bin_dir = root / "bin"
            bin_dir.mkdir()
            write_executable(
                bin_dir / "claude",
                "#!/usr/bin/env bash\n"
                "printf 'external chair should be demoted'\n",
            )

            payload = self.run_router(
                root,
                "AIOS에는 gate 역할의 Agent가 있나?",
                "gate-chair-demotion-test",
                env={"PATH": f"{bin_dir}{os.pathsep}{os.environ['PATH']}"},
            )

            self.assertEqual(payload["chosen_substrate"], "aios_gate")
            self.assertEqual(payload["gate_chair_status"]["mode"], "internal_evidence_synthesizer")
            self.assertEqual(payload["gate_chair_status"]["model"], "deterministic")
            self.assertEqual(payload["gate_chair_status"]["status"], "success")
            self.assertNotIn("external chair should be demoted", payload["response"])
            self.assertIn("demote", payload["response"])

    def test_gate_chair_recovery_eval_clears_prior_demotion(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            config = root / ".aios" / "gate" / "founder" / "chair_runtime.json"
            config.parent.mkdir(parents=True)
            config.write_text(
                json.dumps(
                    {
                        "schema_version": "aios.gate.chair_runtime.v1",
                        "status": "active",
                        "mode": "claude",
                        "model": "chair-test-model",
                    }
                ),
                encoding="utf-8",
            )
            failure = root / ".aios" / "evals" / "gate_chair" / "eval-old-fail" / "report.json"
            failure.parent.mkdir(parents=True)
            failure.write_text(
                json.dumps(
                    {
                        "schema_version": "aios.gate_chair_eval.v1",
                        "eval_id": "eval-old-fail",
                        "promotion_ready": False,
                        "modes": [
                            {
                                "mode": "current",
                                "runs": [
                                    {
                                        "gate_chair_status": {
                                            "status": "gate_chair_timeout",
                                            "mode": "claude",
                                            "model": "chair-test-model",
                                        }
                                    },
                                    {
                                        "gate_chair_status": {
                                            "status": "provider_access_denied",
                                            "mode": "claude",
                                            "model": "chair-test-model",
                                        }
                                    },
                                ],
                            }
                        ],
                    }
                ),
                encoding="utf-8",
            )
            recovery = root / ".aios" / "evals" / "gate_chair" / "eval-new-recovery" / "report.json"
            recovery.parent.mkdir(parents=True)
            recovery.write_text(
                json.dumps(
                    {
                        "schema_version": "aios.gate_chair_eval.v1",
                        "eval_id": "eval-new-recovery",
                        "promotion_ready": True,
                        "scores": {"internal": 1.0, "current": 1.0},
                        "modes": [
                            {
                                "mode": "current",
                                "average_score": 1.0,
                                "runtime_modes": ["claude"],
                                "runtime_models": ["chair-test-model"],
                                "runs": [
                                    {
                                        "ok": True,
                                        "gate_chair_status": {
                                            "status": "success",
                                            "mode": "claude",
                                            "model": "chair-test-model",
                                        },
                                    }
                                ],
                            }
                        ],
                    }
                ),
                encoding="utf-8",
            )
            bin_dir = root / "bin"
            bin_dir.mkdir()
            write_executable(
                bin_dir / "claude",
                "#!/usr/bin/env bash\n"
                "printf 'recovered external chair'\n",
            )

            payload = self.run_router(
                root,
                "AIOS에는 gate 역할의 Agent가 있나?",
                "gate-chair-recovery-test",
                env={"PATH": f"{bin_dir}{os.pathsep}{os.environ['PATH']}"},
            )

            self.assertEqual(payload["chosen_substrate"], "aios_gate")
            self.assertEqual(payload["gate_chair_status"]["mode"], "claude")
            self.assertEqual(payload["gate_chair_status"]["model"], "chair-test-model")
            self.assertIn("recovered external chair", payload["response"])

    def test_gate_chair_candidate_override_summary_names_candidate_path(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            candidate = root / ".aios" / "gate" / "founder" / "chair_candidate_runtime.json"
            candidate.parent.mkdir(parents=True)
            candidate.write_text(
                json.dumps(
                    {
                        "schema_version": "aios.gate.chair_runtime.v1",
                        "status": "candidate",
                        "mode": "claude",
                        "model": "candidate-model",
                    }
                ),
                encoding="utf-8",
            )
            bin_dir = root / "bin"
            bin_dir.mkdir()

            payload = self.run_router(
                root,
                "AIOS에는 gate 역할의 Agent가 있나?",
                "gate-chair-candidate-summary-test",
                env={
                    "AIOS_GATE_CHAIR_RUNTIME_PATH": ".aios/gate/founder/chair_candidate_runtime.json",
                    "PATH": bin_dir.as_posix(),
                },
            )

            self.assertEqual(payload["chosen_substrate"], "aios_gate")
            self.assertIn(".aios/gate/founder/chair_candidate_runtime.json", payload["response"])
            self.assertIn("candidate override", payload["response"])
            self.assertNotIn(".aios/gate/founder/chair_runtime.json이 claude", payload["response"])

    def test_active_gate_pack_enables_gate_chair_by_default(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            self.install_fake_memoryos(root)
            pack = root / ".aios" / "gate" / "founder" / "gate_pack.json"
            pack.parent.mkdir(parents=True)
            pack.write_text(
                json.dumps(
                    {
                        "schema_version": "aios.gate.pack.v1",
                        "id": "gatepack_default",
                        "status": "active",
                        "generated_at": "2026-05-15T00:00:00+09:00",
                        "source_pair_count": 8,
                        "accepted_memory_hint_count": 2,
                        "rules": {"memoryos_context_before_execution": True},
                        "examples": [{"id": "gpair_default"}],
                    }
                ),
                encoding="utf-8",
            )
            bin_dir = root / "bin"
            bin_dir.mkdir()
            write_executable(
                bin_dir / "ollama",
                "#!/usr/bin/env bash\n"
                "printf 'default Gate Chair answer from active pack'\n",
            )

            payload = self.run_router(
                root,
                "나에 대한 기억은?",
                "gate-chair-default-test",
                env={"PATH": f"{bin_dir}{os.pathsep}{os.environ['PATH']}"},
            )

            self.assertEqual(payload["provider_turn"], None)
            self.assertIn("default Gate Chair answer", payload["response"])
            self.assertIn("gate_chair_turns", payload["artifact_paths"])
            self.assertEqual(payload["gate_chair_turn"], ".aios/chat/gate-chair-default-test/gate_chair_turns.jsonl")
            self.assertEqual(payload["gate_chair_status"]["status"], "success")
            self.assertTrue(payload["gate_chair_status"]["executed"])

    def test_gate_chair_can_be_disabled_even_with_active_pack(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            self.install_fake_memoryos(root)
            pack = root / ".aios" / "gate" / "founder" / "gate_pack.json"
            pack.parent.mkdir(parents=True)
            pack.write_text(
                json.dumps(
                    {
                        "schema_version": "aios.gate.pack.v1",
                        "id": "gatepack_disabled",
                        "status": "active",
                        "generated_at": "2026-05-15T00:00:00+09:00",
                        "source_pair_count": 8,
                        "accepted_memory_hint_count": 2,
                        "rules": {"memoryos_context_before_execution": True},
                        "examples": [{"id": "gpair_disabled"}],
                    }
                ),
                encoding="utf-8",
            )
            bin_dir = root / "bin"
            bin_dir.mkdir()
            write_executable(
                bin_dir / "ollama",
                "#!/usr/bin/env bash\n"
                "printf 'this should not run'\n",
            )

            payload = self.run_router(
                root,
                "나에 대한 기억은?",
                "gate-chair-disabled-test",
                env={
                    "PATH": f"{bin_dir}{os.pathsep}{os.environ['PATH']}",
                    "AIOS_GATE_CHAIR_ENABLED": "0",
                },
            )

            self.assertEqual(payload["gate_chair_turn"], None)
            self.assertEqual(payload["gate_chair_status"]["status"], "not_attempted")
            self.assertFalse(payload["gate_chair_status"]["attempted"])
            self.assertNotIn("this should not run", payload["response"])
            self.assertIn("MemoryOS가", payload["response"])

    def test_gate_chair_uses_internal_fallback_when_no_local_runtime_exists(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            self.install_fake_memoryos(root)
            pack = root / ".aios" / "gate" / "founder" / "gate_pack.json"
            pack.parent.mkdir(parents=True)
            pack.write_text(
                json.dumps(
                    {
                        "schema_version": "aios.gate.pack.v1",
                        "id": "gatepack_internal",
                        "status": "active",
                        "generated_at": "2026-05-15T00:00:00+09:00",
                        "source_pair_count": 8,
                        "accepted_memory_hint_count": 2,
                        "rules": {"memoryos_context_before_execution": True},
                        "examples": [{"id": "gpair_internal"}],
                    }
                ),
                encoding="utf-8",
            )

            payload = self.run_router(
                root,
                "나에 대한 기억은?",
                "gate-chair-internal-test",
                env={"PATH": str(root / "empty-bin")},
            )

            self.assertEqual(payload["provider_turn"], None)
            self.assertIn("MemoryOS가", payload["response"])
            self.assertEqual(payload["gate_chair_status"]["status"], "success")
            self.assertEqual(payload["gate_chair_status"]["mode"], "internal_evidence_synthesizer")
            self.assertEqual(payload["gate_chair_status"]["model"], "deterministic")
            self.assertTrue(payload["gate_chair_status"]["executed"])

    def test_negative_evidence_falls_back_to_aios_receipts(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            self.install_fake_memoryos(root)
            result = root / ".aios" / "outbox" / "hivemind" / "asc-demo.hivemind.result.json"
            result.parent.mkdir(parents=True)
            result.write_text(
                json.dumps(
                    {
                        "schema_version": "aios.dispatch.result.v1",
                        "target_repo": "hivemind",
                        "dispatch_id": "asc-demo",
                        "status": "held",
                        "failure_category": "provider_backpressure",
                        "stop_conditions_triggered": ["provider_backpressure"],
                    }
                ),
                encoding="utf-8",
            )

            payload = self.run_router(root, "provider 실패 기억은?", "negative-receipt-test")

            self.assertEqual(payload["provider_turn"], None)
            self.assertEqual(payload["memory_context"]["negative_evidence_source"], "aios_receipts")
            self.assertGreaterEqual(payload["memory_context"]["negative_evidence_count"], 1)
            self.assertIn("local receipts", payload["response"])
            self.assertIn("provider_backpressure", payload["response"])

    def test_gate_chair_eval_timeout_becomes_local_negative_evidence(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            self.install_fake_memoryos(root)
            report = root / ".aios" / "evals" / "gate_chair" / "eval-demo" / "report.json"
            report.parent.mkdir(parents=True)
            report.write_text(
                json.dumps(
                    {
                        "schema_version": "aios.gate_chair_eval.v1",
                        "eval_id": "eval-demo",
                        "promotion_ready": False,
                        "modes": [
                            {
                                "mode": "current",
                                "runs": [
                                    {
                                        "prompt_preview": "나에 대한 기억은?",
                                        "gate_chair_status": {
                                            "status": "gate_chair_timeout",
                                            "mode": "claude",
                                            "model": "claude-opus-4-6",
                                        },
                                    }
                                ],
                            }
                        ],
                    }
                ),
                encoding="utf-8",
            )

            payload = self.run_router(root, "provider 실패 기억은?", "negative-gate-chair-eval-test")

            self.assertEqual(payload["provider_turn"], None)
            self.assertEqual(payload["memory_context"]["negative_evidence_source"], "aios_receipts")
            self.assertEqual(payload["memory_context"]["negative_evidence"][0]["failure_class"], "gate_chair_timeout")
            self.assertIn("gate_chair_timeout", payload["response"])
            self.assertIn("claude", payload["response"])

    def test_gate_chair_chat_timeout_becomes_local_negative_evidence(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            self.install_fake_memoryos(root)
            turns = root / ".aios" / "chat" / "control-center" / "gate_chair_turns.jsonl"
            turns.parent.mkdir(parents=True)
            turns.write_text(
                json.dumps(
                    {
                        "schema_version": "aios.chat.gate_chair_turn.v1",
                        "turn_id": "gatechair_demo",
                        "executed": False,
                        "chair_meta": {
                            "status": "gate_chair_timeout",
                            "meta": {"mode": "claude", "model": "claude-opus-4-6"},
                        },
                        "prompt_preview": "나에 대한 기억은?",
                    },
                    ensure_ascii=False,
                )
                + "\n",
                encoding="utf-8",
            )

            payload = self.run_router(root, "provider 실패 기억은?", "negative-chat-turn-test")

            self.assertEqual(payload["provider_turn"], None)
            self.assertEqual(payload["memory_context"]["negative_evidence_source"], "aios_receipts")
            self.assertEqual(payload["memory_context"]["negative_evidence"][0]["failure_class"], "gate_chair_timeout")
            self.assertIn("Gate Chair chat turn", payload["memory_context"]["negative_evidence"][0]["content"])
            self.assertIn("claude", payload["response"])

    def test_chat_turn_executes_local_provider_when_configured(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            payload = self.run_router(
                root,
                "AIOS 목적을 짧게 말해줘",
                "local-provider-test",
                env={"AIOS_LOCAL_AGENT_COMMAND": "printf 'local answer from provider'"},
            )

            self.assertIn("local answer from provider", payload["response"])
            self.assertNotIn("받았어. 이 대화 턴을 AIOS 라우터로 처리했어.", payload["response"])
            self.assertNotIn("\n---\n", payload["response"])
            self.assertIn("provider_turns", payload["artifact_paths"])
            self.assertTrue((root / ".aios" / "chat" / "local-provider-test" / "provider_turns.jsonl").exists())

    def test_gate_decision_projects_sleep_pack_when_available(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            pack = root / ".aios" / "gate" / "founder" / "gate_pack.json"
            pack.parent.mkdir(parents=True)
            pack.write_text(
                json.dumps(
                    {
                        "schema_version": "aios.gate.pack.v1",
                        "id": "gatepack_demo",
                        "status": "active",
                        "generated_at": "2026-05-14T00:00:00+09:00",
                        "source_pair_count": 3,
                        "accepted_memory_hint_count": 1,
                        "rules": {
                            "current_info_requires_source": True,
                            "provider_is_substrate_not_identity": True,
                            "finetune_ready": False,
                        },
                        "examples": [{"id": "gpair_a"}],
                    }
                ),
                encoding="utf-8",
            )

            payload = self.run_router(root, "hello", "gate-pack-test")

            projection = payload["gate_decision"]["gate_pack"]
            self.assertEqual(projection["pack_id"], "gatepack_demo")
            self.assertEqual(projection["source_pair_count"], 3)
            self.assertIn("current_info_requires_source", projection["rules_applied"])
            self.assertFalse(projection["finetune_ready"])


class Tier2QualityGateTest(unittest.TestCase):
    """ASC-0193 — tier-2 quality gate deterministic signals + eligibility."""

    @staticmethod
    def _module():
        scripts_dir = (ROOT / "scripts").as_posix()
        if scripts_dir not in sys.path:
            sys.path.insert(0, scripts_dir)
        spec = importlib.util.spec_from_file_location("aios_chat_router_t2", SCRIPT)
        module = importlib.util.module_from_spec(spec)
        assert spec and spec.loader
        spec.loader.exec_module(module)
        return module

    def test_deterministic_signal_flags_refusal(self) -> None:
        m = self._module()
        self.assertIsNotNone(
            m.gate_deterministic_signal("fix the bug", "multi_step", "I can't help with that."))

    def test_deterministic_signal_flags_too_short(self) -> None:
        m = self._module()
        self.assertIsNotNone(m.gate_deterministic_signal("explain X", "single_turn", "ok"))

    def test_deterministic_signal_flags_trivial_multi_step(self) -> None:
        m = self._module()
        self.assertIsNotNone(
            m.gate_deterministic_signal("implement the feature", "multi_step", "Done."))

    def test_deterministic_signal_passes_real_answer(self) -> None:
        m = self._module()
        good = ("Here is the fix: the off-by-one is in unused_days; it should add 1 "
                "so the upgrade day itself is counted. I changed the return statement "
                "and the four failing tests now pass.")
        self.assertIsNone(m.gate_deterministic_signal("fix the bug", "multi_step", good))

    def test_eligibility_cheap_route_nontrivial_intent(self) -> None:
        m = self._module()
        self.assertTrue(m.tier2_eligible("ollama_qwen", "multi_step"))
        self.assertFalse(m.tier2_eligible("claude", "multi_step"))
        self.assertFalse(m.tier2_eligible("ollama_qwen", "cheap_single_turn"))

    def test_sanitize_provider_text_strips_ansi_and_thinking_block(self) -> None:
        m = self._module()
        raw = (
            "Thinking...\n"
            "private scratch\x1b[1D\x1b[K\n"
            "...done thinking.\n\n"
            "Final answer\x1b[K with clean text"
        )

        clean = m.sanitize_provider_text(raw)

        self.assertEqual(clean, "Final answer with clean text")
        self.assertNotIn("\x1b", clean)
        self.assertNotIn("Thinking", clean)

    def test_sanitize_provider_text_applies_cursor_erase_and_reflows_wraps(self) -> None:
        m = self._module()
        raw = (
            "Final plan uses a long provenance trace visual row before provider_output_p\x1b[1D\x1b[K\n"
            "`provider_output_projection` artifacts.\n\n"
            "- keep markdown bullets\n"
            "MemoryOS\n"
            "trace"
        )

        clean = m.sanitize_provider_text(raw)

        self.assertIn("provider_output_`provider_output_projection` artifacts.", clean)
        self.assertIn("- keep markdown bullets", clean)
        self.assertIn("MemoryOS trace", clean)
        self.assertNotIn("\x1b", clean)

    def test_capability_matrix_routes_by_rank_and_cost(self) -> None:
        # ASC-0203 — a paid claude card outranks ollama by confidence, but
        # cost=free must stable-prefer the local card; the harness card is
        # not a provider substrate and is dropped.
        m = self._module()
        payload = {
            "recommendations": [
                {"id": "cap_anthropic_claude_opus", "domains": ["claude"],
                 "cost": "metered", "confidence": 0.9},
                {"id": "cap_hivemind_execution_harness", "domains": ["aios"],
                 "cost": "free", "confidence": 0.8},
                {"id": "cap_ollama_qwen25_7b_local", "domains": ["ollama", "qwen"],
                 "cost": "free", "confidence": 0.6},
            ]
        }
        self.assertEqual(
            m.provider_candidates_from_capability(payload),
            ["ollama_qwen", "claude"],
        )

    def test_capability_matrix_with_no_provider_card_defaults_local(self) -> None:
        # ASC-0203 stop condition — matrix maps to no substrate -> local-first.
        m = self._module()
        payload = {
            "recommendations": [
                {"id": "cap_hivemind_execution_harness", "domains": ["aios"],
                 "cost": "free", "confidence": 0.8},
                {"id": "cap_aios_readiness_scorer", "domains": ["aios"],
                 "cost": "free", "confidence": 0.7},
            ]
        }
        self.assertEqual(
            m.provider_candidates_from_capability(payload),
            ["ollama_qwen"],
        )

    def test_capability_payload_without_matrix_uses_substring_fallback(self) -> None:
        # ASC-0203 — no `recommendations` key: degrade to the substring scan.
        m = self._module()
        payload = {"note": "ollama-served local model; claude available as chair"}
        self.assertEqual(
            m.provider_candidates_from_capability(payload),
            ["ollama_qwen", "claude"],
        )


if __name__ == "__main__":
    unittest.main()
