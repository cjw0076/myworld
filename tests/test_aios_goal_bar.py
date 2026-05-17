import importlib.util
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "aios_goal_bar.py"


def load_goal_bar_module():
    spec = importlib.util.spec_from_file_location("aios_goal_bar_under_test", SCRIPT)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


class GoalBarClassifierTest(unittest.TestCase):
    def setUp(self) -> None:
        self.module = load_goal_bar_module()

    def classify(self, text: str) -> dict:
        return self.module.classify(text, ROOT)

    def test_agent_question_routes_to_hive_agents_status(self) -> None:
        payload = self.classify("어떤 Agent가 있지?")
        self.assertEqual(payload["intent"], "hive_agents_status")
        self.assertIn("hivemind.hive agents status", payload["classified_command"])
        self.assertTrue(payload["will_execute"])

    def test_contract_question_routes_to_dispatch_status(self) -> None:
        payload = self.classify("어떤 contract가 열려있나")
        self.assertEqual(payload["intent"], "dispatch_status")
        self.assertIn("aios_dispatch.py status", payload["classified_command"])

    def test_monitor_question_routes_to_primitive_monitor_list(self) -> None:
        payload = self.classify("list monitor primitives")
        self.assertEqual(payload["intent"], "primitive_monitor_list")
        self.assertIn("monitor list", payload["classified_command"])

    def test_memory_question_routes_to_memoryos(self) -> None:
        payload = self.classify("기억 draft 보여줘")
        self.assertEqual(payload["intent"], "memory_drafts_list")
        self.assertEqual(payload["cwd"], "memoryOS")

    def test_capability_question_routes_to_capabilityos(self) -> None:
        payload = self.classify("도구 추천해줘")
        self.assertEqual(payload["intent"], "capability_recommend")
        self.assertEqual(payload["cwd"], "CapabilityOS")

    def test_invoke_question_routes_to_plan_only_invocation(self) -> None:
        payload = self.classify("AIOS로 실행 route 만들어")
        self.assertEqual(payload["intent"], "aios_invoke_plan")
        self.assertIn("--plan-only", payload["classified_command"])

    def test_default_routes_to_hive_ask(self) -> None:
        payload = self.classify("summarize the current system")
        self.assertEqual(payload["intent"], "hive_ask")
        self.assertIn("hivemind.hive ask", payload["classified_command"])

    def test_dangerous_input_rejected(self) -> None:
        payload = self.classify("please sudo rm -rf /")
        self.assertEqual(payload["intent"], "rejected")
        self.assertFalse(payload["will_execute"])
        self.assertTrue(payload["rejected"])

    @patch("subprocess.run")
    def test_execute_uses_argv_without_shell(self, run_mock) -> None:
        completed = subprocess.CompletedProcess(args=["x"], returncode=0, stdout='{"ok": true}\n', stderr="")
        run_mock.return_value = completed
        payload = self.classify("어떤 Agent가 있지?")

        executed = self.module.execute(ROOT, payload)

        self.assertTrue(executed["executed"])
        self.assertTrue(executed["execution"]["ok"])
        _, kwargs = run_mock.call_args
        self.assertFalse(kwargs.get("shell", False))

    def test_cli_json_shape(self) -> None:
        result = subprocess.run(
            [sys.executable, SCRIPT.as_posix(), "--root", ROOT.as_posix(), "어떤 Agent가 있지?", "--json"],
            text=True,
            capture_output=True,
            check=False,
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        payload = json.loads(result.stdout)
        self.assertEqual(payload["schema_version"], "aios.goal_bar.v1")
        self.assertEqual(payload["intent"], "hive_agents_status")


class GoalBarLocalAppApiTest(unittest.TestCase):
    def test_local_app_goal_bar_classify_and_confirm(self) -> None:
        local_app = _load_local_app()
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "scripts").mkdir()
            (root / "scripts" / "aios_goal_bar.py").write_text(
                "import json, sys\n"
                "execute = '--execute' in sys.argv\n"
                "print(json.dumps({'schema_version':'aios.goal_bar.v1','intent':'hive_agents_status','classified_command':'hive agents status','will_execute':True,'executed':execute}))\n",
                encoding="utf-8",
            )

            status, classified = local_app.build_goal_bar_response(root, {"goal": "어떤 Agent가 있지?"})
            blocked_status, blocked = local_app.build_goal_bar_response(root, {"goal": "어떤 Agent가 있지?", "execute": True})
            run_status, ran = local_app.build_goal_bar_response(root, {"goal": "어떤 Agent가 있지?", "execute": True, "confirm": True})

        self.assertEqual(status, 200)
        self.assertTrue(classified["ok"])
        self.assertEqual(blocked_status, 409)
        self.assertEqual(blocked["reason"], "confirmation_required")
        self.assertEqual(run_status, 200)
        self.assertTrue(ran["result"]["executed"])


def _load_local_app():
    script = ROOT / "scripts" / "aios_local_app.py"
    spec = importlib.util.spec_from_file_location("aios_local_app_for_goal_bar_test", script)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


if __name__ == "__main__":
    unittest.main()
