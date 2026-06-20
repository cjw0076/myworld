#!/usr/bin/env python3
"""HiveMind trace extraction job — OpenAI Evals/Traces archive before deprecation.

OpenAI Traces/Evals timeline:
  2026-10-31: read-only cutoff
  2026-11-30: full shutdown

This script pages through the OpenAI Evals + Traces APIs and archives the
structural data (names, statuses, counts — NO raw content) as HiveMind
run_receipts. Privacy: DNA #7 — content never stored, tool names + status only.

Archive path: .aios/trace_archive/<YYYY-MM-DD>/
  evals_index.jsonl     — eval run metadata
  traces_index.jsonl    — trace metadata
  extract_receipt.json  — run summary + verification hash

Usage:
  python scripts/aios_trace_extract.py --dry-run
  python scripts/aios_trace_extract.py --out .aios/trace_archive
  python scripts/aios_trace_extract.py --evals-only
  python scripts/aios_trace_extract.py --traces-only
  OPENAI_API_KEY=sk-... python scripts/aios_trace_extract.py

Schema: aios.hivemind.trace_extract.v1
"""
from __future__ import annotations

import argparse
import datetime
import hashlib
import json
import os
import sys
import time
from pathlib import Path
from typing import Iterator

# No LiteLLM — direct openai SDK only (LiteLLM banned 2026-03-24 supply chain)
try:
    import openai
    _HAS_OPENAI = True
except ImportError:
    _HAS_OPENAI = False

SCHEMA = "aios.hivemind.trace_extract.v1"
DEADLINE_READONLY = "2026-10-31"
DEADLINE_SHUTDOWN  = "2026-11-30"

# Content fields we NEVER store (DNA #7)
_CONTENT_BLACKLIST = frozenset({
    "content", "text", "input", "output", "prompt", "completion",
    "messages", "system_prompt", "instructions", "tool_calls",
    "arguments", "result", "body", "response",
})

# Safe structural fields to keep
_SAFE_EVAL_FIELDS = {
    "id", "name", "model", "status", "created_at", "metadata",
    "data_source_config", "testing_criteria", "per_model_usage",
    "result_counts", "error",
}
_SAFE_TRACE_FIELDS = {
    "id", "name", "status", "created_at", "model", "metadata",
    "usage", "temperature", "top_p", "max_tokens", "tool_choice",
    "parallel_tool_calls",
}


def _redact(obj: dict, safe_keys: set) -> dict:
    """Keep only safe structural keys; strip content fields."""
    out = {}
    for k, v in obj.items():
        if k in _CONTENT_BLACKLIST:
            continue
        if k not in safe_keys:
            continue
        out[k] = v
    return out


def _client(api_key: str | None = None) -> "openai.OpenAI":
    # SDK resolves auth automatically: OPENAI_API_KEY env → ~/.openai/credentials
    # No manual key check needed — headless CLI execution carries auth through env.
    kwargs = {}
    if api_key:
        kwargs["api_key"] = api_key
    return openai.OpenAI(**kwargs)


def _page_evals(client: "openai.OpenAI", limit: int = 100) -> Iterator[dict]:
    """Page through /v1/evals returning redacted structural records."""
    after = None
    while True:
        kwargs: dict = {"limit": limit}
        if after:
            kwargs["after"] = after
        try:
            resp = client.evals.list(**kwargs)
        except AttributeError:
            # SDK version without evals support
            print("[WARN] openai.evals API not available in this SDK version.")
            return
        except Exception as exc:  # noqa: BLE001
            print(f"[WARN] evals list failed: {exc}")
            return
        items = getattr(resp, "data", [])
        if not items:
            break
        for item in items:
            raw = item.model_dump() if hasattr(item, "model_dump") else dict(item)
            yield _redact(raw, _SAFE_EVAL_FIELDS)
        last = items[-1]
        after = getattr(last, "id", None) or (last.get("id") if isinstance(last, dict) else None)
        if not after or not getattr(resp, "has_more", False):
            break
        time.sleep(0.2)


def _page_traces(client: "openai.OpenAI", limit: int = 100) -> Iterator[dict]:
    """Page through /v1/traces returning redacted structural records."""
    after = None
    while True:
        kwargs: dict = {"limit": limit}
        if after:
            kwargs["after"] = after
        try:
            resp = client.responses.list(**kwargs)
        except AttributeError:
            print("[WARN] openai.responses API not available in this SDK version.")
            return
        except Exception as exc:  # noqa: BLE001
            print(f"[WARN] traces list failed: {exc}")
            return
        items = getattr(resp, "data", [])
        if not items:
            break
        for item in items:
            raw = item.model_dump() if hasattr(item, "model_dump") else dict(item)
            yield _redact(raw, _SAFE_TRACE_FIELDS)
        last = items[-1]
        after = getattr(last, "id", None) or (last.get("id") if isinstance(last, dict) else None)
        if not after or not getattr(resp, "has_more", False):
            break
        time.sleep(0.2)


