import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from scripts import aios_gate_chair_eval


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "aios_gate_chair_eval.py"


def write_executable(path: Path, body: str) -> None:
    path.write_text(body, encoding="utf-8")
    path.chmod(path.stat().st_mode | 0o100)


class AiosGateChairEvalTest(unittest.TestCase):
    def test_eval_writes_report_and_runs_internal_baseline(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)

            report = aios_gate_chair_eval.build_report(
                root,
                prompts=["AIOS에는 gate 역할의 Agent가 있나? 아니면 시스템 답변밖에 못하나?"],
                mode="internal",
            )

            self.assertEqual(report["schema_version"], "aios.gate_chair_eval.v1")
            self.assertEqual(report["prompt_count"], 1)
            self.assertEqual(report["modes"][0]["mode"], "internal")
            self.assertEqual(report["modes"][0]["runs"][0]["gate_chair_status"]["mode"], "internal_evidence_synthesizer")
            self.assertFalse(report["promotion_ready"])
            self.assertFalse(report["current_runtime_external"])
            self.assertIn("single-mode", report["readiness_reason"])
            self.assertIn("architecture_discloses_runtime", report["modes"][0]["runs"][0]["checks"])
            self.assertTrue((root / report["report_path"]).exists())

    def test_current_mode_can_use_configured_gate_chair_command(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            env = os.environ.copy()
            env["AIOS_GATE_AGENT_COMMAND"] = "printf 'external chair answer'"

            result = subprocess.run(
                [
                    sys.executable,
                    SCRIPT.as_posix(),
                    "--root",
                    root.as_posix(),
                    "--mode",
                    "current",
                    "--prompt",
                    "AIOS에는 gate 역할의 Agent가 있나? 아니면 시스템 답변밖에 못하나?",
                    "--json",
                ],
                cwd=ROOT,
                text=True,
                capture_output=True,
                env=env,
                check=False,
            )

            self.assertEqual(result.returncode, 0, result.stderr)
            payload = json.loads(result.stdout)
            run = payload["modes"][0]["runs"][0]
            self.assertEqual(run["gate_chair_status"]["mode"], "env_command")
            self.assertTrue(payload["current_runtime_external"])
            self.assertFalse(payload["promotion_ready"])
            self.assertIn("single-mode", payload["readiness_reason"])
            self.assertIn("external chair answer", run["response_preview"])
            self.assertTrue((root / payload["report_path"]).exists())

    def test_current_mode_can_eval_candidate_runtime_without_activating_it(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            candidate = root / ".aios" / "gate" / "founder" / "chair_candidate_runtime.json"
            candidate.parent.mkdir(parents=True)
            candidate.write_text(
                json.dumps(
                    {
                        "schema_version": "aios.gate.chair_runtime.v1",
                        "status": "candidate",
                        "mode": "claude",
                        "model": "candidate-model",
                    }
                ),
                encoding="utf-8",
            )
            bin_dir = root / "bin"
            bin_dir.mkdir()
            write_executable(
                bin_dir / "claude",
                "#!/usr/bin/env bash\n"
                "printf 'candidate chair answer'\n",
            )
            old_path = os.environ.get("PATH", "")
            os.environ["PATH"] = f"{bin_dir}{os.pathsep}{old_path}"
            try:
                report = aios_gate_chair_eval.build_report(
                    root,
                    prompts=["AIOS에는 gate 역할의 Agent가 있나?"],
                    mode="current",
                )
            finally:
                os.environ["PATH"] = old_path

            run = report["modes"][0]["runs"][0]
            self.assertEqual(report["candidate_runtime_path"], ".aios/gate/founder/chair_candidate_runtime.json")
            self.assertEqual(run["gate_chair_status"]["mode"], "claude")
            self.assertIn("candidate chair answer", run["response_preview"])
            self.assertFalse((root / ".aios" / "gate" / "founder" / "chair_runtime.json").exists())

    def test_tied_external_candidate_without_failures_is_promotion_ready(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            candidate = root / ".aios" / "gate" / "founder" / "chair_candidate_runtime.json"
            candidate.parent.mkdir(parents=True)
            candidate.write_text(
                json.dumps(
                    {
                        "schema_version": "aios.gate.chair_runtime.v1",
                        "status": "candidate",
                        "mode": "claude",
                        "model": "candidate-model",
                    }
                ),
                encoding="utf-8",
            )
            bin_dir = root / "bin"
            bin_dir.mkdir()
            write_executable(
                bin_dir / "claude",
                "#!/usr/bin/env bash\n"
                "printf 'Gate Chair runtime 상태: external candidate can answer with evidence discipline.'\n",
            )
            old_path = os.environ.get("PATH", "")
            os.environ["PATH"] = f"{bin_dir}{os.pathsep}{old_path}"
            try:
                report = aios_gate_chair_eval.build_report(
                    root,
                    prompts=["AIOS에는 gate 역할의 Agent가 있나? 아니면 시스템 답변밖에 못하나?"],
                    mode="both",
                )
            finally:
                os.environ["PATH"] = old_path

            self.assertEqual(report["scores"]["internal"], report["scores"]["current"])
            self.assertTrue(report["current_runtime_external"])
            self.assertEqual(report["current_failure_count"], 0)
            self.assertTrue(report["promotion_ready"])
            self.assertIn("matched the internal baseline", report["readiness_reason"])

    def test_eval_failure_writes_memory_draft_candidate(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            candidate = root / ".aios" / "gate" / "founder" / "chair_candidate_runtime.json"
            candidate.parent.mkdir(parents=True)
            candidate.write_text(
                json.dumps(
                    {
                        "schema_version": "aios.gate.chair_runtime.v1",
                        "status": "candidate",
                        "mode": "claude",
                        "model": "timeout-model",
                    }
                ),
                encoding="utf-8",
            )
            bin_dir = root / "bin"
            bin_dir.mkdir()
            write_executable(
                bin_dir / "claude",
                "#!/usr/bin/env bash\n"
                "echo 'rate limit' >&2\n"
                "exit 1\n",
            )
            old_path = os.environ.get("PATH", "")
            os.environ["PATH"] = f"{bin_dir}{os.pathsep}{old_path}"
            try:
                report = aios_gate_chair_eval.build_report(
                    root,
                    prompts=["AIOS에는 gate 역할의 Agent가 있나?"],
                    mode="current",
                )
            finally:
                os.environ["PATH"] = old_path

            draft_ref = report["artifact_paths"]["memory_drafts"]
            self.assertIn("memory_draft_candidate", report)
            self.assertTrue(draft_ref.startswith(".aios/chat/gate-chair-eval-"))
            draft_payload = json.loads((root / draft_ref).read_text(encoding="utf-8"))
            draft = draft_payload["memory_drafts"][0]
            self.assertEqual(draft["type"], "negative_evidence_signal")
            self.assertEqual(draft["origin"], "aios_gate_chair_eval")
            self.assertEqual(draft["status"], "draft")
            self.assertIn("provider_backpressure", draft["content"])
            self.assertIn(report["report_path"], draft["raw_refs"])

    def test_eval_failure_can_request_memory_review(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            candidate = root / ".aios" / "gate" / "founder" / "chair_candidate_runtime.json"
            candidate.parent.mkdir(parents=True)
            candidate.write_text(
                json.dumps(
                    {
                        "schema_version": "aios.gate.chair_runtime.v1",
                        "status": "candidate",
                        "mode": "claude",
                        "model": "timeout-model",
                    }
                ),
                encoding="utf-8",
            )
            bin_dir = root / "bin"
            bin_dir.mkdir()
            write_executable(
                bin_dir / "claude",
                "#!/usr/bin/env bash\n"
                "echo 'rate limit' >&2\n"
                "exit 1\n",
            )
            old_path = os.environ.get("PATH", "")
            os.environ["PATH"] = f"{bin_dir}{os.pathsep}{old_path}"
            try:
                report = aios_gate_chair_eval.build_report(
                    root,
                    prompts=["AIOS에는 gate 역할의 Agent가 있나?"],
                    mode="current",
                    request_memory_review=True,
                )
            finally:
                os.environ["PATH"] = old_path

            review = report["memory_review_request"]
            self.assertEqual(review["status"], "sent_to_memoryOS_inbox")
            packet_ref = report["artifact_paths"]["memory_review_packet"]
            self.assertTrue(packet_ref.startswith(".aios/inbox/memoryOS/"))
            packet = json.loads((root / packet_ref).read_text(encoding="utf-8"))
            self.assertEqual(packet["schema_version"], "aios.memory_draft_review_request.v1")
            self.assertEqual(packet["draft"]["type"], "negative_evidence_signal")
            self.assertEqual(packet["draft"]["origin"], "aios_gate_chair_eval")
            self.assertFalse(packet["review_policy"]["auto_accept"])

    def test_candidate_matrix_evaluates_and_restores_candidate_config(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            candidate = root / ".aios" / "gate" / "founder" / "chair_candidate_runtime.json"
            candidate.parent.mkdir(parents=True)
            previous = {
                "schema_version": "aios.gate.chair_runtime.v1",
                "status": "candidate",
                "mode": "claude",
                "model": "previous-model",
            }
            candidate.write_text(json.dumps(previous), encoding="utf-8")
            bin_dir = root / "bin"
            bin_dir.mkdir()
            write_executable(
                bin_dir / "claude",
                "#!/usr/bin/env bash\n"
                "printf 'candidate chair answer'\n",
            )
            write_executable(
                bin_dir / "codex",
                "#!/usr/bin/env bash\n"
                "echo 'pin required' >&2\n"
                "exit 1\n",
            )
            old_path = os.environ.get("PATH", "")
            os.environ["PATH"] = f"{bin_dir}{os.pathsep}{old_path}"
            try:
                report = aios_gate_chair_eval.build_candidate_matrix(
                    root,
                    prompts=["AIOS에는 gate 역할의 Agent가 있나?"],
                    candidates=["claude", "codex"],
                    request_memory_review=True,
                )
            finally:
                os.environ["PATH"] = old_path

            self.assertEqual(report["schema_version"], "aios.gate_chair_candidate_matrix.v1")
            self.assertTrue((root / report["report_path"]).exists())
            self.assertEqual(json.loads(candidate.read_text(encoding="utf-8")), previous)
            by_mode = {item["mode"]: item for item in report["candidates"]}
            self.assertTrue(by_mode["claude"]["external_runtime_observed"])
            self.assertEqual(by_mode["claude"]["failure_count"], 0)
            self.assertGreaterEqual(by_mode["codex"]["failure_count"], 1)
            self.assertIn("memory_draft_candidate", by_mode["codex"])
            self.assertFalse(report["promotion_ready"])

    def test_candidate_matrix_marks_tied_external_candidate_eligible(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            bin_dir = root / "bin"
            bin_dir.mkdir()
            write_executable(
                bin_dir / "claude",
                "#!/usr/bin/env bash\n"
                "printf 'Gate Chair runtime 상태: external candidate can answer with evidence discipline.'\n",
            )
            old_path = os.environ.get("PATH", "")
            os.environ["PATH"] = f"{bin_dir}{os.pathsep}{old_path}"
            try:
                report = aios_gate_chair_eval.build_candidate_matrix(
                    root,
                    prompts=["AIOS에는 gate 역할의 Agent가 있나? 아니면 시스템 답변밖에 못하나?"],
                    candidates=["claude"],
                )
            finally:
                os.environ["PATH"] = old_path

            candidate = report["candidates"][0]
            self.assertEqual(candidate["baseline_delta"], 0.0)
            self.assertTrue(candidate["external_runtime_observed"])
            self.assertTrue(candidate["promotion_eligible"])
            self.assertTrue(report["promotion_ready"])
            self.assertEqual(report["recommendation"], "candidate_ready:claude")


if __name__ == "__main__":
    unittest.main()
