#!/usr/bin/env python3
"""Secret/credential leak scanner for AIOS artifacts.

Enforces DNA invariant #7 (secrets stay out of shared artifacts / dispatch /
prompts), which until now was prose-only. Absorbed from a peer Agent OS
(ironclaw) whose security layer includes credential leak detection — a concrete
pattern AIOS lacked. Complements aios_commit_guard (which catches gitlinks/junk).

Scans staged changes by default (or given paths) for common secret shapes and
reports redacted findings. Exit 1 on any finding, so it is wireable as a git
pre-commit hook alongside the commit guard.

Schema: aios.secret_scan.v1
Usage: python scripts/aios_secret_scan.py [PATHS...] [--json]
"""
from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCHEMA_VERSION = "aios.secret_scan.v1"

# (name, compiled pattern). Patterns target high-confidence secret shapes to keep
# false positives low. Values are redacted in output — never printed in full.
PATTERNS: list[tuple[str, re.Pattern]] = [
    ("aws_access_key", re.compile(r"\bAKIA[0-9A-Z]{16}\b")),
    ("github_token", re.compile(r"\bgh[opsu]_[A-Za-z0-9]{36,}\b")),
    ("openai_anthropic_key", re.compile(r"\bsk-(?:ant-)?[A-Za-z0-9_\-]{20,}\b")),
    ("slack_token", re.compile(r"\bxox[baprs]-[A-Za-z0-9-]{10,}\b")),
    ("google_api_key", re.compile(r"\bAIza[0-9A-Za-z_\-]{35}\b")),
    ("private_key_block", re.compile(r"-----BEGIN (?:RSA |EC |OPENSSH |DSA |PGP )?PRIVATE KEY-----")),
    ("generic_secret_assign", re.compile(
        r"(?i)\b(?:api[_-]?key|secret|token|password|passwd|access[_-]?key)\b\s*[:=]\s*"
        r"['\"]([A-Za-z0-9_\-/+]{16,})['\"]")),
]

# obvious non-secrets that match generic_secret_assign (placeholders, env refs).
# No \b — placeholder words are often joined by underscores (your_api_key_here).
_PLACEHOLDER = re.compile(
    r"(?i)(example|placeholder|your[_-]|xxx+|changeme|redacted|dummy|sample|"
    r"os\.environ|process\.env|getenv|\$\{?[A-Za-z_]+\}?|<[^>]*>)")


def _redact(s: str) -> str:
    return s[:4] + "…" + str(len(s)) + "ch" if len(s) > 6 else "…"


def scan_text(text: str, path: str = "") -> list[dict]:
    findings: list[dict] = []
    for i, line in enumerate(text.splitlines(), 1):
        for name, pat in PATTERNS:
            m = pat.search(line)
            if not m:
                continue
            captured = m.group(1) if m.groups() else m.group(0)
            if name == "generic_secret_assign" and _PLACEHOLDER.search(line):
                continue  # likely a placeholder / env reference, not a real secret
            findings.append({"path": path, "line": i, "rule": name, "match": _redact(captured)})
    return findings


def staged_files(root: Path) -> list[str]:
    r = subprocess.run(
        ["git", "diff", "--cached", "--name-only", "--diff-filter=ACM"],
        cwd=root, text=True, capture_output=True, check=False,
    )
    return [ln for ln in r.stdout.splitlines() if ln.strip()]


def scan_paths(root: Path, paths: list[str]) -> list[dict]:
    findings: list[dict] = []
    for rel in paths:
        fp = root / rel
        if not fp.is_file():
            continue
        try:
            text = fp.read_text(encoding="utf-8", errors="ignore")
        except OSError:
            continue
        findings.extend(scan_text(text, rel))
    return findings


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("paths", nargs="*", help="files to scan (default: staged changes)")
    p.add_argument("--root", type=Path, default=ROOT)
    p.add_argument("--json", action="store_true")
    return p


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    root = args.root.resolve()
    targets = args.paths or staged_files(root)
    findings = scan_paths(root, targets)
    result = {"schema_version": SCHEMA_VERSION, "scanned": len(targets),
              "findings": findings, "passed": not findings}
    if args.json:
        print(json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True))
    else:
        if not findings:
            print(f"secret_scan: clean ({len(targets)} files)")
        for f in findings:
            print(f"  [SECRET] {f['path']}:{f['line']} {f['rule']} ({f['match']})")
    return 0 if result["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
