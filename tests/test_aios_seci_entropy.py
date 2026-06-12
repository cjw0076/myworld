import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "aios_seci_entropy.py"


class AiosSeciEntropyTest(unittest.TestCase):
    def run_gate(self, *args: str) -> tuple[int, dict]:
        result = subprocess.run(
            [sys.executable, SCRIPT.as_posix(), *args, "--json"],
            text=True,
            capture_output=True,
            check=False,
        )
        self.assertTrue(result.stdout, result.stderr)
        return result.returncode, json.loads(result.stdout)

    def test_blocks_closeout_when_seci_and_entropy_are_missing(self) -> None:
        code, payload = self.run_gate("--text", "Ship this because the implementation looks correct.")

        self.assertEqual(code, 1)
        self.assertFalse(payload["pass"])
        self.assertFalse(payload["execution_enabled"])
        self.assertIn("seci_stage_missing", payload["stop_conditions"])
        self.assertGreaterEqual(len(payload["gaps"]), 4)

    def test_passes_when_all_seci_and_entropy_markers_exist(self) -> None:
        text = (
            "Socialization: shared experience from Claude/Codex/local review. "
            "Externalization: tacit to explicit contract notes. "
            "Combination: synthesis across web, memory, and provider evidence. "
            "Internalization: explicit to tacit habit through a future gate. "
            "Discomfort: named deficit prevents frozen convergence. "
            "Counter-branch: alternative assumption mutation remains open."
        )

        code, payload = self.run_gate("--text", text)

        self.assertEqual(code, 0)
        self.assertTrue(payload["pass"])
        self.assertFalse(payload["gaps"])
        self.assertEqual(payload["authority"], "advisory_only")

    def test_can_evaluate_file_without_storing_raw_private_data(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "summary.md"
            path.write_text(
                "Socialization observation. Externalization explicit note. "
                "Combination synthesis. Internalization habit. "
                "Discomfort need. Counter-branch alternative.",
                encoding="utf-8",
            )

            code, payload = self.run_gate("--path", path.as_posix())

            self.assertEqual(code, 0)
            self.assertEqual(payload["source"], path.as_posix())
            self.assertNotIn("summary.md", json.dumps(payload["checks"]))


if __name__ == "__main__":
    unittest.main()
