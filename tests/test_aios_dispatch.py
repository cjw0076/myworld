import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "aios_dispatch.py"


CONTRACT = """---
contract_id: ASC-0999
status: proposed
goal: Test dispatch flow.
accepted:
closed:
---

# ASC-0999 Test

repos:

- `hivemind`
- `memoryOS`

allowed_files:

- `hivemind/hivemind/memory_bridge.py`
- `memoryOS/memoryos/cli.py`

forbidden_files:

- `CapabilityOS/docs`
- `.env`
"""


ACCEPTED_MYWORLD_CONTRACT = """---
contract_id: ASC-0998
status: accepted
goal: Test watcher flow.
accepted: now
closed:
---

# ASC-0998 Test

repos:

- `myworld`

allowed_files:

- `scripts/aios_dispatch.py`

forbidden_files:

- `.env`

## Verification Gate

Commands:

```bash
cd {root}
python -c "print('watch-ok')"
```
"""


ENRICHED_CONTRACT = """---
contract_id: ASC-0997
status: accepted
goal: Test enriched packet.
accepted: now
closed:
---

# ASC-0997 Test

repos:

- `memoryOS`

allowed_files:

- `memoryOS/memoryos/cli.py`

forbidden_files:

- `.env`

## Responsibilities

### MemoryOS

must_produce:

- `context_pack.md` output
- RetrievalTrace with provenance

## Verification Gate

```bash
cd {root}/memoryOS
python -m pytest tests/test_import_run.py -v
```
"""


