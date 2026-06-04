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

    def test_snapshot_includes_genesisos_repo_surface(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)

            payload = self.run_snapshot(root)

            repos = {row["repo"] for row in payload["repos"]}
            self.assertIn("GenesisOS", repos)
            genesis = next(row for row in payload["repos"] if row["repo"] == "GenesisOS")
            self.assertFalse(genesis["exists"])

    def test_reviewed_genesis_findings_do_not_emit_monitor_advisory(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "GenesisOS").symlink_to(SCRIPT.parents[1] / "GenesisOS", target_is_directory=True)
            contracts = root / "docs" / "contracts"
            contracts.mkdir(parents=True)
            (contracts / "ASC-0001-reviewed.md").write_text(
                """---
contract_id: ASC-0001
status: accepted
---

AIOS dispatch monitor contract ledger cli provider repeats the same control
plane vocabulary for a long enough body to keep the deterministic critic active.

## GenesisOS Escape Review

This review is advisory-only and records the prompt-prison review result.

### Assumptions

- Assumption 1: repeated control-plane wording is acceptable.
- Assumption 2: a reviewed warning should remain visible but not page forever.

Counter branch: negate those assumptions. If the vocabulary is trapping the
work, use a strange alternate framing before dispatch.

### Plain Language

Plain language: this contract was checked for frame lock and still has one
known stylistic risk.

### Cross-Domain Frame

Market analogy: reviewed risk stays on the blotter, but it does not keep
ringing the alarm bell after the owner acknowledged it.

### Time Horizons

- 1h: keep the note visible.
- 1 week: re-run after edits.
""",
                encoding="utf-8",
            )

            from scripts import aios_monitor as monitor

            sys.path.insert(0, SCRIPT.parents[1].joinpath("scripts").as_posix())
            findings = monitor.genesis_critic_advisory(root)

            self.assertEqual([], findings)

    def test_generated_cache_only_repo_status_is_low_signal(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            genesis = root / "GenesisOS"
            (genesis / "genesisos" / "__pycache__").mkdir(parents=True)
            subprocess.run(["git", "init"], cwd=genesis, text=True, capture_output=True, check=True)
            (genesis / "genesisos" / "__pycache__" / "critic.cpython-313.pyc").write_text(
                "cache",
                encoding="utf-8",
            )

            payload = self.run_snapshot(root)

            genesis_status = next(row for row in payload["repos"] if row["repo"] == "GenesisOS")
            self.assertFalse(genesis_status["dirty"])
            self.assertTrue(genesis_status["generated_cache_entries"])
            alerts = [alert for alert in payload["alerts"] if alert.get("repo") == "GenesisOS"]
            self.assertNotIn("repo_dirty", {alert["code"] for alert in alerts})
            self.assertIn("generated_cache_present", {alert["code"] for alert in alerts})

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

    def test_snapshot_reports_malformed_dispatch_jsonl_without_crashing(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            state = root / ".aios" / "state"
            state.mkdir(parents=True)
            good_event = {
                "event": "created",
                "dispatch_id": "asc-good",
                "contract_id": "ASC-GOOD",
                "status": "created",
            }
            (state / "dispatches.jsonl").write_text(
                json.dumps(good_event) + "\n" + '{"event": "created", "dispatch_id": "broken' + "\n",
                encoding="utf-8",
            )

            payload = self.run_snapshot(root)

            dispatches = {row["dispatch_id"]: row for row in payload["dispatches"]}
            self.assertIn("asc-good", dispatches)
            malformed = [
                alert for alert in payload["alerts"] if alert["code"] == "dispatch_state_malformed_jsonl"
            ]
            self.assertEqual(1, len(malformed))
            self.assertEqual(".aios/state/dispatches.jsonl", malformed[0]["path"])
            self.assertEqual(2, malformed[0]["line"])

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
            assessment_log = root / ".aios" / "state" / "monitor_assessments.jsonl"
            assessment_latest = root / ".aios" / "state" / "monitor_assessment.latest.json"
            events = root / ".aios" / "state" / "monitor_events.jsonl"
            self.assertTrue(monitor_log.exists())
            self.assertTrue(latest.exists())
            self.assertTrue(assessment_log.exists())
            self.assertTrue(assessment_latest.exists())
            self.assertTrue(events.exists())
            self.assertEqual(2, len(monitor_log.read_text(encoding="utf-8").splitlines()))
            self.assertEqual(2, len(assessment_log.read_text(encoding="utf-8").splitlines()))
            latest_payload = json.loads(latest.read_text(encoding="utf-8"))
            assessment_payload = json.loads(assessment_latest.read_text(encoding="utf-8"))
            self.assertEqual("aios.monitor.v1", latest_payload["schema_version"])
            self.assertEqual("aios.monitor.assessment.v1", assessment_payload["schema_version"])
            self.assertEqual("clear", assessment_payload["health"])
            event_text = events.read_text(encoding="utf-8")
            self.assertIn("sidecar_start", event_text)
            self.assertIn("sidecar_done", event_text)

    def test_assess_classifies_pending_dispatch_as_blocked(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            state = root / ".aios" / "state"
            state.mkdir(parents=True)
            events = [
                {"event": "created", "dispatch_id": "asc-test", "contract_id": "ASC-TEST"},
                {"event": "sent", "dispatch_id": "asc-test", "repo": "memoryOS"},
            ]
            (state / "dispatches.jsonl").write_text(
                "\n".join(json.dumps(event) for event in events) + "\n",
                encoding="utf-8",
            )

            result = subprocess.run(
                [sys.executable, SCRIPT.as_posix(), "assess", "--json"],
                cwd=root,
                text=True,
                capture_output=True,
                check=True,
            )

            payload = json.loads(result.stdout)
            self.assertEqual("blocked", payload["health"])
            self.assertEqual("dispatch_results_pending", payload["findings"][0]["code"])
            self.assertEqual("myworld", payload["findings"][0]["owner"])
            self.assertEqual("collect_result_or_run_watcher", payload["next_actions"][0]["action"])

    def test_snapshot_reports_orphan_dirty_post_failure(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            repo = root / "memoryOS"
            repo.mkdir()
            subprocess.run(["git", "init"], cwd=repo, text=True, capture_output=True, check=True)
            worklog = repo / "docs" / "AGENT_WORKLOG.md"
            worklog.parent.mkdir()
            worklog.write_text("orphan\n", encoding="utf-8")
            result_dir = root / ".aios" / "outbox" / "memoryOS"
            result_dir.mkdir(parents=True)
            (result_dir / "asc-0992.memoryOS.result.json").write_text(
                json.dumps(
                    {
                        "schema_version": "aios.dispatch.result.v1",
                        "target_repo": "memoryOS",
                        "dispatch_id": "asc-0992",
                        "contract_id": "ASC-0992",
                        "status": "failed",
                        "orphan_work_detected": True,
                        "orphan_work_files": ["?? docs/AGENT_WORKLOG.md"],
                    }
                ),
                encoding="utf-8",
            )

            payload = self.run_snapshot(root)

            alerts = {alert["code"]: alert for alert in payload["alerts"]}
            self.assertIn("orphan_dirty_post_failure", alerts)
            self.assertEqual("memoryOS", alerts["orphan_dirty_post_failure"]["repo"])

    def test_repo_dirty_alert_includes_related_dispatch_context(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            repo = root / "memoryOS"
            repo.mkdir()
            subprocess.run(["git", "init"], cwd=repo, text=True, capture_output=True, check=True)
            (repo / ".tmp_uri_cleanroom_seed.md").write_text("seed\n", encoding="utf-8")
            contract_dir = root / "docs" / "contracts"
            contract_dir.mkdir(parents=True)
            contract = contract_dir / "ASC-0223-test.md"
            contract.write_text(
                "---\ncontract_id: ASC-0223\nstatus: closed\naccepted: now\nclosed: now\n---\n",
                encoding="utf-8",
            )
            state = root / ".aios" / "state"
            state.mkdir(parents=True)
            events = [
                {
                    "event": "created",
                    "dispatch_id": "asc-0223",
                    "contract_id": "ASC-0223",
                    "contract_path": "docs/contracts/ASC-0223-test.md",
                    "contract_status": "accepted",
                    "status": "created",
                    "timestamp": "2026-06-05T01:34:00+09:00",
                },
                {
                    "event": "sent",
                    "dispatch_id": "asc-0223",
                    "repo": "memoryOS",
                    "status": "sent",
                    "timestamp": "2026-06-05T01:35:00+09:00",
                },
                {
                    "event": "collected",
                    "dispatch_id": "asc-0223.memoryOS",
                    "repo": "memoryOS",
                    "status": "collected",
                    "timestamp": "2026-06-05T01:36:00+09:00",
                },
                {
                    "event": "released",
                    "dispatch_id": "asc-0223",
                    "status": "released",
                    "reason": "closed_partial_with_followup",
                    "timestamp": "2026-06-05T01:43:00+09:00",
                },
                {
                    "event": "memory_writeback",
                    "dispatch_id": "asc-0223",
                    "ok": True,
                    "reason": "disabled_by_flag",
                    "skipped": True,
                    "timestamp": "2026-06-05T01:43:01+09:00",
                },
            ]
            (state / "dispatches.jsonl").write_text(
                "\n".join(json.dumps(event) for event in events) + "\n",
                encoding="utf-8",
            )

            payload = self.run_snapshot(root)

            alerts = {alert["code"]: alert for alert in payload["alerts"]}
            dirty = alerts["repo_dirty"]
            self.assertEqual("memoryOS", dirty["repo"])
            self.assertEqual("asc-0223", dirty["related_dispatches"][0]["dispatch_id"])
            self.assertEqual("ASC-0223", dirty["related_dispatches"][0]["contract_id"])
            self.assertEqual("closed", dirty["related_dispatches"][0]["current_contract_status"])
            self.assertEqual("released", dirty["related_dispatches"][0]["latest_status"])
            self.assertEqual("closed_partial_with_followup", dirty["related_dispatches"][0]["latest_reason"])

    def test_status_reports_latest_snapshot(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            subprocess.run(
                [sys.executable, SCRIPT.as_posix(), "assess", "--write"],
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
            self.assertEqual(".aios/state/monitor_assessment.latest.json", payload["latest_assessment"])
            self.assertEqual("clear", payload["latest_health"])
            self.assertIsInstance(payload["latest_alert_count"], int)


if __name__ == "__main__":
    unittest.main()
