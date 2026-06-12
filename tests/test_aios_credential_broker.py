import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "aios_credential_broker.py"


class AiosCredentialBrokerTest(unittest.TestCase):
    def run_broker(self, root: Path, *args: str, env: dict[str, str] | None = None) -> dict:
        merged_env = os.environ.copy()
        merged_env.pop("ANTHROPIC_API_KEY", None)
        merged_env.pop("OPENAI_API_KEY", None)
        if env:
            merged_env.update(env)
        result = subprocess.run(
            [sys.executable, SCRIPT.as_posix(), "--root", root.as_posix(), "--json", *args],
            text=True,
            capture_output=True,
            check=False,
            env=merged_env,
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        return json.loads(result.stdout)

    def test_status_never_prints_env_secret_value(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            secret = "sk-test-value-must-not-appear"
            payload = self.run_broker(
                Path(tmp),
                "status",
                "--keys",
                "OPENAI_API_KEY",
                env={"OPENAI_API_KEY": secret},
            )

            encoded = json.dumps(payload)
            self.assertNotIn(secret, encoded)
            self.assertEqual(payload["credentials"][0]["availability"], "available_via_env")
            self.assertTrue(payload["credentials"][0]["env_present"])

    def test_request_writes_redacted_receipt(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            payload = self.run_broker(
                root,
                "request",
                "ANTHROPIC_API_KEY",
                "--provider",
                "claude",
                "--purpose",
                "multi-provider synthesis",
                "--write",
            )

            receipt = root / payload["receipt"]
            self.assertTrue(receipt.exists())
            stored = json.loads(receipt.read_text(encoding="utf-8"))
            self.assertFalse(stored["allowed_to_print_value"])
            self.assertTrue(stored["privacy"]["values_redacted"])
            self.assertFalse(stored["privacy"]["chat_secret_request_allowed"])
            self.assertNotIn("sk-", json.dumps(stored).lower())
            self.assertNotIn("raw_value", stored)
            self.assertNotIn("credential_value", stored)

    def test_initialized_vault_reports_maybe_without_decrypting(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            vault = root / "vault"
            vault.mkdir()
            (vault / "vault.enc").write_bytes(b"encrypted")
            (vault / "vault.salt").write_bytes(b"salt")
            payload = self.run_broker(
                root,
                "status",
                "--keys",
                "ANTHROPIC_API_KEY",
                env={"AIOS_VAULT_DIR": vault.as_posix()},
            )

            self.assertTrue(payload["vault_initialized"])
            self.assertEqual(payload["credentials"][0]["availability"], "vault_may_hold_value")


if __name__ == "__main__":
    unittest.main()
