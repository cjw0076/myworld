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

    def test_persistent_helper_arms_missing_pulses_idempotently(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            scripts = root / "scripts"
            scripts.mkdir()
            state = root / "primitive_state.json"
            (scripts / "aios_primitives.py").write_text(
                f"""#!/usr/bin/env python3
import json
import sys
from pathlib import Path
state = Path({state.as_posix()!r})
args = sys.argv[1:]
if "list" in args:
    if state.exists():
        print(state.read_text())
    else:
        print("[]")
elif "start" in args:
    name = args[args.index("--name") + 1]
    rows = json.loads(state.read_text()) if state.exists() else []
    if not any(row.get("name") == name for row in rows):
        rows.append({{"name": name, "alive": True, "pid": len(rows) + 1}})
    state.write_text(json.dumps(rows))
    print(json.dumps({{"name": name, "alive": True}}))
else:
    raise SystemExit(2)
""",
                encoding="utf-8",
            )

            first = subprocess.run(
                [
                    sys.executable,
                    str(ROOT / "scripts" / "aios_coevolution" / "persistent.py"),
                    "--root",
                    root.as_posix(),
                    "--json",
                ],
                text=True,
                capture_output=True,
                check=True,
            )
            second = subprocess.run(
                [
                    sys.executable,
                    str(ROOT / "scripts" / "aios_coevolution" / "persistent.py"),
                    "--root",
                    root.as_posix(),
                    "--json",
                ],
                text=True,
                capture_output=True,
                check=True,
            )

            first_payload = json.loads(first.stdout)
            second_payload = json.loads(second.stdout)
            self.assertEqual(first_payload["started"], 3)
            self.assertEqual(second_payload["started"], 0)
            self.assertEqual(
                {"already_alive"},
                {row["action"] for row in second_payload["pulses"].values()},
            )

            alive = subprocess.run(
                [
                    sys.executable,
                    str(ROOT / "scripts" / "aios_coevolution" / "persistent.py"),
                    "--root",
                    root.as_posix(),
                    "--assert-alive",
                    "--json",
                ],
                text=True,
                capture_output=True,
                check=True,
            )
            self.assertEqual(json.loads(alive.stdout)["status"], "passed")


if __name__ == "__main__":
    unittest.main()
