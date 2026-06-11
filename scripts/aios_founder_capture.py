#!/usr/bin/env python3
"""Extract founder directives into a MemoryOS-ingestible payload."""

from __future__ import annotations

import argparse
import json
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


SCHEMA_VERSION = "aios.founder_directive_memory.v1"
FOUNDER_MARKERS = ("founder", "Founder", "재원")
QUOTE_RE = re.compile(r"[\"“”']([^\"“”']{4,240})[\"“”']")
ASC_RE = re.compile(r"\bASC-\d{4}\b")


def now_iso() -> str:
    return datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds")


def stable_directive_id(text: str, source: str) -> str:
    import hashlib

    return "founder_" + hashlib.sha256(f"{text}\n{source}".encode("utf-8")).hexdigest()[:16]


def classify(text: str) -> str:
    lower = text.lower()
    if any(term in lower for term in ("government", "sovereign", "os", "aios", "dna", "constitution", "정부")):
        return "vision"
    if any(term in lower for term in ("scope", "repo", "boundary", "직접", "루트")):
        return "scope"
    if any(term in lower for term in ("불편", "creativity", "창의", "감옥", "discomfort")):
        return "discomfort"
    if any(term in lower for term in ("operator", "founder", "역할", "대신", "감독")):
        return "role"
    if any(term in lower for term in ("private", "privacy", "secret", "pin", "credential", "개인")):
        return "privacy"
    if any(term in lower for term in ("진행", "go", "계속", "멈추지")):
        return "escalation"
    return "other"


def clean_candidate(value: str) -> str:
    text = value.strip().strip("`").strip()
    text = re.sub(r"\s+", " ", text)
    prefixes = (
        "founder directive",
        "founder request",
        "founder turn",
        "founder asked",
        "founder explicitly",
        "per founder",
        "origin",
    )
    lowered = text.lower()
    for prefix in prefixes:
        if lowered.startswith(prefix):
            _, _, after = text.partition(":")
            if after.strip():
                text = after.strip()
            break
    return text


def useful_directive(text: str) -> bool:
    if len(text.strip()) < 4:
        return False
    lowered = text.lower()
    if text.startswith("2026-") or "claude@myworld" in lowered or "codex@myworld" in lowered:
        return False
    if re.fullmatch(r"\d{4}-\d{2}-\d{2}.*", text):
        return False
    return True


def extract_from_line(line: str) -> list[str]:
    if not any(marker in line for marker in FOUNDER_MARKERS):
        return []
    stripped = line.strip()
    if stripped.startswith("accepted:"):
        return []
    quoted = [clean_candidate(match.group(1)) for match in QUOTE_RE.finditer(line)]
    if quoted:
        return [item for item in quoted if useful_directive(item)]
    value = stripped
    lowered = value.lower()
    suffix_markers = (
        "per founder directive that ",
        "founder directive that ",
        "per founder request to ",
        "founder asked ",
        "founder explicitly ",
        "founder request ",
        "founder turn ",
        "founder directive ",
    )
    for marker in suffix_markers:
        if marker in lowered:
            start = lowered.index(marker) + len(marker)
            value = value[start:]
            break
    else:
        for prefix in ("acceptance_authority:", "origin:", "- **"):
            if prefix in value:
                value = value.split(prefix, 1)[1]
    candidate = clean_candidate(value)
    return [candidate] if useful_directive(candidate) else []


def source_contract_id(path: Path, text: str) -> str | None:
    match = ASC_RE.search(path.name) or ASC_RE.search(text[:300])
    return match.group(0) if match else None


def scan_file(path: Path, root: Path) -> list[dict[str, Any]]:
    try:
        lines = path.read_text(encoding="utf-8", errors="replace").splitlines()
    except OSError:
        return []
    text_head = "\n".join(lines[:20])
    contract_id = source_contract_id(path, text_head)
    rel = path.relative_to(root).as_posix() if path.is_relative_to(root) else path.as_posix()
    rows: list[dict[str, Any]] = []
    for index, line in enumerate(lines, start=1):
        stripped = line.strip()
        if ("/docs/contracts/" in f"/{rel}" or "/docs/_history/contracts/" in f"/{rel}") and not stripped.startswith(
            ("accepted:", "acceptance_authority:", "origin:", "proposed_by:")
        ):
            continue
        for directive_text in extract_from_line(line):
            if len(directive_text) > 260:
                directive_text = directive_text[:257].rstrip() + "..."
            cited = sorted(set(ASC_RE.findall(line) + ([contract_id] if contract_id else [])))
            source_ref = f"{rel}:{index}"
            rows.append(
                {
                    "directive_id": stable_directive_id(directive_text, source_ref),
                    "directive_text": directive_text,
                    "reframe_class": classify(directive_text),
                    "cited_in_contracts": cited,
                    "captured_at": now_iso(),
                    "source_path": rel,
                    "raw_refs": [source_ref],
                }
            )
    return rows


def default_sources(root: Path) -> list[Path]:
    paths: list[Path] = []
    # operator sessions were quarantined to docs/_history/sessions (kernel audit);
    # read both locations so capture keeps working across the move.
    sessions = sorted(
        list((root / "docs" / "operator_sessions").glob("*.md"))
        + list((root / "docs" / "_history" / "sessions").glob("*.md"))
    )
    paths.extend(sessions[-3:])
    # founder directives live mostly in the quarantined corpus — mine both the
    # active working set and docs/_history/contracts (capture is a corpus tool).
    paths.extend(sorted(
        list((root / "docs" / "contracts").glob("ASC-*.md"))
        + list((root / "docs" / "_history" / "contracts").glob("ASC-*.md"))
    ))
    return paths


def dedupe(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    by_key: dict[tuple[str, str], dict[str, Any]] = {}
    for row in rows:
        key = (row["directive_text"], row["source_path"])
        existing = by_key.get(key)
        if not existing:
            by_key[key] = row
            continue
        existing["raw_refs"] = sorted(set(existing.get("raw_refs", []) + row.get("raw_refs", [])))
        existing["cited_in_contracts"] = sorted(set(existing.get("cited_in_contracts", []) + row.get("cited_in_contracts", [])))
    return sorted(by_key.values(), key=lambda item: (item["source_path"], item["raw_refs"][0], item["directive_text"]))


def build_payload(root: Path, sources: list[Path], explicit_text: str | None = None) -> dict[str, Any]:
    rows: list[dict[str, Any]] = []
    if explicit_text:
        rows.append(
            {
                "directive_id": stable_directive_id(explicit_text, "explicit"),
                "directive_text": explicit_text,
                "reframe_class": classify(explicit_text),
                "cited_in_contracts": [],
                "captured_at": now_iso(),
                "source_path": "explicit",
                "raw_refs": ["explicit"],
            }
        )
    for path in sources:
        rows.extend(scan_file(path.resolve(), root))
    return {
        "schema_version": SCHEMA_VERSION,
        "captured_at": now_iso(),
        "source_count": len(sources) + (1 if explicit_text else 0),
        "directives": dedupe(rows),
    }


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=Path.cwd())
    parser.add_argument("--source", action="append", type=Path, help="source markdown path; defaults to operator sessions and contracts")
    parser.add_argument("--text", help="explicit founder turn text to capture")
    parser.add_argument("--write")
    parser.add_argument("--json", action="store_true")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    root = args.root.resolve()
    sources = [((root / path).resolve() if not path.is_absolute() else path.resolve()) for path in (args.source or [])]
    if not sources and not args.text:
        sources = default_sources(root)
    payload = build_payload(root, sources, args.text)
    if args.write:
        out = root / args.write
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    if args.json or not args.write:
        print(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
