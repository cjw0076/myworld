#!/usr/bin/env python3
"""Uri markdown relevance filter for AIOS doc scouting.

The filter is read-only toward the Uri repo. It classifies Uri-originated
markdown into AIOS-relevant, Uri-internal, or operator-review buckets and emits
only path-level audit data.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


SCHEMA_VERSION = "aios.uri_filter.v1"
OUTCOMES = {"aios_relevant", "uri_internal", "operator_review", "not_uri"}
SHARED_LANGUAGE_TERMS = {
    "AIOS",
    "contract",
    "dispatch",
    "draft",
    "capability",
    "hive",
    "memory",
    "MemoryOS",
    "CapabilityOS",
    "Hive Mind",
}
WHITELIST_EXACT = {
    "uri/docs/URI_NORTHSTAR.md",
    "uri/docs/AGENT_WORKLOG.md",
    "uri/docs/MEMORY_POLICY.md",
    "uri/docs/CAPABILITY_MAP.md",
    "uri/docs/LEGAL_ETHICAL_GUARDRAILS.md",
    "uri/AGENTS.md",
}
DENY_PREFIXES = {
    "uri/products/",
    "uri/hive/packets/",
    "uri/research/",
    "uri/capabilities/",
    "uri/memory/",
}


@dataclass(frozen=True)
class UriFilterResult:
    schema_version: str
    path: str
    uri_path: str | None
    outcome: str
    reason: str
    matched_terms: list[str]


def now_iso() -> str:
    return datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds")


def normalize_path(path: Path | str, root: Path | None = None) -> str:
    candidate = Path(path)
    if root is not None:
        try:
            candidate = candidate.resolve().relative_to(root.resolve())
        except (OSError, ValueError):
            pass
    return candidate.as_posix().lstrip("./")


def uri_relative_path(path: Path | str, root: Path | None = None) -> str | None:
    rel = normalize_path(path, root)
    parts = Path(rel).parts
    if "uri" not in parts:
        return None
    idx = parts.index("uri")
    return Path(*parts[idx:]).as_posix()


def is_whitelisted(uri_path: str) -> bool:
    return uri_path in WHITELIST_EXACT or (
        uri_path.startswith("uri/docs/AIOS_") and uri_path.endswith((".md", ".mdx"))
    )


def deny_reason(uri_path: str) -> str | None:
    for prefix in sorted(DENY_PREFIXES):
        if uri_path.startswith(prefix):
            return f"deny_prefix:{prefix}"
    return None


def matched_shared_terms(text: str) -> list[str]:
    lower = text.lower()
    found = [term for term in sorted(SHARED_LANGUAGE_TERMS) if term.lower() in lower]
    return found


def classify(path: Path | str, *, root: Path | None = None, text: str | None = None) -> UriFilterResult:
    display_path = normalize_path(path, root)
    uri_path = uri_relative_path(path, root)
    if uri_path is None:
        return UriFilterResult(SCHEMA_VERSION, display_path, None, "not_uri", "outside_uri", [])

    deny = deny_reason(uri_path)
    if deny:
        return UriFilterResult(SCHEMA_VERSION, display_path, uri_path, "uri_internal", deny, [])

    if is_whitelisted(uri_path):
        return UriFilterResult(SCHEMA_VERSION, display_path, uri_path, "aios_relevant", "whitelist", [])

    body = text
    if body is None:
        try:
            body = Path(path).read_text(encoding="utf-8", errors="replace")
        except OSError:
            body = ""
    terms = matched_shared_terms(body)
    if uri_path.startswith("uri/docs/") and len(terms) >= 2:
        return UriFilterResult(
            SCHEMA_VERSION,
            display_path,
            uri_path,
            "aios_relevant",
            "shared_language_terms",
            terms,
        )

    return UriFilterResult(SCHEMA_VERSION, display_path, uri_path, "operator_review", "borderline_uri_doc", terms)


def review_queue_path(root: Path, result: UriFilterResult) -> Path:
    digest = hashlib.sha256((result.uri_path or result.path).encode("utf-8")).hexdigest()[:16]
    return root / ".aios" / "uri_review_queue" / f"{digest}.md"


def write_review_queue(root: Path, result: UriFilterResult) -> Path:
    path = review_queue_path(root, result)
    path.parent.mkdir(parents=True, exist_ok=True)
    lines = [
        "# Uri Operator Review",
        "",
        f"- generated_at: `{now_iso()}`",
        f"- schema_version: `{SCHEMA_VERSION}`",
        f"- source_path: `{result.path}`",
        f"- uri_path: `{result.uri_path}`",
        f"- outcome: `{result.outcome}`",
        f"- reason: `{result.reason}`",
        f"- matched_terms: `{json.dumps(result.matched_terms, ensure_ascii=False)}`",
        "",
        "This receipt stores path-level review metadata only. Re-read the source",
        "file under a later explicit contract before importing any content.",
        "",
    ]
    path.write_text("\n".join(lines), encoding="utf-8")
    return path


def payload(result: UriFilterResult, *, review_queue: Path | None = None) -> dict[str, Any]:
    data = asdict(result)
    if review_queue is not None:
        data["review_queue"] = review_queue.as_posix()
    return data


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Classify Uri markdown relevance for AIOS")
    parser.add_argument("path")
    parser.add_argument("--root", default=".")
    parser.add_argument("--write-review", action="store_true")
    parser.add_argument("--json", action="store_true")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    root = Path(args.root).resolve()
    path = Path(args.path)
    if not path.is_absolute():
        path = root / path
    result = classify(path, root=root)
    review_path = None
    if args.write_review and result.outcome == "operator_review":
        review_path = write_review_queue(root, result)
    if args.json:
        print(json.dumps(payload(result, review_queue=review_path), ensure_ascii=False, indent=2, sort_keys=True))
    else:
        print(f"{result.schema_version} path={result.path} outcome={result.outcome} reason={result.reason}")
    return 0 if result.outcome in OUTCOMES else 1


if __name__ == "__main__":
    raise SystemExit(main())