def _fingerprint(records: list[dict]) -> str:
    blob = json.dumps(records, sort_keys=True, ensure_ascii=False)
    return hashlib.sha256(blob.encode()).hexdigest()[:16]


def _days_until(date_str: str) -> int:
    target = datetime.date.fromisoformat(date_str)
    return (target - datetime.date.today()).days


def extract(
    out_dir: Path,
    api_key: str | None = None,
    dry_run: bool = False,
    evals_only: bool = False,
    traces_only: bool = False,
) -> dict:
    today = datetime.date.today().isoformat()
    archive = out_dir / today
    archive.mkdir(parents=True, exist_ok=True)

    days_to_readonly = _days_until(DEADLINE_READONLY)
    days_to_shutdown  = _days_until(DEADLINE_SHUTDOWN)

    print(f"[aios_trace_extract] deadline: read-only in {days_to_readonly}d, "
          f"shutdown in {days_to_shutdown}d")

    if dry_run:
        print("[dry-run] would connect to OpenAI and page through evals + traces.")
        print(f"[dry-run] archive path: {archive}")
        return {
            "schema": SCHEMA,
            "dry_run": True,
            "archive_path": str(archive),
            "days_to_readonly": days_to_readonly,
            "days_to_shutdown": days_to_shutdown,
        }

    if not _HAS_OPENAI:
        print("[ERROR] openai package not installed. pip install openai")
        sys.exit(1)

    client = _client(api_key)

    eval_records: list[dict] = []
    trace_records: list[dict] = []

    if not traces_only:
        print("[evals] fetching...")
        for rec in _page_evals(client):
            eval_records.append(rec)
        print(f"[evals] {len(eval_records)} records extracted")

    if not evals_only:
        print("[traces] fetching...")
        for rec in _page_traces(client):
            trace_records.append(rec)
        print(f"[traces] {len(trace_records)} records extracted")

    # Write archives — names + status only, no content
    evals_path = archive / "evals_index.jsonl"
    traces_path = archive / "traces_index.jsonl"

    if eval_records:
        with evals_path.open("w", encoding="utf-8") as fh:
            for r in eval_records:
                fh.write(json.dumps(r, ensure_ascii=False) + "\n")

    if trace_records:
        with traces_path.open("w", encoding="utf-8") as fh:
            for r in trace_records:
                fh.write(json.dumps(r, ensure_ascii=False) + "\n")

    receipt = {
        "schema": SCHEMA,
        "extracted_at": datetime.datetime.now().astimezone().isoformat(timespec="seconds"),
        "produced_by": "claude@myworld",
        "archive_path": str(archive),
        "eval_count": len(eval_records),
        "trace_count": len(trace_records),
        "eval_fingerprint":  _fingerprint(eval_records)  if eval_records  else None,
        "trace_fingerprint": _fingerprint(trace_records) if trace_records else None,
        "days_to_readonly": days_to_readonly,
        "days_to_shutdown":  days_to_shutdown,
        "privacy_note": "Content fields stripped. Names, statuses, counts only. DNA #7.",
        "authority": "hivemind_run_receipt",
        "gap_closes": "trace-extraction-deadline (ASC-0278)",
    }

    receipt_path = archive / "extract_receipt.json"
    receipt_path.write_text(json.dumps(receipt, indent=2, ensure_ascii=False), encoding="utf-8")

    print(f"[done] receipt: {receipt_path}")
    return receipt


def _build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        description="HiveMind: extract OpenAI Evals/Traces before deprecation"
    )
    p.add_argument("--out", default=".aios/trace_archive",
                   help="Archive output directory (default: .aios/trace_archive)")
    p.add_argument("--api-key", default=None, help="OpenAI API key override (SDK auto-resolves from env if omitted)")
    p.add_argument("--dry-run", action="store_true", help="Show what would run without calling API")
    p.add_argument("--evals-only", action="store_true", help="Extract evals only")
    p.add_argument("--traces-only", action="store_true", help="Extract traces only")
    p.add_argument("--json", action="store_true", help="Output receipt as JSON")
    return p


if __name__ == "__main__":
    args = _build_parser().parse_args()
    root = Path(__file__).resolve().parents[1]
    out = root / args.out
    result = extract(
        out_dir=out,
        api_key=args.api_key,
        dry_run=args.dry_run,
        evals_only=args.evals_only,
        traces_only=args.traces_only,
    )
    if args.json:
        print(json.dumps(result, indent=2, ensure_ascii=False))
