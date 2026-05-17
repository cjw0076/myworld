#!/usr/bin/env python3
"""Resolve typed AIOS addresses to bounded, privacy-aware records."""

from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any


SCHEMA_VERSION = "aios.address.resolution.v1"
PRIVATE_PATH_RE = re.compile(r"(^/|(^|/)(\.env|raw_exports|_from_desktop|dain|minyoung)(/|$))")


@dataclass(frozen=True)
class AiosAddress:
    raw: str
    kind: str
    parts: list[str]

    @property
    def identifier(self) -> str:
        return "/".join(self.parts)


def parse_address(value: str) -> AiosAddress:
    if not value.startswith("aios://"):
        raise ValueError("address must start with aios://")
    rest = value.removeprefix("aios://").strip("/")
    parts = [part for part in rest.split("/") if part]
    if len(parts) < 2:
        raise ValueError("address must include kind and id")
    return AiosAddress(raw=value, kind=parts[0], parts=parts[1:])


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    rows: list[dict[str, Any]] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        try:
            row = json.loads(line)
        except json.JSONDecodeError:
            continue
        if isinstance(row, dict):
            rows.append(row)
    return rows


def latest_by_id(rows: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    result: dict[str, dict[str, Any]] = {}
    for row in rows:
        row_id = row.get("id")
        if isinstance(row_id, str):
            result[row_id] = row
    return result


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


def contract_path(root: Path, contract_id: str) -> Path | None:
    normalized = contract_id.upper()
    matches = sorted((root / "docs" / "contracts").glob(f"{normalized}-*.md"))
    return matches[0] if matches else None


def bounded_content(value: Any, limit: int = 300) -> str:
    text = " ".join(str(value or "").split())
    return text[:limit]


def is_private_ref(value: str) -> bool:
    return bool(PRIVATE_PATH_RE.search(value))


def redact_record(record: dict[str, Any], audience: str) -> dict[str, Any]:
    if audience != "remote":
        return record
    redacted: dict[str, Any] = {}
    for key, value in record.items():
        if key in {"raw_refs", "content", "stdout", "stderr", "prompt", "full_log"}:
            continue
        if isinstance(value, str):
            redacted[key] = "(private)" if is_private_ref(value) else value
        elif isinstance(value, list):
            redacted[key] = [
                "(private)" if isinstance(item, str) and is_private_ref(item) else item
                for item in value
                if not (isinstance(item, str) and is_private_ref(item))
            ]
        elif isinstance(value, dict):
            redacted[key] = redact_record(value, audience)
        else:
            redacted[key] = value
    return redacted


def envelope(
    address: AiosAddress,
    *,
    found: bool,
    owner_os: str,
    owner_repo: str,
    privacy: str,
    status: str,
    summary: str,
    storage_refs: list[str],
    provenance_refs: list[str],
    record: dict[str, Any] | None = None,
    audience: str = "local",
) -> dict[str, Any]:
    safe_record = redact_record(record or {}, audience)
    safe_storage = [ref for ref in storage_refs if audience == "local" or not is_private_ref(ref)]
    safe_provenance = [ref for ref in provenance_refs if audience == "local" or not is_private_ref(ref)]
    return {
        "schema_version": SCHEMA_VERSION,
        "address": address.raw,
        "found": found,
        "kind": address.kind,
        "id": address.identifier,
        "owner_os": owner_os,
        "owner_repo": owner_repo,
        "privacy": privacy,
        "status": status,
        "summary": summary,
        "storage_refs": safe_storage,
        "provenance_refs": safe_provenance,
        "record": safe_record,
    }


def resolve_contract(root: Path, address: AiosAddress, audience: str) -> dict[str, Any]:
    cid = address.parts[0].upper()
    path = contract_path(root, cid)
    if not path:
        return envelope(address, found=False, owner_os="myworld", owner_repo="myworld", privacy="local", status="missing", summary="", storage_refs=[], provenance_refs=[], audience=audience)
    text = path.read_text(encoding="utf-8")
    frontmatter, body = parse_frontmatter(text)
    record = {
        "contract_id": cid,
        "slug": frontmatter.get("slug"),
        "goal": frontmatter.get("goal"),
        "status": frontmatter.get("status"),
        "path": path.relative_to(root).as_posix(),
    }
    return envelope(
        address,
        found=True,
        owner_os="myworld",
        owner_repo="myworld",
        privacy="local",
        status=frontmatter.get("status") or "unknown",
        summary=frontmatter.get("goal") or bounded_content(body),
        storage_refs=[path.relative_to(root).as_posix()],
        provenance_refs=[path.relative_to(root).as_posix()],
        record=record,
        audience=audience,
    )


def resolve_dispatch(root: Path, address: AiosAddress, audience: str) -> dict[str, Any]:
    dispatch_id = address.identifier
    events = [row for row in read_jsonl(root / ".aios" / "state" / "dispatches.jsonl") if row.get("dispatch_id") == dispatch_id]
    if not events:
        return envelope(address, found=False, owner_os="myworld", owner_repo="myworld", privacy="local", status="missing", summary="", storage_refs=[], provenance_refs=[], audience=audience)
    latest = events[-1]
    refs = [str(row.get("result")) for row in events if row.get("result")]
    return envelope(
        address,
        found=True,
        owner_os="myworld",
        owner_repo="myworld",
        privacy="local",
        status=str(latest.get("status") or latest.get("event") or "unknown"),
        summary=str(latest.get("goal") or latest.get("reason") or latest.get("event") or ""),
        storage_refs=[".aios/state/dispatches.jsonl", *refs],
        provenance_refs=[str(row.get("contract_path")) for row in events if row.get("contract_path")],
        record={"events": events[-12:]},
        audience=audience,
    )


def resolve_memoryos_row(root: Path, address: AiosAddress, *, kind: str, ledger: Path, owner_label: str, audience: str) -> dict[str, Any]:
    rows = latest_by_id(read_jsonl(root / ledger))
    record = rows.get(address.identifier)
    if not record:
        return envelope(address, found=False, owner_os="MemoryOS", owner_repo="memoryOS", privacy="local", status="missing", summary="", storage_refs=[], provenance_refs=[], audience=audience)
    refs = [str(item) for item in record.get("raw_refs", []) if isinstance(item, str)]
    if not refs:
        refs = [str(item) for item in record.get("evidence_refs", []) if isinstance(item, str)]
    return envelope(
        address,
        found=True,
        owner_os="MemoryOS",
        owner_repo="memoryOS",
        privacy="local",
        status=str(record.get("status") or record.get("evidence_state") or "recorded"),
        summary=bounded_content(record.get("content") or record.get("path") or record.get("type") or owner_label),
        storage_refs=[ledger.as_posix()],
        provenance_refs=refs,
        record=record,
        audience=audience,
    )


def resolve_run(root: Path, address: AiosAddress, audience: str) -> dict[str, Any]:
    if len(address.parts) < 2 or address.parts[0] != "hive":
        raise ValueError("run address must look like aios://run/hive/<run_id>")
    run_id = address.parts[1]
    run_dir = root / "hivemind" / ".runs" / run_id
    if not run_dir.exists():
        return envelope(address, found=False, owner_os="Hive Mind", owner_repo="hivemind", privacy="local", status="missing", summary="", storage_refs=[], provenance_refs=[], audience=audience)
    state_path = run_dir / "run_state.json"
    state = {}
    if state_path.exists():
        try:
            state = json.loads(state_path.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            state = {}
    refs = [path.relative_to(root).as_posix() for path in sorted(run_dir.glob("*")) if path.is_file()]
    return envelope(
        address,
        found=True,
        owner_os="Hive Mind",
        owner_repo="hivemind",
        privacy="local",
        status=str(state.get("status") or "recorded"),
        summary=bounded_content(state.get("user_request") or state.get("task") or run_id),
        storage_refs=[run_dir.relative_to(root).as_posix()],
        provenance_refs=refs[:20],
        record={"run_id": run_id, "run_state": state, "artifact_count": len(refs)},
        audience=audience,
    )


def load_capability_cards(root: Path) -> list[dict[str, Any]]:
    cap_dir = root / "CapabilityOS"
    if cap_dir.exists():
        completed = subprocess.run(
            [sys.executable, "-m", "capabilityos.cli", "list", "--json"],
            cwd=cap_dir,
            text=True,
            capture_output=True,
            check=False,
        )
        if completed.returncode == 0:
            try:
                data = json.loads(completed.stdout)
                cards = data.get("capabilities")
                if isinstance(cards, list):
                    return [item for item in cards if isinstance(item, dict)]
            except json.JSONDecodeError:
                pass
    fixture = root / "CapabilityOS" / "tests" / "fixtures" / "capabilities.json"
    if fixture.exists():
        try:
            data = json.loads(fixture.read_text(encoding="utf-8"))
            cards = data.get("capabilities") if isinstance(data, dict) else data
            if isinstance(cards, list):
                return [item for item in cards if isinstance(item, dict)]
        except json.JSONDecodeError:
            pass
    return []


def resolve_capability(root: Path, address: AiosAddress, audience: str) -> dict[str, Any]:
    cap_id = address.identifier
    if address.parts[0] == "provider-route":
        provider = address.parts[1] if len(address.parts) > 1 else ""
        record = {
            "id": cap_id,
            "provider": provider,
            "recommendation_only": True,
            "executes_tools": False,
            "risk_notes": ["provider route address is metadata only"],
        }
        return envelope(
            address,
            found=bool(provider),
            owner_os="CapabilityOS",
            owner_repo="CapabilityOS",
            privacy="local",
            status="planned" if provider else "missing",
            summary=f"Provider route metadata for {provider}",
            storage_refs=["CapabilityOS/capabilityos/catalog.py"],
            provenance_refs=[],
            record=record,
            audience=audience,
        )
    cards = {str(card.get("id")): card for card in load_capability_cards(root)}
    card = cards.get(cap_id)
    if not card:
        return envelope(address, found=False, owner_os="CapabilityOS", owner_repo="CapabilityOS", privacy="local", status="missing", summary="", storage_refs=[], provenance_refs=[], audience=audience)
    return envelope(
        address,
        found=True,
        owner_os="CapabilityOS",
        owner_repo="CapabilityOS",
        privacy=str(card.get("privacy") or "local"),
        status=str(card.get("status") or "active"),
        summary=bounded_content(card.get("description") or card.get("name")),
        storage_refs=["CapabilityOS/capabilityos/catalog.py"],
        provenance_refs=[str(item) for item in card.get("evidence_refs", []) if isinstance(item, str)],
        record={**card, "recommendation_only": True},
        audience=audience,
    )


def resolve(root: Path, raw_address: str, *, audience: str = "local") -> dict[str, Any]:
    address = parse_address(raw_address)
    if address.kind == "contract":
        return resolve_contract(root, address, audience)
    if address.kind == "dispatch":
        return resolve_dispatch(root, address, audience)
    if address.kind == "memory":
        return resolve_memoryos_row(root, address, kind="memory", ledger=Path("memoryOS/memory/objects.jsonl"), owner_label="memory object", audience=audience)
    if address.kind == "source":
        return resolve_memoryos_row(root, address, kind="source", ledger=Path("memoryOS/memory/sources.jsonl"), owner_label="source artifact", audience=audience)
    if address.kind == "trace":
        return resolve_memoryos_row(root, address, kind="trace", ledger=Path("memoryOS/memory/retrieval_traces.jsonl"), owner_label="retrieval trace", audience=audience)
    if address.kind == "hyperedge":
        return resolve_memoryos_row(root, address, kind="hyperedge", ledger=Path("memoryOS/ontology/hyperedges.jsonl"), owner_label="hyperedge", audience=audience)
    if address.kind == "run":
        return resolve_run(root, address, audience)
    if address.kind == "capability":
        return resolve_capability(root, address, audience)
    return envelope(address, found=False, owner_os="unknown", owner_repo="unknown", privacy="local", status="unsupported_kind", summary="", storage_refs=[], provenance_refs=[], audience=audience)


def build_index(root: Path) -> dict[str, Any]:
    contracts: list[str] = []
    for path in (root / "docs" / "contracts").glob("ASC-*.md"):
        match = re.match(r"^(ASC-\d+)", path.stem, re.IGNORECASE)
        if match:
            contracts.append(match.group(1).upper())
    contracts = sorted(set(contracts))
    memory_ids = sorted(latest_by_id(read_jsonl(root / "memoryOS" / "memory" / "objects.jsonl")))
    capabilities = sorted(str(card.get("id")) for card in load_capability_cards(root) if card.get("id"))
    runs = sorted(path.name for path in (root / "hivemind" / ".runs").glob("*") if path.is_dir())
    return {
        "schema_version": "aios.address.index.v1",
        "counts": {
            "contract": len(contracts),
            "memory": len(memory_ids),
            "capability": len(capabilities),
            "hive_run": len(runs),
        },
        "samples": {
            "contract": [f"aios://contract/{item}" for item in contracts[-10:]],
            "memory": [f"aios://memory/{item}" for item in memory_ids[-10:]],
            "capability": [f"aios://capability/{item}" for item in capabilities[:10]],
            "hive_run": [f"aios://run/hive/{item}" for item in runs[-10:]],
        },
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Resolve AIOS typed addresses")
    parser.add_argument("--root", default=".", help="myworld root")
    sub = parser.add_subparsers(dest="cmd", required=True)

    resolve_cmd = sub.add_parser("resolve", help="resolve one aios:// address")
    resolve_cmd.add_argument("address")
    resolve_cmd.add_argument("--audience", choices=("local", "remote"), default="local")
    resolve_cmd.add_argument("--json", action="store_true")

    redact_cmd = sub.add_parser("redact", help="resolve one address for a remote audience")
    redact_cmd.add_argument("address")
    redact_cmd.add_argument("--audience", choices=("remote",), default="remote")
    redact_cmd.add_argument("--json", action="store_true")

    index_cmd = sub.add_parser("index", help="summarize available address spaces")
    index_cmd.add_argument("--json", action="store_true")

    args = parser.parse_args(argv)
    root = Path(args.root).resolve()
    if args.cmd == "index":
        payload = build_index(root)
    elif args.cmd == "redact":
        payload = resolve(root, args.address, audience="remote")
    else:
        payload = resolve(root, args.address, audience=args.audience)
    print(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
