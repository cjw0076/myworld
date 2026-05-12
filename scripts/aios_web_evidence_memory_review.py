#!/usr/bin/env python3
"""Turn validated web evidence receipts into MemoryOS review candidates."""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT_FOR_IMPORTS = Path(__file__).resolve().parents[1]
if str(ROOT_FOR_IMPORTS) not in sys.path:
    sys.path.insert(0, str(ROOT_FOR_IMPORTS))

from scripts.aios_web_research_receipt import load_receipt, validate_receipt


SCHEMA_VERSION = "aios.web_evidence_memory_review.v1"
RUN_SCHEMA_VERSION = "aios.web_evidence_memory_review.run_bundle.v1"
DEFAULT_PROJECT = "AIOS"
FORBIDDEN_MARKERS = (
    "BEGIN PRIVATE KEY",
    "OPENAI_API_KEY",
    "sk-",
    "raw_exports/",
    ".env",
)


def now_iso() -> str:
    return datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds")


def stable_id(prefix: str, *parts: Any) -> str:
    payload = "\n".join(str(part) for part in parts)
    return f"{prefix}_{hashlib.sha256(payload.encode('utf-8')).hexdigest()[:16]}"


def build_review_packet(receipt_path: Path, root: Path) -> dict[str, Any]:
    receipt = load_receipt(receipt_path)
    errors = validate_receipt(receipt)
    if errors:
        raise ValueError("; ".join(errors))

    receipt_ref = relative_ref(receipt_path, root)
    sources = {
        str(source["source_id"]): source
        for source in receipt.get("sources", [])
        if isinstance(source, dict) and source.get("source_id")
    }
    candidates = []
    for index, row in enumerate(receipt.get("synthesis_claims") or []):
        if not isinstance(row, dict):
            continue
        claim = " ".join(str(row.get("claim") or "").split())
        if not claim:
            continue
        source_ids = [str(source_id) for source_id in row.get("source_ids") or []]
        candidate_sources = [safe_source_summary(sources[source_id]) for source_id in source_ids if source_id in sources]
        candidates.append(
            {
                "candidate_id": stable_id(receipt.get("receipt_id", "receipt"), index, claim, *source_ids),
                "type": "idea",
                "content": claim,
                "origin": "assistant",
                "project": DEFAULT_PROJECT,
                "confidence": 0.62,
                "status": "draft",
                "evidence_state": "unreviewed",
                "review_required": True,
                "auto_accept": False,
                "source_ids": source_ids,
                "raw_refs": [receipt_ref],
                "provenance": {
                    "receipt_id": receipt.get("receipt_id"),
                    "receipt_path": receipt_ref,
                    "route_contract": receipt.get("route_contract"),
                    "capability_id": (receipt.get("route") or {}).get("capability_id"),
                    "sources": candidate_sources,
                },
                "review_notes": [
                    "web_derived_fact",
                    "requires_operator_or_memoryos_review",
                    "do_not_auto_accept",
                ],
            }
        )

    packet = {
        "schema_version": SCHEMA_VERSION,
        "generated_at": now_iso(),
        "source_receipt": receipt_ref,
        "receipt_id": receipt.get("receipt_id"),
        "source_schema_version": receipt.get("schema_version"),
        "route_contract": receipt.get("route_contract"),
        "capability_id": (receipt.get("route") or {}).get("capability_id"),
        "status": "review_candidates",
        "auto_accept": False,
        "memoryos_target_status": "draft",
        "review_required": True,
        "candidate_count": len(candidates),
        "candidates": candidates,
        "memoryos_import_hint": {
            "command": "memoryos import-run <run_bundle_dir> --dry-run --json",
            "expected_status": "dry_run_ok",
            "must_not_write_review_acceptance": True,
        },
    }
    errors = validate_review_packet(packet)
    if errors:
        raise ValueError("; ".join(errors))
    return packet


def safe_source_summary(source: dict[str, Any]) -> dict[str, Any]:
    return {
        "source_id": source.get("source_id"),
        "title": source.get("title"),
        "url": source.get("url"),
        "publisher": source.get("publisher"),
        "source_type": source.get("source_type"),
        "accessed_at": source.get("accessed_at"),
    }


def build_run_bundle(packet: dict[str, Any]) -> dict[str, Any]:
    memory_drafts = []
    for candidate in packet.get("candidates") or []:
        memory_drafts.append(
            {
                "type": candidate["type"],
                "content": candidate["content"],
                "origin": candidate["origin"],
                "project": candidate["project"],
                "confidence": candidate["confidence"],
                "status": "draft",
                "raw_refs": list(candidate["raw_refs"]),
            }
        )
    return {
        "schema_version": RUN_SCHEMA_VERSION,
        "run_state": {
            "run_id": f"{packet['receipt_id']}-memory-review",
            "user_request": (
                "Convert validated AIOS web evidence receipt into MemoryOS draft "
                "review candidates without accepting web-derived facts."
            ),
            "project": DEFAULT_PROJECT,
            "phase": "memory_review_candidate",
            "status": "complete",
            "created_at": packet["generated_at"],
        },
        "memory_drafts": {"memory_drafts": memory_drafts},
        "transcript": (
            "# ASC-0041 Web Evidence Memory Review\n\n"
            f"Source receipt: {packet['source_receipt']}\n\n"
            "This bundle is a review-candidate adapter. It does not accept "
            "MemoryOS objects.\n"
        ),
    }


