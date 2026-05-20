import json
import importlib.util
import subprocess
import sys
import tempfile
import time
import unittest
from pathlib import Path


SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "aios_local_app.py"
SNAPSHOT = Path(__file__).resolve().parents[1] / "scripts" / "aios_control_snapshot.py"
MONITOR = Path(__file__).resolve().parents[1] / "scripts" / "aios_monitor.py"
ROUND = Path(__file__).resolve().parents[1] / "scripts" / "aios_round_controller.py"


def load_local_app_module():
    spec = importlib.util.spec_from_file_location("aios_local_app_under_test", SCRIPT)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class AiosLocalAppTest(unittest.TestCase):
    def write_fixture(self, root: Path) -> None:
        (root / "scripts").mkdir()
        (root / "apps" / "control").mkdir(parents=True)
        (root / "apps" / "control" / "index.html").write_text("<!doctype html><div>AIOS</div>\n", encoding="utf-8")
        (root / "apps" / "control" / "app.js").write_text(
            "window.AIOS_CONTROL_SNAPSHOT; function renderContracts(){} function renderDispatches(){} function renderRepos(){} function renderRoster(){} function renderContractBoard(){} function renderRoutes(){} function renderOsObservatory(){} function renderInstallation(){} function renderPromotionQueue(){} function renderMemoryDraftQueue(){}\n",
            encoding="utf-8",
        )
        for source in (SCRIPT, SNAPSHOT, MONITOR, ROUND):
            (root / "scripts" / source.name).write_text(source.read_text(encoding="utf-8"), encoding="utf-8")
        (root / "docs" / "contracts").mkdir(parents=True)
        (root / "docs" / "contracts" / "ASC-0001-demo.md").write_text(
            "---\ncontract_id: ASC-0001\nstatus: closed\ngoal: demo\n---\n# Demo\n",
            encoding="utf-8",
        )
        (root / "docs" / "goals").mkdir(parents=True)
        (root / "docs" / "goals" / "AIOS-GOAL-0001-make-something-great.md").write_text(
            "---\ngoal_id: AIOS-GOAL-0001\nslug: demo\nstatus: active\n---\n# Demo\n\n## North Star\n\nRun.\n",
            encoding="utf-8",
        )

    def run_cli(self, root: Path, *args: str) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            [sys.executable, SCRIPT.as_posix(), "--root", root.as_posix(), *args],
            text=True,
            capture_output=True,
            check=False,
        )

    def test_refresh_writes_snapshot_and_reports_monitor(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            self.write_fixture(root)

            result = self.run_cli(root, "refresh", "--json")

            self.assertEqual(result.returncode, 0, result.stderr)
            data = json.loads(result.stdout)
            self.assertTrue(data["ok"])
            self.assertTrue((root / "apps" / "control" / "aios-control-snapshot.json").exists())
            self.assertTrue((root / "apps" / "control" / "aios-control-data.js").exists())

    def test_start_status_and_stop_server(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            self.write_fixture(root)
            port = "9876"

            start = self.run_cli(root, "start", "--port", port, "--json")
            try:
                self.assertEqual(start.returncode, 0, start.stderr)
                start_data = json.loads(start.stdout)
                self.assertTrue(start_data["server"]["running"])

                status = self.run_cli(root, "status", "--json")
                status_data = json.loads(status.stdout)
                self.assertTrue(status_data["server"]["running"])
                self.assertEqual(status_data["server"]["url"], f"http://127.0.0.1:{port}/")
            finally:
                stop = self.run_cli(root, "stop", "--json")
                self.assertEqual(stop.returncode, 0, stop.stderr)
                time.sleep(0.1)

            status_after = self.run_cli(root, "status", "--json")
            self.assertFalse(json.loads(status_after.stdout)["server"]["running"])

    def test_control_app_contains_end_user_ask_surface(self) -> None:
        root = Path(__file__).resolve().parents[1]
        html = (root / "apps" / "control" / "index.html").read_text(encoding="utf-8")
        app_js = (root / "apps" / "control" / "app.js").read_text(encoding="utf-8")

        self.assertIn('id="ask-form"', html)
        self.assertIn('id="session-form"', html)
        self.assertIn('id="session-input"', html)
        self.assertIn('id="session-contract-id"', html)
        self.assertIn('id="genesis-branch-grid"', html)
        self.assertIn('id="os-orbit"', html)
        self.assertIn('id="os-lane-grid"', html)
        self.assertIn('id="quick-action-row"', html)
        self.assertIn('id="friction-grid"', html)
        self.assertIn('id="memory-draft-grid"', html)
        self.assertIn('id="memory-draft-status"', html)
        self.assertIn("data-chat-prompt", html)
        self.assertIn('id="ask-input"', html)
        self.assertIn('id="ask-draft-contract"', html)
        self.assertIn('id="goal-bar-form"', html)
        self.assertIn('id="goal-bar-input"', html)
        self.assertIn("goal_bar.js", html)
        self.assertIn('fetch("/api/session"', app_js)
        self.assertIn('fetch("/api/promote_session"', app_js)
        self.assertIn('fetch("/api/memory_draft_review"', app_js)
        self.assertIn('fetch("/api/artifact"', app_js)
        self.assertIn('fetch("/api/gate_chair_probe"', app_js)
        self.assertIn('fetch("/api/gate_chair_eval"', app_js)
        self.assertIn('fetch("/api/gate_chair_runtime"', app_js)
        self.assertIn('fetch("/api/gate_chair_promote"', app_js)
        self.assertIn("Test Gate Chair", app_js)
        self.assertIn("Eval Chair", app_js)
        self.assertIn("Promote Chair", app_js)
        self.assertIn("Use Internal", app_js)
        self.assertIn("Try Ollama", app_js)
        self.assertIn("Try Claude", app_js)
        self.assertIn("Try Codex", app_js)
        self.assertIn("Try Gemini", app_js)
        self.assertIn("command missing", app_js)
        self.assertIn("internal fallback expected", app_js)
        self.assertIn("artifactPreviewControl", app_js)
        self.assertIn("artifactFromHash", app_js)
        self.assertIn("artifactAuthority", app_js)
        self.assertIn("authority-badge", app_js)
        self.assertIn("restoreArtifactHash", app_js)
        self.assertIn("artifact-hash-panel", app_js)
        self.assertIn("hive-artifact-open", app_js)
        self.assertIn("agent-artifact-open", app_js)
        self.assertIn("artifact-lane-open", app_js)
        self.assertIn("renderGenesisLens", app_js)
        self.assertIn("renderFrictionRadar", app_js)
        self.assertIn("renderOsObservatory", app_js)
        self.assertIn("renderMemoryDraftQueue", app_js)
        self.assertIn("memory-draft-open", app_js)
        self.assertIn("requestMemoryDraftReview", app_js)
        self.assertIn("renderSessionPromotion", app_js)
        self.assertIn('fetch("/api/ask"', app_js)
        self.assertIn("installSessionForm", app_js)
        self.assertIn("installAskForm", app_js)

    def test_artifact_api_reads_allowed_control_artifact(self) -> None:
        module = load_local_app_module()
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            artifact = root / ".aios" / "chat" / "demo" / "messages.jsonl"
            artifact.parent.mkdir(parents=True)
            artifact.write_text('{"role":"assistant","content":"ok"}\n', encoding="utf-8")
            json_artifact = root / ".aios" / "chat" / "demo" / "cost.json"
            json_artifact.write_text(json.dumps({"total_cost_usd": 0}), encoding="utf-8")
            app_artifact = root / "apps" / "control" / "aios-control-snapshot.json"
            app_artifact.parent.mkdir(parents=True)
            app_artifact.write_text(json.dumps({"snapshot": True}), encoding="utf-8")

            status, payload = module.build_artifact_response(root, {"path": ".aios/chat/demo/messages.jsonl"})
            json_status, json_payload = module.build_artifact_response(root, {"path": ".aios/chat/demo/cost.json"})
            app_status, app_payload = module.build_artifact_response(root, {"path": "apps/control/aios-control-snapshot.json"})

        self.assertEqual(status, 200)
        self.assertTrue(payload["ok"])
        self.assertEqual(payload["path"], ".aios/chat/demo/messages.jsonl")
        self.assertEqual(payload["format"], "jsonl")
        self.assertIn('"content":"ok"', payload["text"])
        self.assertEqual(json_status, 200)
        self.assertEqual(json_payload["format"], "json")
        self.assertEqual(json_payload["json"]["total_cost_usd"], 0)
        self.assertEqual(app_status, 200)
        self.assertTrue(app_payload["json"]["snapshot"])

    def test_artifact_api_rejects_private_or_external_refs(self) -> None:
        module = load_local_app_module()
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / ".env").write_text("SECRET=1\n", encoding="utf-8")

            for ref in ("../outside.txt", "/tmp/outside.txt", ".env", ".aios/secrets/token.txt"):
                status, payload = module.build_artifact_response(root, {"path": ref})
                self.assertEqual(status, 400)
                self.assertFalse(payload["ok"])
                self.assertEqual(payload["reason"], "artifact_ref_not_allowed")

    def test_ask_api_rejects_empty_goal(self) -> None:
        module = load_local_app_module()
        with tempfile.TemporaryDirectory() as tmp:
            status, payload = module.build_ask_response(Path(tmp), {"goal": "   "})

        self.assertEqual(status, 400)
        self.assertFalse(payload["ok"])
        self.assertEqual(payload["reason"], "goal_missing")

    def test_ask_api_runs_plan_only_ask_script(self) -> None:
        module = load_local_app_module()
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "scripts").mkdir()
            (root / "scripts" / "aios_ask.py").write_text(
                "\n".join(
                    [
                        "import json, sys",
                        "payload = {",
                        "  'schema_version': 'aios.ask.receipt.v1',",
                        "  'ask_id': 'ask-test',",
                        "  'status': 'passed',",
                        "  'artifact_paths': {'instruction': '.aios/asks/ask-test/instruction.md', 'praxis': '.aios/asks/ask-test/praxis.json', 'contract_seed': '.aios/asks/ask-test/contract_seed.md'},",
                        "}",
                        "assert '--draft-contract' in sys.argv",
                        "print(json.dumps(payload))",
                    ]
                )
                + "\n",
                encoding="utf-8",
            )

            status, payload = module.build_ask_response(root, {"goal": "ship end user ask", "draft_contract": True})

        self.assertEqual(status, 200)
        self.assertTrue(payload["ok"])
        self.assertEqual(payload["receipt"]["ask_id"], "ask-test")
        self.assertEqual(payload["receipt"]["artifact_paths"]["contract_seed"], ".aios/asks/ask-test/contract_seed.md")

    def test_session_api_rejects_empty_goal(self) -> None:
        module = load_local_app_module()
        with tempfile.TemporaryDirectory() as tmp:
            status, payload = module.build_session_response(Path(tmp), {"goal": "   "})

        self.assertEqual(status, 400)
        self.assertFalse(payload["ok"])
        self.assertEqual(payload["reason"], "goal_missing")

    def test_session_api_runs_invocation_and_returns_envelope(self) -> None:
        module = load_local_app_module()
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "scripts").mkdir()
            (root / "scripts" / "aios_invoke.py").write_text(
                "\n".join(
                    [
                        "import json, pathlib, sys",
                        "write = pathlib.Path(sys.argv[sys.argv.index('--write') + 1])",
                        "out = pathlib.Path.cwd() / write",
                        "out.mkdir(parents=True, exist_ok=True)",
                        "envelope_path = out / 'session_envelope.json'",
                        "envelope = {",
                        "  'schema_version': 'aios.session_envelope.v1',",
                        "  'invocation_id': out.name,",
                        "  'role_statuses': {'genesis':'passed','memory':'degraded','capability':'passed','hive':'passed'},",
                        "  'role_artifacts': {'genesis': str(write / 'genesis/branches.json'), 'memory_context_pack': str(write / 'memory/context_pack.md'), 'capability_route': str(write / 'capability/route.json'), 'hive_execution_plan': str(write / 'hive/execution_plan.json')},",
                        "  'executor_assignment': {'default_executor':'codex','execution_owner':'hivemind'},",
                        "}",
                        "envelope_path.write_text(json.dumps(envelope), encoding='utf-8')",
                        "receipt = {'schema_version':'aios.invocation_receipt.v1','invocation_id':out.name,'overall_status':'degraded','next_action':'review_degraded_roles','session_envelope': str(write / 'session_envelope.json'), 'role_statuses': envelope['role_statuses']}",
                        "assert '--plan-only' in sys.argv",
                        "print(json.dumps(receipt))",
                    ]
                )
                + "\n",
                encoding="utf-8",
            )

            status, payload = module.build_session_response(root, {"goal": "make an end-user AIOS interface"})

        self.assertEqual(status, 200)
        self.assertTrue(payload["ok"])
        self.assertEqual(payload["receipt"]["overall_status"], "degraded")
        self.assertEqual(payload["session_envelope"]["schema_version"], "aios.session_envelope.v1")
        self.assertEqual(payload["session_envelope"]["executor_assignment"]["execution_owner"], "hivemind")

    def test_session_promotion_requires_confirmation(self) -> None:
        module = load_local_app_module()
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            envelope = root / ".aios" / "invocations" / "demo" / "session_envelope.json"
            envelope.parent.mkdir(parents=True)
            envelope.write_text(
                json.dumps({"schema_version": "aios.session_envelope.v1", "goal": "promote me"}),
                encoding="utf-8",
            )

            status, payload = module.build_session_promotion_response(
                root,
                {"session_envelope": ".aios/invocations/demo/session_envelope.json"},
            )

        self.assertEqual(status, 409)
        self.assertFalse(payload["ok"])
        self.assertEqual(payload["reason"], "confirmation_required")

    def test_session_promotion_writes_contract_seed_with_envelope_ref(self) -> None:
        module = load_local_app_module()
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            envelope = root / ".aios" / "invocations" / "demo" / "session_envelope.json"
            envelope.parent.mkdir(parents=True)
            envelope.write_text(
                json.dumps(
                    {
                        "schema_version": "aios.session_envelope.v1",
                        "goal": "Build reviewed promotion",
                        "role_artifacts": {"dispatch_packets": ".aios/invocations/demo/dispatch/packets.json"},
                    }
                ),
                encoding="utf-8",
            )

            status, payload = module.build_session_promotion_response(
                root,
                {"session_envelope": ".aios/invocations/demo/session_envelope.json", "confirm": True},
            )

            self.assertEqual(status, 200)
            self.assertTrue(payload["ok"])
            receipt = payload["receipt"]
            self.assertFalse(receipt["execution_started"])
            self.assertEqual(receipt["session_envelope"]["ref"], ".aios/invocations/demo/session_envelope.json")
            seed = root / receipt["artifact_paths"]["contract_seed"]
            self.assertTrue(seed.exists())
            seed_text = seed.read_text(encoding="utf-8")
            self.assertIn("session_envelope_ref: .aios/invocations/demo/session_envelope.json", seed_text)
            self.assertIn("dispatch_preview: `.aios/invocations/demo/dispatch/packets.json`", seed_text)
            self.assertIn("## AIOS Role Evidence", seed_text)
            self.assertIn("### MemoryOS", seed_text)
            self.assertIn("### CapabilityOS", seed_text)
            self.assertIn("### GenesisOS", seed_text)
            self.assertIn("### Hive Mind", seed_text)

    def test_session_promotion_rejects_external_envelope_ref(self) -> None:
        module = load_local_app_module()
        with tempfile.TemporaryDirectory() as tmp:
            status, payload = module.build_session_promotion_response(
                Path(tmp),
                {"session_envelope": "docs/session_envelope.json", "confirm": True},
            )

        self.assertEqual(status, 400)
        self.assertFalse(payload["ok"])
        self.assertEqual(payload["reason"], "session_envelope_ref_outside_invocations")

    def test_memory_draft_review_requires_confirmation(self) -> None:
        module = load_local_app_module()
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            draft_path = root / ".aios" / "chat" / "demo" / "memory_drafts.json"
            draft_path.parent.mkdir(parents=True)
            draft_path.write_text(
                json.dumps({"schema_version": "aios.chat.memory_drafts.v1", "memory_drafts": []}),
                encoding="utf-8",
            )

            status, payload = module.build_memory_draft_review_response(
                root,
                {"source_artifact": ".aios/chat/demo/memory_drafts.json", "draft_id": "demo:0"},
            )

        self.assertEqual(status, 409)
        self.assertFalse(payload["ok"])
        self.assertEqual(payload["reason"], "confirmation_required")

    def test_memory_draft_review_writes_memoryos_inbox_packet(self) -> None:
        module = load_local_app_module()
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            draft_path = root / ".aios" / "chat" / "demo" / "memory_drafts.json"
            draft_path.parent.mkdir(parents=True)
            draft_path.write_text(
                json.dumps(
                    {
                        "schema_version": "aios.chat.memory_drafts.v1",
                        "memory_drafts": [
                            {
                                "type": "genesis_friction_signal",
                                "origin": "aios_chat_genesis",
                                "status": "draft",
                                "confidence": 0.67,
                                "conversation_id": "demo",
                                "project": "AIOS",
                                "content": "GenesisOS projected discomfort/need signal.",
                                "raw_refs": ["messages.jsonl", ".aios/invocations/demo/genesis/branches.json"],
                                "provenance": {"created_at": "2026-05-15T00:00:00+09:00", "source": "aios_chat"},
                            }
                        ],
                    }
                ),
                encoding="utf-8",
            )

            status, payload = module.build_memory_draft_review_response(
                root,
                {"source_artifact": ".aios/chat/demo/memory_drafts.json", "draft_id": "demo:0", "confirm": True},
            )

            self.assertEqual(status, 200)
            self.assertTrue(payload["ok"])
            receipt = payload["receipt"]
            self.assertEqual(receipt["status"], "sent_to_memoryOS_inbox")
            self.assertEqual(receipt["source_artifact"], ".aios/chat/demo/memory_drafts.json")
            self.assertEqual(receipt["draft_type"], "genesis_friction_signal")
            packet = root / receipt["artifact_paths"]["packet"]
            self.assertTrue(packet.exists())
            packet_payload = json.loads(packet.read_text(encoding="utf-8"))
            self.assertEqual(packet_payload["schema_version"], "aios.memory_draft_review_request.v1")
            self.assertEqual(packet_payload["dispatch_id"], receipt["request_id"])
            self.assertEqual(packet_payload["contract_path"], "docs/AIOS_CHAT.md")
            self.assertEqual(packet_payload["target_repo"], "memoryOS")
            self.assertFalse(packet_payload["review_policy"]["auto_accept"])
            self.assertIn("provenance link back", " ".join(packet_payload["must_produce"]))
            self.assertTrue((root / ".aios" / "state" / "memory_draft_reviews.jsonl").exists())

    def test_goal_bar_api_requires_confirmation_before_execute(self) -> None:
        module = load_local_app_module()
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "scripts").mkdir()
            (root / "scripts" / "aios_goal_bar.py").write_text(
                "import json, sys\n"
                "print(json.dumps({'schema_version':'aios.goal_bar.v1','intent':'hive_agents_status','classified_command':'hive agents status','will_execute':True,'executed':'--execute' in sys.argv}))\n",
                encoding="utf-8",
            )

            classify_status, classify_payload = module.build_goal_bar_response(root, {"goal": "어떤 Agent가 있지?"})
            blocked_status, blocked_payload = module.build_goal_bar_response(root, {"goal": "어떤 Agent가 있지?", "execute": True})

        self.assertEqual(classify_status, 200)
        self.assertTrue(classify_payload["ok"])
        self.assertFalse(classify_payload["result"]["executed"])
        self.assertEqual(blocked_status, 409)
        self.assertEqual(blocked_payload["reason"], "confirmation_required")

    def test_chat_api_runs_chat_script(self) -> None:
        module = load_local_app_module()
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "scripts").mkdir()
            (root / "scripts" / "aios_chat.py").write_text(
                "import json, sys\n"
                "assert '--message' in sys.argv\n"
                "assert '--conversation' in sys.argv\n"
                "print(json.dumps({'schema_version':'aios.chat.turn.v1','status':'routed','conversation_id':'web','response':'ok','chosen_substrate':'local_llm'}))\n",
                encoding="utf-8",
            )

            status, payload = module.build_chat_response(root, {"message": "hello", "conversation_id": "web"})

        self.assertEqual(status, 200)
        self.assertTrue(payload["ok"])
        self.assertTrue(payload["result"]["ok"])
        self.assertEqual(payload["result"]["chosen_substrate"], "local_llm")

    def test_gate_chair_probe_runs_chat_script(self) -> None:
        module = load_local_app_module()
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "scripts").mkdir()
            (root / "scripts" / "aios_chat.py").write_text(
                "import json, sys\n"
                "assert '--message' in sys.argv\n"
                "assert '--conversation' in sys.argv\n"
                "print(json.dumps({"
                "'schema_version':'aios.chat.turn.v1',"
                "'status':'routed',"
                "'conversation_id':'gate-chair-probe',"
                "'response':'ok',"
                "'chosen_substrate':'ollama_qwen',"
                "'route_reason':'capability_cost_tier',"
                "'gate_chair_turn':'.aios/chat/gate-chair-probe/gate_chair_turns.jsonl',"
                "'gate_chair_status':{'attempted':True,'executed':True,'status':'success','mode':'internal_evidence_synthesizer','model':'deterministic'},"
                "'artifact_paths':{'gate_chair_turns':'.aios/chat/gate-chair-probe/gate_chair_turns.jsonl'}"
                "}))\n",
                encoding="utf-8",
            )

            status, payload = module.build_gate_chair_probe_response(root, {})

        self.assertEqual(status, 200)
        self.assertTrue(payload["ok"])
        self.assertEqual(payload["schema_version"], "aios.gate_chair_probe.v1")
        self.assertEqual(payload["gate_chair_status"]["status"], "success")
        self.assertEqual(payload["gate_chair_status"]["mode"], "internal_evidence_synthesizer")
        self.assertEqual(payload["gate_chair_turn"], ".aios/chat/gate-chair-probe/gate_chair_turns.jsonl")

    def test_gate_chair_eval_runs_eval_script(self) -> None:
        module = load_local_app_module()
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "scripts").mkdir()
            (root / "scripts" / "aios_gate_chair_eval.py").write_text(
                "import json, sys\n"
                "assert '--mode' in sys.argv\n"
                "print(json.dumps({"
                "'schema_version':'aios.gate_chair_eval.v1',"
                "'eval_id':'eval_demo',"
                "'verdict':'tie_or_no_external_delta',"
                "'scores':{'internal':1.0,'current':1.0},"
                "'promotion_ready':False,"
                "'readiness_reason':'current Chair uses the internal deterministic runtime; no provider-grade runtime delta exists.',"
                "'current_runtime_external':False,"
                "'current_runtime_modes':['internal_evidence_synthesizer'],"
                "'prompt_count':4,"
                "'report_path':'.aios/evals/gate_chair/eval_demo/report.json',"
                "'modes':[{'mode':'internal','average_score':1.0}]"
                "}))\n",
                encoding="utf-8",
            )

            status, payload = module.build_gate_chair_eval_response(root, {"mode": "both"})

        self.assertEqual(status, 200)
        self.assertTrue(payload["ok"])
        self.assertEqual(payload["schema_version"], "aios.gate_chair_eval_api.v1")
        self.assertEqual(payload["verdict"], "tie_or_no_external_delta")
        self.assertEqual(payload["scores"]["internal"], 1.0)
        self.assertFalse(payload["promotion_ready"])
        self.assertFalse(payload["current_runtime_external"])
        self.assertIn("internal deterministic", payload["readiness_reason"])
        self.assertEqual(payload["report_path"], ".aios/evals/gate_chair/eval_demo/report.json")

    def test_gate_chair_eval_rejects_invalid_mode(self) -> None:
        module = load_local_app_module()
        with tempfile.TemporaryDirectory() as tmp:
            status, payload = module.build_gate_chair_eval_response(Path(tmp), {"mode": "unsafe"})

        self.assertEqual(status, 400)
        self.assertFalse(payload["ok"])
        self.assertEqual(payload["reason"], "gate_chair_eval_mode_invalid")

    def test_gate_chair_runtime_requires_confirmation(self) -> None:
        module = load_local_app_module()
        with tempfile.TemporaryDirectory() as tmp:
            status, payload = module.build_gate_chair_runtime_response(
                Path(tmp),
                {"mode": "internal_evidence_synthesizer"},
            )

        self.assertEqual(status, 409)
        self.assertFalse(payload["ok"])
        self.assertEqual(payload["reason"], "confirmation_required")

    def test_gate_chair_runtime_writes_config(self) -> None:
        module = load_local_app_module()
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            status, payload = module.build_gate_chair_runtime_response(
                root,
                {"mode": "ollama", "model": "qwen2.5:7b", "confirm": True, "activate": True},
            )

            config_path = root / ".aios" / "gate" / "founder" / "chair_runtime.json"
            candidate_path = root / ".aios" / "gate" / "founder" / "chair_candidate_runtime.json"
            config = json.loads(config_path.read_text(encoding="utf-8"))

        self.assertEqual(status, 200)
        self.assertTrue(payload["ok"])
        self.assertEqual(payload["schema_version"], "aios.gate_chair_runtime_api.v1")
        self.assertFalse(payload["activation_required"])
        self.assertEqual(payload["runtime_config_path"], ".aios/gate/founder/chair_runtime.json")
        self.assertEqual(config["schema_version"], "aios.gate.chair_runtime.v1")
        self.assertEqual(config["status"], "active")
        self.assertFalse(candidate_path.exists())

    def test_gate_chair_runtime_writes_ollama_candidate_by_default(self) -> None:
        module = load_local_app_module()
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            status, payload = module.build_gate_chair_runtime_response(
                root,
                {"mode": "ollama", "model": "qwen2.5:7b", "confirm": True},
            )

            config_path = root / ".aios" / "gate" / "founder" / "chair_candidate_runtime.json"
            config = json.loads(config_path.read_text(encoding="utf-8"))

        self.assertEqual(status, 200)
        self.assertTrue(payload["ok"])
        self.assertTrue(payload["activation_required"])
        self.assertEqual(payload["runtime_config_path"], ".aios/gate/founder/chair_candidate_runtime.json")
        self.assertEqual(config["mode"], "ollama")
        self.assertEqual(config["status"], "candidate")
        self.assertEqual(config["model"], "qwen2.5:7b")
        self.assertIn("command_available", config)

    def test_gate_chair_runtime_writes_provider_cli_config(self) -> None:
        module = load_local_app_module()
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            status, payload = module.build_gate_chair_runtime_response(
                root,
                {"mode": "claude", "model": "claude-test-model", "confirm": True},
            )

            config_path = root / ".aios" / "gate" / "founder" / "chair_candidate_runtime.json"
            config = json.loads(config_path.read_text(encoding="utf-8"))

        self.assertEqual(status, 200)
        self.assertTrue(payload["ok"])
        self.assertTrue(payload["activation_required"])
        self.assertEqual(payload["runtime_config_path"], ".aios/gate/founder/chair_candidate_runtime.json")
        self.assertEqual(config["mode"], "claude")
        self.assertEqual(config["status"], "candidate")
        self.assertEqual(config["model"], "claude-test-model")
        self.assertEqual(config["provider_substrate"], "claude")
        self.assertIn("command_available", config)

    def test_gate_chair_runtime_rejects_private_model_marker(self) -> None:
        module = load_local_app_module()
        with tempfile.TemporaryDirectory() as tmp:
            status, payload = module.build_gate_chair_runtime_response(
                Path(tmp),
                {"mode": "ollama", "model": "secret-model", "confirm": True},
            )

        self.assertEqual(status, 400)
        self.assertFalse(payload["ok"])
        self.assertEqual(payload["reason"], "model_contains_private_marker")

    def test_gate_chair_promote_requires_ready_eval_report(self) -> None:
        module = load_local_app_module()
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            candidate = root / ".aios" / "gate" / "founder" / "chair_candidate_runtime.json"
            candidate.parent.mkdir(parents=True)
            candidate.write_text(
                json.dumps(
                    {
                        "schema_version": "aios.gate.chair_runtime.v1",
                        "status": "candidate",
                        "mode": "claude",
                        "model": "claude-test-model",
                    }
                ),
                encoding="utf-8",
            )
            report = root / ".aios" / "evals" / "gate_chair" / "eval-ready" / "report.json"
            report.parent.mkdir(parents=True)
            report.write_text(
                json.dumps(
                    {
                        "schema_version": "aios.gate_chair_eval.v1",
                        "promotion_ready": True,
                        "candidate_runtime_path": ".aios/gate/founder/chair_candidate_runtime.json",
                        "readiness_reason": "candidate beat baseline",
                    }
                ),
                encoding="utf-8",
            )

            status, payload = module.build_gate_chair_promote_response(
                root,
                {"confirm": True, "report_path": ".aios/evals/gate_chair/eval-ready/report.json"},
            )
            active = json.loads((root / ".aios" / "gate" / "founder" / "chair_runtime.json").read_text(encoding="utf-8"))

        self.assertEqual(status, 200)
        self.assertTrue(payload["ok"])
        self.assertEqual(payload["schema_version"], "aios.gate_chair_promote_api.v1")
        self.assertEqual(active["status"], "active")
        self.assertEqual(active["mode"], "claude")
        self.assertEqual(active["promotion_report"], ".aios/evals/gate_chair/eval-ready/report.json")

    def test_gate_chair_promote_rejects_not_ready_report(self) -> None:
        module = load_local_app_module()
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            report = root / ".aios" / "evals" / "gate_chair" / "eval-held" / "report.json"
            report.parent.mkdir(parents=True)
            report.write_text(
                json.dumps(
                    {
                        "schema_version": "aios.gate_chair_eval.v1",
                        "promotion_ready": False,
                        "readiness_reason": "candidate did not beat baseline",
                    }
                ),
                encoding="utf-8",
            )

            status, payload = module.build_gate_chair_promote_response(
                root,
                {"confirm": True, "report_path": ".aios/evals/gate_chair/eval-held/report.json"},
            )

        self.assertEqual(status, 409)
        self.assertFalse(payload["ok"])
        self.assertEqual(payload["reason"], "promotion_not_ready")


if __name__ == "__main__":
    unittest.main()
