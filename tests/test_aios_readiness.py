import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "aios_readiness.py"


class AiosReadinessTest(unittest.TestCase):
    def run_readiness(self, root: Path) -> dict:
        result = subprocess.run(
            [sys.executable, SCRIPT.as_posix(), "--json"],
            cwd=root,
            text=True,
            capture_output=True,
            check=False,
        )
        return json.loads(result.stdout)

    def test_missing_definition_is_below_l0(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            payload = self.run_readiness(root)

            self.assertEqual(payload["level"], -1)
            self.assertFalse(payload["ready"])
            self.assertIn("AIOS strict definition is missing", payload["gaps"])

    def test_closed_loop_fixture_reaches_l6(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "docs" / "contracts").mkdir(parents=True)
            (root / "docs" / "AIOS_DEFINITION.md").write_text("# AIOS Definition\n", encoding="utf-8")
            (root / "scripts").mkdir()
            (root / "scripts" / "aios_child_watcher.sh").write_text("#!/usr/bin/env bash\n", encoding="utf-8")
            (root / "scripts" / "aios_pingpong.sh").write_text("#!/usr/bin/env bash\n", encoding="utf-8")
            for idx in range(1, 7):
                contract = root / "docs" / "contracts" / f"ASC-{idx:04d}-fixture.md"
                contract.write_text(
                    f"---\ncontract_id: ASC-{idx:04d}\nstatus: closed\n---\n",
                    encoding="utf-8",
                )
            state = root / ".aios" / "state"
            state.mkdir(parents=True)
            events = [
                {"event": "sent", "dispatch_id": "a", "repo": "hivemind"},
                {"event": "sent", "dispatch_id": "b", "repo": "memoryOS"},
                {"event": "sent", "dispatch_id": "c", "repo": "CapabilityOS"},
                {"event": "collected", "dispatch_id": "a", "repo": "hivemind", "result": ".aios/outbox/hivemind/a.json"},
            ]
            (state / "dispatches.jsonl").write_text(
                "\n".join(json.dumps(row) for row in events) + "\n",
                encoding="utf-8",
            )
            outbox = root / ".aios" / "outbox" / "hivemind"
            outbox.mkdir(parents=True)
            (outbox / "a.json").write_text(
                json.dumps(
                    {
                        "schema_version": "aios.dispatch.result.v1",
                        "target_repo": "hivemind",
                        "dispatch_id": "a",
                        "contract_id": "ASC-0001",
                        "status": "passed",
                        "evidence": [],
                        "stop_conditions_triggered": [],
                    }
                ),
                encoding="utf-8",
            )

            payload = self.run_readiness(root)

            self.assertTrue(payload["ready"])
            self.assertEqual(payload["level"], 6)
            self.assertFalse(payload["gaps"])


if __name__ == "__main__":
    unittest.main()
