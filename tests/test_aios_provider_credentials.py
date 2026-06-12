import importlib.util
import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch


ROOT = Path(__file__).resolve().parents[1]
PROVIDER = ROOT / "scripts" / "aios_provider.py"


def load_provider_module():
    spec = importlib.util.spec_from_file_location("aios_provider_under_test", PROVIDER)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


class AiosProviderCredentialTest(unittest.TestCase):
    def test_missing_claude_key_writes_broker_request_without_secret(self) -> None:
        module = load_provider_module()
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            with patch.dict(os.environ, {"AIOS_ROOT": root.as_posix()}, clear=True):
                result = module.call_claude("hello", timeout=1)

            self.assertFalse(result["ok"])
            self.assertEqual(result["error"], "credential unavailable; broker request written")
            request = result["credential_request"]
            self.assertEqual(request["schema_version"], "aios.credential_broker.v1")
            self.assertEqual(request["key"], "ANTHROPIC_API_KEY")
            self.assertFalse(request["allowed_to_print_value"])
            receipt = root / request["receipt"]
            self.assertTrue(receipt.exists())
            text = receipt.read_text(encoding="utf-8")
            self.assertNotIn("sk-", text)
            self.assertIn("values_redacted", text)


if __name__ == "__main__":
    unittest.main()
