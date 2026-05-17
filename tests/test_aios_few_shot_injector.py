import json
import subprocess
import sys
import unittest
from pathlib import Path

from scripts.aios_few_shot_injector import inject_prompt


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "aios_few_shot_injector.py"


class AiosFewShotInjectorTest(unittest.TestCase):
    def test_injects_draft_patterns_and_writes_audit(self) -> None:
        payload = inject_prompt(ROOT, "test prompt", user="founder", substrate="local_llm", limit=2)

        self.assertEqual(payload["schema_version"], "aios.few_shot_injection.v1")
        self.assertGreaterEqual(len(payload["patterns_injected"]), 1)
        self.assertIn("AIOS User Pattern Few-Shots", payload["injected_prompt"])
        self.assertTrue((ROOT / payload["audit_path"]).exists())
        as_text = json.dumps(payload, ensure_ascii=False)
        self.assertNotIn("_from_desktop", as_text)
        self.assertNotIn("secret", as_text.lower())
        self.assertNotIn("q1q1e3e3", as_text.lower())

    def test_cli_excludes_private_content(self) -> None:
        result = subprocess.run(
            [
                sys.executable,
                SCRIPT.as_posix(),
                "--root",
                ROOT.as_posix(),
                "--substrate-prompt",
                "test prompt",
                "--user",
                "founder",
                "--json",
            ],
            cwd=ROOT,
            text=True,
            capture_output=True,
            check=False,
        )

        self.assertEqual(result.returncode, 0, result.stderr)
        payload = json.loads(result.stdout)
        self.assertGreaterEqual(len(payload["patterns_injected"]), 1)
        as_text = json.dumps(payload, ensure_ascii=False)
        self.assertNotIn("_from_desktop", as_text)
        self.assertNotIn("q1q1e3e3", as_text.lower())


if __name__ == "__main__":
    unittest.main()
