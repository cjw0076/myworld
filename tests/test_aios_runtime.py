import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "aios_runtime.py"


class AiosRuntimeTest(unittest.TestCase):
    def run_runtime(self, *args: str, cwd: Path = ROOT, check: bool = True) -> subprocess.CompletedProcess[str]:
        result = subprocess.run(
            [sys.executable, SCRIPT.as_posix(), *args],
            cwd=cwd,
            text=True,
            capture_output=True,
        )
        if check and result.returncode != 0:
            self.fail(result.stderr or result.stdout)
        return result

    def test_status_returns_aggregate_json(self):
        result = self.run_runtime("status", "--json")
        payload = json.loads(result.stdout)

        self.assertEqual(payload["schema_version"], "aios.runtime.status.v1")
        self.assertIn(payload["status"], {"ready", "blocked"})
        self.assertIn("monitor", payload)
        self.assertIn("readiness", payload)
        self.assertIn("dispatch", payload)
        self.assertIn("primitive_events", payload)

    def test_step_emits_runtime_primitive_event(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            (root / "scripts").mkdir()
            source = ROOT / "scripts" / "aios_runtime.py"
            target = root / "scripts" / "aios_runtime.py"
            target.write_text(source.read_text(encoding="utf-8"), encoding="utf-8")
            for name, body in {
                "aios_round_controller.py": '{"status":"passed","recommended_next":{"action":"continue_observing"}}',
            }.items():
                (root / "scripts" / name).write_text(
                    "#!/usr/bin/env python3\nimport json\nprint(" + repr(body) + ")\n",
                    encoding="utf-8",
                )
            result = self.run_runtime("--root", root.as_posix(), "step", "--json", cwd=ROOT)
            payload = json.loads(result.stdout)
            self.assertEqual(payload["schema_version"], "aios.runtime.step.v1")
            self.assertEqual(payload["status"], "passed")
            events_path = root / ".aios" / "primitives" / "events.jsonl"
            self.assertTrue(events_path.exists())
            self.assertIn("aios.runtime.step", events_path.read_text(encoding="utf-8"))

    def test_run_is_bounded_by_max_rounds(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            (root / "scripts").mkdir()
            target = root / "scripts" / "aios_runtime.py"
            target.write_text(SCRIPT.read_text(encoding="utf-8"), encoding="utf-8")
            (root / "scripts" / "aios_round_controller.py").write_text(
                "#!/usr/bin/env python3\nprint('{\"status\":\"passed\",\"recommended_next\":{\"action\":\"continue_observing\"}}')\n",
                encoding="utf-8",
            )
            result = self.run_runtime(
                "--root",
                root.as_posix(),
                "run",
                "--max-rounds",
                "2",
                "--interval-seconds",
                "0",
                "--json",
                cwd=ROOT,
            )
            payload = json.loads(result.stdout)
            self.assertEqual(payload["schema_version"], "aios.runtime.run.v1")
            self.assertEqual(payload["status"], "passed")
            self.assertEqual(len(payload["rounds"]), 2)

    def test_submit_goal_delegates_to_repo_goal_cli(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            (root / "scripts").mkdir()
            (root / "scripts" / "aios_runtime.py").write_text(SCRIPT.read_text(encoding="utf-8"), encoding="utf-8")
            (root / "scripts" / "aios_repo_goal.py").write_text(
                "#!/usr/bin/env python3\nimport json\nprint(json.dumps({'schema_version':'aios.repo_goal.v1','goal_id':'rg-test'}))\n",
                encoding="utf-8",
            )
            result = self.run_runtime(
                "--root",
                root.as_posix(),
                "submit-goal",
                "--repo",
                "hivemind",
                "--kind",
                "goal",
                "--goal",
                "test goal",
                "--json",
                cwd=ROOT,
            )
            payload = json.loads(result.stdout)
            self.assertEqual(payload["schema_version"], "aios.runtime.submit_goal.v1")
            self.assertEqual(payload["status"], "passed")

    def test_step_surfaces_subprocess_failure(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            (root / "scripts").mkdir()
            (root / "scripts" / "aios_runtime.py").write_text(SCRIPT.read_text(encoding="utf-8"), encoding="utf-8")
            (root / "scripts" / "aios_round_controller.py").write_text(
                "#!/usr/bin/env python3\nimport sys\nprint('bad')\nsys.exit(7)\n",
                encoding="utf-8",
            )
            result = self.run_runtime("--root", root.as_posix(), "step", "--json", cwd=ROOT, check=False)
            payload = json.loads(result.stdout)
            self.assertNotEqual(result.returncode, 0)
            self.assertEqual(payload["status"], "failed")
            self.assertEqual(payload["step"]["returncode"], 7)


if __name__ == "__main__":
    unittest.main()
