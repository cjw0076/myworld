import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


class AiosCoevolutionTest(unittest.TestCase):
    def run_script(self, script: str, tmp: Path) -> subprocess.CompletedProcess[str]:
        env = os.environ.copy()
        env["AIOS_COEVOLUTION_ROOT"] = tmp.as_posix()
        env["AIOS_COEVOLUTION_TEST_MODE"] = "1"
        env["PYTHONPATH"] = f"{ROOT / 'scripts'}:{env.get('PYTHONPATH', '')}"
        result = subprocess.run(
            ["bash", str(ROOT / "scripts" / "aios_coevolution" / script)],
            cwd=ROOT,
            text=True,
            capture_output=True,
            env=env,
        )
        if result.returncode != 0:
            self.fail(result.stderr or result.stdout)
        return result

    def test_pulses_emit_one_summary_line_in_test_mode(self):
        with tempfile.TemporaryDirectory() as td:
            tmp = Path(td)
            memory = self.run_script("memory_pulse.sh", tmp)
            capability = self.run_script("capability_pulse.sh", tmp)
            hive = self.run_script("hive_pulse.sh", tmp)

            self.assertIn("memory_pulse stage=done", memory.stdout)
            self.assertIn("capability_pulse stage=done", capability.stdout)
            self.assertIn("hive_pulse stage=done", hive.stdout)

    def test_status_parses_latest_pulse_events(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            events = root / ".aios" / "primitives" / "events.jsonl"
            events.parent.mkdir(parents=True)
            events.write_text(
                "\n".join(
                    [
                        json.dumps(
                            {
                                "schema_version": "aios.primitive_event.v1",
                                "kind": "monitor.event",
                                "name": "aios-memory-pulse",
                                "ts_iso": "2026-05-12T00:00:00+09:00",
                                "ts_monotonic_ns": 1,
                                "payload": {"line": "memory_pulse stage=done scout_signals=1 imported=1 skipped=0"},
                            }
                        ),
                        json.dumps(
                            {
                                "schema_version": "aios.primitive_event.v1",
                                "kind": "monitor.event",
                                "name": "aios-hive-pulse",
                                "ts_iso": "2026-05-12T00:00:01+09:00",
                                "ts_monotonic_ns": 2,
                                "payload": {"line": "hive_pulse stage=done dispatch_in_flight=0"},
                            }
                        ),
                    ]
                )
                + "\n",
                encoding="utf-8",
            )
            result = subprocess.run(
                [
                    sys.executable,
                    str(ROOT / "scripts" / "aios_coevolution" / "status.py"),
                    "--root",
                    root.as_posix(),
                    "--json",
                ],
                text=True,
                capture_output=True,
                check=True,
            )
            payload = json.loads(result.stdout)
            self.assertEqual(payload["schema_version"], "aios.coevolution.status.v1")
            self.assertEqual(payload["pulses"]["aios-memory-pulse"]["events"], 1)
            self.assertIn("memory_pulse", payload["pulses"]["aios-memory-pulse"]["last_line"])
            self.assertIsNone(payload["pulses"]["aios-capability-pulse"]["last_line"])

    def test_arm_and_stop_are_wired_to_aios_primitives(self):
        arm = (ROOT / "scripts" / "aios_coevolution" / "arm.sh").read_text(encoding="utf-8")
        stop = (ROOT / "scripts" / "aios_coevolution" / "stop.sh").read_text(encoding="utf-8")
        self.assertIn("aios_primitives.py monitor start --name aios-memory-pulse", arm)
        self.assertIn("aios_primitives.py monitor stop --name aios-memory-pulse", stop)


if __name__ == "__main__":
    unittest.main()
