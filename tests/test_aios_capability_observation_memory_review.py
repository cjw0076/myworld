import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from scripts.aios_capability_observation_memory_review import build_review_packet, validate_review_packet


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "aios_capability_observation_memory_review.py"
MEMORYOS_ROOT = ROOT / "memoryOS"


def observation_payload() -> dict:
    return {
        "contract": "capabilityos.observe_results.v1",
        "recommendation_only": True,
        "source_inbox": "../.aios/outbox",
        "source_radar": "../docs/AIOS_TASK_RADAR.md",
        "result_files": 3,
        "observations_count": 3,
        "observations": [
            {
                "schema_version": "aios.capability_observation.v1",
                "capability_id": "cap_capabilityos_recommendation",
                "dispatch_id": "asc-0002",
                "contract_id": "ASC-0002",
                "child_agent": "codex",
                "repo": "CapabilityOS",
                "outcome": "passed",
                "latency_seconds": None,
                "evidence_refs": [
                    "../.aios/outbox/CapabilityOS/asc-0002.CapabilityOS.result.json",
                    "../docs/contracts/ASC-0002-capabilityos-executable-surface.md",
                ],
                "observed_at": "2026-05-12T01:00:00+09:00",
            },
            {
                "schema_version": "aios.capability_observation.v1",
                "capability_id": "cap_capabilityos_recommendation",
                "dispatch_id": "asc-0009",
                "contract_id": "ASC-0009",
                "child_agent": "codex",
                "repo": "CapabilityOS",
                "outcome": "passed",
                "latency_seconds": None,
                "evidence_refs": [
                    "../.aios/outbox/CapabilityOS/asc-0009.CapabilityOS.result.json",
                    "../docs/contracts/ASC-0009-capability-observation-feedback.md",
                ],
                "observed_at": "2026-05-12T01:10:00+09:00",
            },
            {
                "schema_version": "aios.capability_observation.v1",
                "capability_id": "cap_hivemind_execution_harness",
                "dispatch_id": "asc-0010",
                "contract_id": "ASC-0010",
                "child_agent": "codex",
                "repo": "hivemind",
                "outcome": "failed",
                "latency_seconds": None,
                "evidence_refs": [
                    "../.aios/outbox/hivemind/asc-0010.hivemind.result.json",
                    "../docs/contracts/ASC-0010-hive-semantic-quality-gate.md",
                ],
                "observed_at": "2026-05-12T01:20:00+09:00",
            },
        ],
        "gaps": [],
        "radar_signals": [],
        "updated_capabilities": [],
    }


class AiosCapabilityObservationMemoryReviewTest(unittest.TestCase):
    def test_build_review_packet_rolls_up_passed_capability_observations(self) -> None:
        packet = build_review_packet(observation_payload(), observation_ref="docs/evidence/obs.json")

        self.assertEqual(packet["schema_version"], "aios.capability_observation_memory_review.v1")
        self.assertFalse(packet["auto_accept"])
        self.assertEqual(packet["memoryos_target_status"], "draft")
        self.assertEqual(packet["candidate_count"], 1)
        self.assertEqual(packet["excluded_count"], 1)
        candidate = packet["candidates"][0]
        self.assertEqual(candidate["capability_id"], "cap_capabilityos_recommendation")
        self.assertEqual(candidate["observation_count"], 2)
        self.assertEqual(candidate["status"], "draft")
        self.assertEqual(candidate["evidence_state"], "unreviewed")
        self.assertFalse(candidate["auto_accept"])
        self.assertIn("docs/evidence/obs.json", candidate["raw_refs"])

    def test_validate_rejects_auto_accept_candidate(self) -> None:
        packet = build_review_packet(observation_payload(), observation_ref="docs/evidence/obs.json")
        packet["candidates"][0]["auto_accept"] = True

        errors = validate_review_packet(packet)

        self.assertIn("candidates[0].auto_accept must be false", errors)

    def test_cli_builds_candidates_from_result_outbox(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            outbox = root / ".aios" / "outbox"
            self.write_result(outbox / "CapabilityOS" / "asc-0002.CapabilityOS.result.json", "CapabilityOS", "ASC-0002")
            self.write_result(outbox / "hivemind" / "asc-0010.hivemind.result.json", "hivemind", "ASC-0010")
            output = root / "candidates.json"
            observation_output = root / "observations.json"
            run_bundle = root / "run_bundle"

            result = subprocess.run(
                [
                    sys.executable,
                    SCRIPT.as_posix(),
                    "--root",
                    ROOT.as_posix(),
                    "build",
                    "--outbox",
                    outbox.as_posix(),
                    "--observation-output",
                    observation_output.as_posix(),
                    "--output",
                    output.as_posix(),
                    "--run-bundle",
                    run_bundle.as_posix(),
                    "--json",
                ],
                cwd=ROOT,
                text=True,
                capture_output=True,
                check=False,
            )

            self.assertEqual(result.returncode, 0, result.stderr)
            packet = json.loads(output.read_text(encoding="utf-8"))
            self.assertEqual(packet["candidate_count"], 2)
            self.assertTrue((run_bundle / "memory_drafts.json").exists())
            self.assertTrue(observation_output.exists())

    def test_memoryos_import_run_dry_run_accepts_generated_bundle(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            outbox = root / ".aios" / "outbox"
            self.write_result(outbox / "CapabilityOS" / "asc-0002.CapabilityOS.result.json", "CapabilityOS", "ASC-0002")
            run_bundle = root / "run_bundle"
            subprocess.run(
                [
                    sys.executable,
                    SCRIPT.as_posix(),
                    "--root",
                    ROOT.as_posix(),
                    "build",
                    "--outbox",
                    outbox.as_posix(),
                    "--run-bundle",
                    run_bundle.as_posix(),
                ],
                cwd=ROOT,
                text=True,
                capture_output=True,
                check=True,
            )

            result = subprocess.run(
                [
                    sys.executable,
                    "-m",
                    "memoryos.cli",
                    "--root",
                    ROOT.as_posix(),
                    "import-run",
                    run_bundle.as_posix(),
                    "--dry-run",
                    "--json",
                ],
                cwd=MEMORYOS_ROOT,
                text=True,
                capture_output=True,
                check=False,
            )

            self.assertEqual(result.returncode, 0, result.stderr)
            payload = json.loads(result.stdout)
            self.assertEqual(payload["schema_version"], "K43.2")
            self.assertEqual(payload["status"], "dry_run_ok")
            self.assertEqual(payload["counts"]["planned"]["memory_objects"], 1)
            self.assertFalse(payload["run_refs"]["raw_refs_included"])

    def write_result(self, path: Path, repo: str, contract_id: str) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(
            json.dumps(
                {
                    "schema_version": "aios.dispatch.result.v1",
                    "target_repo": repo,
                    "dispatch_id": path.name.replace(".result.json", ""),
                    "contract_id": contract_id,
                    "status": "passed",
                    "agent_assigned": "codex",
                    "executed_at": "2026-05-12T01:00:00+09:00",
                    "evidence": [{"kind": "test", "status": "passed"}],
                    "stop_conditions_triggered": [],
                }
            ),
            encoding="utf-8",
        )


if __name__ == "__main__":
    unittest.main()
