#!/usr/bin/env python3
"""Validate AIOS web research evidence receipts."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any
from urllib.parse import urlparse


SCHEMA_VERSION = "aios.web_research_receipt.v1"
ROUTE_CONTRACT = "capabilityos.web_research_route.v1"
FORBIDDEN_MARKERS = (
    "BEGIN PRIVATE KEY",
    "OPENAI_API_KEY",
    "sk-",
    "raw_exports/",
    ".env",
)


def load_receipt(path: Path) -> dict[str, Any]:
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError("receipt must be a JSON object")
    return data


def validate_receipt(data: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    if data.get("schema_version") != SCHEMA_VERSION:
        errors.append(f"schema_version must be {SCHEMA_VERSION}")
    if data.get("route_contract") != ROUTE_CONTRACT:
        errors.append(f"route_contract must be {ROUTE_CONTRACT}")
    if not _string(data.get("task")):
        errors.append("task is required")
    if not _string(data.get("executed_at")):
        errors.append("executed_at is required")
    if data.get("recommendation_only") is not True:
        errors.append("recommendation_only must be true")
    if data.get("capabilityos_executed_network") is not False:
        errors.append("capabilityos_executed_network must be false")

    route = data.get("route")
    if not isinstance(route, dict):
        errors.append("route object is required")
    else:
        if route.get("capability_id") != "cap_web_research_route":
            errors.append("route.capability_id must be cap_web_research_route")
        if not isinstance(route.get("route_steps"), list) or not route["route_steps"]:
            errors.append("route.route_steps must be a non-empty list")

    queries = data.get("queries")
    if not isinstance(queries, list) or not queries:
        errors.append("queries must be a non-empty list")
    elif len(queries) > 4:
        errors.append("queries must respect max_initial_queries <= 4")
    else:
        for index, query in enumerate(queries):
            if not _string(query):
                errors.append(f"queries[{index}] must be a non-empty string")

    sources = data.get("sources")
    if not isinstance(sources, list) or len(sources) < 3:
        errors.append("sources must include at least three source objects")
    else:
        for index, source in enumerate(sources):
            errors.extend(_validate_source(source, index))

    claims = data.get("synthesis_claims")
    if not isinstance(claims, list) or not claims:
        errors.append("synthesis_claims must be a non-empty list")
    else:
        source_ids = {source.get("source_id") for source in sources or [] if isinstance(source, dict)}
        for index, claim in enumerate(claims):
            if not isinstance(claim, dict):
                errors.append(f"synthesis_claims[{index}] must be an object")
                continue
            if not _string(claim.get("claim")):
                errors.append(f"synthesis_claims[{index}].claim is required")
            refs = claim.get("source_ids")
            if not isinstance(refs, list) or not refs:
                errors.append(f"synthesis_claims[{index}].source_ids must be non-empty")
            elif any(ref not in source_ids for ref in refs):
                errors.append(f"synthesis_claims[{index}].source_ids contains unknown source")

    encoded = json.dumps(data, ensure_ascii=False)
    for marker in FORBIDDEN_MARKERS:
        if marker in encoded:
            errors.append(f"forbidden marker present: {marker}")
    if len(encoded) > 120_000:
        errors.append("receipt is too large; store short claims, not raw page bodies")
    return errors


def _validate_source(source: Any, index: int) -> list[str]:
    errors: list[str] = []
    if not isinstance(source, dict):
        return [f"sources[{index}] must be an object"]
    for field in ("source_id", "title", "url", "publisher", "source_type", "accessed_at", "claims"):
        if field == "claims":
            if not isinstance(source.get(field), list) or not source[field]:
                errors.append(f"sources[{index}].claims must be a non-empty list")
            continue
        if not _string(source.get(field)):
            errors.append(f"sources[{index}].{field} is required")
    parsed = urlparse(str(source.get("url") or ""))
    if parsed.scheme not in {"http", "https"} or not parsed.netloc:
        errors.append(f"sources[{index}].url must be http(s)")
    claims = source.get("claims")
    if isinstance(claims, list):
        for claim_index, claim in enumerate(claims):
            if not _string(claim):
                errors.append(f"sources[{index}].claims[{claim_index}] must be non-empty text")
            elif len(str(claim).split()) > 80:
                errors.append(f"sources[{index}].claims[{claim_index}] is too long; paraphrase instead")
    return errors


def _string(value: Any) -> bool:
    return isinstance(value, str) and bool(value.strip())


def cmd_validate(args: argparse.Namespace) -> int:
    path = Path(args.path)
    data = load_receipt(path)
    errors = validate_receipt(data)
    payload = {
        "schema_version": "aios.web_research_receipt.validation.v1",
        "path": path.as_posix(),
        "ok": not errors,
        "errors": errors,
    }
    if args.json:
        print(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True))
    elif errors:
        for error in errors:
            print(error, file=sys.stderr)
    else:
        print(f"ok {path}")
    return 0 if not errors else 1


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Validate AIOS web research evidence receipts")
    sub = parser.add_subparsers(dest="cmd", required=True)
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
