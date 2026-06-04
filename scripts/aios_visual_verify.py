#!/usr/bin/env python3
"""Bounded visual verification for local AIOS web surfaces.

This script is intentionally small and dependency-free. It verifies that a URL
loads, attempts a headless browser screenshot, and always writes a receipt so a
failed or hanging browser check becomes evidence instead of a stuck operator
turn.
"""

from __future__ import annotations

import argparse
import json
import os
import shutil
import signal
import subprocess
import sys
import tempfile
import time
import urllib.error
import urllib.request
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


SCHEMA_VERSION = "aios.visual_verification.v1"
DEFAULT_BROWSER = "firefox"
DEFAULT_FALLBACK_BROWSERS = ("chromium", "google-chrome", "chrome", "ms-playwright-chromium")
DEFAULT_WINDOW = "1440,1100"
DEFAULT_TIMEOUT = 15
DEFAULT_MIN_SCREENSHOT_BYTES = 12_000
RECEIPT_ROOT = Path(".aios/visual_verification")
SCREENSHOT_ROOT = Path(".aios/screenshots")


def now_iso() -> str:
    return datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds")


def relative_ref(root: Path, path: Path) -> str:
    try:
        return path.resolve().relative_to(root.resolve()).as_posix()
    except ValueError:
        return path.as_posix()


def fetch_page(url: str, *, timeout: int) -> dict[str, Any]:
    started = time.monotonic()
    try:
        request = urllib.request.Request(url, headers={"User-Agent": "AIOS visual verifier"})
        with urllib.request.urlopen(request, timeout=timeout) as response:
            body = response.read(250_000)
            text = body.decode("utf-8", errors="replace")
            return {
                "status": "passed" if text.strip() else "failed",
                "status_code": getattr(response, "status", None),
                "bytes_read": len(body),
                "has_content": bool(text.strip()),
                "elapsed_seconds": round(time.monotonic() - started, 3),
            }
    except urllib.error.HTTPError as exc:
        return {
            "status": "failed",
            "reason": "http_error",
            "status_code": exc.code,
            "elapsed_seconds": round(time.monotonic() - started, 3),
        }
    except Exception as exc:
        return {
            "status": "failed",
            "reason": exc.__class__.__name__,
            "error": str(exc),
            "elapsed_seconds": round(time.monotonic() - started, 3),
        }


def browser_command(browser_path: str, profile: Path, screenshot: Path, url: str, window_size: str) -> list[str]:
    name = Path(browser_path).name.lower()
    if "firefox" in name:
        return [
            browser_path,
            "--headless",
            "--new-instance",
            "--profile",
            profile.as_posix(),
            "--window-size",
            window_size,
            "--screenshot",
            screenshot.as_posix(),
            url,
        ]
    if "chrom" in name or "chrome" in name:
        width, _, height = window_size.partition(",")
        size = f"{width or '1440'},{height or '1100'}"
        return [
            browser_path,
            "--headless=new",
            "--disable-gpu",
            "--no-sandbox",
            f"--window-size={size}",
            f"--screenshot={screenshot.as_posix()}",
            url,
        ]
    return [browser_path, "--headless", "--screenshot", screenshot.as_posix(), url]


def _terminate_process_group(proc: subprocess.Popen[str]) -> None:
    try:
        os.killpg(proc.pid, signal.SIGTERM)
    except Exception:
        proc.terminate()
    try:
        proc.wait(timeout=2)
    except subprocess.TimeoutExpired:
        try:
            os.killpg(proc.pid, signal.SIGKILL)
        except Exception:
            proc.kill()
        proc.wait(timeout=2)


def _playwright_chromium_paths() -> list[Path]:
    cache = Path.home() / ".cache" / "ms-playwright"
    if not cache.exists():
        return []
    candidates = []
    for pattern in (
        "chromium_headless_shell-*/chrome-headless-shell-linux64/chrome-headless-shell",
        "chromium-*/chrome-linux/chrome",
    ):
        candidates.extend(sorted(cache.glob(pattern), reverse=True))
    return [path for path in candidates if path.exists()]


def resolve_browser_path(browser: str) -> str:
    if browser == "ms-playwright-chromium":
        paths = _playwright_chromium_paths()
        return paths[0].as_posix() if paths else ""
    return shutil.which(browser) or (browser if Path(browser).exists() else "")


