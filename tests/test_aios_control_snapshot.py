import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "aios_control_snapshot.py"


class AiosControlSnapshotTest(unittest.TestCase):
    def write_fixture(self, root: Path) -> None:
        (root / "docs" / "contracts").mkdir(parents=True)
        (root / "docs" / "goals").mkdir(parents=True)
        (root / "docs" / "contracts" / "ASC-0001-demo.md").write_text(
            """---
contract_id: ASC-0001
slug: demo
status: closed
goal: Demo contract.
created: now
closed: now
---

# ASC-0001 Demo

## AIOS Inputs Used

- MemoryOS: `trace_id=rtrace_demo123`
- CapabilityOS: `cap_demo_route`
- Hive: `run_20260512_000000_demo`

## Stop Conditions

- verification_gate_failed
- scope_violation
""",
            encoding="utf-8",
        )
        (root / "docs" / "goals" / "AIOS-GOAL-0001-demo.md").write_text(
            """---
goal_id: AIOS-GOAL-0001
slug: demo
status: active
---

# Demo Goal

## North Star

Build the loop.

## Preferred Next Improvements

- visual_control_application: show the loop.

## Completed Improvements

- self_resonant_repo_loop: route repo goals.
""",
            encoding="utf-8",
        )
        (root / "docs" / "goals" / "AIOS-GOAL-0001-evolution.md").write_text(
            """# AIOS Goal Evolution Plan

- monitor_health: `clear`
- readiness: `L6 repeatable`

## Recommendation

- path: `goal:visual_control_application`
""",
            encoding="utf-8",
        )
        state = root / ".aios" / "state"
        state.mkdir(parents=True)
        (state / "dispatches.jsonl").write_text(
            "\n".join(
                [
                    json.dumps({"dispatch_id": "asc-0001", "contract_id": "ASC-0001", "event": "created", "status": "created", "timestamp": "1"}),
                    json.dumps({"dispatch_id": "asc-0001", "event": "sent", "repo": "myworld", "status": "sent", "timestamp": "2"}),
                    json.dumps({"dispatch_id": "asc-0001", "event": "collected", "repo": "myworld", "status": "collected", "timestamp": "3"}),
                    json.dumps({"dispatch_id": "asc-0001", "event": "released", "status": "released", "reason": "verified", "timestamp": "4"}),
                ]
            )
            + "\n",
            encoding="utf-8",
        )
        (state / "monitor_assessment.latest.json").write_text(
            json.dumps({"health": "clear", "findings": [], "next_actions": [{"action": "continue_observing"}]}),
            encoding="utf-8",
        )

    def run_cli(self, root: Path, *args: str) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            [sys.executable, SCRIPT.as_posix(), "--root", root.as_posix(), *args],
            text=True,
            capture_output=True,
            check=False,
        )

    def test_snapshot_contains_control_plane_sections(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            self.write_fixture(root)

            result = self.run_cli(root, "--json")

            self.assertEqual(result.returncode, 0, result.stderr)
            data = json.loads(result.stdout)
            self.assertEqual(data["schema_version"], "aios.control_snapshot.v1")
            self.assertEqual(data["goals"]["active"]["id"], "AIOS-GOAL-0001")
            self.assertEqual(data["goals"]["evolution"]["recommendation"], "goal:visual_control_application")
            self.assertEqual(data["contracts"]["counts"]["closed"], 1)
            self.assertEqual(data["dispatches"]["counts"]["released"], 1)
            self.assertEqual(data["monitor"]["health"], "clear")
            self.assertEqual(data["aios_inputs"]["memory_traces"], ["rtrace_demo123"])
            self.assertEqual(data["aios_inputs"]["capability_routes"], ["cap_demo_route"])
            self.assertEqual(data["aios_inputs"]["hive_runs"], ["run_20260512_000000_demo"])
            self.assertIn("stop_lanes", data)

    def test_writes_json_and_browser_data_file(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            self.write_fixture(root)

            result = self.run_cli(
                root,
                "--write-json",
                "apps/control/aios-control-snapshot.json",
                "--write-js",
                "apps/control/aios-control-data.js",
            )

            self.assertEqual(result.returncode, 0, result.stderr)
            json_path = root / "apps" / "control" / "aios-control-snapshot.json"
            js_path = root / "apps" / "control" / "aios-control-data.js"
            self.assertTrue(json_path.exists())
            self.assertTrue(js_path.exists())
            self.assertIn("window.AIOS_CONTROL_SNAPSHOT", js_path.read_text(encoding="utf-8"))
            self.assertEqual(json.loads(json_path.read_text(encoding="utf-8"))["schema_version"], "aios.control_snapshot.v1")

    def test_check_app_js_reports_missing_file(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)

            result = self.run_cli(root, "--check-app-js", "apps/control/app.js", "--json")

            self.assertNotEqual(result.returncode, 0)
            data = json.loads(result.stdout)
            self.assertFalse(data["ok"])
            self.assertIn("app js not found", data["errors"])


if __name__ == "__main__":
    unittest.main()
