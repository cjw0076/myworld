import json
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from scripts import aios_visual_verify as visual_verify


class AiosVisualVerifyTest(unittest.TestCase):
    def test_passes_when_page_and_screenshot_succeed(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            screenshot = root / ".aios" / "screenshots" / "ok.png"

            def fake_capture(**kwargs):
                screenshot.parent.mkdir(parents=True, exist_ok=True)
                screenshot.write_bytes(b"png")
                return {
                    "status": "passed",
                    "screenshot": ".aios/screenshots/ok.png",
                    "bytes": 3,
                }

            with mock.patch.object(visual_verify, "fetch_page", return_value={"status": "passed", "has_content": True}), mock.patch.object(
                visual_verify, "capture_screenshot", side_effect=fake_capture
            ):
                receipt = visual_verify.run_visual_verification(root, url="http://127.0.0.1:1/", screenshot=screenshot)

            self.assertEqual(receipt["schema_version"], "aios.visual_verification.v1")
            self.assertEqual(receipt["status"], "passed")
            self.assertEqual(receipt["screenshot_path"], ".aios/screenshots/ok.png")
            self.assertTrue((root / receipt["receipt_path"]).exists())
            saved = json.loads((root / receipt["receipt_path"]).read_text(encoding="utf-8"))
            self.assertEqual(saved["verification_id"], receipt["verification_id"])

    def test_degrades_when_page_loads_but_browser_times_out(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            with mock.patch.object(visual_verify, "fetch_page", return_value={"status": "passed", "has_content": True}), mock.patch.object(
                visual_verify,
                "capture_screenshot",
                return_value={"status": "failed", "reason": "browser_timeout", "timeout_seconds": 1},
            ):
                receipt = visual_verify.run_visual_verification(root, url="http://127.0.0.1:1/")

            self.assertEqual(receipt["status"], "degraded")
            self.assertIn("browser_visual_evidence_missing", receipt["stop_conditions"])
            self.assertIn("browser_verification_timeout", receipt["stop_conditions"])

    def test_require_screenshot_turns_missing_visual_evidence_into_failure(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            with mock.patch.object(visual_verify, "fetch_page", return_value={"status": "passed", "has_content": True}), mock.patch.object(
                visual_verify,
                "capture_screenshot",
                return_value={"status": "failed", "reason": "browser_unavailable"},
            ):
                receipt = visual_verify.run_visual_verification(
                    root,
                    url="http://127.0.0.1:1/",
                    require_screenshot=True,
                )

            self.assertEqual(receipt["status"], "failed")
            self.assertIn("browser_visual_evidence_missing", receipt["stop_conditions"])

    def test_screenshot_capture_falls_back_after_primary_timeout(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            screenshot = root / ".aios" / "screenshots" / "fallback.png"

            def fake_resolve(browser: str) -> str:
                return f"/bin/{browser}"

            def fake_capture(**kwargs):
                if kwargs["browser"] == "firefox":
                    return {"status": "failed", "reason": "browser_timeout", "browser": kwargs["browser_path"]}
                screenshot.parent.mkdir(parents=True, exist_ok=True)
                screenshot.write_bytes(b"png")
                return {
                    "status": "passed",
                    "browser": kwargs["browser_path"],
                    "screenshot": ".aios/screenshots/fallback.png",
                    "bytes": 3,
                }

            with mock.patch.object(visual_verify, "resolve_browser_path", side_effect=fake_resolve), mock.patch.object(
                visual_verify, "_capture_screenshot_once", side_effect=fake_capture
            ):
                shot = visual_verify.capture_screenshot(
                    root=root,
                    url="http://127.0.0.1:1/",
                    screenshot=screenshot,
                    browser="firefox",
                    fallback_browsers=("chromium",),
                    timeout=1,
                    window_size="390,844",
                )

            self.assertEqual(shot["status"], "passed")
            self.assertTrue(shot["fallback_used"])
            self.assertEqual(shot["primary_browser"], "firefox")
            self.assertEqual(len(shot["attempts"]), 2)
            self.assertEqual(shot["attempts"][0]["reason"], "browser_timeout")
            self.assertEqual(shot["browser"], "/bin/chromium")
            json.dumps(shot)

    def test_all_browser_attempts_failed_records_fallback_exhausted(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            with mock.patch.object(visual_verify, "fetch_page", return_value={"status": "passed", "has_content": True}), mock.patch.object(
                visual_verify, "resolve_browser_path", return_value=""
            ):
                receipt = visual_verify.run_visual_verification(
                    root,
                    url="http://127.0.0.1:1/",
                    fallback_browsers=("chromium",),
                    require_screenshot=True,
                )

            self.assertEqual(receipt["status"], "failed")
            self.assertEqual(receipt["checks"]["screenshot"]["reason"], "all_browser_attempts_failed")
            self.assertIn("browser_fallback_exhausted", receipt["stop_conditions"])

    def test_suspiciously_small_screenshot_is_not_passed(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            with mock.patch.object(visual_verify, "fetch_page", return_value={"status": "passed", "has_content": True}), mock.patch.object(
                visual_verify,
                "capture_screenshot",
                return_value={
                    "status": "failed",
                    "reason": "screenshot_suspiciously_small",
                    "screenshot": ".aios/screenshots/blank.png",
                    "bytes": 7130,
                    "min_screenshot_bytes": 12000,
                },
            ):
                receipt = visual_verify.run_visual_verification(root, url="http://127.0.0.1:1/")

            self.assertEqual(receipt["status"], "degraded")
            self.assertIn("browser_visual_evidence_missing", receipt["stop_conditions"])
            self.assertIn("browser_visual_evidence_suspicious", receipt["stop_conditions"])

    def test_suspicious_attempt_inside_fallback_exhaustion_is_recorded(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            with mock.patch.object(visual_verify, "fetch_page", return_value={"status": "passed", "has_content": True}), mock.patch.object(
                visual_verify,
                "capture_screenshot",
                return_value={
                    "status": "failed",
                    "reason": "all_browser_attempts_failed",
                    "attempts": [
                        {"status": "failed", "reason": "browser_timeout"},
                        {"status": "failed", "reason": "screenshot_suspiciously_small", "bytes": 7130},
                    ],
                },
            ):
                receipt = visual_verify.run_visual_verification(root, url="http://127.0.0.1:1/")

            self.assertEqual(receipt["status"], "degraded")
            self.assertIn("browser_fallback_exhausted", receipt["stop_conditions"])
            self.assertIn("browser_visual_evidence_suspicious", receipt["stop_conditions"])


if __name__ == "__main__":
    unittest.main()
