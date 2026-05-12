#!/usr/bin/env python3
"""Check whether repo agents know the AIOS shared language."""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


SCHEMA_VERSION = "aios.semantic_handshake.v1"
REPOS = ("hivemind", "memoryOS", "CapabilityOS")
REQUIRED_TERMS = (
    "AIOS",
    "AIOS smart contract",
    "dispatch packet",
    "memory draft",
    "capability route",
    "hive execution",
    "stop condition",
    "semantic handshake",
)
REQUIRED_GLOSSARY = "docs/AIOS_SHARED_LANGUAGE.md"


def now_iso() -> str:
    return datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds")


def read_text(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return ""


def term_present(text: str, term: str) -> bool:
    return term.lower() in text.lower()


def assess_repo(root: Path, repo: str) -> dict[str, Any]:
    path = root / repo / "AGENTS.md"
    text = read_text(path)
    missing_terms = [term for term in REQUIRED_TERMS if not term_present(text, term)]
    glossary_refs = (
        REQUIRED_GLOSSARY,
        f"../{REQUIRED_GLOSSARY}",
        f"{root.as_posix()}/{REQUIRED_GLOSSARY}",
    )
    has_glossary_ref = any(ref in text for ref in glossary_refs)
    return {
        "repo": repo,
        "path": path.relative_to(root).as_posix(),
        "exists": path.exists(),
        "has_glossary_ref": has_glossary_ref,
        "missing_terms": missing_terms,
        "status": "pass" if path.exists() and has_glossary_ref and not missing_terms else "fail",
    }


def assess(root: Path) -> dict[str, Any]:
    glossary = root / REQUIRED_GLOSSARY
    glossary_text = read_text(glossary)
    missing_glossary_terms = [term for term in REQUIRED_TERMS if not term_present(glossary_text, term)]
    repos = [assess_repo(root, repo) for repo in REPOS]
    return {
        "schema_version": SCHEMA_VERSION,
        "generated_at": now_iso(),
        "root": root.as_posix(),
        "glossary": {
            "path": REQUIRED_GLOSSARY,
            "exists": glossary.exists(),
            "missing_terms": missing_glossary_terms,
            "status": "pass" if glossary.exists() and not missing_glossary_terms else "fail",
        },
        "repos": repos,
        "status": "pass" if glossary.exists() and not missing_glossary_terms and all(row["status"] == "pass" for row in repos) else "fail",
    }


def write_markdown(path: Path, payload: dict[str, Any]) -> None:
    lines = [
        "# AIOS Semantic Handshake Report",
        "",
        f"- generated_at: `{payload['generated_at']}`",
        f"- status: `{payload['status']}`",
        f"- glossary: `{payload['glossary']['status']}`",
        "",
        "| Repo | Status | Glossary Ref | Missing Terms |",
        "| --- | --- | --- | --- |",
    ]
    for row in payload["repos"]:
        missing = ", ".join(row["missing_terms"]) or "-"
        lines.append(f"| {row['repo']} | {row['status']} | {row['has_glossary_ref']} | {missing} |")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Validate AIOS shared language handshake readiness")
    parser.add_argument("--root", default=Path.cwd().as_posix())
    parser.add_argument("--write", help="write markdown report")
    parser.add_argument("--json", action="store_true")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    root = Path(args.root).resolve()
    payload = assess(root)
    if args.write:
        write_markdown(Path(args.write), payload)
    if args.json or not args.write:
        print(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True))
    return 0 if payload["status"] == "pass" else 1


if __name__ == "__main__":
    sys.exit(main())
