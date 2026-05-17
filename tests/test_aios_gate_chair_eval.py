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


if __name__ == "__main__":
    unittest.main()
