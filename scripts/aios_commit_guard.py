#!/usr/bin/env python3
"""Pre-commit guard for the AIOS control plane — catch the commit mistakes that
actually recur, before they land.

Motivated by real session damage: a 0-byte junk file literally named `0` sat
untracked for weeks, and the GenesisOS local-only repo was nearly committed as a
broken gitlink (embedded git repo with no .gitmodules entry). Both are
high-confidence, mechanical to detect, and easy to miss by eye.

Checks the staged set and reports:
- ERROR: a path staged as a gitlink (mode 160000) that has NO matching
  `.gitmodules` entry → a broken submodule on clone. (The GenesisOS case.)
- WARN: a newly-added 0-byte file with a junk-looking name (e.g. `0`, `.1`).

Exit 1 if any ERROR (so this is wireable as a git pre-commit hook later), else 0.
Run on demand: `python scripts/aios_commit_guard.py [--json]`. Non-blocking by
default — it is NOT auto-wired as a blocking hook; the operator opts in.

Schema: aios.commit_guard.v1
"""
from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCHEMA_VERSION = "aios.commit_guard.v1"

_RAW = re.compile(r"^:\d+ (\d+) [0-9a-f]+ [0-9a-f]+ (\w)\t(.+)$")
# Accidental-artifact names. Only ever flagged together with a 0-byte size
# (see analyze), which keeps false positives near zero. Covers redirect numerals
# ("0"), editor/OS temp files, and "untitled" scratch files (gemini review #3).
_JUNK_NAME = re.compile(r"^\.?\d+$|~$|\.(swp|swo|orig|bak|tmp)$", re.I)
_JUNK_EXACT = {".ds_store", "thumbs.db", "untitled", "untitled.md", "untitled.txt"}


def gitmodules_paths(root: Path) -> set[str]:
    text = (root / ".gitmodules").read_text() if (root / ".gitmodules").exists() else ""
    return {m.group(1).strip() for m in re.finditer(r"^\s*path\s*=\s*(.+)$", text, re.M)}


def is_junk_name(path: str) -> bool:
    name = Path(path).name
    return bool(_JUNK_NAME.search(name)) or name.lower() in _JUNK_EXACT


def analyze(entries: list[dict], submodule_paths: set[str]) -> list[dict]:
    """Pure core: classify staged entries into findings. Easy to unit-test.

    entries: [{"dst_mode": "160000", "status": "A", "path": "GenesisOS", "size": 0}]
    """
    findings: list[dict] = []
    for e in entries:
        path = e["path"]
        if e.get("dst_mode") == "160000" and e["path"] not in submodule_paths:
            findings.append(
                {
                    "level": "error",
                    "path": path,
                    "rule": "gitlink_without_submodule",
                    "message": (
                        f"{path} is staged as a gitlink (embedded git repo) but has no "
                        ".gitmodules entry — a broken submodule on clone. Remove it "
                        "(git rm --cached) or register it as a real submodule."
                    ),
                }
            )
        if e["status"] == "A" and e.get("size") == 0 and is_junk_name(path):
            findings.append(
                {
                    "level": "warn",
                    "path": path,
                    "rule": "empty_junk_file",
                    "message": f"{path} is a 0-byte file with a junk-looking name — likely an accidental artifact.",
                }
            )
    return findings


def staged_entries(root: Path) -> list[dict]:
    raw = subprocess.run(
        ["git", "diff", "--cached", "--raw"],
        cwd=root,
        text=True,
        capture_output=True,
        check=False,
    )
    entries: list[dict] = []
    for line in raw.stdout.splitlines():
        m = _RAW.match(line)
        if not m:
            continue
        dst_mode, status, path = m.group(1), m.group(2), m.group(3)
        size = None
        if status == "A" and dst_mode != "160000":
            fp = root / path
            size = fp.stat().st_size if fp.exists() else None
        entries.append({"dst_mode": dst_mode, "status": status, "path": path, "size": size})
    return entries


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=ROOT)
    parser.add_argument("--json", action="store_true")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    root = args.root.resolve()
    findings = analyze(staged_entries(root), gitmodules_paths(root))
    errors = [f for f in findings if f["level"] == "error"]
    result = {
        "schema_version": SCHEMA_VERSION,
        "findings": findings,
        "errors": len(errors),
        "warnings": len(findings) - len(errors),
        "passed": not errors,
    }
    if args.json:
        print(json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True))
    else:
        if not findings:
            print("commit_guard: clean")
        for f in findings:
            print(f"  [{f['level'].upper()}] {f['rule']}: {f['message']}")
    return 0 if result["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
