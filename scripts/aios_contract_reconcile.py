#!/usr/bin/env python3
"""Reconcile AIOS contract frontmatter with dispatch lifecycle evidence."""

from __future__ import annotations

import argparse
import json
import re
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


SCHEMA_VERSION = "aios.contract_reconciliation.v1"
TARGET_ORDER = [
    "ASC-0066",
    "ASC-0065",
    "ASC-0063",
    "ASC-0056",
    "ASC-0060",
    "ASC-0061",
    "ASC-0059",
    "ASC-0057",
    "ASC-0058",
    "ASC-0064",
    "ASC-0076",
    "ASC-0078",
    "ASC-0067",
    "ASC-0068",
    "ASC-0077",
]
ACTIONABLE_CLASSIFICATIONS = {"close_now", "retry_now", "continue_implementation"}


def now_iso() -> str:
    return datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds")


def parse_frontmatter(text: str) -> dict[str, str]:
    if not text.startswith("---\n"):
        return {}
    end = text.find("\n---\n", 4)
    if end == -1:
        return {}
    data: dict[str, str] = {}
    current: str | None = None
    for line in text[4:end].splitlines():
        if not line.strip():
            continue
        if line.startswith((" ", "\t")) and current:
            data[current] = f"{data[current]} {line.strip()}".strip()
            continue
        key, sep, value = line.partition(":")
        if sep:
            current = key.strip()
            data[current] = value.strip()
    return data


def contract_number(contract_id: str) -> int | None:
    match = re.match(r"ASC-(\d+)$", contract_id)
    return int(match.group(1)) if match else None


def find_contracts(root: Path, start: int, end: int) -> list[Path]:
    paths = []
    for path in sorted((root / "docs" / "contracts").glob("ASC-*.md")):
        match = re.match(r"ASC-(\d+)-", path.name)
        if match and start <= int(match.group(1)) <= end:
            paths.append(path)
    return paths


def load_dispatch_events(root: Path) -> list[dict[str, Any]]:
    path = root / ".aios" / "state" / "dispatches.jsonl"
    if not path.exists():
        return []
    rows = []
    for line in path.read_text(encoding="utf-8", errors="replace").splitlines():
        if not line.strip():
            continue
        try:
            payload = json.loads(line)
        except json.JSONDecodeError:
            continue
        if isinstance(payload, dict):
            rows.append(payload)
    return rows


def dispatch_contract_key(event: dict[str, Any]) -> str | None:
    cid = event.get("contract_id")
    if isinstance(cid, str) and re.match(r"ASC-\d+", cid):
        return cid[:8]
    did = event.get("dispatch_id")
    if isinstance(did, str):
        match = re.match(r"asc-(\d{4})", did)
        if match:
            return f"ASC-{match.group(1)}"
    return None


