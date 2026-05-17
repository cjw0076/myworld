import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "aios_round_controller.py"


def write_executable(path: Path, text: str) -> None:
    path.write_text(text, encoding="utf-8")
    path.chmod(path.stat().st_mode | 0o111)


class AiosRoundControllerTest(unittest.TestCase):
    def write_fixture(
        self,
        root: Path,
        *,
        loop_actions: list[dict] | None = None,
        loop_observations: list[dict] | None = None,
        pending: int = 0,
    ) -> None:
        scripts = root / "scripts"
        scripts.mkdir(parents=True)
        goal = root / "docs" / "goals" / "AIOS-GOAL-0001-make-something-great.md"
        goal.parent.mkdir(parents=True)
        goal.write_text(
            "---\ngoal_id: AIOS-GOAL-0001\nstatus: active\n---\n# Goal\n",
            encoding="utf-8",
        )
        write_executable(
            scripts / "aios_monitor.py",
            """#!/usr/bin/env python3
import json
print(json.dumps({"schema_version":"aios.monitor.assessment.v1","health":"clear","findings":[]}))
""",
        )
        coevolution = scripts / "aios_coevolution"
        coevolution.mkdir()
        write_executable(
            coevolution / "persistent.py",
            """#!/usr/bin/env python3
import json
from pathlib import Path
Path(".aios/state/pulses_armed").parent.mkdir(parents=True, exist_ok=True)
Path(".aios/state/pulses_armed").write_text("armed", encoding="utf-8")
print(json.dumps({"schema_version":"aios.coevolution.persistent.v1","status":"passed","started":3,"failed":0}))
""",
        )
        write_executable(
            scripts / "aios_goal_evolution.py",
            """#!/usr/bin/env python3
import json
print(json.dumps({
  "schema_version":"aios.goal_evolution.v1",
  "recommendation":{"path":"goal:persistent_control_loop","candidate_task":"keep running"},
  "stop_conditions":[]
}))
""",
        )
        write_executable(
            scripts / "aios_loop.py",
            f"""#!/usr/bin/env python3
import json
print(json.dumps({{"schema_version":"aios.loop.v1","actions":{json.dumps(loop_actions or [])},"observations":{json.dumps(loop_observations or [])}}}))
""",
        )
        write_executable(
            scripts / "aios_child_watcher.sh",
            f"""#!/usr/bin/env bash
set -euo pipefail
case "${{1:-}}" in
  status)
    echo "hivemind running=false inbox=0 outbox=0 pending={pending}"
    echo "memoryOS running=false inbox=0 outbox=0 pending=0"
    echo "CapabilityOS running=false inbox=0 outbox=0 pending=0"
    ;;
  once)
    echo "ran ${{3:-unknown}}"
    ;;
esac
""",
        )

    def run_controller(self, root: Path, *args: str) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            [sys.executable, SCRIPT.as_posix(), *args],
            cwd=root,
            text=True,
            capture_output=True,
            check=False,
        )

    def test_once_writes_round_receipt_and_latest_state(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            self.write_fixture(root)

            result = self.run_controller(root, "once", "--root", root.as_posix(), "--json")

            self.assertEqual(result.returncode, 0, result.stderr)
            data = json.loads(result.stdout)
            self.assertEqual(data["schema_version"], "aios.round_controller.v1")
            self.assertEqual(data["status"], "passed")
            self.assertEqual(data["steps"]["coevolution_pulses"]["status"], "passed")
            self.assertEqual(data["recommended_next"]["action"], "open_next_contract")
            self.assertTrue((root / ".aios" / "state" / "pulses_armed").exists())
            latest = root / ".aios" / "state" / "round_controller.latest.json"
            self.assertTrue(latest.exists())
            self.assertIn("goal:persistent_control_loop", latest.read_text(encoding="utf-8"))
            event_log = root / ".aios" / "state" / "round_controller.jsonl"
            self.assertEqual(1, len(event_log.read_text(encoding="utf-8").splitlines()))

    def test_pending_child_packets_recommend_child_watcher_without_default_execution(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            self.write_fixture(root, pending=2)

            result = self.run_controller(root, "once", "--root", root.as_posix(), "--json")

            self.assertEqual(result.returncode, 0, result.stderr)
            data = json.loads(result.stdout)
            self.assertEqual(data["recommended_next"]["action"], "run_child_watchers")
            self.assertEqual(data["child_executions"], [])

    def test_pending_dispatch_results_recommend_dispatch_watcher_before_child_execution(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            self.write_fixture(
                root,
                loop_observations=[
                    {
                        "contract_id": "ASC-0099",
                        "dispatch_id": "asc-0099",
                        "pending_results": ["myworld"],
                    }
                ],
                pending=2,
            )

            result = self.run_controller(root, "once", "--root", root.as_posix(), "--json")

            self.assertEqual(result.returncode, 0, result.stderr)
            data = json.loads(result.stdout)
            self.assertEqual(data["recommended_next"]["action"], "run_dispatch_watcher")
            self.assertEqual(["myworld"], data["recommended_next"]["pending"][0]["pending_results"])

    def test_execute_children_runs_one_explicit_child_pass(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            self.write_fixture(root, pending=1)

            result = self.run_controller(root, "once", "--root", root.as_posix(), "--execute-children", "--json")

            self.assertEqual(result.returncode, 0, result.stderr)
            data = json.loads(result.stdout)
            self.assertEqual(["child_once_hivemind"], [item["name"] for item in data["child_executions"]])

    def test_status_reports_latest_round(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            self.write_fixture(root)
            once = self.run_controller(root, "once", "--root", root.as_posix(), "--json")
            self.assertEqual(once.returncode, 0, once.stderr)

            status = self.run_controller(root, "status", "--root", root.as_posix())

            self.assertEqual(status.returncode, 0, status.stderr)
            self.assertIn("running=false", status.stdout)
            self.assertIn("latest_status=passed", status.stdout)
            self.assertIn("latest_next=open_next_contract", status.stdout)


class BuildRecommendedNextHoldTest(unittest.TestCase):
    """ASC-0116 — dispatch holds only on a genuinely BROKEN monitor state,
    not on every non-clear health (busy/stale must not freeze the loop)."""

    @staticmethod
    def _recommend(health: str) -> dict:
        import importlib.util

        sys.path.insert(0, str(SCRIPT.parent))
        spec = importlib.util.spec_from_file_location("aios_round_controller", SCRIPT)
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        steps = {"monitor": {"parsed": {"health": health, "findings": []}}}
        return mod.build_recommended_next(steps, {"repos": {}}, [])

    def test_blocked_holds_dispatch(self) -> None:
        self.assertEqual(self._recommend("blocked")["action"], "hold_for_monitor")

    def test_attention_does_not_hold(self) -> None:
        self.assertNotEqual(self._recommend("attention").get("action"), "hold_for_monitor")

    def test_watch_does_not_hold(self) -> None:
        self.assertNotEqual(self._recommend("watch").get("action"), "hold_for_monitor")


if __name__ == "__main__":
    unittest.main()
