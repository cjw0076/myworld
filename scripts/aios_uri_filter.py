#!/usr/bin/env python3
"""URI path classifier for the AIOS doc scout.

Classifies files under the uri/ product repo as:
  - aios_relevant: carries AIOS architectural signal
  - uri_internal: implementation detail, internal to the uri product
  - operator_review: ambiguous — needs human triage

Priority order:
  1. deny_prefix  → always uri_internal (even if text has AIOS terms)
  2. shared_language_terms (≥2 AIOS terms in text) → aios_relevant
  3. whitelist prefix → aios_relevant
  4. default → operator_review
"""
from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Sequence


# Paths that are always internal to the URI product — never AIOS-relevant
_DENY_PREFIXES: list[str] = [
    "uri/hive/",
    "uri/products/",
    "uri/apps/",
    "uri/.aios/",
]

# Paths always relevant to AIOS (when no conflicting text signal)
_WHITELIST_PREFIXES: list[str] = [
    "uri/docs/",
]

# AIOS shared vocabulary — terms that signal cross-system relevance
_AIOS_TERMS: list[str] = [
    "aios", "dispatch", "memoryos", "capabilityos", "genesisos",
    "hivemind", "hive", "contract", "capability", "routing",
    "provenance", "ledger", "operator", "workstream",
]


@dataclass
class ClassifyResult:
    uri_path: str
    outcome: str   # "aios_relevant" | "uri_internal" | "operator_review" | "not_uri"
    reason: str
    matched_terms: list[str] = field(default_factory=list)


def _extract_uri_path(path: Path, root: Path | None) -> str | None:
    """Normalize path to a uri/... string, or None if not under uri/."""
    if root is not None:
        try:
            rel = str(path.relative_to(root)).replace("\\", "/")
        except ValueError:
            rel = str(path).replace("\\", "/")
    else:
        rel = str(path).replace("\\", "/")
        if rel.startswith("myworld/"):
            rel = rel[len("myworld/"):]

    # Only classify paths that live under uri/
    idx = rel.find("uri/")
    if idx < 0:
        return None
    # Make sure it's an actual uri/ path segment, not e.g. "capabilityos/"
    candidate = rel[idx:]
    if not candidate.startswith("uri/"):
        return None
    return candidate


def classify(path: Path, root: Path | None = None, text: str | None = None) -> ClassifyResult:
    """Classify a path (and optionally its text content) for AIOS relevance.

    Returns outcome "not_uri" for files not under the uri/ product directory.
    """
    uri_path = _extract_uri_path(path, root)

    if uri_path is None:
        # Not a URI repo file — caller should scan it normally
        return ClassifyResult(
            uri_path=str(path),
            outcome="not_uri",
            reason="not_under_uri",
        )

    # 1. Deny list — wins over everything
    for prefix in _DENY_PREFIXES:
        if uri_path.startswith(prefix):
            return ClassifyResult(
                uri_path=uri_path,
                outcome="uri_internal",
                reason=f"deny_prefix:{uri_path}",
            )

    # 2. Shared language check — text with ≥2 AIOS terms → aios_relevant
    if text:
        lower = text.lower()
        matched = [t for t in _AIOS_TERMS if re.search(r'\b' + re.escape(t) + r'\b', lower)]
        if len(matched) >= 2:
            return ClassifyResult(
                uri_path=uri_path,
                outcome="aios_relevant",
                reason="shared_language_terms",
                matched_terms=matched,
            )

    # 3. Whitelist prefix — path is in known AIOS-relevant docs
    for prefix in _WHITELIST_PREFIXES:
        if uri_path.startswith(prefix):
            return ClassifyResult(
                uri_path=uri_path,
                outcome="aios_relevant",
                reason="whitelist",
            )

    # 4. Default — needs human triage
    return ClassifyResult(
        uri_path=uri_path,
        outcome="operator_review",
        reason="no_signal",
    )


def write_review_queue(root: Path, result: ClassifyResult) -> Path:
    """Write a review receipt (path-level metadata only, never text content)."""
    queue_dir = root / ".aios" / "review_queue"
    queue_dir.mkdir(parents=True, exist_ok=True)
    ts = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%f")
    slug = re.sub(r"[^a-z0-9_-]", "_", result.uri_path.lower())[:40]
    receipt_path = queue_dir / f"{ts}_{slug}.json"
    payload = {
        "source_path": result.uri_path,
        "outcome": result.outcome,
        "reason": result.reason,
        "matched_terms": result.matched_terms,
        "ts": ts,
    }
    receipt_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    return receipt_path
