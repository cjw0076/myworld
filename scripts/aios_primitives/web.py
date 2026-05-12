"""Cited web fetch/search primitive.

Mirrors claude@myworld's WebFetch / WebSearch. Always writes a cited evidence
artifact matching the `aios.web_research_receipt.v1` shape established by
ASC-0031 so downstream MemoryOS review (ASC-0041) can consume it.

This primitive does NOT bind a network capability. It records a plan +
operator-supplied evidence. Actual network fetch happens in execution layer
(hivemind harness or operator browser); this surface stores the receipt.
"""
from __future__ import annotations

import json
import uuid
from pathlib import Path
from typing import Any

from . import events as ev

SCHEMA = "aios.web_research_receipt.v1"


def _receipts_dir(root: Path | None = None) -> Path:
    return ev.ensure_dir("web_receipts", root)


def fetch(url: str, claims: list[str], publisher: str | None = None,
          accessed_at: str | None = None, source_type: str = "documentation",
          source_date: str | None = None, record: str | None = None,
          root: Path | None = None) -> dict[str, Any]:
    """Record a cited web fetch.

    `claims`: short paraphrased claims (no raw page bodies). At least one
    required per stop condition `web_fetch_uncited`.
    `record`: output path; if None, generates under `.aios/primitives/web_receipts/`.
    """
    if not claims:
        raise ValueError("web.fetch requires at least one claim")
    rid = "w-" + uuid.uuid4().hex[:12]
    receipt = {
        "schema_version": SCHEMA,
        "capability_route": "capabilityos.web_research_route.v1",
        "receipt_id": rid,
        "kind": "fetch",
        "research_question": None,
        "sources": [
            {
                "url": url,
                "publisher": publisher,
                "accessed_at": accessed_at or ev.now_iso()[:10],
                "source_date": source_date,
                "source_type": source_type,
                "claims": claims,
            }
        ],
        "summary_claims": claims,
        "created_at": ev.now_iso(),
    }
    if record:
        out_path = Path(record)
        out_path.parent.mkdir(parents=True, exist_ok=True)
    else:
        out_path = _receipts_dir(root) / f"{rid}.json"
    out_path.write_text(json.dumps(receipt, indent=2, ensure_ascii=False), encoding="utf-8")
    ev.emit("web.fetched", rid, {"url": url, "path": out_path.as_posix()}, root)
    receipt["path"] = out_path.as_posix()
    return receipt


def search(query: str, sources: list[dict[str, Any]], record: str | None = None,
           root: Path | None = None) -> dict[str, Any]:
    """Record a cited web search.

    `sources`: list of dicts with at least `url` + `claims`.
    """
    if not sources:
        raise ValueError("web.search requires at least one source")
    for s in sources:
        if not s.get("url") or not s.get("claims"):
            raise ValueError("each source needs url and claims")
    rid = "w-" + uuid.uuid4().hex[:12]
    normalized: list[dict[str, Any]] = []
    for s in sources:
        normalized.append(
            {
                "url": s["url"],
                "publisher": s.get("publisher"),
                "accessed_at": s.get("accessed_at") or ev.now_iso()[:10],
                "source_date": s.get("source_date"),
                "source_type": s.get("source_type", "search_result"),
                "claims": s["claims"],
            }
        )
    receipt = {
        "schema_version": SCHEMA,
        "capability_route": "capabilityos.web_research_route.v1",
        "receipt_id": rid,
        "kind": "search",
        "research_question": query,
        "sources": normalized,
        "summary_claims": [c for s in normalized for c in s["claims"]],
        "created_at": ev.now_iso(),
    }
    if record:
        out_path = Path(record)
        out_path.parent.mkdir(parents=True, exist_ok=True)
    else:
        out_path = _receipts_dir(root) / f"{rid}.json"
    out_path.write_text(json.dumps(receipt, indent=2, ensure_ascii=False), encoding="utf-8")
    ev.emit("web.searched", rid, {"query": query, "path": out_path.as_posix()}, root)
    receipt["path"] = out_path.as_posix()
    return receipt