def validate_review_packet(packet: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    if packet.get("schema_version") != SCHEMA_VERSION:
        errors.append(f"schema_version must be {SCHEMA_VERSION}")
    if packet.get("auto_accept") is not False:
        errors.append("auto_accept must be false")
    if packet.get("memoryos_target_status") != "draft":
        errors.append("memoryos_target_status must be draft")
    if packet.get("review_required") is not True:
        errors.append("review_required must be true")
    candidates = packet.get("candidates")
    if not isinstance(candidates, list) or not candidates:
        errors.append("candidates must be a non-empty list")
        candidates = []
    for index, candidate in enumerate(candidates):
        errors.extend(validate_candidate(candidate, index))
    encoded = json.dumps(packet, ensure_ascii=False)
    for marker in FORBIDDEN_MARKERS:
        if marker in encoded:
            errors.append(f"forbidden marker present: {marker}")
    return errors


def validate_candidate(candidate: Any, index: int) -> list[str]:
    errors: list[str] = []
    if not isinstance(candidate, dict):
        return [f"candidates[{index}] must be an object"]
    required_strings = ("candidate_id", "type", "content", "origin", "project", "status", "evidence_state")
    for field in required_strings:
        if not isinstance(candidate.get(field), str) or not candidate[field].strip():
            errors.append(f"candidates[{index}].{field} is required")
    if candidate.get("status") != "draft":
        errors.append(f"candidates[{index}].status must be draft")
    if candidate.get("evidence_state") != "unreviewed":
        errors.append(f"candidates[{index}].evidence_state must be unreviewed")
    if candidate.get("review_required") is not True:
        errors.append(f"candidates[{index}].review_required must be true")
    if candidate.get("auto_accept") is not False:
        errors.append(f"candidates[{index}].auto_accept must be false")
    confidence = candidate.get("confidence")
    if not isinstance(confidence, (int, float)) or not (0 <= float(confidence) <= 1):
        errors.append(f"candidates[{index}].confidence must be between 0 and 1")
    if not isinstance(candidate.get("source_ids"), list) or not candidate["source_ids"]:
        errors.append(f"candidates[{index}].source_ids must be non-empty")
    refs = candidate.get("raw_refs")
    if not isinstance(refs, list) or not refs:
        errors.append(f"candidates[{index}].raw_refs must be non-empty")
    elif any(str(ref).startswith("/") for ref in refs):
        errors.append(f"candidates[{index}].raw_refs must not contain absolute paths")
    provenance = candidate.get("provenance")
    if not isinstance(provenance, dict):
        errors.append(f"candidates[{index}].provenance is required")
    elif not provenance.get("sources"):
        errors.append(f"candidates[{index}].provenance.sources must be non-empty")
    return errors


def relative_ref(path: Path, root: Path) -> str:
    resolved = path.resolve()
    try:
        return resolved.relative_to(root.resolve()).as_posix()
    except ValueError:
        return path.as_posix()


def write_json(path: Path, data: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def write_run_bundle(path: Path, bundle: dict[str, Any]) -> None:
    path.mkdir(parents=True, exist_ok=True)
    write_json(path / "run_state.json", bundle["run_state"])
    write_json(path / "memory_drafts.json", bundle["memory_drafts"])
    (path / "transcript.md").write_text(bundle["transcript"], encoding="utf-8")


def cmd_build(args: argparse.Namespace) -> int:
    root = Path(args.root).resolve()
    receipt_path = Path(args.receipt)
    if not receipt_path.is_absolute():
        receipt_path = root / receipt_path
    packet = build_review_packet(receipt_path, root)
    if args.output:
        write_json(Path(args.output), packet)
    if args.run_bundle:
        write_run_bundle(Path(args.run_bundle), build_run_bundle(packet))
    if args.json:
        print(json.dumps(packet, ensure_ascii=False, indent=2, sort_keys=True))
    else:
        print(f"ok candidates={packet['candidate_count']}")
    return 0


def cmd_validate(args: argparse.Namespace) -> int:
    data = json.loads(Path(args.path).read_text(encoding="utf-8"))
    errors = validate_review_packet(data)
    payload = {
        "schema_version": f"{SCHEMA_VERSION}.validation",
        "path": args.path,
        "ok": not errors,
        "errors": errors,
        "candidate_count": len(data.get("candidates") or []) if isinstance(data, dict) else 0,
    }
    if args.json:
        print(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True))
    elif errors:
        for error in errors:
            print(error, file=sys.stderr)
    else:
        print(f"ok {args.path}")
    return 0 if not errors else 1


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Build MemoryOS review candidates from web evidence receipts")
    parser.add_argument("--root", default=".")
    sub = parser.add_subparsers(dest="cmd", required=True)

    build = sub.add_parser("build")
    build.add_argument("receipt")
    build.add_argument("--output")
    build.add_argument("--run-bundle")
    build.add_argument("--json", action="store_true")
    build.set_defaults(func=cmd_build)

    validate = sub.add_parser("validate")
    validate.add_argument("path")
    validate.add_argument("--json", action="store_true")
    validate.set_defaults(func=cmd_validate)
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        return int(args.func(args))
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        print(str(exc), file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.exit(main())
