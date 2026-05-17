from __future__ import annotations

import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "aios_genesis_seed_capture.py"


class AiosGenesisSeedCaptureTest(unittest.TestCase):
    def make_root(self, tmp: str) -> Path:
        root = Path(tmp)
        (root / "GenesisOS").symlink_to(ROOT / "GenesisOS", target_is_directory=True)
        return root

    def test_capture_writes_seed_and_receipt_without_mutating_source(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = self.make_root(tmp)
            source = root / "operator_seed.md"
            source.write_text("What if release blockers became training prompts?", encoding="utf-8")
            before = source.read_bytes()

            sys.path.insert(0, ROOT.as_posix())
            from scripts.aios_genesis_seed_capture import build_report

            report = build_report(
                root,
                text=source.read_text(encoding="utf-8"),
                source="operator",
                tags=["release", "prompt-prison"],
                confidence=0.3,
                captured_by="codex-test",
                seeds_root=(root / "seeds").as_posix(),
            )

            self.assertEqual(report["schema_version"], "aios.genesis_seed_capture.v1")
            self.assertEqual(report["authority"], "speculative_only")
            self.assertTrue(report["review_required_before_promotion"])
            self.assertTrue((root / report["seed_path"]).exists())
            self.assertTrue((root / report["receipt_path"]).exists())
            self.assertEqual(source.read_bytes(), before)
            self.assertIn("prompt-prison", report["seed"]["tags"])

    def test_cli_json(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = self.make_root(tmp)
            result = subprocess.run(
                [
                    sys.executable,
                    SCRIPT.as_posix(),
                    "--root",
                    root.as_posix(),
                    "--inline",
                    "Keep a risky branch before verifier pressure removes it.",
                    "--source",
                    "operator",
                    "--tags",
                    "library,operator",
                    "--confidence",
                    "0.2",
                    "--captured-by",
                    "codex-test",
                    "--seeds-root",
                    (root / "seeds").as_posix(),
                    "--json",
                ],
                text=True,
                capture_output=True,
                check=False,
            )

            self.assertEqual(result.returncode, 0, result.stderr)
            payload = json.loads(result.stdout)
            self.assertEqual(payload["schema_version"], "aios.genesis_seed_capture.v1")
            self.assertTrue((root / payload["seed_path"]).exists())
            self.assertEqual(payload["seed"]["source"], "operator")
            self.assertIn("operator", payload["seed"]["tags"])


if __name__ == "__main__":
    unittest.main()
