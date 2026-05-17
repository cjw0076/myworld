#!/usr/bin/env python3
"""Audit whether accepted MemoryOS records are retrievable by context build."""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_MEMORYOS_DIR = ROOT / "memoryOS"
SCHEMA_VERSION = "aios.memory_retrieval_audit.v1"


@dataclass(frozen=True)
class RetrievalCase:
    query: str
    expected_ids: tuple[str, ...]
    project: str = "AIOS"


DEFAULT_CASES: tuple[RetrievalCase, ...] = (
    RetrievalCase(
        "AIOS완성 공진화 memoryOS capabilityOS hive mind founder directive",
        ("mem_70c8edbf4c5c9c7b",),
    ),
    RetrievalCase(
        "founder role delegated living organism 작업방식 memoryOS",
        ("mem_7a13c1fc3880df9c", "mem_3d34968d34418b03"),
    ),
    RetrievalCase(
        "사용자 로그 작업방식 user 행동 패턴 few shot",
        ("mem_fdf38e3f47d1aed4",),
    ),
    RetrievalCase(
        "Claude CLI Codex local LLM provider 흡수",
        ("mem_001f6d5191fb8e51", "mem_1f18cea463eed9fd"),
    ),
)


def parse_case(value: str) -> RetrievalCase:
    if "::" not in value:
        raise argparse.ArgumentTypeError("case must use QUERY::EXPECTED_ID[,EXPECTED_ID]")
    query, ids_raw = value.split("::", 1)
    expected_ids = tuple(item.strip() for item in ids_raw.split(",") if item.strip())
    if not query.strip() or not expected_ids:
        raise argparse.ArgumentTypeError("case must include non-empty query and expected ids")
    return RetrievalCase(query.strip(), expected_ids)


def selected_ids(pack: dict[str, Any]) -> list[str]:
    ids: list[str] = []
    for key in ("decisions", "constraints", "open_questions", "recent_actions", "other"):
        for item in pack.get(key) or []:
            if item.get("id"):
                ids.append(str(item["id"]))
    return ids


def excluded_reasons(pack: dict[str, Any]) -> dict[str, str]:
    reasons: dict[str, str] = {}
    for item in pack.get("excluded_candidates") or []:
        target_id = item.get("target_id")
        reason = item.get("exclusion_reason")
        if target_id and reason:
            reasons[str(target_id)] = str(reason)
    return reasons


def diagnose_drop(pack: dict[str, Any], expected_ids: tuple[str, ...], selected: list[str]) -> str:
    if any(expected_id in selected for expected_id in expected_ids):
        return "selected"
    if not pack.get("total_accepted"):
        return "no_accepted_memory"
    reasons = excluded_reasons(pack)
    matched_reasons = sorted({reasons[expected_id] for expected_id in expected_ids if expected_id in reasons})
    if matched_reasons:
        return "excluded:" + ",".join(matched_reasons)
    if pack.get("context_items", 0) == 0:
        return "empty_context_pool"
    return "not_selected"


def run_context_case(memoryos_dir: Path, memory_root: Path, case: RetrievalCase) -> dict[str, Any]:
    command = [
        sys.executable,
        "-m",
        "memoryos.cli",
        "--root",
        memory_root.as_posix(),
        "context",
        "build",
        "--task",
        case.query,
        "--for",
        "hive",
        "--project",
        case.project,
        "--json",
        "--explain",
        "--include-excluded",
    ]
    result = subprocess.run(
        command,
        cwd=memoryos_dir,
        text=True,
        capture_output=True,
        check=False,
    )
    if result.returncode != 0:
        return {
            "query": case.query,
            "expected_ids": list(case.expected_ids),
            "status": "error",
            "hit": False,
            "selected_ids": [],
            "drop_at_stage": "context_build_failed",
            "stderr": result.stderr.strip()[:1000],
        }
    try:
        pack = json.loads(result.stdout)
    except json.JSONDecodeError as exc:
        return {
            "query": case.query,
            "expected_ids": list(case.expected_ids),
            "status": "error",
            "hit": False,
            "selected_ids": [],
            "drop_at_stage": "context_build_invalid_json",
            "stderr": str(exc),
        }
    selected = selected_ids(pack)
    hit_ids = [expected_id for expected_id in case.expected_ids if expected_id in selected]
    return {
        "query": case.query,
        "project": case.project,
        "expected_ids": list(case.expected_ids),
        "selected_ids": selected,
        "hit_ids": hit_ids,
        "hit": bool(hit_ids),
        "status": "passed" if hit_ids else "failed",
        "drop_at_stage": diagnose_drop(pack, case.expected_ids, selected),
        "trace_id": pack.get("trace_id"),
        "total_accepted": pack.get("total_accepted", 0),
        "context_items": pack.get("context_items", 0),
        "candidate_summary": pack.get("candidate_summary"),
    }


def run_audit(memoryos_dir: Path, memory_root: Path, cases: tuple[RetrievalCase, ...]) -> dict[str, Any]:
    rows = [run_context_case(memoryos_dir, memory_root, case) for case in cases]
    hits = sum(1 for row in rows if row.get("hit"))
    total = len(rows)
    rate = hits / total if total else 0.0
    return {
        "schema_version": SCHEMA_VERSION,
        "memoryos_dir": memoryos_dir.as_posix(),
        "memory_root": memory_root.as_posix(),
        "total_cases": total,
        "hits": hits,
        "misses": total - hits,
        "retrieval_rate": round(rate, 4),
        "passed": rate >= 0.5,
        "cases": rows,
    }


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--memoryos-dir", type=Path, default=DEFAULT_MEMORYOS_DIR)
    parser.add_argument("--root", type=Path, default=DEFAULT_MEMORYOS_DIR)
    parser.add_argument("--case", dest="cases", action="append", type=parse_case)
    parser.add_argument("--min-rate", type=float, default=0.5)
    parser.add_argument("--json", action="store_true")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    cases = tuple(args.cases) if args.cases else DEFAULT_CASES
    result = run_audit(args.memoryos_dir.resolve(), args.root.resolve(), cases)
    result["passed"] = bool(result["retrieval_rate"] >= args.min_rate)
    result["min_rate"] = args.min_rate
    if args.json:
        print(json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True))
    else:
        print(
            "memory_retrieval_audit "
            f"rate={result['retrieval_rate']} hits={result['hits']}/{result['total_cases']} "
            f"passed={str(result['passed']).lower()}"
        )
        for row in result["cases"]:
            print(
                f"- {row['status']} query={row['query']!r} "
                f"hit_ids={','.join(row.get('hit_ids') or []) or '-'} "
                f"drop={row.get('drop_at_stage')}"
            )
    return 0 if result["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
