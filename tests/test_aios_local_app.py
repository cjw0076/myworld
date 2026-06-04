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
            "window.AIOS_CONTROL_SNAPSHOT; function renderContracts(){} function renderDispatches(){} function renderRepos(){} function renderRoster(){} function renderContractBoard(){} function renderRoutes(){} function renderOsObservatory(){} function renderInstallation(){} function renderPromotionQueue(){} function renderCapabilityRouter(){} function renderMemoryLibrary(){} function renderMemoryDraftQueue(){}\n",
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
        chat_html = (root / "apps" / "control" / "chat.html").read_text(encoding="utf-8")
        app_js = (root / "apps" / "control" / "app.js").read_text(encoding="utf-8")
        chat_js = (root / "apps" / "control" / "chat.js").read_text(encoding="utf-8")

        self.assertIn('id="ask-form"', html)
        self.assertIn('id="session-form"', html)
        self.assertIn('id="session-input"', html)
        self.assertIn('id="session-contract-id"', html)
        self.assertIn('id="genesis-cycle-grid"', html)
        self.assertIn('id="genesis-worldline-map"', html)
        self.assertIn('id="genesis-branch-grid"', html)
        self.assertIn('id="os-orbit"', html)
        self.assertIn('id="os-lane-grid"', html)
        self.assertIn('id="quick-action-row"', html)
        self.assertIn('id="anticipatory-surface"', html)
        self.assertIn('id="conversation"', html)
        self.assertIn('id="control-visual-workflow"', html)
        self.assertIn('id="control-visual-evidence"', html)
        self.assertIn("AIOS Control Center", html)
        self.assertIn('id="command-evidence-desk"', html)
        self.assertIn('id="command-governed-ask"', html)
        self.assertIn('id="command-evidence-grid"', html)
        self.assertIn('id="command-receipt-list"', html)
        self.assertIn('href="./chat.html"', html)
        self.assertIn('id="chat-history-list"', chat_html)
        self.assertIn('id="chat-history-refresh"', chat_html)
        self.assertIn('id="chat-decision-map"', chat_html)
        self.assertIn('id="chat-decision-flow"', chat_html)
        self.assertIn('id="offline-user-panel"', chat_html)
        self.assertIn('id="offline-user-body"', chat_html)
        self.assertIn('id="artifact-evidence-desk"', chat_html)
        self.assertIn("Evidence Desk", chat_html)
        self.assertIn("artifact-summary", chat_html)
        self.assertIn("evidence-desk-ask", chat_html)
        self.assertIn("Ask About This", chat_html)
        self.assertIn("visual-workflow", chat_html)
        self.assertIn("screenshot-first", chat_html)
        self.assertIn('fetch("/api/visual_workflow"', chat_js)
        self.assertIn("showVisualWorkflowItem", chat_js)
        self.assertIn('data-history-filter="provider_chair"', chat_html)
        self.assertIn('data-history-filter="memory_review_needed"', chat_html)
        self.assertIn('data-history-filter="failed_provider"', chat_html)
        self.assertIn('fetch("/api/chat_history_action"', chat_js)
        self.assertIn("capability_fallback_preview", chat_js)
        self.assertIn("Preview", chat_js)
        self.assertIn("Fallback", chat_js)
        self.assertIn("Review", chat_js)
        self.assertIn('id="friction-grid"', html)
        self.assertIn('id="capability-router"', html)
        self.assertIn('id="capability-router-grid"', html)
        self.assertIn('id="capability-router-status"', html)
        self.assertIn('id="memory-library"', html)
        self.assertIn('id="memory-library-grid"', html)
        self.assertIn('id="memory-library-status"', html)
        self.assertIn('id="genesis-lens"', html)
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
        self.assertIn('fetch("/api/promote_chat_route"', chat_js)
        self.assertIn('fetch("/api/promote_friction_seed"', app_js)
        self.assertIn('fetch("/api/genesis_break_frame_seed"', app_js)
        self.assertIn('fetch("/api/materialize_promotion_contract"', app_js)
        self.assertIn('fetch("/api/materialize_ask_contract"', app_js)
        self.assertIn('fetch("/api/contract_review_action"', app_js)
        self.assertIn('fetch("/api/visual_workflow"', app_js)
        self.assertIn("renderControlVisualWorkflow", app_js)
        self.assertIn("renderVisualFixWorkItem", app_js)
        self.assertIn("Visual fix prompt prepared", app_js)
        self.assertIn('fetch("/api/promote_visual_fix"', app_js)
        self.assertIn("Promote Fix", app_js)
        self.assertIn("next_contract_id", app_js)
        self.assertIn("visual_focus", app_js)
        self.assertIn("mitigated_by_visual_focus", app_js)
        self.assertIn("No ASC needed unless reopened", app_js)
        self.assertIn("Propose Contract", app_js)
        self.assertIn("Break Frame", app_js)
        self.assertIn("Plan Cleanup", app_js)
        self.assertIn("friction-plan-cleanup", app_js)
        self.assertIn("provenance cleanup", app_js)
        self.assertIn('fetch("/api/memory_draft_review"', app_js)
        self.assertIn('fetch("/api/memory_review_evidence"', app_js)
        self.assertIn("Request Re-review", app_js)
        self.assertIn('fetch("/api/artifact"', app_js)
        self.assertIn('fetch("/api/gate_chair_probe"', app_js)
        self.assertIn('fetch("/api/gate_chair_eval"', app_js)
        self.assertIn('fetch("/api/gate_chair_runtime"', app_js)
        self.assertIn('fetch("/api/gate_chair_promote"', app_js)
        self.assertIn('localStorage.getItem("aios-control-mode") || "simple"', app_js)
        self.assertIn('event.key === "Enter" && !event.shiftKey', app_js)
        self.assertIn("focusInlineChat", app_js)
        self.assertIn("chatPromptButton", app_js)
        self.assertIn("askActionButton", app_js)
        self.assertIn("submitAskGoal", app_js)
        self.assertIn("Creating governed ask", app_js)
        self.assertIn("Ask AIOS", app_js)
        self.assertIn("renderCommandEvidence", app_js)
        self.assertIn("renderAnticipatorySurface", app_js)
        self.assertIn("Next If Idle", app_js)
        self.assertIn("renderOsLiveLoop", app_js)
        self.assertIn("renderGovernedAskCard", app_js)
        self.assertIn("Governed Ask", app_js)
        self.assertIn("renderOfflineUserCard", app_js)
        self.assertIn("Offline User Agent", app_js)
        self.assertIn("offline-user-review", app_js)
        self.assertIn("memory_draft_source", app_js)
        self.assertIn("offline-user-evidence-form", app_js)
        self.assertIn("Operator evidence note", app_js)
        self.assertIn("Propose Contract", app_js)
        self.assertIn('id="os-live-loop"', html)
        self.assertIn("os-live-loop-surface", app_js)
        self.assertIn("Decision Map", app_js)
        self.assertIn("command-decision-node", app_js)
        self.assertIn("resizeInput", app_js)
        self.assertIn("roleProgress", app_js)
        self.assertIn("agent-progress", app_js)
        self.assertIn("Test Gate Chair", app_js)
        self.assertIn("Eval Chair", app_js)
        self.assertIn("Compare Chairs", app_js)
        self.assertIn("Promote Chair", app_js)
        self.assertIn("Gate Runtime Map", app_js)
        self.assertIn("runtime_preview", app_js)
        self.assertIn("runtime-flow-node", app_js)
        self.assertIn("Recovery proof", app_js)
        self.assertIn("chat-runtime-strip", app_js)
        self.assertIn("AIOS runtime evidence", app_js)
        self.assertIn('label: "Chair"', app_js)
        self.assertIn('label: "Memory"', app_js)
        self.assertIn('label: "Capability"', app_js)
        self.assertIn('label: "Genesis"', app_js)
        self.assertIn("Promote Seed", app_js)
        self.assertIn("Create Contract", app_js)
        self.assertIn("Use Internal", app_js)
        self.assertIn("Try Ollama", app_js)
        self.assertIn("Try Claude", app_js)
        self.assertIn("chat-runtime-strip", chat_js)
        self.assertIn("renderChatDecisionMap", chat_js)
        self.assertIn("renderOfflineUserPanel", chat_js)
        self.assertIn("Offline user prompt prepared", chat_js)
        self.assertIn("requestOfflineMemoryReview", chat_js)
        self.assertIn("recordOfflineMemoryEvidence", chat_js)
        self.assertIn("Offline user memory review queued", chat_js)
        self.assertIn("Offline user evidence recorded", chat_js)
        self.assertIn("chat-decision-node", chat_js)
        self.assertIn("has-artifact", chat_js)
        self.assertIn("openArtifact(node.path", chat_js)
        self.assertIn("Promote Route", chat_js)
        self.assertIn("route_promotion", chat_js)
        self.assertIn("Create Contract", chat_js)
        self.assertIn("/api/materialize_promotion_contract", chat_js)
        self.assertIn("AIOS runtime evidence", chat_js)
        self.assertIn("renderMessageBody", chat_js)
        self.assertIn("chat-message-body", chat_js)
        self.assertIn('label: "Chair"', chat_js)
        self.assertIn('label: "Memory"', chat_js)
        self.assertIn('label: "Capability"', chat_js)
        self.assertIn('label: "Genesis"', chat_js)
        self.assertIn('fetch("/api/chat_history"', chat_js)
        self.assertIn("chat-history-card", chat_js)
        self.assertIn("historyChairLabel", chat_js)
        self.assertIn("historyMatchesFilter", chat_js)
        self.assertIn("historyFilterCounts", chat_js)
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
        self.assertIn("artifact-evidence-desk", chat_js)
        self.assertIn("evidence-desk-clear", chat_js)
        self.assertIn("renderArtifactSummary", chat_js)
        self.assertIn("activeArtifactPath", chat_js)
        self.assertIn("Prompt prepared", chat_js)
        self.assertIn("Visual verification", chat_js)
        self.assertIn("Capability route", chat_js)
        self.assertIn("Memory context", chat_js)
        self.assertIn("visual verification", chat_js)
        self.assertIn("hive-artifact-open", app_js)
        self.assertIn("agent-artifact-open", app_js)
        self.assertIn("artifact-lane-open", app_js)
        self.assertIn("renderGenesisLens", app_js)
        self.assertIn("How AIOS escapes the obvious answer", app_js)
        self.assertIn("Feel Friction", app_js)
        self.assertIn("Make Worlds", app_js)
        self.assertIn("Worldline Map", app_js)
        self.assertIn("genesis-worldline-node", app_js)
        self.assertIn("worldline_preview", app_js)
        self.assertIn("Discomfort", app_js)
        self.assertIn("Invention seed", app_js)
        self.assertIn("Develop Seed", app_js)
        self.assertIn("Use Branch", app_js)
        self.assertIn("what_it_breaks", app_js)
        self.assertIn("aios-inline-action", (root / "apps" / "control" / "styles.css").read_text(encoding="utf-8"))
        self.assertIn("anticipatory-surface", (root / "apps" / "control" / "styles.css").read_text(encoding="utf-8"))
        self.assertIn("anticipatory-action", (root / "apps" / "control" / "styles.css").read_text(encoding="utf-8"))
        self.assertIn("command-evidence-desk", (root / "apps" / "control" / "styles.css").read_text(encoding="utf-8"))
        self.assertIn("os-live-loop", (root / "apps" / "control" / "styles.css").read_text(encoding="utf-8"))
        self.assertIn("command-decision-map", (root / "apps" / "control" / "styles.css").read_text(encoding="utf-8"))
        self.assertIn("chat-decision-map", (root / "apps" / "control" / "styles.css").read_text(encoding="utf-8"))
        self.assertIn("chat-decision-node.has-artifact:hover", (root / "apps" / "control" / "styles.css").read_text(encoding="utf-8"))
        self.assertIn("chat-materialize-contract", (root / "apps" / "control" / "styles.css").read_text(encoding="utf-8"))
        self.assertIn("visual-focus-harness", (root / "apps" / "control" / "styles.css").read_text(encoding="utf-8"))
        self.assertIn("control-visual-workflow", (root / "apps" / "control" / "styles.css").read_text(encoding="utf-8"))
        self.assertIn("visual-fix-work-item", (root / "apps" / "control" / "styles.css").read_text(encoding="utf-8"))
        self.assertIn("visual-fix-actions", (root / "apps" / "control" / "styles.css").read_text(encoding="utf-8"))
        self.assertIn("promotion-next-row", (root / "apps" / "control" / "styles.css").read_text(encoding="utf-8"))
        self.assertIn("promotion-quality", (root / "apps" / "control" / "styles.css").read_text(encoding="utf-8"))
        self.assertIn("promotion-materialize-held", (root / "apps" / "control" / "styles.css").read_text(encoding="utf-8"))
        self.assertIn("command-receipt-row", (root / "apps" / "control" / "styles.css").read_text(encoding="utf-8"))
        self.assertIn("command-governed-ask", (root / "apps" / "control" / "styles.css").read_text(encoding="utf-8"))
        self.assertIn("governed-ask-row", (root / "apps" / "control" / "styles.css").read_text(encoding="utf-8"))
        self.assertIn("governed-ask-materialize", (root / "apps" / "control" / "styles.css").read_text(encoding="utf-8"))
        self.assertIn("agent-progress-track", (root / "apps" / "control" / "styles.css").read_text(encoding="utf-8"))
        self.assertIn("runtime-flow-card", (root / "apps" / "control" / "styles.css").read_text(encoding="utf-8"))
        self.assertIn("runtime-flow-edge.demotes", (root / "apps" / "control" / "styles.css").read_text(encoding="utf-8"))
        self.assertIn("genesis-cycle-card", (root / "apps" / "control" / "styles.css").read_text(encoding="utf-8"))
        self.assertIn("genesis-worldline-card", (root / "apps" / "control" / "styles.css").read_text(encoding="utf-8"))
        self.assertIn("genesis-worldline-edge.invents", (root / "apps" / "control" / "styles.css").read_text(encoding="utf-8"))
        self.assertIn("os-product-metrics", (root / "apps" / "control" / "styles.css").read_text(encoding="utf-8"))
        self.assertIn("os-product-actions", (root / "apps" / "control" / "styles.css").read_text(encoding="utf-8"))
        self.assertIn("renderFrictionRadar", app_js)
        self.assertIn("renderOsObservatory", app_js)
        self.assertIn("renderOsSignal", app_js)
        self.assertIn("retrieval selectivity", app_js)
        self.assertIn("route coverage", app_js)
        self.assertIn("divergence width", app_js)
        self.assertIn("execution proof", app_js)
        self.assertIn("renderCapabilityRouter", app_js)
        self.assertIn("Tools, providers, and search routes", html)
        self.assertIn("How AIOS chooses tools and providers", app_js)
        self.assertIn("Route Task", app_js)
        self.assertIn("Ask Permission", app_js)
        self.assertIn("requires_network", app_js)
        self.assertIn("Gap pressure", app_js)
        self.assertIn("이 route를 지금 작업에 써도 되는지", app_js)
        self.assertIn("Choose Source", app_js)
        self.assertIn("Review Gaps", app_js)
        self.assertIn("Internal/Web/API/MCP/Connector", app_js)
        self.assertIn("route_preview", app_js)
        self.assertIn("Route Evidence Map", app_js)
        self.assertIn("capability-route-map", (root / "apps" / "control" / "styles.css").read_text(encoding="utf-8"))
        self.assertIn("capability-route-edge.fallback", (root / "apps" / "control" / "styles.css").read_text(encoding="utf-8"))
        self.assertIn("capability-router-meter", (root / "apps" / "control" / "styles.css").read_text(encoding="utf-8"))
        self.assertIn("capability-source-grid", (root / "apps" / "control" / "styles.css").read_text(encoding="utf-8"))
        self.assertIn("capability-gap-row", (root / "apps" / "control" / "styles.css").read_text(encoding="utf-8"))
        self.assertIn("renderMemoryLibrary", app_js)
        self.assertIn("What MemoryOS knows", html)
        self.assertIn("What AIOS can remember for you", app_js)
        self.assertIn("Ask Memory", app_js)
        self.assertIn("Find Missing", app_js)
        self.assertIn('get("mode")', app_js)
        self.assertIn("restoreSectionHash", app_js)
        self.assertIn("retrieval_traces_with_selected", app_js)
        self.assertIn("provenance links per graph node", app_js)
        self.assertIn("memory-graph-map", app_js)
        self.assertIn("graph_preview", app_js)
        self.assertIn("memory-graph-edge.provenance", (root / "apps" / "control" / "styles.css").read_text(encoding="utf-8"))
        self.assertIn("selected_memory_ids", app_js)
        self.assertIn("Latest request", app_js)
        self.assertIn("memory-library-meter", (root / "apps" / "control" / "styles.css").read_text(encoding="utf-8"))
        self.assertIn("memory-graph-node", (root / "apps" / "control" / "styles.css").read_text(encoding="utf-8"))
        self.assertIn("memory-trace-box", (root / "apps" / "control" / "styles.css").read_text(encoding="utf-8"))
        self.assertIn("os-signal-track", (root / "apps" / "control" / "styles.css").read_text(encoding="utf-8"))
        self.assertIn("renderMemoryDraftQueue", app_js)
        self.assertIn("memory-draft-open", app_js)
        self.assertIn("requestMemoryDraftReview", app_js)
        self.assertIn("next_evidence", app_js)
        self.assertIn("memory-draft-next-evidence", app_js)
        self.assertIn("recordMemoryReviewEvidence", app_js)
        self.assertIn("Add Evidence", app_js)
        self.assertIn("completionBlockers", app_js)
        self.assertIn("AIOS readiness audit", app_js)
        self.assertIn("Do not declare complete yet", app_js)
        self.assertIn("Readiness Audit", html)
        self.assertIn("readiness-blocker-list", app_js)
        self.assertIn("readiness-blocker-card", app_js)
        self.assertIn("readiness-blocker-row", (root / "apps" / "control" / "styles.css").read_text(encoding="utf-8"))
        self.assertIn("min-height: 128px", (root / "apps" / "control" / "styles.css").read_text(encoding="utf-8"))
        self.assertIn("overflow-x: auto", (root / "apps" / "control" / "styles.css").read_text(encoding="utf-8"))
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

    def test_visual_workflow_returns_latest_screenshots_and_receipt(self) -> None:
        module = load_local_app_module()
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            screenshots = root / ".aios" / "screenshots"
            screenshots.mkdir(parents=True)
            (screenshots / "aios-chat-reference-before.png").write_bytes(b"\x89PNG\r\nreference")
            (screenshots / "aios-chat-design-workflow-after.png").write_bytes(b"\x89PNG\r\nafter")
            (screenshots / "vis-demo.png").write_bytes(b"\x89PNG\r\nlatest")
            receipt = root / ".aios" / "visual_verification" / "vis-demo" / "receipt.json"
            receipt.parent.mkdir(parents=True)
            receipt.write_text(
                json.dumps(
                    {
                        "schema_version": "aios.visual_verification.v1",
                        "status": "degraded",
                        "screenshot_path": ".aios/screenshots/vis-demo.png",
                        "stop_conditions": ["browser_verification_timeout"],
                    }
                ),
                encoding="utf-8",
            )

            status, payload = module.build_visual_workflow_response(root)

        self.assertEqual(status, 200)
        self.assertTrue(payload["ok"])
        self.assertEqual(payload["schema_version"], "aios.visual_workflow.v1")
        self.assertEqual(payload["status"], "ready")
        self.assertEqual(payload["items"]["reference"]["path"], ".aios/screenshots/aios-chat-reference-before.png")
        self.assertEqual(payload["items"]["after"]["path"], ".aios/screenshots/vis-demo.png")
        self.assertTrue(payload["items"]["reference"]["data_url"].startswith("data:image/png;base64,"))
        self.assertEqual(payload["items"]["receipt"]["status"], "degraded")
        self.assertIn("browser_verification_timeout", payload["items"]["receipt"]["stop_conditions"])
        self.assertEqual(payload["action"]["kind"], "visual_fix_work_item")
        self.assertIn("receipt=.aios/visual_verification/vis-demo/receipt.json", payload["action"]["prompt"])
        self.assertIn("browser_verification_timeout", payload["action"]["prompt"])

    def test_visual_fix_promotion_writes_contract_seed(self) -> None:
        module = load_local_app_module()
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            receipt = root / ".aios" / "visual_verification" / "vis-demo" / "receipt.json"
            receipt.parent.mkdir(parents=True)
            receipt.write_text(
                json.dumps(
                    {
                        "schema_version": "aios.visual_verification.v1",
                        "status": "degraded",
                        "screenshot_path": ".aios/screenshots/vis-demo.png",
                        "stop_conditions": ["browser_visual_evidence_suspicious"],
                    }
                ),
                encoding="utf-8",
            )

            status, payload = module.build_visual_fix_promotion_response(
                root,
                {"visual_receipt": ".aios/visual_verification/vis-demo/receipt.json", "confirm": True},
            )

            self.assertEqual(status, 200)
            self.assertTrue(payload["ok"])
            promotion = payload["receipt"]
            self.assertFalse(promotion["execution_started"])
            self.assertTrue(promotion["materialization_recommended"])
            self.assertEqual(promotion["source"]["status"], "degraded")
            seed = root / promotion["artifact_paths"]["contract_seed"]
            self.assertTrue(seed.exists())
            seed_text = seed.read_text(encoding="utf-8")
            self.assertIn("origin: AIOS visual workflow promotion", seed_text)
            self.assertIn("visual_receipt: `.aios/visual_verification/vis-demo/receipt.json`", seed_text)
            self.assertIn("browser_visual_evidence_suspicious", seed_text)

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
            context_pack = root / ".aios" / "invocations" / "demo" / "memory" / "context_pack.md"
            context_pack.parent.mkdir(parents=True)
            context_pack.write_text(
                "\n".join(
                    [
                        "# Context pack",
                        "- selected_memory_ids: [\"mem_founder\", \"mem_route\"]",
                        "- trace_id: rtrace_promotionfixture",
                        "- signal_coverage: 1.0",
                        "",
                    ]
                ),
                encoding="utf-8",
            )
            envelope.write_text(
                json.dumps(
                    {
                        "schema_version": "aios.session_envelope.v1",
                        "goal": "Build reviewed promotion",
                        "role_artifacts": {
                            "dispatch_packets": ".aios/invocations/demo/dispatch/packets.json",
                            "memory_context_pack": ".aios/invocations/demo/memory/context_pack.md",
                            "capability_route": ".aios/invocations/demo/capability/route.json",
                            "genesis": ".aios/invocations/demo/genesis/branches.json",
                            "hive_execution_plan": ".aios/invocations/demo/hive/execution_plan.json",
                        },
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
            self.assertTrue(receipt["materialization_recommended"])
            self.assertEqual(receipt["quality_warnings"], [])
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
            self.assertIn("retrieval_trace: `rtrace_promotionfixture`", seed_text)
            self.assertIn("signal_coverage: `1.0`", seed_text)
            self.assertIn("MemoryOS / Retriever: retrieval_trace `rtrace_promotionfixture`, signal_coverage: `1.0`", seed_text)

    def test_chat_route_promotion_uses_invocation_receipt_envelope(self) -> None:
        module = load_local_app_module()
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            invocation = root / ".aios" / "invocations" / "chat-demo"
            invocation.mkdir(parents=True)
            (invocation / "session_envelope.json").write_text(
                json.dumps(
                    {
                        "schema_version": "aios.session_envelope.v1",
                        "goal": "Promote route from chat",
                        "role_artifacts": {"memory_context_pack": ".aios/invocations/chat-demo/memory/context_pack.md"},
                    }
                ),
                encoding="utf-8",
            )
            (invocation / "receipt.json").write_text(
                json.dumps(
                    {
                        "schema_version": "aios.invocation_receipt.v1",
                        "invocation_id": "chat-demo",
                        "overall_status": "passed",
                        "session_envelope": ".aios/invocations/chat-demo/session_envelope.json",
                    }
                ),
                encoding="utf-8",
            )

            status, payload = module.build_chat_route_promotion_response(
                root,
                {"invocation_receipt": ".aios/invocations/chat-demo/receipt.json", "confirm": True},
            )

            self.assertEqual(status, 200)
            self.assertTrue(payload["ok"])
            self.assertEqual(payload["schema_version"], "aios.chat_route_promotion.v1")
            self.assertEqual(payload["source_invocation_receipt"], ".aios/invocations/chat-demo/receipt.json")
            receipt = payload["receipt"]
            self.assertFalse(receipt["execution_started"])
            self.assertEqual(receipt["session_envelope"]["ref"], ".aios/invocations/chat-demo/session_envelope.json")
            self.assertTrue((root / receipt["artifact_paths"]["contract_seed"]).exists())

    def test_chat_route_promotion_marks_weak_route_and_blocks_materialization(self) -> None:
        module = load_local_app_module()
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            invocation = root / ".aios" / "invocations" / "chat-weak"
            invocation.mkdir(parents=True)
            (invocation / "session_envelope.json").write_text(
                json.dumps(
                    {
                        "schema_version": "aios.session_envelope.v1",
                        "goal": "status?",
                        "role_artifacts": {
                            "memory_context_pack": ".aios/invocations/chat-weak/memory/context_pack.md",
                        },
                    }
                ),
                encoding="utf-8",
            )
            (invocation / "receipt.json").write_text(
                json.dumps(
                    {
                        "schema_version": "aios.invocation_receipt.v1",
                        "invocation_id": "chat-weak",
                        "overall_status": "passed",
                        "session_envelope": ".aios/invocations/chat-weak/session_envelope.json",
                    }
                ),
                encoding="utf-8",
            )

            status, payload = module.build_chat_route_promotion_response(
                root,
                {"invocation_receipt": ".aios/invocations/chat-weak/receipt.json", "confirm": True},
            )

            self.assertEqual(status, 200)
            receipt = payload["receipt"]
            self.assertFalse(receipt["materialization_recommended"])
            self.assertIn("goal_too_short_for_contract_materialization", receipt["quality_warnings"])

            material_status, material_payload = module.build_promotion_contract_materialization_response(
                root,
                {
                    "promotion_receipt": receipt["artifact_paths"]["receipt"],
                    "asc_id": "ASC-0998",
                    "confirm": True,
                },
            )

            self.assertEqual(material_status, 409)
            self.assertEqual(material_payload["reason"], "promotion_quality_warning")
            self.assertIn("weak_route_materialization_requires_revision_or_override", material_payload["stop_condition"])

    def test_friction_seed_promotion_writes_contract_seed_copy(self) -> None:
        module = load_local_app_module()
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            seed = root / ".aios" / "chat" / "demo" / "friction_contract_seed.md"
            seed.parent.mkdir(parents=True)
            seed.write_text(
                "\n".join(
                    [
                        "---",
                        "contract_id: ASC-XXXX",
                        "status: proposed",
                        "authority: speculative_only",
                        "---",
                        "",
                        "# Demo Seed",
                        "",
                        "This file is not execution authority; it is a reviewable bridge.",
                        "",
                        "## Proposed Goal",
                        "",
                        "Turn GenesisOS discomfort into a scoped AIOS contract.",
                        "",
                        "## Evidence",
                        "",
                        "- genesis_branches: `.aios/invocations/demo/genesis/branches.json`",
                    ]
                )
                + "\n",
                encoding="utf-8",
            )

            status, payload = module.build_friction_seed_promotion_response(
                root,
                {"source_seed": ".aios/chat/demo/friction_contract_seed.md", "confirm": True},
            )

            self.assertEqual(status, 200)
            self.assertTrue(payload["ok"])
            receipt = payload["receipt"]
            self.assertFalse(receipt["execution_started"])
            self.assertEqual(receipt["source_seed"], ".aios/chat/demo/friction_contract_seed.md")
            self.assertEqual(receipt["goal"], "Turn GenesisOS discomfort into a scoped AIOS contract.")
            copied = root / receipt["artifact_paths"]["contract_seed"]
            self.assertTrue(copied.exists())
            copied_text = copied.read_text(encoding="utf-8")
            self.assertIn("Promotion Receipt", copied_text)
            self.assertIn("source_seed: `.aios/chat/demo/friction_contract_seed.md`", copied_text)

    def test_promotion_contract_materialization_writes_proposed_contract(self) -> None:
        module = load_local_app_module()
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            promotion = root / ".aios" / "promotions" / "promotion-demo"
            promotion.mkdir(parents=True)
            seed = promotion / "contract_seed.md"
            seed.write_text(
                "\n".join(
                    [
                        "---",
                        "contract_id: ASC-XXXX",
                        "status: proposed",
                        "goal: Turn GenesisOS discomfort into a scoped AIOS contract.",
                        "---",
                        "",
                        "# ASC-XXXX Genesis Discomfort Contract",
                        "",
                        "## Scope",
                        "",
                        "allowed_files:",
                        "",
                        "- `docs/contracts/ASC-XXXX-turn-genesisos-discomfort-into-a-scoped-aios-contract.md`",
                    ]
                )
                + "\n",
                encoding="utf-8",
            )
            receipt = promotion / "promotion.json"
            receipt.write_text(
                json.dumps(
                    {
                        "schema_version": "aios.session_promotion.v1",
                        "promotion_id": "promotion-demo",
                        "status": "proposed_contract_seed",
                        "goal": "Turn GenesisOS discomfort into a scoped AIOS contract.",
                        "artifact_paths": {
                            "receipt": ".aios/promotions/promotion-demo/promotion.json",
                            "contract_seed": ".aios/promotions/promotion-demo/contract_seed.md",
                        },
                        "execution_started": False,
                    }
                ),
                encoding="utf-8",
            )

            status, payload = module.build_promotion_contract_materialization_response(
                root,
                {
                    "promotion_receipt": ".aios/promotions/promotion-demo/promotion.json",
                    "asc_id": "ASC-0999",
                    "confirm": True,
                },
            )

            self.assertEqual(status, 200)
            self.assertTrue(payload["ok"])
            materialization = payload["materialization"]
            self.assertFalse(materialization["execution_started"])
            self.assertEqual(materialization["contract_id"], "ASC-0999")
            contract = root / materialization["contract_path"]
            self.assertTrue(contract.exists())
            text = contract.read_text(encoding="utf-8")
            self.assertIn("contract_id: ASC-0999", text)
            self.assertIn("# ASC-0999 Genesis Discomfort Contract", text)
            self.assertNotIn("ASC-XXXX", text)
            mat_receipt = promotion / "materialization.json"
            self.assertTrue(mat_receipt.exists())

    def test_genesis_break_frame_seed_materializes_proposed_contract(self) -> None:
        module = load_local_app_module()
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            contract_dir = root / "docs" / "contracts"
            contract_dir.mkdir(parents=True)
            source = contract_dir / "ASC-0999-source.md"
            source.write_text("---\ncontract_id: ASC-0999\nstatus: accepted\n---\n# Source\n", encoding="utf-8")

            status, payload = module.build_genesis_break_frame_seed_response(
                root,
                {
                    "confirm": True,
                    "materialize": True,
                    "contract_id": "ASC-0999",
                    "contract_path": "docs/contracts/ASC-0999-source.md",
                    "reason": "GenesisOS critic found prompt-prison signatures.",
                    "escape_vectors": ["restate as schema", "negate assumptions"],
                    "signatures": [{"signature": "mono-language", "evidence": "long prose"}],
                },
            )

            self.assertEqual(status, 200)
            self.assertTrue(payload["ok"])
            self.assertFalse(payload["execution_started"])
            self.assertIn(".aios/chat/friction-radar-", payload["source_seed"])
            self.assertEqual(payload["materialization"]["contract_id"], "ASC-1000")
            materialized = root / payload["materialization"]["contract_path"]
            self.assertTrue(materialized.exists())
            text = materialized.read_text(encoding="utf-8")
            self.assertIn("contract_id: ASC-1000", text)
            self.assertIn("authority: speculative_only", text)
            self.assertIn("This file is not execution authority", text)
            self.assertIn(f"- `{payload['materialization']['contract_path']}`", text)
            self.assertIn("restate as schema", text)

    def test_promotion_contract_materialization_requires_confirmation(self) -> None:
        module = load_local_app_module()
        with tempfile.TemporaryDirectory() as tmp:
            status, payload = module.build_promotion_contract_materialization_response(
                Path(tmp),
                {"promotion_receipt": ".aios/promotions/demo/promotion.json", "asc_id": "ASC-0999"},
            )

        self.assertEqual(status, 409)
        self.assertFalse(payload["ok"])
        self.assertEqual(payload["reason"], "confirmation_required")

    def test_ask_contract_materialization_writes_proposed_contract(self) -> None:
        module = load_local_app_module()
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            ask = root / ".aios" / "asks" / "ask-demo"
            ask.mkdir(parents=True)
            (ask / "contract_seed.md").write_text(
                "\n".join(
                    [
                        "---",
                        "contract_id: ASC-XXXX",
                        "status: proposed",
                        "goal: Turn ask into a governed contract.",
                        "---",
                        "",
                        "# ASC-XXXX Ask Contract",
                    ]
                )
                + "\n",
                encoding="utf-8",
            )
            (ask / "receipt.json").write_text(
                json.dumps(
                    {
                        "schema_version": "aios.ask.receipt.v1",
                        "ask_id": "ask-demo",
                        "goal": "Turn ask into a governed contract.",
                        "status": "passed",
                        "artifact_paths": {
                            "contract_seed": ".aios/asks/ask-demo/contract_seed.md",
                        },
                    }
                ),
                encoding="utf-8",
            )

            status, payload = module.build_ask_contract_materialization_response(
                root,
                {
                    "ask_receipt": ".aios/asks/ask-demo/receipt.json",
                    "asc_id": "ASC-0998",
                    "confirm": True,
                },
            )

            self.assertEqual(status, 200)
            self.assertTrue(payload["ok"])
            materialization = payload["materialization"]
            self.assertFalse(materialization["execution_started"])
            self.assertEqual(materialization["ask_id"], "ask-demo")
            self.assertEqual(materialization["contract_id"], "ASC-0998")
            contract = root / materialization["contract_path"]
            self.assertTrue(contract.exists())
            text = contract.read_text(encoding="utf-8")
            self.assertIn("contract_id: ASC-0998", text)
            self.assertIn("# ASC-0998 Ask Contract", text)
            self.assertNotIn("ASC-XXXX", text)
            self.assertTrue((ask / "materialization.json").exists())

    def test_contract_review_action_marks_proposed_contract_superseded(self) -> None:
        module = load_local_app_module()
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            contract = root / "docs" / "contracts" / "ASC-0999-weak.md"
            contract.parent.mkdir(parents=True)
            contract.write_text(
                "---\ncontract_id: ASC-0999\nstatus: proposed\ngoal: weak\n---\n\n# Weak\n",
                encoding="utf-8",
            )

            status, payload = module.build_contract_review_action_response(
                root,
                {
                    "contract_path": "docs/contracts/ASC-0999-weak.md",
                    "action": "mark_superseded",
                    "reason": "weak route promotion",
                    "confirm": True,
                },
            )

            self.assertEqual(status, 200)
            self.assertTrue(payload["ok"])
            text = contract.read_text(encoding="utf-8")
            self.assertIn("status: superseded", text)
            self.assertIn("superseded_reason: weak route promotion", text)
            receipt = root / ".aios" / "contract_reviews" / payload["receipt"]["review_id"] / "review_action.json"
            self.assertTrue(receipt.exists())
            self.assertFalse(payload["receipt"]["execution_started"])

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

    def test_offline_user_field_observation_review_preserves_source_packet(self) -> None:
        module = load_local_app_module()
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            packet_ref = ".aios/inbox/memoryOS/asc-0210.field-observation.visual-check.json"
            draft_path = root / ".aios" / "chat" / "offline-user" / "memory_drafts.json"
            draft_path.parent.mkdir(parents=True)
            draft_path.write_text(
                json.dumps(
                    {
                        "schema_version": "aios.chat.memory_drafts.v1",
                        "memory_drafts": [
                            {
                                "id": "offline-user:visual-check",
                                "type": "field_observation",
                                "origin": "offline_user_agent",
                                "status": "draft",
                                "confidence": 0.74,
                                "conversation_id": "offline-user",
                                "project": "AIOS",
                                "content": "The operator understood the offline-user card but wanted it closer to the top.",
                                "raw_refs": [packet_ref],
                                "provenance": {
                                    "source": "aios_offline_user_agent",
                                    "source_packet": packet_ref,
                                    "observed_by": "user@offline",
                                    "private_data_included": False,
                                },
                            }
                        ],
                    }
                ),
                encoding="utf-8",
            )

            status, payload = module.build_memory_draft_review_response(
                root,
                {
                    "source_artifact": ".aios/chat/offline-user/memory_drafts.json",
                    "draft_id": "offline-user:visual-check",
                    "confirm": True,
                },
            )

            self.assertEqual(status, 200)
            receipt = payload["receipt"]
            packet = json.loads((root / receipt["artifact_paths"]["packet"]).read_text(encoding="utf-8"))
            self.assertEqual(packet["draft"]["type"], "field_observation")
            self.assertEqual(packet["draft"]["origin"], "offline_user_agent")
            self.assertEqual(packet["draft"]["raw_refs"], [packet_ref])
            self.assertEqual(packet["draft"]["provenance"]["observed_by"], "user@offline")
            self.assertFalse(packet["review_policy"]["auto_accept"])
            self.assertTrue(packet["review_policy"]["draft_first"])

    def test_memory_review_evidence_writes_receipt_without_accepting(self) -> None:
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
                                "content": "Needs stronger evidence.",
                                "raw_refs": ["messages.jsonl"],
                                "provenance": {"source": "aios_chat"},
                            }
                        ],
                    }
                ),
                encoding="utf-8",
            )
            evidence_artifact = root / ".aios" / "chat" / "demo" / "messages.jsonl"
            evidence_artifact.write_text('{"role":"user","content":"repeat"}\n', encoding="utf-8")

            status, payload = module.build_memory_review_evidence_response(
                root,
                {
                    "source_artifact": ".aios/chat/demo/memory_drafts.json",
                    "draft_id": "demo:0",
                    "note": "Founder repeated the same discomfort in a later turn.",
                    "evidence_artifact": ".aios/chat/demo/messages.jsonl",
                    "confirm": True,
                },
            )

            self.assertEqual(status, 200)
            self.assertTrue(payload["ok"])
            receipt = payload["receipt"]
            self.assertFalse(receipt["execution_started"])
            self.assertEqual(receipt["status"], "evidence_recorded")
            self.assertEqual(receipt["draft_id"], "demo:0")
            self.assertEqual(receipt["evidence_artifact"], ".aios/chat/demo/messages.jsonl")
            self.assertTrue((root / receipt["artifact_paths"]["evidence"]).exists())
            self.assertTrue((root / ".aios" / "state" / "memory_review_evidence.jsonl").exists())
            self.assertEqual(receipt["next_action"], "request_memoryos_review_again_when_evidence_is_sufficient")

    def test_memory_draft_rereview_includes_supplemental_evidence_refs(self) -> None:
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
                                "type": "negative_evidence_signal",
                                "origin": "aios_chat_negative_evidence",
                                "status": "draft",
                                "content": "Provider failed in a repeated pattern.",
                                "raw_refs": ["messages.jsonl"],
                                "provenance": {"source": "aios_chat"},
                            }
                        ],
                    }
                ),
                encoding="utf-8",
            )
            evidence_artifact = root / ".aios" / "chat" / "demo" / "provider_failure.json"
            evidence_artifact.write_text('{"status":"provider_access_denied"}\n', encoding="utf-8")

            evidence_status, evidence_payload = module.build_memory_review_evidence_response(
                root,
                {
                    "source_artifact": ".aios/chat/demo/memory_drafts.json",
                    "draft_id": "demo:0",
                    "note": "The same provider failed again during Gate Chair eval.",
                    "evidence_artifact": ".aios/chat/demo/provider_failure.json",
                    "confirm": True,
                },
            )
            self.assertEqual(evidence_status, 200)

            review_status, review_payload = module.build_memory_draft_review_response(
                root,
                {"source_artifact": ".aios/chat/demo/memory_drafts.json", "draft_id": "demo:0", "confirm": True},
            )

            self.assertEqual(review_status, 200)
            receipt = review_payload["receipt"]
            self.assertEqual(receipt["supplemental_evidence_count"], 1)
            packet = json.loads((root / receipt["artifact_paths"]["packet"]).read_text(encoding="utf-8"))
            self.assertEqual(len(packet["supplemental_evidence"]), 1)
            raw_refs = packet["draft"]["raw_refs"]
            self.assertIn("messages.jsonl", raw_refs)
            self.assertIn(evidence_payload["receipt"]["artifact_paths"]["evidence"], raw_refs)
            self.assertIn(".aios/chat/demo/provider_failure.json", raw_refs)
            self.assertIn("supplemental evidence refs preserved", " ".join(packet["must_produce"]))

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

    def test_chat_history_summarizes_runtime_without_private_preview(self) -> None:
        module = load_local_app_module()
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            chat = root / ".aios" / "chat" / "demo"
            chat.mkdir(parents=True)
            (chat / "messages.jsonl").write_text(
                "\n".join(
                    [
                        json.dumps(
                            {
                                "schema_version": "aios.chat.message.v1",
                                "turn_id": "turn_demo",
                                "role": "user",
                                "content": "내 이메일 cjw070690@example.com 과 pin q1q1e3e3 기억해?",
                                "created_at": "2026-05-17T00:00:00+09:00",
                            },
                            ensure_ascii=False,
                        ),
                        json.dumps(
                            {
                                "schema_version": "aios.chat.message.v1",
                                "turn_id": "turn_demo",
                                "role": "assistant",
                                "content": "MemoryOS가 cjw070690@example.com 관련 기억을 찾았어.",
                                "created_at": "2026-05-17T00:00:01+09:00",
                                "substrate": "aios_gate",
                                "route_reason": "gate_answer",
                                "intent": "aios_architecture",
                            },
                            ensure_ascii=False,
                        ),
                    ]
                )
                + "\n",
                encoding="utf-8",
            )
            (chat / "gate_chair_turns.jsonl").write_text(
                json.dumps(
                    {
                        "schema_version": "aios.chat.gate_chair_turn.v1",
                        "turn_id": "gatechair_demo",
                        "executed": True,
                        "created_at": "2026-05-17T00:00:01+09:00",
                        "chair_meta": {
                            "status": "success",
                            "meta": {"mode": "claude", "model": "claude-opus-4-6"},
                        },
                    },
                    ensure_ascii=False,
                )
                + "\n",
                encoding="utf-8",
            )
            (chat / "cost.json").write_text("{}", encoding="utf-8")
            (chat / "memory_drafts.json").write_text(
                json.dumps({"schema_version": "aios.chat.memory_drafts.v1", "memory_drafts": []}),
                encoding="utf-8",
            )
            (chat / "provider_turns.jsonl").write_text(
                json.dumps(
                    {
                        "schema_version": "aios.chat.provider_turn.v1",
                        "turn_id": "provider_demo",
                        "executed": False,
                        "provider_meta": {"status": "provider_backpressure"},
                    },
                    ensure_ascii=False,
                )
                + "\n",
                encoding="utf-8",
            )
            review = root / ".aios" / "outbox" / "memoryOS" / "mdrev-demo.memoryOS.result.json"
            review.parent.mkdir(parents=True)
            review.write_text(
                json.dumps(
                    {
                        "schema_version": "aios.dispatch.result.v1",
                        "review_request": {
                            "source_artifact": ".aios/chat/demo/memory_drafts.json",
                            "review_decision": "needs_more_evidence",
                        },
                    },
                    ensure_ascii=False,
                ),
                encoding="utf-8",
            )

            status, payload = module.build_chat_history_response(root)

        self.assertEqual(status, 200)
        self.assertTrue(payload["ok"])
        self.assertEqual(payload["schema_version"], "aios.chat.history.v1")
        self.assertEqual(payload["items"][0]["conversation_id"], "demo")
        self.assertEqual(payload["items"][0]["chair"]["mode"], "claude")
        self.assertEqual(payload["items"][0]["substrate"], "aios_gate")
        self.assertIn("provider_chair", payload["items"][0]["flags"])
        self.assertIn("memory_review_needed", payload["items"][0]["flags"])
        self.assertIn("failed_provider", payload["items"][0]["flags"])
        self.assertEqual(payload["counts"]["provider_chair"], 1)
        self.assertEqual(payload["counts"]["memory_review_needed"], 1)
        self.assertEqual(payload["counts"]["failed_provider"], 1)
        self.assertEqual(payload["items"][0]["memory_review_decisions"], ["needs_more_evidence"])
        self.assertEqual(payload["items"][0]["provider_failure_statuses"], ["provider_backpressure"])
        self.assertIn("[REDACTED_PRIVATE]", payload["items"][0]["last_user_preview"])
        self.assertIn("[REDACTED_PRIVATE]", payload["items"][0]["last_response_preview"])
        self.assertNotIn("cjw070690@example.com", json.dumps(payload, ensure_ascii=False))
        self.assertNotIn("q1q1e3e3", json.dumps(payload, ensure_ascii=False))
        self.assertEqual(payload["items"][0]["artifact_paths"]["messages"], ".aios/chat/demo/messages.jsonl")

    def test_chat_history_action_writes_capability_fallback_packet(self) -> None:
        module = load_local_app_module()
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            chat = root / ".aios" / "chat" / "demo"
            chat.mkdir(parents=True)
            (chat / "messages.jsonl").write_text(
                json.dumps({"role": "user", "content": "provider failed", "created_at": "2026-05-17T00:00:00+09:00"})
                + "\n"
                + json.dumps(
                    {
                        "role": "assistant",
                        "content": "fallback needed",
                        "created_at": "2026-05-17T00:00:01+09:00",
                        "substrate": "aios_gate",
                        "route_reason": "gate_answer",
                        "intent": "aios_architecture",
                    }
                )
                + "\n",
                encoding="utf-8",
            )
            (chat / "gate_chair_turns.jsonl").write_text(
                json.dumps(
                    {
                        "schema_version": "aios.chat.gate_chair_turn.v1",
                        "turn_id": "gatechair_demo",
                        "executed": False,
                        "created_at": "2026-05-17T00:00:01+09:00",
                        "chair_meta": {
                            "status": "gate_chair_timeout",
                            "meta": {"mode": "claude", "model": "claude-opus-4-6"},
                        },
                    }
                )
                + "\n",
                encoding="utf-8",
            )
            (chat / "provider_turns.jsonl").write_text(
                json.dumps(
                    {
                        "schema_version": "aios.chat.provider_turn.v1",
                        "turn_id": "provider_demo",
                        "executed": False,
                        "provider_meta": {"status": "provider_backpressure"},
                    }
                )
                + "\n",
                encoding="utf-8",
            )
            gate_dir = chat / "gate_decisions"
            gate_dir.mkdir()
            (gate_dir / "turn.json").write_text("{}", encoding="utf-8")
            (chat / "cost.json").write_text("{}", encoding="utf-8")
            (chat / "run_state.json").write_text("{}", encoding="utf-8")

            status, payload = module.build_chat_history_action_response(
                root,
                {"conversation_id": "demo", "action": "capability_fallback_review", "confirm": True},
            )

            self.assertEqual(status, 200)
            self.assertTrue(payload["ok"])
            receipt = payload["receipt"]
            self.assertEqual(receipt["status"], "sent_to_CapabilityOS_inbox")
            packet = root / receipt["artifact_paths"]["packet"]
            self.assertTrue(packet.exists())
            packet_payload = json.loads(packet.read_text(encoding="utf-8"))
            self.assertEqual(packet_payload["target_repo"], "CapabilityOS")
            self.assertEqual(packet_payload["contract_id"], "CHAT-HISTORY-FALLBACK-REVIEW")
            self.assertIn("gate_chair_timeout", packet_payload["failure_statuses"])
            self.assertIn("provider_backpressure", packet_payload["failure_statuses"])
            self.assertIn("provider_turns", packet_payload["source_artifacts"])
            self.assertNotIn(".aios/chat/*/messages.jsonl", packet_payload["scope"]["allowed_files"])
            self.assertTrue((root / ".aios" / "state" / "capability_fallback_reviews.jsonl").exists())

    def test_chat_history_action_previews_capability_fallback_without_writing_packet(self) -> None:
        module = load_local_app_module()
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            chat = root / ".aios" / "chat" / "demo"
            chat.mkdir(parents=True)
            (chat / "messages.jsonl").write_text(
                json.dumps({"role": "user", "content": "provider failed", "created_at": "2026-05-17T00:00:00+09:00"})
                + "\n"
                + json.dumps({"role": "assistant", "content": "fallback needed", "created_at": "2026-05-17T00:00:01+09:00"})
                + "\n",
                encoding="utf-8",
            )
            (chat / "gate_chair_turns.jsonl").write_text(
                json.dumps(
                    {
                        "schema_version": "aios.chat.gate_chair_turn.v1",
                        "turn_id": "gatechair_demo",
                        "executed": False,
                        "created_at": "2026-05-17T00:00:01+09:00",
                        "chair_meta": {"status": "gate_chair_timeout", "meta": {"mode": "claude"}},
                    }
                )
                + "\n",
                encoding="utf-8",
            )
            (chat / "provider_turns.jsonl").write_text(
                json.dumps(
                    {
                        "schema_version": "aios.chat.provider_turn.v1",
                        "turn_id": "provider_demo",
                        "executed": False,
                        "provider_meta": {"status": "provider_backpressure"},
                    }
                )
                + "\n",
                encoding="utf-8",
            )
            cap = root / "CapabilityOS" / "capabilityos"
            cap.mkdir(parents=True)
            (cap / "__init__.py").write_text("", encoding="utf-8")
            (cap / "cli.py").write_text(
                "\n".join(
                    [
                        "import json",
                        "print(json.dumps({",
                        "  'schema_version': 'capabilityos.provider_route.v1',",
                        "  'recommendation_only': True,",
                        "  'assigned_agent': 'claude',",
                        "  'fallback_agents': ['local', 'gemini'],",
                        "  'routes': [{'provider': 'local', 'reason': 'offline fallback'}]",
                        "}))",
                    ]
                ),
                encoding="utf-8",
            )

            status, payload = module.build_chat_history_action_response(
                root,
                {"conversation_id": "demo", "action": "capability_fallback_preview"},
            )

            self.assertEqual(status, 200)
            self.assertTrue(payload["ok"])
            self.assertFalse(payload["execution_started"])
            self.assertEqual(payload["schema_version"], "aios.capability_fallback_preview.v1")
            self.assertEqual(payload["route_plan"]["fallback_agents"], ["local", "gemini"])
            self.assertFalse((root / ".aios" / "inbox" / "CapabilityOS").exists())

    def test_chat_history_action_rereviews_memory_gap(self) -> None:
        module = load_local_app_module()
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            chat = root / ".aios" / "chat" / "demo"
            chat.mkdir(parents=True)
            (chat / "messages.jsonl").write_text(
                json.dumps({"role": "user", "content": "기억 보강", "created_at": "2026-05-17T00:00:00+09:00"})
                + "\n"
                + json.dumps({"role": "assistant", "content": "ok", "created_at": "2026-05-17T00:00:01+09:00"})
                + "\n",
                encoding="utf-8",
            )
            (chat / "memory_drafts.json").write_text(
                json.dumps(
                    {
                        "schema_version": "aios.chat.memory_drafts.v1",
                        "memory_drafts": [
                            {
                                "type": "negative_evidence_signal",
                                "origin": "aios_chat_negative_evidence",
                                "status": "draft",
                                "content": "Provider failed repeatedly.",
                                "raw_refs": ["gate_chair_turns.jsonl"],
                                "provenance": {"source": "aios_chat"},
                            }
                        ],
                    }
                ),
                encoding="utf-8",
            )
            review = root / ".aios" / "outbox" / "memoryOS" / "mdrev-demo.memoryOS.result.json"
            review.parent.mkdir(parents=True)
            review.write_text(
                json.dumps(
                    {
                        "schema_version": "aios.dispatch.result.v1",
                        "review_request": {
                            "source_artifact": ".aios/chat/demo/memory_drafts.json",
                            "draft_id": "demo:0",
                            "review_decision": "needs_more_evidence",
                        },
                    }
                ),
                encoding="utf-8",
            )

            status, payload = module.build_chat_history_action_response(
                root,
                {"conversation_id": "demo", "action": "memory_rereview", "confirm": True},
            )

            self.assertEqual(status, 200)
            self.assertTrue(payload["ok"])
            receipt = payload["receipt"]
            self.assertEqual(receipt["status"], "sent_to_memoryOS_inbox")
            self.assertEqual(receipt["source_artifact"], ".aios/chat/demo/memory_drafts.json")
            self.assertEqual(receipt["draft_id"], "demo:0")
            packet = root / receipt["artifact_paths"]["packet"]
            self.assertTrue(packet.exists())
            self.assertEqual(json.loads(packet.read_text(encoding="utf-8"))["target_repo"], "memoryOS")

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

    def test_gate_chair_eval_runs_candidate_matrix_script(self) -> None:
        module = load_local_app_module()
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "scripts").mkdir()
            (root / "scripts" / "aios_gate_chair_eval.py").write_text(
                "import json, sys\n"
                "assert '--candidate-matrix' in sys.argv\n"
                "assert sys.argv.count('--candidate') == 2\n"
                "assert '--request-memory-review' in sys.argv\n"
                "print(json.dumps({"
                "'schema_version':'aios.gate_chair_candidate_matrix.v1',"
                "'matrix_id':'matrix_demo',"
                "'recommendation':'hold_all_candidates',"
                "'promotion_ready':False,"
                "'baseline':{'mode':'internal','average_score':1.0,'report_path':'.aios/evals/gate_chair/base/report.json'},"
                "'candidates':[{'mode':'claude','average_score':0.75,'failure_count':1,'external_runtime_observed':True}],"
                "'best_candidate':{'mode':'claude','average_score':0.75},"
                "'prompt_count':1,"
                "'request_memory_review':True,"
                "'report_path':'.aios/evals/gate_chair_matrix/matrix_demo/report.json'"
                "}))\n",
                encoding="utf-8",
            )

            status, payload = module.build_gate_chair_eval_response(
                root,
                {
                    "candidate_matrix": True,
                    "candidates": ["claude", "codex"],
                    "request_memory_review": True,
                    "prompts": ["AIOS gate?"],
                },
            )

        self.assertEqual(status, 200)
        self.assertTrue(payload["ok"])
        self.assertEqual(payload["schema_version"], "aios.gate_chair_eval_api.v1")
        self.assertEqual(payload["report_kind"], "candidate_matrix")
        self.assertEqual(payload["matrix_id"], "matrix_demo")
        self.assertEqual(payload["recommendation"], "hold_all_candidates")
        self.assertFalse(payload["promotion_ready"])
        self.assertEqual(payload["baseline"]["average_score"], 1.0)
        self.assertEqual(payload["candidates"][0]["mode"], "claude")
        self.assertTrue(payload["request_memory_review"])
        self.assertEqual(payload["report_path"], ".aios/evals/gate_chair_matrix/matrix_demo/report.json")

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
