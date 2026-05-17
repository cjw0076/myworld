import importlib.util
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
FILTER_SCRIPT = ROOT / "scripts" / "aios_uri_filter.py"
SCOUT_SCRIPT = ROOT / "scripts" / "aios_doc_scout.py"


def load_filter_module():
    spec = importlib.util.spec_from_file_location("aios_uri_filter", FILTER_SCRIPT)
    module = importlib.util.module_from_spec(spec)
    assert spec and spec.loader
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


class AiosUriFilterTest(unittest.TestCase):
    def setUp(self) -> None:
        self.filter = load_filter_module()

    def test_whitelisted_uri_doc_is_aios_relevant(self) -> None:
        result = self.filter.classify(Path("myworld/uri/docs/URI_NORTHSTAR.md"))

        self.assertEqual(result.uri_path, "uri/docs/URI_NORTHSTAR.md")
        self.assertEqual(result.outcome, "aios_relevant")
        self.assertEqual(result.reason, "whitelist")

    def test_denylist_wins_over_shared_language_terms(self) -> None:
        result = self.filter.classify(
            Path("myworld/uri/hive/packets/URI-999.md"),
            text="AIOS contract dispatch capability hive memory",
        )

        self.assertEqual(result.outcome, "uri_internal")
        self.assertTrue(result.reason.startswith("deny_prefix:uri/hive/packets/"))

    def test_docs_with_two_shared_terms_are_aios_relevant(self) -> None:
        result = self.filter.classify(
            Path("myworld/uri/docs/WORKSTREAMS.md"),
            text="This mentions AIOS dispatch and MemoryOS routing.",
        )

        self.assertEqual(result.outcome, "aios_relevant")
        self.assertEqual(result.reason, "shared_language_terms")
        self.assertGreaterEqual(len(result.matched_terms), 2)

    def test_borderline_uri_doc_goes_to_operator_review(self) -> None:
        result = self.filter.classify(Path("myworld/uri/README.md"), text="Product readme")

        self.assertEqual(result.outcome, "operator_review")

    def test_review_queue_receipt_stores_path_level_metadata_only(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            result = self.filter.classify(Path("uri/README.md"), root=root, text="Product readme")
            receipt = self.filter.write_review_queue(root, result)

            text = receipt.read_text(encoding="utf-8")
            self.assertIn("source_path", text)
            self.assertIn("uri/README.md", text)
            self.assertNotIn("Product readme", text)

    def test_real_uri_examples_classify_expected_paths(self) -> None:
        northstar = ROOT / "uri" / "docs" / "URI_NORTHSTAR.md"
        route_arch = ROOT / "uri" / "products" / "digital-campus" / "ROUTE_ARCHITECTURE.md"

        self.assertTrue(northstar.exists())
        self.assertTrue(route_arch.exists())
        self.assertEqual(self.filter.classify(northstar, root=ROOT).outcome, "aios_relevant")
        self.assertEqual(self.filter.classify(route_arch, root=ROOT).outcome, "uri_internal")

    def test_doc_scout_reports_uri_filter_counts(self) -> None:
        result = subprocess.run(
            [
                sys.executable,
                SCOUT_SCRIPT.as_posix(),
                "--root",
                ROOT.as_posix(),
                "--limit",
                "80",
                "--json",
            ],
            cwd=ROOT,
            text=True,
            capture_output=True,
            check=False,
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        payload = json.loads(result.stdout)
        counts = payload.get("uri_filter_counts") or {}

        self.assertGreater(counts.get("aios_relevant", 0), 0)
        self.assertGreater(counts.get("uri_internal", 0), 0)
        self.assertGreater(counts.get("operator_review", 0), 0)


if __name__ == "__main__":
    unittest.main()
