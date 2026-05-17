#!/usr/bin/env python3
"""Workspace doc scout for the AIOS control plane.

The scout reads documentation files, not raw exports, and emits task signals
that can become AIOS contracts. It is intentionally conservative: it stores
paths, line numbers, headings, and signal labels, not raw document bodies.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import aios_uri_filter


DEFAULT_ROOT = Path("/home/user/workspaces/jaewon")
MARKDOWN_SUFFIXES = {".md", ".mdx"}
EXCLUDED_PARTS = {
    ".aios",
    ".ai-runs",
    ".agent",
    ".claude",
    ".conda",
    ".git",
    ".mypy_cache",
    ".pytest_cache",
    ".runs",
    ".venv",
    "__pycache__",
    "build",
    "checkpoints",
    "data",
    "dist",
    "exports",
    "logs",
    "node_modules",
    "outputs",
    "raw_exports",
    "results",
    "runs",
    "site-packages",
    "venv",
    "weights",
}
EXCLUDED_FILENAMES = {".env", ".env.local", ".envrc", "aios_task_radar.md"}
EXCLUDED_FILENAME_FRAGMENTS = ("secret", "credential")
MAX_HITS_PER_KIND_PER_FILE = 12

SIGNALS: tuple[tuple[str, re.Pattern[str], int], ...] = (
    ("p0", re.compile(r"\bP0\b", re.IGNORECASE), 9),
    ("blocker", re.compile(r"\b(blocker|blocked|blocking)\b", re.IGNORECASE), 8),
    ("stop_condition", re.compile(r"\bstop[_ -]?condition", re.IGNORECASE), 8),
    ("todo", re.compile(r"\b(TODO|FIXME)\b", re.IGNORECASE), 6),
    ("next", re.compile(r"\b(next|다음|해야|해야할|할 일)\b", re.IGNORECASE), 5),
    ("gap", re.compile(r"\b(gap|missing|미완|부족|없음)\b", re.IGNORECASE), 5),
    ("contract", re.compile(r"\b(ASC-\d{4}|contract|smart contract|계약)\b", re.IGNORECASE), 4),
    ("aios", re.compile(r"\bAIOS\b", re.IGNORECASE), 4),
    ("hivemind", re.compile(r"\b(hivemind|hive mind|hive)\b", re.IGNORECASE), 3),
    ("memoryos", re.compile(r"\b(memoryOS|memory os|memory)\b", re.IGNORECASE), 3),
    ("capabilityos", re.compile(r"\b(CapabilityOS|capability os|capability)\b", re.IGNORECASE), 3),
    ("verify", re.compile(r"\b(test|pytest|verification|검증)\b", re.IGNORECASE), 3),
)


@dataclass(frozen=True)
class SignalHit:
    kind: str
    line: int
    weight: int


@dataclass(frozen=True)
class DocItem:
    path: str
    domain: str
    first_heading: str
    score: int
    signals: list[SignalHit]


def now_iso() -> str:
    return datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds")


def is_excluded(path: Path) -> bool:
    lower_name = path.name.lower()
    if lower_name in EXCLUDED_FILENAMES or lower_name.startswith(".env."):
        return True
    if any(fragment in lower_name for fragment in EXCLUDED_FILENAME_FRAGMENTS):
        return True
    return any(part in EXCLUDED_PARTS for part in path.parts)


def iter_doc_paths(root: Path) -> list[Path]:
    paths: list[Path] = []
    for current, dirs, files in os.walk(root):
        current_path = Path(current)
        dirs[:] = sorted(
            name
            for name in dirs
            if not is_excluded(current_path / name)
        )
        for name in sorted(files):
            path = current_path / name
            if is_excluded(path):
                continue
            if path.suffix.lower() in MARKDOWN_SUFFIXES:
                paths.append(path)
    return paths


def domain_for(rel_path: str) -> str:
    parts = Path(rel_path).parts
    if not parts:
        return "unknown"
    if "uri" in parts:
        return "uri"
    if "myworld" in parts:
        idx = parts.index("myworld")
        if idx + 1 < len(parts) and parts[idx + 1] in {"hivemind", "memoryOS", "CapabilityOS"}:
            return parts[idx + 1]
        return "myworld"
    for repo in ("hivemind", "memoryOS", "CapabilityOS"):
        if repo in parts:
            return repo
    return parts[0]


def first_heading(lines: list[str]) -> str:
    for line in lines:
        stripped = line.strip()
        if stripped.startswith("#"):
            return stripped.lstrip("#").strip()[:120]
    return ""


def scan_file(path: Path, root: Path) -> DocItem | None:
    try:
        text = path.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return None
    lines = text.splitlines()
    signals: list[SignalHit] = []
    seen: set[tuple[str, int]] = set()
    per_kind: dict[str, int] = {}
    for idx, line in enumerate(lines, start=1):
        for kind, pattern, weight in SIGNALS:
            if per_kind.get(kind, 0) >= MAX_HITS_PER_KIND_PER_FILE:
                continue
            if pattern.search(line):
                key = (kind, idx)
                if key not in seen:
                    signals.append(SignalHit(kind=kind, line=idx, weight=weight))
                    seen.add(key)
                    per_kind[kind] = per_kind.get(kind, 0) + 1
        if len(signals) >= 80:
            break
    if not signals:
        return None
    rel_path = path.relative_to(root).as_posix()
    score = sum(hit.weight for hit in signals)
    # Prefer docs that are both important and compact enough for contract work.
    if len(lines) <= 240:
        score += 2
    if "/docs/" in f"/{rel_path}":
        score += 3
    return DocItem(
        path=rel_path,
        domain=domain_for(rel_path),
        first_heading=first_heading(lines),
        score=score,
        signals=signals,
    )


def maybe_scan_file(path: Path, root: Path, uri_filter_counts: dict[str, int]) -> DocItem | None:
    result = aios_uri_filter.classify(path, root=root)
    if result.outcome != "not_uri":
        uri_filter_counts[result.outcome] = uri_filter_counts.get(result.outcome, 0) + 1
        if result.outcome == "operator_review":
            aios_uri_filter.write_review_queue(root, result)
            return None
        if result.outcome == "uri_internal":
            return None
    return scan_file(path, root)


def summarize_signals(signals: list[SignalHit]) -> dict[str, Any]:
    counts: dict[str, int] = {}
    line_samples: dict[str, list[int]] = {}
    for hit in signals:
        counts[hit.kind] = counts.get(hit.kind, 0) + 1
        line_samples.setdefault(hit.kind, [])
        if len(line_samples[hit.kind]) < 5:
            line_samples[hit.kind].append(hit.line)
    return {"counts": dict(sorted(counts.items())), "line_samples": line_samples}


def candidate_task(item: DocItem) -> str:
    if item.domain == "uri":
        return "triage Uri-originated AIOS signal before promoting it into a control-plane contract or memory draft"
    if item.domain == "myworld":
        return "promote this control-plane signal into an AIOS contract or readiness gate"
    if item.domain == "memoryOS":
        return "issue a MemoryOS packet for context/provenance/review lifecycle follow-up"
    if item.domain == "hivemind":
        return "issue a Hive Mind packet for execution, harness, or verification follow-up"
    if item.domain == "CapabilityOS":
        return "issue a CapabilityOS packet for routing, capability map, or fallback follow-up"
    return "triage as external workspace context before importing into AIOS"


def existing_contract_dir(root: Path) -> Path | None:
    candidates = [root / "docs" / "contracts", root / "myworld" / "docs" / "contracts"]
    for candidate in candidates:
        if candidate.exists():
            return candidate
    return None


def next_contract_number(root: Path) -> int:
    contract_dir = existing_contract_dir(root)
    if contract_dir is None:
        return 8
    highest = 7
    for path in contract_dir.glob("ASC-*.md"):
        match = re.match(r"ASC-(\d{4})-", path.name)
        if match:
            highest = max(highest, int(match.group(1)))
    return highest + 1


def existing_contract_slugs(root: Path) -> set[str]:
    contract_dir = existing_contract_dir(root)
    if contract_dir is None:
        return set()
    slugs: set[str] = set()
    for path in contract_dir.glob("ASC-*.md"):
        text = path.read_text(encoding="utf-8", errors="replace")
        match = re.search(r"^slug:\s*(.+?)\s*$", text, flags=re.MULTILINE)
        if match:
            slugs.add(match.group(1).strip())
            continue
        parts = path.stem.split("-", 2)
        if len(parts) == 3:
            slugs.add(parts[2])
    return slugs


def proposed_contracts(items: list[DocItem], root: Path) -> list[dict[str, Any]]:
    domains = {item.domain for item in items}
    templates = [
        {
            "slug": "workspace-instruction-index",
            "owner": "myworld",
            "goal": "index AGENTS, CLAUDE, CODEX, CURRENT, and repo ownership rules into a control-plane instruction map",
            "trigger": "multi-agent work needs durable instruction lookup without depending on chat context",
            "depends_on": "ASC-0007",
        },
        {
            "slug": "hive-worklog-gap-cleanup",
            "owner": "hivemind",
            "goal": "turn Hive task-radar worklog and gap signals into a bounded cleanup packet with semantic review evidence",
            "trigger": "Hive worklog and gap docs remain top executable radar candidates",
            "depends_on": "ASC-0007",
        },
        {
            "slug": "capability-gap-triage",
            "owner": "CapabilityOS",
            "goal": "triage task-radar candidates marked hold_for_capability into explicit capability records or operator-review gaps",
            "trigger": "loop policy reports many high-score candidates blocked on capability evidence",
            "depends_on": "ASC-0007",
        },
        {
            "slug": "memoryos-radar-review-queue",
            "owner": "memoryOS",
            "goal": "convert MemoryOS radar holds into review-queue entries with provenance and no raw document bodies",
            "trigger": "MemoryOS TODO and worklog docs remain high-score context candidates",
            "depends_on": "ASC-0007",
        },
    ]
    if "myworld" not in domains:
        templates = [template for template in templates if template["owner"] != "myworld"]
    existing_slugs = existing_contract_slugs(root)
    templates = [template for template in templates if template["slug"] not in existing_slugs]
    next_number = next_contract_number(root)
    contracts = []
    for offset, template in enumerate(templates):
        contracts.append({"contract_id": f"ASC-{next_number + offset:04d}", **template})
    return contracts


def build_report(root: Path, limit: int) -> dict[str, Any]:
    doc_paths = iter_doc_paths(root)
    uri_filter_counts: dict[str, int] = {}
    items = [item for path in doc_paths if (item := maybe_scan_file(path, root, uri_filter_counts))]
    items.sort(key=lambda item: (-item.score, item.path))
    top = items[:limit]
    counts_by_domain: dict[str, int] = {}
    for item in items:
        counts_by_domain[item.domain] = counts_by_domain.get(item.domain, 0) + 1
    return {
        "schema_version": "aios.doc_scout.v1",
        "generated_at": now_iso(),
        "root": root.as_posix(),
        "privacy": {
            "content_policy": "paths, headings, line numbers, and signal labels only; no raw document bodies",
            "excluded_parts": sorted(EXCLUDED_PARTS),
            "excluded_filenames": sorted(EXCLUDED_FILENAMES),
            "excluded_filename_fragments": sorted(EXCLUDED_FILENAME_FRAGMENTS),
        },
        "counts": {
            "documents_scanned": len(doc_paths),
            "documents_with_signals": len(items),
            "by_domain": dict(sorted(counts_by_domain.items())),
        },
        "uri_filter_counts": dict(sorted(uri_filter_counts.items())),
        "top_tasks": [
            {
                "path": item.path,
                "domain": item.domain,
                "score": item.score,
                "first_heading": item.first_heading,
                "signals": summarize_signals(item.signals),
                "candidate_task": candidate_task(item),
            }
            for item in top
        ],
        "proposed_contracts": proposed_contracts(top, root),
    }


def write_markdown(path: Path, report: dict[str, Any]) -> None:
    lines = [
        "# AIOS Task Radar",
        "",
        "Generated by `scripts/aios_doc_scout.py`.",
        "",
        "This file stores doc-scout signals only. It does not store raw export",
        "content, secrets, or full document bodies.",
        "",
        "## Summary",
        "",
        f"- generated_at: `{report['generated_at']}`",
        f"- root: `{report['root']}`",
        f"- documents_scanned: `{report['counts']['documents_scanned']}`",
        f"- documents_with_signals: `{report['counts']['documents_with_signals']}`",
        f"- by_domain: `{json.dumps(report['counts']['by_domain'], ensure_ascii=False, sort_keys=True)}`",
        "",
        "## Top Task Signals",
        "",
        "| Score | Domain | Path | Signals | Candidate Task |",
        "| ---: | --- | --- | --- | --- |",
    ]
    for task in report["top_tasks"]:
        signal_counts = ",".join(f"{key}:{value}" for key, value in task["signals"]["counts"].items())
        lines.append(
            f"| {task['score']} | {task['domain']} | `{task['path']}` | `{signal_counts}` | {task['candidate_task']} |"
        )
    lines.extend(["", "## Proposed Next Contracts", ""])
    for contract in report["proposed_contracts"]:
        lines.extend(
            [
                f"### {contract['contract_id']} — {contract['slug']}",
                "",
                f"- owner: `{contract['owner']}`",
                f"- goal: {contract['goal']}",
                f"- trigger: {contract['trigger']}",
                f"- depends_on: `{contract['depends_on']}`",
                "",
            ]
        )
    lines.extend(
        [
            "## Privacy Boundary",
            "",
            "- excludes dependency/cache/runtime/raw-data directories",
            "- emits file paths, headings, line numbers, and signal labels only",
            "- next contracts must re-read source docs under their own scope before acting",
            "",
        ]
    )
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines), encoding="utf-8")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Scan workspace docs for AIOS task signals")
    parser.add_argument("--root", default=DEFAULT_ROOT.as_posix(), help="workspace root to scan")
    parser.add_argument("--limit", type=int, default=30, help="max top task signals to emit")
    parser.add_argument("--write", help="write markdown task radar to this path")
    parser.add_argument("--json", action="store_true", help="print JSON report")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    root = Path(args.root).resolve()
    if not root.exists():
        print(f"root not found: {root}", file=sys.stderr)
        return 2
    report = build_report(root, max(args.limit, 1))
    if args.write:
        write_markdown(Path(args.write), report)
    if args.json or not args.write:
        print(json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    sys.exit(main())