class AiosDispatchTest(unittest.TestCase):
    def run_cli(self, root: Path, *args: str, check: bool = True) -> subprocess.CompletedProcess[str]:
        result = subprocess.run(
            [sys.executable, SCRIPT.as_posix(), *args],
            cwd=root,
            text=True,
            capture_output=True,
        )
        if check and result.returncode != 0:
            self.fail(result.stderr or result.stdout)
        return result

    def test_create_records_dispatch_without_inbox_packet(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            contract = root / "ASC-0999-test.md"
            contract.write_text(CONTRACT, encoding="utf-8")

            result = self.run_cli(root, "create", contract.as_posix())
            payload = json.loads(result.stdout)

            self.assertTrue(payload["ok"])
            self.assertEqual(payload["dispatch_id"], "asc-0999")
            state = root / ".aios" / "state" / "dispatches.jsonl"
            self.assertTrue(state.exists())
            self.assertFalse(list((root / ".aios" / "inbox" / "hivemind").glob("*.json")))

    def test_send_requires_accepted_contract_by_default(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            contract = root / "ASC-0999-test.md"
            contract.write_text(CONTRACT, encoding="utf-8")
            self.run_cli(root, "create", contract.as_posix())

            result = self.run_cli(root, "send", "--repo", "hivemind", check=False)

            self.assertNotEqual(result.returncode, 0)
            self.assertIn("operator acceptance required", result.stderr)

    def test_send_writes_scoped_packet_when_allowed_for_test(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            contract = root / "ASC-0999-test.md"
            contract.write_text(CONTRACT, encoding="utf-8")
            self.run_cli(root, "create", contract.as_posix())

            self.run_cli(root, "send", "--repo", "memoryOS", "--agent", "codex", "--allow-proposed")

            packet_path = root / ".aios" / "inbox" / "memoryOS" / "asc-0999.memoryOS.json"
            packet = json.loads(packet_path.read_text(encoding="utf-8"))
            self.assertEqual(packet["target_repo"], "memoryOS")
            self.assertEqual(packet["contract_status"], "proposed")
            self.assertIn("memoryOS/memoryos/cli.py", packet["scope"]["allowed_files"])
            self.assertEqual(packet["control_plane"]["root"], "myworld")
            self.assertIn("docs/AIOS_BUILD_METHOD.md", packet["required_reading"])
            self.assertEqual(packet["result_schema_version"], "aios.dispatch.result.v1")
            self.assertIn("must_produce", packet)
            self.assertIn("verification_commands", packet)

    def test_send_enriches_packet_with_repo_slice(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            contract = root / "ASC-0997-test.md"
            contract.write_text(ENRICHED_CONTRACT.format(root=root.as_posix()), encoding="utf-8")
            self.run_cli(root, "create", contract.as_posix())

            self.run_cli(root, "send", "--repo", "memoryOS", "--agent", "codex")

            packet_path = root / ".aios" / "inbox" / "memoryOS" / "asc-0997.memoryOS.json"
            packet = json.loads(packet_path.read_text(encoding="utf-8"))
            self.assertEqual(packet["schema_version"], "aios.dispatch.v1")
            self.assertEqual(packet["result_schema_version"], "aios.dispatch.result.v1")
            self.assertIn("context_pack.md", " ".join(packet["must_produce"]))
            self.assertEqual(packet["verification_commands"][0]["command"], "python -m pytest tests/test_import_run.py -v")
            self.assertTrue(packet["verification_commands"][0]["cwd"].endswith("/memoryOS"))
            self.assertEqual(packet["result_contract"]["schema_version"], "aios.dispatch.result.v1")

    def test_release_transition_is_first_class_state(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            contract = root / "ASC-0999-test.md"
            contract.write_text(CONTRACT, encoding="utf-8")
            self.run_cli(root, "create", contract.as_posix())

            self.run_cli(root, "release", "--dispatch-id", "asc-0999", "--reason", "verified")

            status = self.run_cli(root, "status", "--json")
            data = json.loads(status.stdout)
            self.assertEqual(data["dispatches"][0]["status"], "released")
            self.assertEqual(data["dispatches"][0]["reason"], "verified")

    def test_watch_once_runs_verification_and_writes_result_packet(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            contract = root / "ASC-0998-test.md"
            contract.write_text(ACCEPTED_MYWORLD_CONTRACT.format(root=root.as_posix()), encoding="utf-8")
            self.run_cli(root, "create", contract.as_posix())
            self.run_cli(root, "send", "--repo", "myworld")

            result = self.run_cli(root, "watch", "--repo", "myworld", "--dispatch-id", "asc-0998", "--once")
            payload = json.loads(result.stdout)

            self.assertTrue(payload["ok"])
            result_path = root / payload["result"]
            data = json.loads(result_path.read_text(encoding="utf-8"))
            self.assertEqual(data["schema_version"], "aios.dispatch.result.v1")
            self.assertEqual(data["status"], "passed")
            self.assertEqual(data["target_repo"], "myworld")
            self.assertFalse(data["stop_conditions_triggered"])
            self.assertTrue((root / ".aios" / "logs" / "asc-0998.myworld.log").exists())

    def test_collect_skips_already_collected_result_packets(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            result_dir = root / ".aios" / "outbox" / "myworld"
            result_dir.mkdir(parents=True)
            (result_dir / "asc-0998.myworld.result.json").write_text(
                json.dumps(
                    {
                        "schema_version": "aios.dispatch.result.v1",
                        "target_repo": "myworld",
                        "dispatch_id": "asc-0998",
                        "contract_id": "ASC-0998",
                        "status": "passed",
                        "evidence": [],
                        "stop_conditions_triggered": [],
                    }
                ),
                encoding="utf-8",
            )

            first = self.run_cli(root, "collect", "--repo", "myworld")
            second = self.run_cli(root, "collect", "--repo", "myworld")

            self.assertEqual(len(json.loads(first.stdout)["collected"]), 1)
            self.assertEqual(json.loads(second.stdout)["collected"], [])

    def test_collect_rejects_malformed_v1_result_packet(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            result_dir = root / ".aios" / "outbox" / "myworld"
            result_dir.mkdir(parents=True)
            (result_dir / "bad.myworld.result.json").write_text(
                json.dumps({"schema_version": "aios.dispatch.result.v1", "dispatch_id": "bad"}),
                encoding="utf-8",
            )

            result = self.run_cli(root, "collect", "--repo", "myworld", check=False)

            self.assertNotEqual(result.returncode, 0)
            self.assertIn("malformed result packet", result.stderr)

    def test_collect_rejects_result_packet_with_wrong_dispatch_id(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            result_dir = root / ".aios" / "outbox" / "CapabilityOS"
            result_dir.mkdir(parents=True)
            (result_dir / "asc-0012.CapabilityOS.result.json").write_text(
                json.dumps(
                    {
                        "schema_version": "aios.dispatch.result.v1",
                        "target_repo": "CapabilityOS",
                        "dispatch_id": "asc-0012.CapabilityOS",
                        "contract_id": "ASC-0012",
                        "status": "passed",
                        "evidence": [],
                        "stop_conditions_triggered": [],
                    }
                ),
                encoding="utf-8",
            )

            result = self.run_cli(root, "collect", "--repo", "CapabilityOS", check=False)

            self.assertNotEqual(result.returncode, 0)
            self.assertIn("dispatch_id asc-0012.CapabilityOS != asc-0012", result.stderr)


if __name__ == "__main__":
    unittest.main()
