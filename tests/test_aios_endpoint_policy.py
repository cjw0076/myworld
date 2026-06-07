import sys
import unittest
from pathlib import Path

sys.path.insert(0, (Path(__file__).resolve().parents[1] / "scripts").as_posix())

import aios_endpoint_policy as p


class HostOfTests(unittest.TestCase):
    def test_host_of(self) -> None:
        self.assertEqual(p.host_of("https://api.github.com/search?q=x"), "api.github.com")
        self.assertEqual(p.host_of("http://127.0.0.1:11434/api/tags"), "127.0.0.1")
        self.assertEqual(p.host_of("https://user@raw.githubusercontent.com/a/b"), "raw.githubusercontent.com")


class IsAllowedTests(unittest.TestCase):
    def test_allowed_hosts(self) -> None:
        self.assertTrue(p.is_allowed("https://api.github.com/x"))
        self.assertTrue(p.is_allowed("http://127.0.0.1:11434/api/generate"))
        self.assertTrue(p.is_allowed("http://localhost:8765/plan"))
        self.assertTrue(p.is_allowed("https://raw.githubusercontent.com/a/b/main/README.md"))

    def test_subdomain_allowed(self) -> None:
        self.assertTrue(p.is_allowed("https://objects.githubusercontent.com/x", allow=frozenset({"githubusercontent.com"})))

    def test_denied_hosts(self) -> None:
        self.assertFalse(p.is_allowed("https://evil.example.com/exfil"))
        self.assertFalse(p.is_allowed("http://169.254.169.254/latest/meta-data"))  # cloud metadata
        self.assertFalse(p.is_allowed("https://api.github.com.evil.com/x"))  # suffix-spoof not allowed

    def test_guarded_urlopen_denies(self) -> None:
        with self.assertRaises(p.EndpointDenied):
            p.guarded_urlopen("https://evil.example.com/exfil")


if __name__ == "__main__":
    unittest.main()
