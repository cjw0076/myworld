#!/usr/bin/env python3
"""Audit whether accepted MemoryOS records are retrievable by context build.

Also audits DOMAIN COVERAGE of accepted memory: what fraction of accepted
objects is product-domain (outside AIOS) vs AIOS-internal (the 5 OS + control
plane). An absorption-delta probe (2026-06-05) found accepted memory was
100% AIOS-internal (0 product) — retrieve returned null on any product task
because the graph only remembered AIOS's own plumbing. `inward_growth_alarm`
fires when product coverage is 0, surfacing the founder-override pathology
(AIOS remembering only itself) as a standing metric rather than a one-off
diagnosis. See memory project_memoryos_inward_growth_finding.
"""

from __future__ import annotations

import argparse
import json
import re
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
    # Product-domain probe (project URI). Guards against the inward-growth
    # regression: if this misses, accepted product memory has gone empty again.
    RetrievalCase(
        "uri campus wiki clean-room seed sourcing scholarship 울산대",
        ("mem_0c66b6db9ac73100",),
        project="URI",
    ),
)


# AIOS-internal = the five sibling OS + the control plane. Anything else
# (URI and any future product/testbed) counts as product-domain coverage.
INTERNAL_PROJECTS = frozenset(
    p.casefold()
    for p in (
        "AIOS",
        "myworld",
        "hivemind",
        "Hive Mind",
        "memoryOS",
        "CapabilityOS",
        "GenesisOS",
    )
)


def _is_internal(project: Any) -> bool:
    return str(project or "").casefold() in INTERNAL_PROJECTS


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


def accepted_domain_coverage(memoryos_dir: Path, memory_root: Path) -> dict[str, Any]:
    """Classify accepted memory objects as AIOS-internal vs product-domain."""
    command = [
        sys.executable,
        "-m",
        "memoryos.cli",
        "--root",
        memory_root.as_posix(),
        "drafts",
        "list",
        "--status",
        "accepted",
        "--json",
    ]
    result = subprocess.run(
        command, cwd=memoryos_dir, text=True, capture_output=True, check=False
    )
    if result.returncode != 0:
        return {"status": "error", "stderr": result.stderr.strip()[:1000]}
    try:
        objects = json.loads(result.stdout)
    except json.JSONDecodeError as exc:
        return {"status": "error", "stderr": str(exc)}
    by_project: dict[str, int] = {}
    internal = product = 0
    for obj in objects:
        project = str(obj.get("project") or "?")
        by_project[project] = by_project.get(project, 0) + 1
        if _is_internal(project):
            internal += 1
        else:
            product += 1
    total = internal + product
    coverage = product / total if total else 0.0
    return {
        "status": "ok",
        "total_accepted": total,
        "internal": internal,
        "product": product,
        "product_coverage": round(coverage, 4),
        "by_project": dict(sorted(by_project.items(), key=lambda kv: -kv[1])),
        "inward_growth_alarm": total > 0 and product == 0,
    }


# Provenance ref-integrity (gemini review #5): flag accepted memory whose
# DURABLE evidence file is gone. Ephemeral run artifacts (.runs/.agent/.aios/…)
# are transient by design — checking them would be pure noise, so they're skipped.
_EPHEMERAL = (".runs", ".agent", ".aios", ".local", "node_modules", "__pycache__", ".git/")
_REF_ID = re.compile(r"^(src_|node_|mem_|rtrace|run_)")


def durable_ref_path(ref: str) -> str | None:
    """Cleaned durable file path to existence-check, or None to skip (ids, urls,
    ephemeral run artifacts, non-paths). Strips #L.. / ;meta / :line suffixes."""
    if "://" in ref or _REF_ID.match(ref) or "/" not in ref:
        return None
    path = re.split(r"[#;]", ref, maxsplit=1)[0]
    path = re.sub(r":\d+(-\d+)?$", "", path).strip()
    if not path or any(seg in path for seg in _EPHEMERAL):
        return None
    return path


def ref_exists(path: str, roots: list[Path]) -> bool:
    if path.startswith("/"):
        return Path(path).exists()
    return any((root / path).exists() for root in roots)


def accepted_provenance_integrity(memoryos_dir: Path, memory_root: Path) -> dict[str, Any]:
    command = [
        sys.executable, "-m", "memoryos.cli", "--root", memory_root.as_posix(),
        "drafts", "list", "--status", "accepted", "--json",
    ]
    result = subprocess.run(command, cwd=memoryos_dir, text=True, capture_output=True, check=False)
    if result.returncode != 0:
        return {"status": "error", "stderr": result.stderr.strip()[:1000]}
    try:
        objects = json.loads(result.stdout)
    except json.JSONDecodeError as exc:
        return {"status": "error", "stderr": str(exc)}
    # Refs are root-ambiguous (e.g. bare `docs/HANDOFF.json` may live in a child
    # repo). Resolve against ROOT, its parent, and each sibling git repo so we
    # only flag evidence that exists nowhere reachable — not mere root ambiguity.
    roots = [ROOT, ROOT.parent]
    try:
        roots += [p for p in ROOT.iterdir() if p.is_dir() and (p / ".git").exists()]
    except OSError:
        pass
    checked = 0
    dangling: list[dict[str, str]] = []
    for obj in objects:
        for ref in obj.get("raw_refs") or []:
            path = durable_ref_path(str(ref))
            if path is None:
                continue
            checked += 1
            if not ref_exists(path, roots):
                dangling.append({"id": obj.get("id", "?"), "ref": path})
    return {
        "status": "ok",
        "durable_refs_checked": checked,
        "dangling_count": len(dangling),
        "dangling": dangling[:20],
        "ok": not dangling,
    }


def run_audit(memoryos_dir: Path, memory_root: Path, cases: tuple[RetrievalCase, ...]) -> dict[str, Any]:
    rows = [run_context_case(memoryos_dir, memory_root, case) for case in cases]
    hits = sum(1 for row in rows if row.get("hit"))
    total = len(rows)
    rate = hits / total if total else 0.0
    coverage = accepted_domain_coverage(memoryos_dir, memory_root)
    provenance = accepted_provenance_integrity(memoryos_dir, memory_root)
    return {
        "schema_version": SCHEMA_VERSION,
        "memoryos_dir": memoryos_dir.as_posix(),
        "memory_root": memory_root.as_posix(),
        "total_cases": total,
        "hits": hits,
        "misses": total - hits,
        "retrieval_rate": round(rate, 4),
        "passed": rate >= 0.5,
        "domain_coverage": coverage,
        "provenance_integrity": provenance,
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
        cov = result.get("domain_coverage") or {}
        if cov.get("status") == "ok":
            print(
                f"  domain_coverage product={cov['product']}/{cov['total_accepted']} "
                f"({cov['product_coverage']}) internal={cov['internal']} "
                f"inward_growth_alarm={str(cov['inward_growth_alarm']).lower()}"
            )
        prov = result.get("provenance_integrity") or {}
        if prov.get("status") == "ok":
            print(
                f"  provenance_integrity dangling={prov['dangling_count']}/"
                f"{prov['durable_refs_checked']} durable refs"
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
