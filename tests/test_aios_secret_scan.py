import sys
import unittest
from pathlib import Path

sys.path.insert(0, (Path(__file__).resolve().parents[1] / "scripts").as_posix())

import aios_secret_scan as s


class ScanTextTests(unittest.TestCase):
    def test_detects_aws_key(self) -> None:
        f = s.scan_text("aws = AKIAIOSFODNN7EXAMPLE here")
        self.assertEqual(len(f), 1)
        self.assertEqual(f[0]["rule"], "aws_access_key")

    def test_detects_private_key_block(self) -> None:
        f = s.scan_text("-----BEGIN OPENSSH PRIVATE KEY-----")
        self.assertTrue(any(x["rule"] == "private_key_block" for x in f))

    def test_detects_sk_key(self) -> None:
        f = s.scan_text('OPENAI="sk-ant-abcdef0123456789ABCDEF"')
        self.assertTrue(any(x["rule"] in ("openai_anthropic_key", "generic_secret_assign") for x in f))

    def test_generic_assignment_detected(self) -> None:
        f = s.scan_text('password = "s3cr3tValue_abcdef1234"')
        self.assertTrue(any(x["rule"] == "generic_secret_assign" for x in f))

    def test_placeholder_not_flagged(self) -> None:
        # env refs / placeholders must not trip the generic rule
        self.assertEqual(s.scan_text('api_key = "your_api_key_here_example"'), [])
        self.assertEqual(s.scan_text('token = "${GITHUB_TOKEN}"'), [])
        self.assertEqual(s.scan_text("api_key: os.environ['API_KEY']"), [])

    def test_clean_text(self) -> None:
        self.assertEqual(s.scan_text("just some normal code\nx = compute(y)"), [])

    def test_match_is_redacted(self) -> None:
        f = s.scan_text("key = AKIAIOSFODNN7EXAMPLE")
        self.assertNotIn("AKIAIOSFODNN7EXAMPLE", f[0]["match"])  # never print the full secret

    def test_scan_paths_skips_missing(self) -> None:
        self.assertEqual(s.scan_paths(Path("/"), ["does/not/exist.txt"]), [])


if __name__ == "__main__":
    unittest.main()
