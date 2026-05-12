#!/usr/bin/env python3
"""Turn CapabilityOS result observations into MemoryOS review candidates."""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


ROOT_FOR_IMPORTS = Path(__file__).resolve().parents[1]
CAPABILITYOS_SRC = ROOT_FOR_IMPORTS / "CapabilityOS"
for import_path in (ROOT_FOR_IMPORTS, CAPABILITYOS_SRC):
    if str(import_path) not in sys.path:
        sys.path.insert(0, str(import_path))

from capabilityos.catalog import load_catalog  # noqa: E402
from capabilityos.observation import observe_results  # noqa: E402


SCHEMA_VERSION = "aios.capability_observation_memory_review.v1"
RUN_SCHEMA_VERSION = "aios.capability_observation_memory_review.run_bundle.v1"
OBSERVE_RESULTS_CONTRACT = "capabilityos.observe_results.v1"
DEFAULT_PROJECT = "AIOS"
FORBIDDEN_MARKERS = ("BEGIN PRIVATE KEY", "OPENAI_API_KEY", "sk-", ".env", "raw_exports/")


def now_iso() -> str:
    return datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds")


def stable_id(prefix: str, *parts: Any) -> str:
    payload = "\n".join(str(part) for part in parts)
    return f"{prefix}_{hashlib.sha256(payload.encode('utf-8')).hexdigest()[:16]}"


def build_observation_payload(root: Path, outbox: Path, radar: Path | None) -> dict[str, Any]:
    catalog_path = root / "CapabilityOS" / "tests" / "fixtures" / "capabilities.json"
    return observe_results(
        outbox,
        load_catalog(catalog_path),
        radar=radar if radar and radar.exists() else None,
        evidence_base=root / "CapabilityOS",
    )


def build_review_packet(payload: dict[str, Any], *, observation_ref: str) -> dict[str, Any]:
    errors = validate_observation_payload(payload)
    if errors:
        raise ValueError("; ".join(errors))

    groups: dict[str, list[dict[str, Any]]] = defaultdict(list)
    excluded = []
    for row in payload.get("observations") or []:
        reason = exclusion_reason(row)
        if reason:
            excluded.append(
                {
                    "capability_id": row.get("capability_id"),
                    "dispatch_id": row.get("dispatch_id"),
                    "reason": reason,
                }
            )
            continue
        groups[str(row["capability_id"])].append(row)

    candidates = [candidate_from_group(capability_id, rows, observation_ref) for capability_id, rows in sorted(groups.items())]
    packet = {
        "schema_version": SCHEMA_VERSION,
        "generated_at": now_iso(),
        "source_observations": observation_ref,
        "source_contract": payload.get("contract"),
        "status": "review_candidates",
        "auto_accept": False,
        "memoryos_target_status": "draft",
        "review_required": True,
        "candidate_count": len(candidates),
        "observation_count": len(payload.get("observations") or []),
        "excluded_count": len(excluded),
        "excluded_observations": excluded,
        "gaps_count": len(payload.get("gaps") or []),
        "gaps_policy": "operator_review_only",
        "candidates": candidates,
        "memoryos_import_hint": {
            "command": "memoryos import-run <run_bundle_dir> --dry-run --json",
            "expected_status": "dry_run_ok",
            "must_not_write_review_acceptance": True,
        },
    }
    packet_errors = validate_review_packet(packet)
    if packet_errors:
        raise ValueError("; ".join(packet_errors))
    return packet


def exclusion_reason(row: Any) -> str | None:
    if not isinstance(row, dict):
        return "not_object"
    if row.get("outcome") != "passed":
        return "non_passed_outcome"
    if not str(row.get("capability_id") or "").startswith("cap_"):
        return "unknown_capability"
    if not row.get("contract_id") or row.get("contract_id") == "unknown":
        return "missing_contract"
    refs = row.get("evidence_refs")
    if not isinstance(refs, list) or not refs:
        return "missing_evidence_refs"
    return None


def candidate_from_group(capability_id: str, rows: list[dict[str, Any]], observation_ref: str) -> dict[str, Any]:
    contracts = sorted({str(row["contract_id"]) for row in rows})
    repos = sorted({str(row.get("repo") or "unknown") for row in rows})
    evidence_refs = dedupe(
        [observation_ref]
        + [
            normalize_capability_ref(str(ref))
            for row in rows
            for ref in (row.get("evidence_refs") or [])
            if str(ref).strip()
        ]
    )
    content = (
        f"Capability observation rollup: {capability_id} has {len(rows)} passed "
        f"dispatch observation(s) across repos {', '.join(repos)} and contracts "
        f"{', '.join(contracts[:8])}. Treat this as reviewable routing evidence, "
        "not an accepted guarantee of future capability performance."
    )
    return {
        "candidate_id": stable_id("capmem", capability_id, len(rows), *contracts, *evidence_refs[:12]),
        "type": "artifact",
        "content": content,
        "origin": "assistant",
        "project": DEFAULT_PROJECT,
        "confidence": min(0.78, 0.55 + (0.03 * len(rows))),
        "status": "draft",
        "evidence_state": "unreviewed",
        "review_required": True,
        "auto_accept": False,
        "capability_id": capability_id,
        "observation_count": len(rows),
        "source_contract_ids": contracts,
        "source_repos": repos,
        "raw_refs": evidence_refs[:20],
        "provenance": {
            "observation_snapshot": observation_ref,
            "observation_schema": OBSERVE_RESULTS_CONTRACT,
            "dispatch_ids": [str(row.get("dispatch_id")) for row in rows],
            "evidence_refs": evidence_refs[:20],
        },
        "review_notes": [
            "capability_observation_rollup",
            "requires_operator_or_memoryos_review",
            "do_not_auto_accept",
        ],
    }


