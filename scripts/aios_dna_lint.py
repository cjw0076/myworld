#!/usr/bin/env python3
"""Check whether an AIOS contract cites required DNA invariants."""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Any


CHILD_REPOS = {"hivemind", "memoryOS", "CapabilityOS", "GenesisOS"}
AUTHORITY_TERMS = (
    "authority",
    "execution",
    "execute",
    "dispatch",
    "provider",
    "capability",
    "external action",
    "override",
    "private",
    "credential",
    "memory auto",
    "auto-write",
)


def parse_frontmatter(text: str) -> tuple[dict[str, str], str]:
    if not text.startswith("---\n"):
        return {}, text
    end = text.find("\n---\n", 4)
    if end == -1:
        return {}, text
    data: dict[str, str] = {}
    for raw in text[4:end].splitlines():
        key, sep, value = raw.partition(":")
        if sep:
            data[key.strip()] = value.strip().strip('"')
    return data, text[end + 5 :]


def section(body: str, heading: str) -> str:
    pattern = re.compile(rf"^##\s+{re.escape(heading)}\s*$", flags=re.MULTILINE)
    match = pattern.search(body)
    if not match:
        return ""
    rest = body[match.end() :]
    next_heading = re.search(r"^##\s+", rest, flags=re.MULTILINE)
    return rest[: next_heading.start()] if next_heading else rest


def scope_repos(scope: str) -> set[str]:
    repos: set[str] = set()
    lines = scope.splitlines()
    capture = False
    for raw in lines:
        stripped = raw.strip()
        lower = stripped.lower()
        if lower.startswith("repos"):
            capture = True
            for repo in CHILD_REPOS | {"myworld"}:
                if re.search(rf"\b{re.escape(repo)}\b", stripped):
                    repos.add(repo)
            continue
        if capture and not stripped:
            continue
        if capture and (lower.endswith("files:") or stripped.startswith("forbidden_files")):
            capture = False
        if capture:
            for repo in CHILD_REPOS | {"myworld"}:
                if re.search(rf"\b{re.escape(repo)}\b", stripped):
                    repos.add(repo)
    return repos


def dna_citations(text: str) -> list[int]:
    found: set[int] = set()
    patterns = (
        r"\bInvariant\s+([1-8])\b",
        r"\bDNA\s+Invariant\s*([1-8])\b",
    )
    for line in text.splitlines():
        if "ASC-0084" in line and "AIOS_DNA" not in line:
            continue
        for pattern in patterns:
            for match in re.finditer(pattern, line, flags=re.IGNORECASE):
                found.add(int(match.group(1)))
    return sorted(found)


def requires_dna(frontmatter: dict[str, str], body: str) -> tuple[bool, list[str]]:
    scope = section(body, "Scope")
    repos = scope_repos(scope)
    reasons: list[str] = []
    if repos - {"myworld"}:
        reasons.append("cross_repo_scope")
    lower = "\n".join([frontmatter.get("goal", ""), body]).lower()
    for term in AUTHORITY_TERMS:
        if term in lower:
            reasons.append(f"authority_or_execution_term:{term}")
            break
    return bool(reasons), reasons


def lint_contract(path: Path) -> dict[str, Any]:
    text = path.read_text(encoding="utf-8")
    frontmatter, body = parse_frontmatter(text)
    required, reasons = requires_dna(frontmatter, body)
    citations = dna_citations(text)
    return {
        "schema_version": "aios.dna_lint.v1",
        "path": path.as_posix(),
        "contract_id": frontmatter.get("contract_id") or path.stem.split("-", 1)[0],
        "citations": citations,
        "required": required,
        "missing": required and not citations,
        "reasons": reasons,
    }


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("contract", type=Path)
    parser.add_argument("--json", action="store_true")
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        result = lint_contract(args.contract)
    except OSError as exc:
        print(str(exc), file=sys.stderr)
        return 2
    if args.json:
        print(json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True))
    else:
        status = "missing" if result["missing"] else "ok"
        print(f"{result['contract_id']} dna_lint={status} citations={result['citations']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