def _capture_screenshot_once(
    *,
    root: Path,
    url: str,
    screenshot: Path,
    browser: str,
    browser_path: str,
    timeout: int,
    window_size: str,
    min_screenshot_bytes: int,
) -> dict[str, Any]:
    if not browser_path:
        return {"status": "failed", "reason": "browser_unavailable", "browser": browser}
    screenshot.parent.mkdir(parents=True, exist_ok=True)
    started = time.monotonic()
    with tempfile.TemporaryDirectory(prefix="aios-visual-profile-") as profile_dir:
        command = browser_command(browser_path, Path(profile_dir), screenshot, url, window_size)
        proc = subprocess.Popen(
            command,
            cwd=root,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            start_new_session=True,
        )
        try:
            stdout, stderr = proc.communicate(timeout=timeout)
        except subprocess.TimeoutExpired:
            _terminate_process_group(proc)
            return {
                "status": "failed",
                "reason": "browser_timeout",
                "browser": browser_path,
                "command": command,
                "timeout_seconds": timeout,
                "elapsed_seconds": round(time.monotonic() - started, 3),
            }
    exists = screenshot.exists() and screenshot.stat().st_size > 0
    screenshot_bytes = screenshot.stat().st_size if exists else 0
    suspiciously_small = proc.returncode == 0 and exists and screenshot_bytes < min_screenshot_bytes
    return {
        "status": "passed" if proc.returncode == 0 and exists and not suspiciously_small else "failed",
        "reason": None if proc.returncode == 0 and exists and not suspiciously_small else ("screenshot_suspiciously_small" if suspiciously_small else "screenshot_missing"),
        "browser": browser_path,
        "command": command,
        "returncode": proc.returncode,
        "stdout": (stdout or "")[-2000:],
        "stderr": (stderr or "")[-2000:],
        "screenshot": relative_ref(root, screenshot) if exists else None,
        "bytes": screenshot_bytes,
        "min_screenshot_bytes": min_screenshot_bytes,
        "elapsed_seconds": round(time.monotonic() - started, 3),
    }


def capture_screenshot(
    *,
    root: Path,
    url: str,
    screenshot: Path,
    browser: str,
    timeout: int,
    window_size: str,
    min_screenshot_bytes: int = DEFAULT_MIN_SCREENSHOT_BYTES,
    fallback_browsers: tuple[str, ...] = DEFAULT_FALLBACK_BROWSERS,
) -> dict[str, Any]:
    attempts = []
    tried_paths = set()
    browser_order = [browser, *[candidate for candidate in fallback_browsers if candidate != browser]]
    for candidate in browser_order:
        browser_path = resolve_browser_path(candidate)
        if browser_path and browser_path in tried_paths:
            continue
        if browser_path:
            tried_paths.add(browser_path)
        shot = _capture_screenshot_once(
            root=root,
            url=url,
            screenshot=screenshot,
            browser=candidate,
            browser_path=browser_path,
            timeout=timeout,
            window_size=window_size,
            min_screenshot_bytes=min_screenshot_bytes,
        )
        attempts.append(shot)
        if shot.get("status") == "passed":
            passed = dict(shot)
            passed["attempts"] = [dict(attempt) for attempt in attempts]
            if len(attempts) > 1:
                passed["fallback_used"] = True
                passed["primary_browser"] = browser
            return passed
        if shot.get("reason") not in {"browser_timeout", "browser_unavailable", "screenshot_missing", "screenshot_suspiciously_small"}:
            break

    final = attempts[-1] if attempts else {"status": "failed", "reason": "browser_unavailable", "browser": browser}
    final = dict(final)
    final["attempts"] = attempts
    if len(attempts) > 1:
        final["reason"] = "all_browser_attempts_failed"
        final["primary_reason"] = attempts[0].get("reason")
    return final


def final_status(page: dict[str, Any], shot: dict[str, Any], *, require_screenshot: bool) -> str:
    if page.get("status") != "passed":
        return "failed"
    if shot.get("status") == "passed":
        return "passed"
    return "failed" if require_screenshot else "degraded"


