#!/usr/bin/env python3
"""Validate AIOS Sovereign Swarm share projections.

This is a local preflight validator only. It does not create peers, sign keys,
sync git repositories, fetch remotes, import memory, or execute providers.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
from pathlib import Path
from typing import Any


VERIFY_SCHEMA = "aios.share_projection.verify.v1"
PROJECTION_SCHEMA = "aios.share_projection.v1"
POLICY_VERSION = "aios.share_policy.v1"

ALLOWED_SOURCE_OS = {"myworld", "memoryOS", "CapabilityOS", "hivemind"}
ELIGIBLE_RECORD_KINDS = {
    "memory_draft_projection",
    "capability_observation_projection",
    "hive_run_receipt_projection",
    "contract_projection",
    "ledger_projection",
}
ALLOWED_PURPOSES = {
    "peer_review",
    "capability_observation",
    "run_receipt",
    "contract_projection",
}
ALLOWED_REMOVED_CLASSES = {
    "secret",
    "personal_data",
    "raw_export",
    "provider_output",
    "local_path",
    "private_transcript",
}

HARD_BAN_FRAGMENTS = (
    "_from_desktop/",
    "dain/",
    "minyoung/",
    ".env",
    "secret",
    "credential",
    "token",
    "raw_exports/",
    "data/",
    ".aios/logs/",
    ".runs/",
)
SECRET_PATTERNS = (
    re.compile(r"AIza[0-9A-Za-z_\-]{20,}"),
    re.compile(r"sk-[0-9A-Za-z_\-]{20,}"),
    re.compile(r"(?i)(api[_-]?key|secret|token|credential)\s*[:=]\s*\S+"),
)
HASH_RE = re.compile(r"^sha256:[0-9a-f]{64}$")


def canonical_json(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def sha256_json(value: Any) -> str:
    return "sha256:" + hashlib.sha256(canonical_json(value).encode("utf-8")).hexdigest()


def load_record(path: Path) -> dict[str, Any]:
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError("projection record must be a JSON object")
    return data


def verify_record(record: dict[str, Any], *, path: Path | None = None) -> dict[str, Any]:
    errors: list[str] = []
    warnings: list[str] = []

    required = [
        "schema_version",
        "projection_id",
        "source_os",
        "record_kind",
        "visibility",
        "source_ref",
        "source_hash",
        "projection_hash",
        "redaction_proof",
        "payload",
        "producer",
        "signature",
        "created_at",
    ]
    for field in required:
        if field not in record:
            errors.append(f"missing:{field}")

    schema_version = str(record.get("schema_version", ""))
    if schema_version != PROJECTION_SCHEMA:
        if schema_version.startswith("aios.share_projection."):
            warnings.append(f"review_queue:unsupported_schema:{schema_version}")
        else:
            errors.append(f"schema_version_invalid:{schema_version or '<missing>'}")

    source_os = str(record.get("source_os", ""))
    if source_os not in ALLOWED_SOURCE_OS:
        errors.append(f"source_os_invalid:{source_os or '<missing>'}")

    record_kind = str(record.get("record_kind", ""))
    if record_kind not in ELIGIBLE_RECORD_KINDS:
        errors.append(f"record_kind_not_share_eligible:{record_kind or '<missing>'}")
    if "accepted" in record_kind or record_kind in {"memory_object", "accepted_memory", "raw_memory"}:
        errors.append("raw_or_accepted_memory_not_shareable")

    visibility = record.get("visibility")
    if not isinstance(visibility, dict):
        errors.append("visibility_not_object")
        visibility = {}
    if visibility.get("share") is not True:
        errors.append("visibility_default_deny")
    if not isinstance(visibility.get("peer_whitelist", []), list):
        errors.append("visibility_peer_whitelist_not_list")
    if visibility.get("encryption") not in {None, "age", "sealed_box"}:
        errors.append("visibility_encryption_invalid")
    purpose = str(visibility.get("purpose", ""))
    if purpose not in ALLOWED_PURPOSES:
        errors.append(f"visibility_purpose_invalid:{purpose or '<missing>'}")

    source_ref = str(record.get("source_ref", ""))
    if has_hard_ban(source_ref):
        errors.append("hard_ban_source_ref")
    if path and has_hard_ban(path.as_posix()):
        errors.append("hard_ban_record_path")

    payload = record.get("payload")
    payload_text = canonical_json(payload)
    for class_name, triggered in scan_payload(payload_text).items():
        if triggered:
            errors.append(f"payload_contains_{class_name}")

    source_hash = str(record.get("source_hash", ""))
    if not HASH_RE.match(source_hash):
        errors.append("source_hash_invalid")
    projection_hash = str(record.get("projection_hash", ""))
    expected_projection_hash = sha256_json(payload)
    if not HASH_RE.match(projection_hash):
        errors.append("projection_hash_invalid")
    elif projection_hash != expected_projection_hash:
        errors.append("projection_hash_mismatch")

    redaction_proof = record.get("redaction_proof")
    if not isinstance(redaction_proof, dict):
        errors.append("redaction_proof_not_object")
        redaction_proof = {}
    if redaction_proof.get("policy_version") != POLICY_VERSION:
        errors.append("redaction_policy_version_invalid")
    removed_paths = redaction_proof.get("removed_paths")
    if not isinstance(removed_paths, list):
        errors.append("redaction_removed_paths_not_list")
    removed_classes = redaction_proof.get("removed_classes")
    if not isinstance(removed_classes, list):
        errors.append("redaction_removed_classes_not_list")
    else:
        unknown = sorted({str(item) for item in removed_classes} - ALLOWED_REMOVED_CLASSES)
        if unknown:
            errors.append("redaction_removed_classes_unknown:" + ",".join(unknown))

    producer = record.get("producer")
    if not isinstance(producer, dict) or not str(producer.get("id", "")).strip():
        errors.append("producer_id_missing")
    signature = record.get("signature")
    if not isinstance(signature, dict):
        errors.append("signature_not_object")
    else:
        if not str(signature.get("algorithm", "")).strip():
            errors.append("signature_algorithm_missing")
        if not str(signature.get("value", "")).strip():
            errors.append("signature_value_missing")

    status = "blocked" if errors else ("review_queue" if warnings else "passed")
    return {
        "schema_version": VERIFY_SCHEMA,
        "status": status,
        "projection_id": record.get("projection_id"),
        "record_kind": record.get("record_kind"),
        "source_os": record.get("source_os"),
        "policy_version": POLICY_VERSION,
        "errors": errors,
        "warnings": warnings,
        "network_used": False,
        "git_sync_used": False,
        "memory_acceptance_used": False,
        "provider_execution_used": False,
    }


def has_hard_ban(text: str) -> bool:
    normalized = text.replace("\\", "/").lower()
    return any(fragment in normalized for fragment in HARD_BAN_FRAGMENTS)


def scan_payload(text: str) -> dict[str, bool]:
    normalized = text.replace("\\", "/").lower()
    return {
        "hard_ban_path": any(fragment in normalized for fragment in HARD_BAN_FRAGMENTS),
        "secret": any(pattern.search(text) for pattern in SECRET_PATTERNS),
        "provider_output": "stdout" in normalized or "stderr" in normalized,
        "raw_memory": "accepted_memory" in normalized or "raw_memory" in normalized or "raw transcript" in normalized,
    }


def emit(payload: dict[str, Any], as_json: bool) -> None:
    if as_json:
        print(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True))
    else:
        print(f"{payload['schema_version']} status={payload['status']}")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Validate local AIOS share projection records")
    sub = parser.add_subparsers(dest="cmd", required=True)
    verify = sub.add_parser("verify")
    verify.add_argument("record", type=Path)
    verify.add_argument("--json", action="store_true")
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    if args.cmd == "verify":
        try:
            record = load_record(args.record)
            payload = verify_record(record, path=args.record)
        except (OSError, json.JSONDecodeError, ValueError) as exc:
            payload = {
                "schema_version": VERIFY_SCHEMA,
                "status": "failed",
                "errors": [str(exc)],
                "warnings": [],
                "network_used": False,
                "git_sync_used": False,
                "memory_acceptance_used": False,
                "provider_execution_used": False,
            }
            emit(payload, args.json)
            return 2
        emit(payload, args.json)
        return 0
    parser.error(f"unknown command: {args.cmd}")
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
