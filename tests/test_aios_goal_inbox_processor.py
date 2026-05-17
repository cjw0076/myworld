import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "aios_goal_inbox_processor.py"


def write_goal(root: Path, repo: str, goal_id: str, goal: str, *, kind: str = "goal", summary: str = "") -> Path:
    path = root / ".aios" / "goal_inbox" / repo / f"{goal_id}.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "schema_version": "aios.repo_goal.v1",
        "goal_id": goal_id,
        "source_repo": repo,
        "kind": kind,
        "goal": goal,
        "summary": summary,
        "evidence_refs": [],
        "priority": "high",
        "created_at": "2026-05-13T00:00:00+09:00",
        "status": "pending_route",
    }
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return path


class GoalInboxProcessorTest(unittest.TestCase):
    def run_cli(self, root: Path, *args: str, check: bool = True) -> subprocess.CompletedProcess[str]:
        result = subprocess.run(
            [sys.executable, SCRIPT.as_posix(), "--root", root.as_posix(), *args],
            cwd=root,
            text=True,
            capture_output=True,
        )
        if check and result.returncode != 0:
            self.fail(f"command failed: {result.returncode}\nSTDOUT:\n{result.stdout}\nSTDERR:\n{result.stderr}")
        return result

    def test_auto_promotes_distinct_provider_goal_without_deleting_inbox(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "docs" / "contracts").mkdir(parents=True)
            write_goal(
                root,
                "hivemind",
                "rg_provider",
                "AIOS provider fallback should use local LLM when Claude hits rate limit",
                kind="blocker",
            )

            result = self.run_cli(root, "--json", "--assert-min-classified", "1")
            payload = json.loads(result.stdout)

            self.assertEqual(payload["classified"], 1)
            self.assertEqual(payload["counts"]["auto_promote_distinct"], 1)
            self.assertEqual(payload["counts"]["silently_skipped"], 0)
            self.assertTrue((root / ".aios" / "goal_inbox" / "hivemind" / "rg_provider.json").exists())
            candidates = payload["contract_candidates"]
            self.assertEqual(len(candidates), 1)
            contract = root / candidates[0]
            self.assertTrue(contract.exists())
            text = contract.read_text(encoding="utf-8")
            self.assertIn("status: proposed", text)
            self.assertIn("rg_provider", text)
            self.assertIn("## AIOS Role Evidence", text)
            self.assertIn("### MemoryOS", text)
            self.assertIn("### CapabilityOS", text)
            self.assertIn("### GenesisOS", text)
            self.assertIn("### Hive Mind", text)

    def test_idempotent_second_run_preserves_explicit_response_without_skip(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "docs" / "contracts").mkdir(parents=True)
            write_goal(root, "uri", "rg_sprint", "Uri Sprint should run through AIOS product repo sprint driver")

            first = json.loads(self.run_cli(root, "--json").stdout)
            second = json.loads(self.run_cli(root, "--json").stdout)

            self.assertEqual(first["classified"], 1)
            self.assertEqual(second["classified"], 1)
            self.assertEqual(second["skipped_already_processed"], 0)
            self.assertEqual(second["silently_skipped"], 0)
            self.assertEqual(second["previously_processed"], 1)
            self.assertEqual(len(list((root / "docs" / "contracts").glob("ASC-*-product-repo-sprint-driver-*.md"))), 1)

    def test_malformed_packet_goes_to_operator_queue(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            bad = root / ".aios" / "goal_inbox" / "hivemind" / "bad.json"
            bad.parent.mkdir(parents=True, exist_ok=True)
            bad.write_text('{"schema_version":"wrong"}\n', encoding="utf-8")

            payload = json.loads(self.run_cli(root, "--json").stdout)

            self.assertEqual(payload["counts"]["reject_out_of_scope"], 1)
            self.assertEqual(len(payload["operator_queue"]), 1)
            self.assertTrue((root / payload["operator_queue"][0]).exists())

    def test_report_summarizes_latest_receipt(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "docs" / "contracts").mkdir(parents=True)
            write_goal(root, "uri", "rg_research", "Add research_to_sprint_context primitive")
            self.run_cli(root, "--json")

            result = subprocess.run(
                [sys.executable, SCRIPT.as_posix(), "report", "--root", root.as_posix(), "--json"],
                cwd=root,
                text=True,
                capture_output=True,
            )
            self.assertEqual(result.returncode, 0, result.stderr)
            payload = json.loads(result.stdout)
            self.assertEqual(payload["goal_inbox_packets"], 1)
            self.assertEqual(payload["processed_index_count"], 1)
            self.assertEqual(payload["receipt_count"], 1)

    def test_assert_per_citizen_response_passes_for_distinct_contract(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "docs" / "contracts").mkdir(parents=True)
            write_goal(root, "uri", "rg_sprint", "Uri Sprint should run through AIOS product repo sprint driver")

            result = self.run_cli(root, "--assert-silently-skipped-zero", "--assert-per-citizen-response", "--json")
            payload = json.loads(result.stdout)

            self.assertEqual(payload["counts"]["auto_promote_distinct"], 1)
            self.assertEqual(payload["counts"]["silently_skipped"], 0)


if __name__ == "__main__":
    unittest.main()