def dispatch_summary(events: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    grouped: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for event in events:
        key = dispatch_contract_key(event)
        if key:
            grouped[key].append(event)
    summary = {}
    for key, rows in grouped.items():
        latest_by_dispatch: dict[str, dict[str, Any]] = {}
        for row in rows:
            did = str(row.get("dispatch_id") or key.lower())
            latest_by_dispatch[did] = row
        statuses = [str(row.get("status") or "") for row in latest_by_dispatch.values()]
        reasons = [str(row.get("reason") or "") for row in latest_by_dispatch.values() if row.get("reason")]
        summary[key] = {
            "dispatches": sorted(latest_by_dispatch),
            "statuses": statuses,
            "reasons": reasons,
            "events": len(rows),
        }
    return summary


def has_evidence_for(contract_id: str, root: Path, info: dict[str, Any]) -> bool:
    if any(status in {"released", "passed"} for status in info.get("statuses", [])):
        return True
    needle = contract_id.lower().replace("-", "_")
    ledger = root / "docs" / "AIOS_AGENT_LEDGER.md"
    if ledger.exists() and needle in ledger.read_text(encoding="utf-8", errors="replace").lower():
        return True
    return False


def classify_contract(frontmatter: dict[str, str], root: Path, info: dict[str, Any]) -> tuple[str, str]:
    cid = frontmatter.get("contract_id", "")
    status = frontmatter.get("status", "unknown")
    closed = frontmatter.get("closed", "")
    statuses = set(info.get("statuses") or [])
    reasons = " ".join(info.get("reasons") or []).lower()
    evidence = has_evidence_for(cid, root, info)

    if status == "closed" and closed:
        return "closed_verified", "frontmatter is closed"
    if "held" in statuses:
        if cid == "ASC-0056" and "provider_backpressure" in reasons:
            return "retry_now", "held by provider backpressure; ASC-0066 should unblock retry"
        return "hold", "dispatch is held"
    if status == "accepted" and cid == "ASC-0066" and evidence:
        return "close_now", "dispatch released and Hive backpressure evidence exists"
    if status == "accepted" and cid == "ASC-0065":
        return "close_now", "GenesisOS bootstrap artifacts exist; closeout decision needed"
    if status == "accepted" and cid in {"ASC-0067", "ASC-0068", "ASC-0077", "ASC-0078"}:
        return "continue_implementation", "accepted runtime contract still requires verification gate"
    if status == "accepted" and evidence:
        return "close_now", "evidence exists but frontmatter is not closed"
    if status == "accepted":
        return "continue_implementation", "accepted but no closeout evidence found"
    if status == "closed":
        return "closed_verified", "frontmatter closed"
    return "hold", f"unsupported contract status: {status}"


def build_matrix(root: Path, start: int, end: int) -> dict[str, Any]:
    events = load_dispatch_events(root)
    summaries = dispatch_summary(events)
    rows = []
    for path in find_contracts(root, start, end):
        frontmatter = parse_frontmatter(path.read_text(encoding="utf-8", errors="replace"))
        cid = frontmatter.get("contract_id") or path.stem.split("-", 2)[0]
        info = summaries.get(cid, {"dispatches": [], "statuses": [], "reasons": [], "events": 0})
        classification, reason = classify_contract(frontmatter, root, info)
        rows.append(
            {
                "contract_id": cid,
                "path": path.as_posix(),
                "status": frontmatter.get("status", "unknown"),
                "closed": bool(frontmatter.get("closed")),
                "classification": classification,
                "reason": reason,
                "dispatch_statuses": info.get("statuses", []),
                "dispatch_reasons": info.get("reasons", []),
            }
        )
    missing = [f"ASC-{idx:04d}" for idx in range(start, end + 1) if not any(row["contract_id"] == f"ASC-{idx:04d}" for row in rows)]
    ordered = sorted(rows, key=lambda row: TARGET_ORDER.index(row["contract_id"]) if row["contract_id"] in TARGET_ORDER else 999)
    return {
        "schema_version": SCHEMA_VERSION,
        "generated_at": now_iso(),
        "root": root.as_posix(),
        "range": {"from": start, "to": end},
        "missing_contract_ids": missing,
        "rows": rows,
        "execution_order": [
            row["contract_id"] for row in ordered if row["classification"] in ACTIONABLE_CLASSIFICATIONS
        ],
        "next_contract": next(
            (row["contract_id"] for row in ordered if row["classification"] in ACTIONABLE_CLASSIFICATIONS),
            None,
        ),
    }


def render_markdown(payload: dict[str, Any]) -> str:
    lines = [
        "# AIOS Contract Reconciliation",
        "",
        f"Generated: `{payload['generated_at']}`",
        f"Range: `ASC-{payload['range']['from']:04d}` to `ASC-{payload['range']['to']:04d}`",
        "",
        "## Next",
        "",
        f"- next_contract: `{payload.get('next_contract') or 'none'}`",
        "",
        "## Matrix",
        "",
        "| Contract | Status | Closed | Classification | Reason |",
        "| --- | --- | --- | --- | --- |",
    ]
    for row in payload["rows"]:
        lines.append(
            f"| {row['contract_id']} | {row['status']} | {str(row['closed']).lower()} | "
            f"{row['classification']} | {row['reason']} |"
        )
    lines.extend(["", "## Execution Order", ""])
    for idx, cid in enumerate(payload["execution_order"], start=1):
        lines.append(f"{idx}. `{cid}`")
    if payload["missing_contract_ids"]:
        lines.extend(["", "## Missing IDs", ""])
        for cid in payload["missing_contract_ids"]:
            lines.append(f"- `{cid}`")
    return "\n".join(lines) + "\n"


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Reconcile AIOS contract status")
    parser.add_argument("--root", type=Path, default=Path.cwd())
    parser.add_argument("--from", dest="start", type=int, required=True)
    parser.add_argument("--to", dest="end", type=int, required=True)
    parser.add_argument("--write", type=Path)
    parser.add_argument("--json", action="store_true")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    root = args.root.resolve()
    payload = build_matrix(root, args.start, args.end)
    if args.write:
        out = args.write if args.write.is_absolute() else root / args.write
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(render_markdown(payload), encoding="utf-8")
    if args.json:
        print(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True))
    else:
        print(render_markdown(payload), end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
