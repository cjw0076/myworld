import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "aios_chat.py"
LAUNCHER = ROOT / "scripts" / "aios_launcher.py"
DASHBOARD_WS = ROOT / "scripts" / "aios_dashboard_ws.py"


class AiosChatCliTest(unittest.TestCase):
    def test_single_message_and_list(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            turn = subprocess.run(
                [
                    sys.executable,
                    SCRIPT.as_posix(),
                    "--root",
                    root.as_posix(),
                    "--conversation",
                    "cli-test",
                    "--message",
                    "test",
                    "--json",
                ],
                cwd=ROOT,
                text=True,
                capture_output=True,
                check=True,
            )
            payload = json.loads(turn.stdout)
            self.assertEqual(payload["status"], "routed")
            self.assertEqual(payload["conversation_id"], "cli-test")

            listed = subprocess.run(
                [sys.executable, SCRIPT.as_posix(), "--root", root.as_posix(), "--list", "--json"],
                cwd=ROOT,
                text=True,
                capture_output=True,
                check=True,
            )
            conversations = json.loads(listed.stdout)["conversations"]
            self.assertEqual(conversations[0]["conversation_id"], "cli-test")
            self.assertEqual(conversations[0]["messages"], 2)

    def test_launcher_constructs_chat_delegation(self) -> None:
        import importlib.util

        spec = importlib.util.spec_from_file_location("aios_launcher", LAUNCHER)
        module = importlib.util.module_from_spec(spec)
        assert spec and spec.loader
        spec.loader.exec_module(module)

        command = module.chat_command(ROOT, ["--message", "hello", "--json"])

        self.assertEqual(command[0], sys.executable)
        self.assertEqual(command[1], (ROOT / "scripts" / "aios_chat.py").as_posix())
        self.assertEqual(command[2:4], ["--root", ROOT.as_posix()])
        self.assertEqual(command[-1], "--json")

    def test_websocket_server_has_chat_route_helpers(self) -> None:
        import importlib.util

        spec = importlib.util.spec_from_file_location("aios_dashboard_ws", DASHBOARD_WS)
        module = importlib.util.module_from_spec(spec)
        assert spec and spec.loader
        spec.loader.exec_module(module)

        request = "GET /chat HTTP/1.1\r\nHost: localhost\r\n\r\n"
        self.assertEqual(module.DashboardWebSocketHandler.parse_path(request), "/chat")
        frame = module.encode_frame({"type": "chat_ready"})
        self.assertEqual(frame[0], 0x81)

    def test_web_files_exist_and_reference_chat_route(self) -> None:
        html = (ROOT / "apps" / "control" / "chat.html").read_text(encoding="utf-8")
        js = (ROOT / "apps" / "control" / "chat.js").read_text(encoding="utf-8")
        index = (ROOT / "apps" / "control" / "index.html").read_text(encoding="utf-8")
        app_js = (ROOT / "apps" / "control" / "app.js").read_text(encoding="utf-8")

        self.assertIn('id="chat-form"', html)
        self.assertIn("불편함 찾기", html)
        self.assertIn('id="offline-user-panel"', html)
        self.assertIn("aios-control-data.js", html)
        self.assertIn("/chat", js)
        self.assertIn("/api/chat", js)
        self.assertIn("sendViaHttp", js)
        self.assertIn("HTTP fallback", js)
        self.assertIn("chosen_substrate", js)
        self.assertIn("chat-evidence", js)
        self.assertIn("Trace", js)
        self.assertIn("/api/artifact", js)
        self.assertIn("chat-evidence-open", js)
        self.assertIn("Copy path", js)
        self.assertIn("Copy preview", js)
        self.assertIn("artifactFromHash", js)
        self.assertIn("artifactAuthority", js)
        self.assertIn("authority-badge", js)
        self.assertIn("restoreArtifactHash", js)
        self.assertIn("artifact-hash-panel", js)
        self.assertIn("renderOfflineUserPanel", js)
        self.assertIn("Offline user prompt prepared", js)
        self.assertIn("selected_memories", js)
        self.assertIn("negative_evidence", js)
        self.assertIn("negative:", js)
        self.assertIn("genesis_friction", js)
        self.assertIn("genesis:", js)
        self.assertIn("provider_turn", js)
        self.assertIn("gate_chair_turn", js)
        self.assertIn("friction_contract_seed", js)
        self.assertIn("/api/promote_friction_seed", js)
        self.assertIn("Promote Seed", js)
        self.assertIn('id="inline-chat-form"', index)
        self.assertIn('id="inline-chat-thread"', index)
        self.assertIn("Find Friction", index)
        self.assertIn("/chat", app_js)
        self.assertIn("/api/chat", app_js)
        self.assertIn("inline-chat-evidence", app_js)
        self.assertIn("AIOS Gate", app_js)
        self.assertIn("Trace", app_js)
        self.assertIn("안녕. 바로 물어봐.", app_js)
        self.assertIn("/api/artifact", app_js)
        self.assertIn("inline-chat-open", app_js)
        self.assertIn("artifact-copy", app_js)
        self.assertIn("Copy preview", app_js)
        self.assertIn("selected_memories", app_js)
        self.assertIn("negative_evidence", app_js)
        self.assertIn("negative:", app_js)
        self.assertIn("genesis_friction", app_js)
        self.assertIn("genesis:", app_js)
        self.assertIn("provider_turn", app_js)
        self.assertIn("gate_chair_turn", app_js)
        self.assertIn("friction_contract_seed", app_js)
        self.assertIn("/api/promote_friction_seed", app_js)
        self.assertIn("Promote Seed", app_js)
        self.assertIn("renderOfflineUserCard", app_js)
        self.assertIn("Offline User Agent", app_js)
        self.assertIn("installInlineChat", app_js)


if __name__ == "__main__":
    unittest.main()
