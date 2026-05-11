import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "aios_monitor.py"


class AiosMonitorTest(unittest.TestCase):
    def run_snapshot(self, root: Path) -> dict:
        result = subprocess.run(
            [sys.executable, SCRIPT.as_posix(), "snapshot", "--json"],
            cwd=root,
            text=True,
            capture_output=True,
            check=True,
        )
        return json.loads(result.stdout)

    def test_snapshot_reports_contract_status_drift(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            contract_dir = root / "docs" / "contracts"
            contract_dir.mkdir(parents=True)
            contract = contract_dir / "ASC-0001-test.md"
            contract.write_text(
                "---\ncontract_id: ASC-0001\nstatus: closed\naccepted: now\nclosed: now\n---\n",
                encoding="utf-8",
            )
            state = root / ".aios" / "state"
            state.mkdir(parents=True)
            (state / "dispatches.jsonl").write_text(
                json.dumps(
                    {
                        "event": "created",
                        "dispatch_id": "asc-0001",
                        "contract_id": "ASC-0001",
                        "contract_path": "docs/contracts/ASC-0001-test.md",
                        "contract_status": "proposed",
                        "status": "created",
                    }
                )
                + "\n",
                encoding="utf-8",
            )

            payload = self.run_snapshot(root)

            codes = {alert["code"] for alert in payload["alerts"]}
            self.assertIn("dispatch_contract_status_stale", codes)

    def test_snapshot_applies_exact_reconciliation(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            contract_dir = root / "docs" / "contracts"
            contract_dir.mkdir(parents=True)
            contract_path = contract_dir / "ASC-0001-test.md"
            contract_path.write_text(
                "---\ncontract_id: ASC-0001\nstatus: closed\naccepted: now\nclosed: now\n---\n",
                encoding="utf-8",
            )
            (root / "docs" / "AIOS_MONITOR_RECONCILIATIONS.json").write_text(
                json.dumps(
                    {
                        "schema_version": "aios.monitor_reconciliations.v1",
                        "reconciliations": [
                            {
                                "id": "known-bootstrap-drift",
                                "match": {
                                    "code": "dispatch_contract_status_stale",
                                    "dispatch_id": "asc-0001",
                                    "recorded": "proposed",
                                    "current": "closed",
                                    "contract_path": "docs/contracts/ASC-0001-test.md",
                                },
                                "reason": "test reconciliation",
                                "accepted_by": "test",
                                "accepted_at": "now",
                                "authorized_by_contract": "ASC-TEST",
                            }
                        ],
                    }
                ),
                encoding="utf-8",
            )
            state = root / ".aios" / "state"
            state.mkdir(parents=True)
            (state / "dispatches.jsonl").write_text(
                json.dumps(
                    {
                        "event": "created",
                        "dispatch_id": "asc-0001",
                        "contract_id": "ASC-0001",
                        "contract_path": "docs/contracts/ASC-0001-test.md",
                        "contract_status": "proposed",
                        "status": "created",
                    }
                )
                + "\n",
                encoding="utf-8",
            )

            payload = self.run_snapshot(root)

            self.assertEqual([], payload["alerts"])
            self.assertEqual("known-bootstrap-drift", payload["reconciliations_applied"][0]["id"])

    def test_snapshot_does_not_apply_partial_reconciliation(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            contract_dir = root / "docs" / "contracts"
            contract_dir.mkdir(parents=True)
            (contract_dir / "ASC-0002-test.md").write_text(
                "---\ncontract_id: ASC-0002\nstatus: closed\naccepted: now\nclosed: now\n---\n",
                encoding="utf-8",
            )
            (root / "docs" / "AIOS_MONITOR_RECONCILIATIONS.json").write_text(
                json.dumps(
                    {
                        "schema_version": "aios.monitor_reconciliations.v1",
                        "reconciliations": [
                            {
                                "id": "different-drift",
                                "match": {
                                    "code": "dispatch_contract_status_stale",
                                    "dispatch_id": "asc-0001",
                                    "recorded": "proposed",
                                    "current": "closed",
                                    "contract_path": "docs/contracts/ASC-0001-test.md",
                                },
                            }
                        ],
                    }
                ),
                encoding="utf-8",
            )
            state = root / ".aios" / "state"
            state.mkdir(parents=True)
            (state / "dispatches.jsonl").write_text(
                json.dumps(
                    {
                        "event": "created",
                        "dispatch_id": "asc-0002",
                        "contract_id": "ASC-0002",
                        "contract_path": "docs/contracts/ASC-0002-test.md",
                        "contract_status": "proposed",
                        "status": "created",
                    }
                )
                + "\n",
                encoding="utf-8",
            )

            payload = self.run_snapshot(root)

            codes = {alert["code"] for alert in payload["alerts"]}
            self.assertIn("dispatch_contract_status_stale", codes)
            self.assertEqual([], payload["reconciliations_applied"])

    def test_snapshot_does_not_report_accepted_to_closed_as_stale(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            contract_dir = root / "docs" / "contracts"
            contract_dir.mkdir(parents=True)
            (contract_dir / "ASC-0002-test.md").write_text(
                "---\ncontract_id: ASC-0002\nstatus: closed\naccepted: now\nclosed: now\n---\n",
                encoding="utf-8",
            )
            state = root / ".aios" / "state"
            state.mkdir(parents=True)
            (state / "dispatches.jsonl").write_text(
                json.dumps(
                    {
                        "event": "created",
                        "dispatch_id": "asc-0002",
                        "contract_id": "ASC-0002",
                        "contract_path": "docs/contracts/ASC-0002-test.md",
                        "contract_status": "accepted",
                        "status": "created",
                    }
                )
                + "\n",
                encoding="utf-8",
            )

            payload = self.run_snapshot(root)

            codes = {alert["code"] for alert in payload["alerts"]}
            self.assertNotIn("dispatch_contract_status_stale", codes)

    def test_snapshot_normalizes_repo_suffixed_dispatch_ids(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            state = root / ".aios" / "state"
            state.mkdir(parents=True)
            events = [
                {
                    "event": "created",
                    "dispatch_id": "asc-0012",
                    "contract_id": "ASC-0012",
                    "status": "created",
                    "repos": ["CapabilityOS"],
                },
                {
                    "event": "sent",
                    "dispatch_id": "asc-0012",
                    "repo": "CapabilityOS",
                    "status": "sent",
                },
                {
                    "event": "collected",
                    "dispatch_id": "asc-0012.CapabilityOS",
                    "repo": "CapabilityOS",
                    "result": ".aios/outbox/CapabilityOS/asc-0012.CapabilityOS.result.json",
                    "status": "collected",
                },
            ]
            (state / "dispatches.jsonl").write_text(
                "\n".join(json.dumps(event) for event in events) + "\n",
                encoding="utf-8",
            )

            payload = self.run_snapshot(root)

            dispatches = {row["dispatch_id"]: row for row in payload["dispatches"]}
            self.assertIn("asc-0012", dispatches)
            self.assertNotIn("asc-0012.CapabilityOS", dispatches)
            codes = {alert["code"] for alert in payload["alerts"]}
            self.assertNotIn("dispatch_results_pending", codes)

    def test_snapshot_tolerates_created_event_without_contract_path(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            state = root / ".aios" / "state"
            state.mkdir(parents=True)
            (state / "dispatches.jsonl").write_text(
                json.dumps(
                    {
                        "event": "created",
                        "dispatch_id": "legacy",
                        "contract_id": "ASC-LEGACY",
                        "contract_status": "accepted",
                    }
                )
                + "\n",
                encoding="utf-8",
            )

            payload = self.run_snapshot(root)

            codes = {alert["code"] for alert in payload["alerts"]}
            self.assertIn("dispatch_contract_path_missing", codes)

    def test_run_sidecar_iterations_write_monitor_state(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)

            result = subprocess.run(
                [
                    sys.executable,
                    SCRIPT.as_posix(),
                    "run",
                    "--iterations",
                    "2",
                    "--interval",
                    "1",
                    "--quiet",
                ],
                cwd=root,
                text=True,
                capture_output=True,
                check=True,
            )

            self.assertEqual("", result.stdout)
            monitor_log = root / ".aios" / "state" / "monitor.jsonl"
            latest = root / ".aios" / "state" / "monitor.latest.json"
            events = root / ".aios" / "state" / "monitor_events.jsonl"
            self.assertTrue(monitor_log.exists())
            self.assertTrue(latest.exists())
            self.assertTrue(events.exists())
            self.assertEqual(2, len(monitor_log.read_text(encoding="utf-8").splitlines()))
            latest_payload = json.loads(latest.read_text(encoding="utf-8"))
            self.assertEqual("aios.monitor.v1", latest_payload["schema_version"])
            event_text = events.read_text(encoding="utf-8")
            self.assertIn("sidecar_start", event_text)
            self.assertIn("sidecar_done", event_text)

    def test_status_reports_latest_snapshot(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            self.run_snapshot(root)
            subprocess.run(
                [sys.executable, SCRIPT.as_posix(), "snapshot", "--write"],
                cwd=root,
                text=True,
                capture_output=True,
                check=True,
            )

            result = subprocess.run(
                [sys.executable, SCRIPT.as_posix(), "status", "--json"],
                cwd=root,
                text=True,
                capture_output=True,
                check=True,
            )

            payload = json.loads(result.stdout)
            self.assertFalse(payload["running"])
            self.assertEqual(".aios/state/monitor.latest.json", payload["latest_snapshot"])
            self.assertIsInstance(payload["latest_alert_count"], int)


if __name__ == "__main__":
    unittest.main()
