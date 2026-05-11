#!/usr/bin/env python3
"""Build a bounded instruction map for the AIOS workspace."""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


SCHEMA_VERSION = "aios.instruction_index.v1"
DEFAULT_ROOT = Path("/home/user/workspaces/jaewon/myworld")
TARGET_NAMES = {"AGENTS.md", "CLAUDE.md", "CODEX.md", "CURRENT.md"}
EXCLUDED_PARTS = {
    ".aios",
    ".ai-runs",
    ".agent",
    ".claude",
    ".conda",
    ".git",
    ".pytest_cache",
    ".runs",
    ".venv",
    "__pycache__",
    "data",
    "exports",
    "logs",
    "node_modules",
    "raw_exports",
    "site-packages",
    "venv",
    "weights",
}


def now_iso() -> str:
    return datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds")


def is_excluded(path: Path) -> bool:
    return any(part in EXCLUDED_PARTS for part in path.parts)


def domain_for(rel_path: str) -> str:
    parts = Path(rel_path).parts
    if not parts:
        return "myworld"
    if parts[0] in {"hivemind", "memoryOS", "CapabilityOS"}:
        return parts[0]
    return "myworld"


def first_heading(lines: list[str]) -> str:
    for line in lines:
        stripped = line.strip()
        if stripped.startswith("#"):
            return stripped.lstrip("#").strip()[:120]
    return ""


def extract_rule_signals(lines: list[str]) -> dict[str, int]:
    patterns = {
        "must": re.compile(r"\b(must|must not|required|never|do not|절대|해야)\b", re.IGNORECASE),
        "scope": re.compile(r"\b(scope|allowed|forbidden|boundary|ownership|repo)\b", re.IGNORECASE),
        "test": re.compile(r"\b(test|pytest|verification|검증)\b", re.IGNORECASE),
        "privacy": re.compile(r"\b(privacy|secret|credential|raw|private|개인)\b", re.IGNORECASE),
        "agent": re.compile(r"\b(agent|codex|claude|operator|worker)\b", re.IGNORECASE),
    }
    counts = {key: 0 for key in patterns}
    for line in lines:
        for key, pattern in patterns.items():
            if pattern.search(line):
                counts[key] += 1
    return {key: value for key, value in counts.items() if value}


def iter_instruction_files(root: Path) -> list[Path]:
    files: list[Path] = []
    for current, dirs, names in os.walk(root):
        current_path = Path(current)
        dirs[:] = sorted(name for name in dirs if not is_excluded(current_path / name))
        for name in sorted(names):
            path = current_path / name
            if is_excluded(path):
                continue
            if name in TARGET_NAMES or (name == "README.md" and path.parent.name in {"docs", "agents"}):
                files.append(path)
    return files


def build_index(root: Path) -> dict[str, Any]:
    entries = []
    for path in iter_instruction_files(root):
        try:
            lines = path.read_text(encoding="utf-8", errors="replace").splitlines()
        except OSError:
            continue
        rel = path.relative_to(root).as_posix()
        entries.append(
            {
                "path": rel,
                "domain": domain_for(rel),
                "kind": path.name,
                "first_heading": first_heading(lines),
                "rule_signals": extract_rule_signals(lines),
                "line_count": len(lines),
            }
        )
    entries.sort(key=lambda row: (row["domain"], row["path"]))
    return {
        "schema_version": SCHEMA_VERSION,
        "generated_at": now_iso(),
        "root": root.as_posix(),
        "counts": {
            "instruction_files": len(entries),
            "by_domain": {
                domain: sum(1 for entry in entries if entry["domain"] == domain)
                for domain in sorted({entry["domain"] for entry in entries})
            },
        },
        "privacy": {
            "content_policy": "metadata only: paths, headings, counts, and signal labels",
            "excluded_parts": sorted(EXCLUDED_PARTS),
        },
        "entries": entries,
    }


def write_markdown(path: Path, index: dict[str, Any]) -> None:
    lines = [
        "# AIOS Instruction Index",
        "",
        f"- generated_at: `{index['generated_at']}`",
        f"- root: `{index['root']}`",
        f"- instruction_files: `{index['counts']['instruction_files']}`",
        f"- by_domain: `{json.dumps(index['counts']['by_domain'], ensure_ascii=False, sort_keys=True)}`",
        "",
        "| Domain | Kind | Path | Heading | Signals |",
        "| --- | --- | --- | --- | --- |",
    ]
    for entry in index["entries"]:
        signals = ",".join(f"{key}:{value}" for key, value in sorted(entry["rule_signals"].items()))
        lines.append(
            f"| {entry['domain']} | {entry['kind']} | `{entry['path']}` | {entry['first_heading']} | `{signals}` |"
        )
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Build the AIOS instruction index")
    parser.add_argument("--root", default=DEFAULT_ROOT.as_posix())
    parser.add_argument("--write", help="write markdown index")
    parser.add_argument("--json", action="store_true")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    root = Path(args.root).resolve()
    if not root.exists():
        print(f"root not found: {root}", file=sys.stderr)
        return 2
    index = build_index(root)
    if args.write:
        write_markdown(Path(args.write), index)
    if args.json or not args.write:
        print(json.dumps(index, ensure_ascii=False, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    sys.exit(main())