def run_visual_verification(
    root: Path,
    *,
    url: str,
    screenshot: Path | None = None,
    browser: str = DEFAULT_BROWSER,
    fallback_browsers: tuple[str, ...] = DEFAULT_FALLBACK_BROWSERS,
    timeout: int = DEFAULT_TIMEOUT,
    window_size: str = DEFAULT_WINDOW,
    min_screenshot_bytes: int = DEFAULT_MIN_SCREENSHOT_BYTES,
    require_screenshot: bool = False,
) -> dict[str, Any]:
    root = root.resolve()
    verification_id = "vis-" + uuid.uuid4().hex[:12]
    screenshot_path = screenshot or (root / SCREENSHOT_ROOT / f"{verification_id}.png")
    if not screenshot_path.is_absolute():
        screenshot_path = root / screenshot_path
    receipt_dir = root / RECEIPT_ROOT / verification_id
    receipt_dir.mkdir(parents=True, exist_ok=True)

    page = fetch_page(url, timeout=timeout)
    shot = capture_screenshot(
        root=root,
        url=url,
        screenshot=screenshot_path,
        browser=browser,
        fallback_browsers=fallback_browsers,
        timeout=timeout,
        window_size=window_size,
        min_screenshot_bytes=min_screenshot_bytes,
    )
    status = final_status(page, shot, require_screenshot=require_screenshot)
    stop_conditions = []
    if page.get("status") != "passed":
        stop_conditions.append("page_load_failed")
    if shot.get("status") != "passed":
        stop_conditions.append("browser_visual_evidence_missing")
        if shot.get("reason") == "browser_timeout":
            stop_conditions.append("browser_verification_timeout")
        if shot.get("reason") == "all_browser_attempts_failed":
            stop_conditions.append("browser_fallback_exhausted")
        attempt_reasons = [attempt.get("reason") for attempt in shot.get("attempts", []) if isinstance(attempt, dict)]
        if (
            shot.get("reason") == "screenshot_suspiciously_small"
            or shot.get("primary_reason") == "screenshot_suspiciously_small"
            or "screenshot_suspiciously_small" in attempt_reasons
        ):
            stop_conditions.append("browser_visual_evidence_suspicious")

    receipt = {
        "schema_version": SCHEMA_VERSION,
        "verification_id": verification_id,
        "created_at": now_iso(),
        "root": root.as_posix(),
        "url": url,
        "status": status,
        "require_screenshot": require_screenshot,
        "checks": {
            "page_load": page,
            "screenshot": shot,
        },
        "screenshot_path": shot.get("screenshot"),
        "receipt_path": relative_ref(root, receipt_dir / "receipt.json"),
        "stop_conditions": stop_conditions,
    }
    (receipt_dir / "receipt.json").write_text(json.dumps(receipt, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    return receipt


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Run bounded AIOS visual verification.")
    parser.add_argument("url", help="URL to verify")
    parser.add_argument("--root", default=".", help="AIOS workspace root")
    parser.add_argument("--browser", default=DEFAULT_BROWSER, help="Browser executable name/path")
    parser.add_argument(
        "--fallback-browser",
        action="append",
        dest="fallback_browsers",
        help="Fallback browser executable/name. Repeatable. Defaults to Chromium/Chrome and Playwright cached Chromium.",
    )
    parser.add_argument("--no-browser-fallback", action="store_true", help="Only try --browser.")
    parser.add_argument("--timeout", type=int, default=DEFAULT_TIMEOUT, help="Per-step timeout in seconds")
    parser.add_argument("--window-size", default=DEFAULT_WINDOW, help="Screenshot size, e.g. 1440,1100")
    parser.add_argument(
        "--min-screenshot-bytes",
        type=int,
        default=DEFAULT_MIN_SCREENSHOT_BYTES,
        help="Treat smaller successful screenshots as suspicious visual evidence.",
    )
    parser.add_argument("--screenshot", help="Screenshot path; defaults under .aios/screenshots/")
    parser.add_argument("--require-screenshot", action="store_true", help="Exit non-zero if screenshot capture fails")
    parser.add_argument("--allow-degraded", action="store_true", help="Exit zero when page load passed but screenshot failed")
    parser.add_argument("--json", action="store_true", help="Print JSON receipt")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    root = Path(args.root).resolve()
    receipt = run_visual_verification(
        root,
        url=args.url,
        screenshot=Path(args.screenshot) if args.screenshot else None,
        browser=args.browser,
        fallback_browsers=() if args.no_browser_fallback else tuple(args.fallback_browsers or DEFAULT_FALLBACK_BROWSERS),
        timeout=max(1, args.timeout),
        window_size=args.window_size,
        min_screenshot_bytes=max(1, args.min_screenshot_bytes),
        require_screenshot=args.require_screenshot,
    )
    if args.json:
        print(json.dumps(receipt, indent=2, ensure_ascii=False))
    else:
        print(f"{receipt['status']} {receipt['receipt_path']}")
    if receipt["status"] == "passed":
        return 0
    if receipt["status"] == "degraded" and args.allow_degraded:
        return 0
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