def build_run_bundle(packet: dict[str, Any]) -> dict[str, Any]:
    return {
        "schema_version": RUN_SCHEMA_VERSION,
        "run_state": {
            "run_id": "ASC-0042-capability-observation-memory-review",
            "user_request": (
                "Convert CapabilityOS result observations into MemoryOS draft "
                "review candidates without accepting capability claims."
            ),
            "project": DEFAULT_PROJECT,
            "phase": "capability_observation_memory_review",
            "status": "complete",
            "created_at": packet["generated_at"],
        },
        "memory_drafts": {
            "memory_drafts": [
                {
                    "type": candidate["type"],
                    "content": candidate["content"],
                    "origin": candidate["origin"],
                    "project": candidate["project"],
                    "confidence": candidate["confidence"],
                    "status": "draft",
                    "raw_refs": candidate["raw_refs"],
                }
                for candidate in packet.get("candidates") or []
            ]
        },
        "transcript": (
            "# ASC-0042 Capability Observation Memory Review\n\n"
            f"Source observations: {packet['source_observations']}\n\n"
            "This bundle is a review-candidate adapter. It does not accept "
            "MemoryOS objects.\n"
        ),
    }


def validate_observation_payload(payload: dict[str, Any]) -> list[str]:
    errors = []
    if payload.get("contract") != OBSERVE_RESULTS_CONTRACT:
        errors.append(f"contract must be {OBSERVE_RESULTS_CONTRACT}")
    if payload.get("recommendation_only") is not True:
        errors.append("recommendation_only must be true")
    if not isinstance(payload.get("observations"), list):
        errors.append("observations must be a list")
    if not isinstance(payload.get("gaps"), list):
        errors.append("gaps must be a list")
    return errors


def validate_review_packet(packet: dict[str, Any]) -> list[str]:
    errors = []
    if packet.get("schema_version") != SCHEMA_VERSION:
        errors.append(f"schema_version must be {SCHEMA_VERSION}")
    if packet.get("auto_accept") is not False:
        errors.append("auto_accept must be false")
    if packet.get("memoryos_target_status") != "draft":
        errors.append("memoryos_target_status must be draft")
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
    errors = []
    if not isinstance(candidate, dict):
        return [f"candidates[{index}] must be an object"]
    if candidate.get("status") != "draft":
        errors.append(f"candidates[{index}].status must be draft")
    if candidate.get("evidence_state") != "unreviewed":
        errors.append(f"candidates[{index}].evidence_state must be unreviewed")
    if candidate.get("review_required") is not True:
        errors.append(f"candidates[{index}].review_required must be true")
    if candidate.get("auto_accept") is not False:
        errors.append(f"candidates[{index}].auto_accept must be false")
    if not str(candidate.get("capability_id") or "").startswith("cap_"):
        errors.append(f"candidates[{index}].capability_id must be a cap_* id")
    if not isinstance(candidate.get("observation_count"), int) or candidate["observation_count"] < 1:
        errors.append(f"candidates[{index}].observation_count must be positive")
    if not isinstance(candidate.get("source_contract_ids"), list) or not candidate["source_contract_ids"]:
        errors.append(f"candidates[{index}].source_contract_ids must be non-empty")
    refs = candidate.get("raw_refs")
    if not isinstance(refs, list) or not refs:
        errors.append(f"candidates[{index}].raw_refs must be non-empty")
    elif any(str(ref).startswith("/") for ref in refs):
        errors.append(f"candidates[{index}].raw_refs must not contain absolute paths")
    if not isinstance(candidate.get("provenance"), dict) or not candidate["provenance"].get("dispatch_ids"):
        errors.append(f"candidates[{index}].provenance.dispatch_ids must be non-empty")
    return errors


def dedupe(values: list[str]) -> list[str]:
    seen = set()
    result = []
    for value in values:
        if value in seen:
            continue
        seen.add(value)
        result.append(value)
    return result


def normalize_capability_ref(ref: str) -> str:
    text = ref.strip()
    while text.startswith("../"):
        text = text[3:]
    if text.startswith("./"):
        text = text[2:]
    return text


def relative_ref(path: Path, root: Path) -> str:
    resolved = path.resolve()
    try:
        return resolved.relative_to(root.resolve()).as_posix()
    except ValueError:
        return path.name


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
    outbox = Path(args.outbox)
    if not outbox.is_absolute():
        outbox = root / outbox
    radar = Path(args.radar) if args.radar else None
    if radar and not radar.is_absolute():
        radar = root / radar
    observation_output = Path(args.observation_output) if args.observation_output else None
    payload = build_observation_payload(root, outbox, radar)
    observation_ref = relative_ref(observation_output, root) if observation_output else relative_ref(outbox, root)
    if observation_output:
        write_json(observation_output, payload)
    packet = build_review_packet(payload, observation_ref=observation_ref)
    if args.output:
        write_json(Path(args.output), packet)
    if args.run_bundle:
        write_run_bundle(Path(args.run_bundle), build_run_bundle(packet))
    if args.json:
        print(json.dumps(packet, ensure_ascii=False, indent=2, sort_keys=True))
    else:
        print(f"ok candidates={packet['candidate_count']} observations={packet['observation_count']}")
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
    parser = argparse.ArgumentParser(description="Build MemoryOS review candidates from CapabilityOS observations")
    parser.add_argument("--root", default=".")
    sub = parser.add_subparsers(dest="cmd", required=True)

    build = sub.add_parser("build")
    build.add_argument("--outbox", default=".aios/outbox")
    build.add_argument("--radar", default="docs/AIOS_TASK_RADAR.md")
    build.add_argument("--observation-output")
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
