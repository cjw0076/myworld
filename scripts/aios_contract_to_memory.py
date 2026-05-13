#!/usr/bin/env python3
"""Emit MemoryOS draft payloads from closed AIOS smart contracts."""

from __future__ import annotations

import argparse
import json
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


SCHEMA_VERSION = "aios.contract_closeout_memory.v1"


def now_iso() -> str:
    return datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds")


def parse_frontmatter(text: str) -> tuple[dict[str, str], str]:
    if not text.startswith("---\n"):
        return {}, text
    end = text.find("\n---\n", 4)
    if end == -1:
        return {}, text
    data: dict[str, str] = {}
    current_key: str | None = None
    for raw in text[4:end].splitlines():
        if not raw.strip():
            continue
        if raw.startswith((" ", "\t")) and current_key:
            data[current_key] = f"{data[current_key]} {raw.strip()}".strip()
            continue
        key, sep, value = raw.partition(":")
        if sep:
            current_key = key.strip()
            data[current_key] = value.strip().strip('"')
    return data, text[end + 5 :]


def find_contract(root: Path, contract: str) -> Path:
    target = contract.upper()
    if contract.endswith(".md") or "/" in contract:
        path = (root / contract).resolve() if not Path(contract).is_absolute() else Path(contract)
        if not path.exists():
            raise SystemExit(f"contract not found: {path}")
        return path
    matches = sorted((root / "docs" / "contracts").glob(f"{target}-*.md"))
    if not matches:
        matches = sorted((root / "docs" / "contracts").glob(f"{target.lower()}-*.md"))
    if not matches:
        raise SystemExit(f"contract not found: {contract}")
    return matches[0]


def section_after_heading(body: str, heading: str) -> str:
    match = re.search(rf"^##\s+{re.escape(heading)}\s*$", body, flags=re.MULTILINE)
    if not match:
        return ""
    rest = body[match.end() :]
    next_heading = re.search(r"^##\s+", rest, flags=re.MULTILINE)
    return rest[: next_heading.start()] if next_heading else rest


def bullet_lines(text: str) -> list[str]:
    values: list[str] = []
    current: str | None = None
    for raw in text.splitlines():
        stripped = raw.strip()
        if not stripped:
            continue
        if stripped.startswith("- "):
            if current:
                values.append(current)
            current = stripped[2:].strip().strip("`")
        elif current and raw.startswith((" ", "\t")):
            current = f"{current} {stripped}".strip()
        elif current:
            values.append(current)
            current = None
    if current:
        values.append(current)
    return values


def markdown_refs(text: str) -> list[str]:
    refs: list[str] = []
    for value in re.findall(r"`([^`]+)`", text):
        if re.search(r"\s", value):
            continue
        if "/" in value or value.startswith(("ASC-", ".aios/", "docs/", "memoryOS/")):
            refs.append(value)
    for value in re.findall(r"\b[0-9a-f]{7,40}\b", text):
        refs.append(value)
    return refs


def cited_contracts(text: str, own_id: str) -> list[str]:
    found = sorted(set(re.findall(r"\bASC-\d{4}\b", text)))
    return [item for item in found if item != own_id]


def ledger_excerpt(root: Path, contract_id: str) -> list[str]:
    path = root / "docs" / "AIOS_AGENT_LEDGER.md"
    if not path.exists():
        return []
    lines = path.read_text(encoding="utf-8").splitlines()
    hits: list[str] = []
    for idx, line in enumerate(lines):
        if contract_id not in line:
            continue
        start = max(0, idx - 1)
        end = min(len(lines), idx + 5)
        hits.extend(lines[start:end])
        break
    return [line.strip() for line in hits if line.strip()][:8]


def result_packets(root: Path, contract_id: str) -> list[dict[str, Any]]:
    observations: list[dict[str, Any]] = []
    for path in sorted((root / ".aios" / "outbox").glob("*/*.json")):
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            continue
        if str(payload.get("contract_id", "")).upper() != contract_id:
            continue
        observations.append(
            {
                "repo": payload.get("target_repo"),
                "result_ref": path.relative_to(root).as_posix(),
                "status": payload.get("status"),
                "fallback_used": payload.get("fallback_used"),
                "final_agent": payload.get("final_agent") or payload.get("agent"),
            }
        )
    return observations


def state_observations(root: Path, contract_id: str) -> list[dict[str, Any]]:
    path = root / ".aios" / "state" / "dispatches.jsonl"
    if not path.exists():
        return []
    observations: list[dict[str, Any]] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        try:
            event = json.loads(line)
        except json.JSONDecodeError:
            continue
        if str(event.get("contract_id", "")).upper() != contract_id:
            continue
        if event.get("event") not in {"sent", "collected", "released", "held", "retried", "escalated"}:
            continue
        observations.append(
            {
                "repo": event.get("repo"),
                "event": event.get("event"),
                "status": event.get("status"),
                "agent": event.get("agent"),
                "result_ref": event.get("result"),
            }
        )
    return observations[-12:]


def build_payload(root: Path, contract: str, *, closed_by: str = "codex") -> dict[str, Any]:
    contract_path = find_contract(root, contract)
    text = contract_path.read_text(encoding="utf-8")
    frontmatter, body = parse_frontmatter(text)
    contract_id = (frontmatter.get("contract_id") or contract_path.stem.split("-", 1)[0]).upper()
    receipts = section_after_heading(body, "Receipts")
    receipt_bullets = bullet_lines(receipts)
    evidence_refs = sorted(
        set(
            [contract_path.relative_to(root).as_posix()]
            + markdown_refs(receipts)
            + [item for item in receipt_bullets if item.startswith((".aios/", "docs/", "memoryOS/"))]
        )
    )
    if not evidence_refs:
        evidence_refs = [contract_path.relative_to(root).as_posix()]
    ledger = ledger_excerpt(root, contract_id)
    if ledger:
        evidence_refs.append("docs/AIOS_AGENT_LEDGER.md")
    evidence_refs = sorted(set(evidence_refs))
    key_learnings = receipt_bullets or ledger[:4]
    observations = result_packets(root, contract_id) or state_observations(root, contract_id)
    return {
        "schema_version": SCHEMA_VERSION,
        "contract_id": contract_id,
        "slug": frontmatter.get("slug") or contract_path.stem,
        "goal": frontmatter.get("goal") or "",
        "status": frontmatter.get("status") or "unknown",
        "closed_at": frontmatter.get("closed") or now_iso(),
        "closed_by": closed_by,
        "evidence_refs": evidence_refs,
        "key_learnings": key_learnings[:12],
        "cross_references": cited_contracts(text + "\n" + "\n".join(ledger), contract_id),
        "substrate_observations": observations,
        "source_refs": [contract_path.relative_to(root).as_posix(), "docs/AIOS_AGENT_LEDGER.md"],
        "privacy": {
            "raw_provider_output_included": False,
            "local_paths": "manifest_refs_only",
        },
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Convert AIOS contract closeout into MemoryOS draft JSON")
    sub = parser.add_subparsers(dest="cmd", required=True)
    emit = sub.add_parser("emit", help="emit contract closeout memory payload")
    emit.add_argument("--contract", required=True, help="contract id, e.g. ASC-0095")
    emit.add_argument("--root", default=".", help="myworld root")
    emit.add_argument("--closed-by", default="codex")
    emit.add_argument("--json", action="store_true", help="emit JSON")
    args = parser.parse_args(argv)

    if args.cmd == "emit":
        payload = build_payload(Path(args.root).resolve(), args.contract, closed_by=args.closed_by)
        print(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True))
        return 0
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
