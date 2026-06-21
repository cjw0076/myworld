import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "aios_readiness.py"


def write_l6_fixture(root: Path) -> None:
    # L0: definition
    (root / "docs" / "contracts").mkdir(parents=True)
    (root / "docs" / "AIOS_DEFINITION.md").write_text("# AIOS Definition\n", encoding="utf-8")

    # L1: at least one contract
    (root / "docs" / "contracts" / "ASC-0099-fixture.md").write_text(
        "---\ncontract_id: ASC-0099\nstatus: closed\n---\n", encoding="utf-8"
    )

    # L2/L3: dispatch events for all 3 organs
    state = root / ".aios" / "state"
    state.mkdir(parents=True)
    events = [
        {"event": "sent", "dispatch_id": "a", "repo": "hivemind"},
        {"event": "sent", "dispatch_id": "b", "repo": "memoryOS"},
        {"event": "sent", "dispatch_id": "c", "repo": "CapabilityOS"},
        {"event": "collected", "dispatch_id": "a", "repo": "hivemind",
         "result": ".aios/outbox/hivemind/a.json"},
    ]
    (state / "dispatches.jsonl").write_text(
        "\n".join(json.dumps(row) for row in events) + "\n", encoding="utf-8"
    )

    # L4: passing result packet
    outbox = root / ".aios" / "outbox" / "hivemind"
    outbox.mkdir(parents=True)
    (outbox / "a.json").write_text(
        json.dumps({
            "schema_version": "aios.dispatch.result.v1",
            "target_repo": "hivemind",
            "dispatch_id": "a",
            "contract_id": "ASC-0099",
            "status": "passed",
            "evidence": [],
            "stop_conditions_triggered": [],
        }),
        encoding="utf-8",
    )

    # L5: organ implementation artifacts
    scripts = root / "scripts"
    scripts.mkdir(exist_ok=True)
    (scripts / "aios_capabilityos_bridge.py").write_text("# fixture\n", encoding="utf-8")
    (scripts / "aios_harness.py").write_text("# fixture\n", encoding="utf-8")
    (scripts / "aios_role_router.py").write_text("# fixture\n", encoding="utf-8")
    (root / "memoryOS" / "memoryos").mkdir(parents=True)
    (root / "memoryOS" / "memoryos" / "__init__.py").write_text("", encoding="utf-8")

    # L6: kernel head + turn loop + live-execute proof + canonical docs
    (scripts / "aios_head.py").write_text("# fixture\n", encoding="utf-8")
    (scripts / "aios_turn_loop.py").write_text("# fixture\n", encoding="utf-8")
    docs = root / "docs"
    (docs / "AIOS_GETTING_STARTED.md").write_text("# fixture\n", encoding="utf-8")
    (docs / "AIOS_CANONICAL_SHAPE.md").write_text("# fixture\n", encoding="utf-8")
    (docs / "aios-standards.md").write_text("# fixture\n", encoding="utf-8")


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
            write_l6_fixture(root)

            payload = self.run_readiness(root)

            self.assertTrue(payload["ready"])
            self.assertEqual(payload["level"], 6)
            self.assertFalse(payload["gaps"])

    def test_unreconciled_pending_packet_blocks_l6(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            write_l6_fixture(root)
            inbox = root / ".aios" / "inbox" / "myworld"
            inbox.mkdir(parents=True)
            (inbox / "stale.myworld.json").write_text(
                json.dumps(
                    {
                        "dispatch_id": "stale",
                        "target_repo": "myworld",
                        "return_to": ".aios/outbox/myworld/stale.myworld.result.json",
                    }
                ),
                encoding="utf-8",
            )

            payload = self.run_readiness(root)

            self.assertFalse(payload["ready"])
            self.assertEqual(payload["level"], 5)
            self.assertIn(".aios/inbox/myworld/stale.myworld.json", payload["gaps"][0])

    def test_reconciled_pending_packet_does_not_block_l6(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            write_l6_fixture(root)
            inbox = root / ".aios" / "inbox" / "myworld"
            inbox.mkdir(parents=True)
            (inbox / "stale.myworld.json").write_text(
                json.dumps(
                    {
                        "dispatch_id": "stale",
                        "target_repo": "myworld",
                        "return_to": ".aios/outbox/myworld/stale.myworld.result.json",
                    }
                ),
                encoding="utf-8",
            )
            (root / "docs" / "AIOS_MONITOR_RECONCILIATIONS.json").write_text(
                json.dumps(
                    {
                        "schema_version": "aios.monitor_reconciliations.v1",
                        "reconciliations": [
                            {
                                "id": "known-pending",
                                "match": {
                                    "code": "dispatch_results_pending",
                                    "dispatch_id": "stale",
                                    "repos": ["myworld"],
                                },
                                "reason": "test pending drift",
                                "accepted_by": "test",
                                "accepted_at": "now",
                                "authorized_by_contract": "ASC-TEST",
                            }
                        ],
                    }
                ),
                encoding="utf-8",
            )

            payload = self.run_readiness(root)

            self.assertTrue(payload["ready"])
            self.assertEqual(payload["level"], 6)
            self.assertFalse(payload["gaps"])

    def test_running_packet_does_not_block_its_own_readiness_gate(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            write_l6_fixture(root)
            inbox = root / ".aios" / "inbox" / "myworld"
            inbox.mkdir(parents=True)
            (inbox / "active.myworld.json").write_text(
                json.dumps(
                    {
                        "dispatch_id": "active",
                        "target_repo": "myworld",
                        "return_to": ".aios/outbox/myworld/active.myworld.result.json",
                    }
                ),
                encoding="utf-8",
            )
            state = root / ".aios" / "state" / "dispatches.jsonl"
            with state.open("a", encoding="utf-8") as handle:
                handle.write(json.dumps({"event": "sent", "dispatch_id": "active", "repo": "myworld", "status": "sent"}) + "\n")
                handle.write(json.dumps({"event": "running", "dispatch_id": "active", "repo": "myworld", "status": "running"}) + "\n")

            payload = self.run_readiness(root)

            self.assertTrue(payload["ready"])
            self.assertEqual(payload["level"], 6)
            self.assertFalse(payload["gaps"])


if __name__ == "__main__":
    unittest.main()
