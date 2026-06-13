#!/usr/bin/env python3
"""Redacted serving support projections and incident timelines for AIOS.

Emits user-scoped incident timelines and admin summaries that preserve
operational signal (stage, status, error type, severity, retryability) while
stripping raw user content, memory bodies, provider logs, prompt text,
credential material, and private exports.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from typing import Any, Final


SCHEMA_VERSION_PROJECTION: Final = "aios.serving_support_projection.v1"
SCHEMA_VERSION_TIMELINE: Final = "aios.serving_incident_timeline.v1"

RAW_FIELDS: Final = frozenset({
    "message_body",
    "memory_body",
    "provider_output",
    "tool_output",
    "prompt_text",
    "credential_value",
    "token",
    "private_export",
    "raw_provider_log",
    "raw_tool_response",
    "user_message",
    "raw_output",
    "secret",
    "password",
    "api_key",
    "auth_token",
    "bearer_token",
    "access_token",
    "refresh_token",
})

CREDENTIAL_PATTERNS: Final = (
    re.compile(r"(?i)(sk-[a-zA-Z0-9\-]{20,})"),
    re.compile(r"(?i)(ghp_[a-zA-Z0-9]{36,})"),
    re.compile(r"(?i)(xox[bprs]-[a-zA-Z0-9\-]+)"),
    re.compile(r"(?i)(eyJ[a-zA-Z0-9_\-]{10,}\.[a-zA-Z0-9_\-]{10,})"),
    re.compile(r"(?i)(AKIA[A-Z0-9]{12,})"),
    re.compile(r"(?i)(bearer\s+\S{8,})", re.IGNORECASE),
)

SAFE_METADATA_KEYS: Final = frozenset({
    "user_id",
    "session_id",
    "incident_id",
    "stage",
    "status",
    "timestamp",
    "error_type",
    "severity",
    "retryable",
    "ref",
    "component",
    "owner_repo",
    "schema_version",
    "event_index",
})


def _looks_like_credential(value: str) -> bool:
    for pattern in CREDENTIAL_PATTERNS:
        if pattern.search(value):
            return True
    return False


def _redact_value(key: str, value: Any) -> Any:
    if key in RAW_FIELDS:
        return "[REDACTED]"
    if isinstance(value, str) and _looks_like_credential(value):
        return "[REDACTED:credential_pattern]"
    if isinstance(value, dict):
        return {k: _redact_value(k, v) for k, v in value.items()}
    if isinstance(value, list):
        return [_redact_value(key, item) for item in value]
    return value


def redact_event(event: dict[str, Any]) -> dict[str, Any]:
    """Return a copy of *event* with raw/private fields redacted."""
    return {k: _redact_value(k, v) for k, v in event.items()}


def build_incident_timeline(
    events: list[dict[str, Any]],
    user_id: str,
) -> dict[str, Any]:
    """Build a redacted incident timeline scoped to *user_id*.

    Returns a denial payload if the events belong to a different user.
    """
    if not events:
        return {
            "schema_version": SCHEMA_VERSION_TIMELINE,
            "user_id": user_id,
            "status": "empty",
            "timeline": [],
        }

    owners = {e.get("user_id") for e in events if e.get("user_id")}
    if owners and user_id not in owners:
        return {
            "schema_version": SCHEMA_VERSION_TIMELINE,
            "user_id": user_id,
            "status": "denied",
            "reason": "requesting_user_does_not_match_incident_owner",
            "timeline": [],
        }

    user_events = [e for e in events if e.get("user_id") == user_id]

    timeline_entries: list[dict[str, Any]] = []
    for idx, event in enumerate(user_events):
        redacted = redact_event(event)
        entry: dict[str, Any] = {"event_index": idx}
        for key in (
            "stage",
            "status",
            "timestamp",
            "error_type",
            "severity",
            "retryable",
            "incident_id",
            "session_id",
            "component",
            "owner_repo",
        ):
            if key in redacted:
                entry[key] = redacted[key]
        if "ref" not in redacted and "incident_id" in redacted:
            entry["ref"] = f"opaque:{redacted['incident_id']}"
        elif "ref" in redacted:
            entry["ref"] = redacted["ref"]
        timeline_entries.append(entry)

    return {
        "schema_version": SCHEMA_VERSION_TIMELINE,
        "user_id": user_id,
        "status": "ok",
        "event_count": len(timeline_entries),
        "timeline": timeline_entries,
    }


def build_admin_summary(events: list[dict[str, Any]]) -> dict[str, Any]:
    """Build an admin summary exposing only counts and status/error metadata."""
    stage_counts: dict[str, int] = {}
    status_counts: dict[str, int] = {}
    error_type_counts: dict[str, int] = {}
    severity_counts: dict[str, int] = {}
    user_count: set[str] = set()

    for event in events:
        stage = event.get("stage", "unknown")
        stage_counts[stage] = stage_counts.get(stage, 0) + 1

        status = event.get("status", "unknown")
        status_counts[status] = status_counts.get(status, 0) + 1

        error_type = event.get("error_type")
        if error_type:
            error_type_counts[error_type] = error_type_counts.get(error_type, 0) + 1

        severity = event.get("severity")
        if severity:
            severity_counts[severity] = severity_counts.get(severity, 0) + 1

        uid = event.get("user_id")
        if uid:
            user_count.add(uid)

    return {
        "schema_version": SCHEMA_VERSION_PROJECTION,
        "mode": "admin_summary",
        "total_events": len(events),
        "distinct_users": len(user_count),
        "by_stage": stage_counts,
        "by_status": status_counts,
        "by_error_type": error_type_counts,
        "by_severity": severity_counts,
    }


def project_support(
    events: list[dict[str, Any]],
    *,
    user_id: str | None = None,
    mode: str = "timeline",
) -> dict[str, Any]:
    """Main entry point for serving support projections.

    mode="timeline": requires user_id, returns redacted incident timeline.
    mode="admin": returns aggregate admin summary (no raw content).
    """
    if mode == "admin":
        return build_admin_summary(events)

    if mode == "timeline":
        if not user_id:
            return {
                "schema_version": SCHEMA_VERSION_PROJECTION,
                "status": "error",
                "reason": "user_id_required_for_timeline",
            }
        return build_incident_timeline(events, user_id)

    return {
        "schema_version": SCHEMA_VERSION_PROJECTION,
        "status": "error",
        "reason": f"unknown_mode:{mode}",
    }


def cmd_project(args: argparse.Namespace) -> int:
    try:
        raw = sys.stdin.read()
        events = json.loads(raw)
    except (json.JSONDecodeError, ValueError) as exc:
        payload = {"ok": False, "error": f"invalid_json: {exc}"}
        if args.json:
            print(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True))
        else:
            print(f"error: {payload['error']}")
        return 2

    if not isinstance(events, list):
        events = [events]

    result = project_support(events, user_id=args.user_id, mode=args.mode)
    if args.json:
        print(json.dumps({"ok": True, "projection": result}, ensure_ascii=False, indent=2, sort_keys=True))
    else:
        print(json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True))
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Redacted AIOS serving support projections"
    )
    sub = parser.add_subparsers(dest="cmd", required=True)
    proj = sub.add_parser("project", help="project redacted support view from stdin events")
    proj.add_argument("--mode", choices=["timeline", "admin"], default="timeline")
    proj.add_argument("--user-id", default=None)
    proj.add_argument("--json", action="store_true")
    proj.set_defaults(func=cmd_project)
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
