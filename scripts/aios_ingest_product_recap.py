#!/usr/bin/env python3
"""Ingest product-repo recap packets per aios.product_recap.v1.

Implements ASC-0173 Packet A. Reads JSON packets from `.aios/inbox/myworld/`,
validates consent + privacy invariants, and produces:

  (a) a MemoryOS-importable markdown at docs/imports/product_recap__*.md
  (b) a CapabilityOS observation entry at .aios/capability_observations/<repo>_capabilities.json

Does NOT auto-accept memory drafts (Invariant 2). Does NOT execute product-repo
code. Does NOT bulk-pull git history.
"""

from __future__ import annotations

import argparse
import json
import re
import shutil
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parent))
from aios_workbench_registry import is_emit_eligible, registered_repos  # noqa: E402

SCHEMA = "aios.product_recap.v1"
CONSENT_EXACT = (
    "I authorize AIOS to ingest this packet as a MemoryOS draft "
    "and CapabilityOS observation."
)
FORBIDDEN_MARKERS = (
    "BEGIN PRIVATE KEY",
    "OPENAI_API_KEY",
    "ANTHROPIC_API_KEY",
    "sk-",
    "_from_desktop/",
    "dain/",
    "minyoung/",
    ".env",
    "raw_exports/",
)
SECRET_PATTERN = re.compile(r"sk-[A-Za-z0-9]{16,}")


def now_iso() -> str:
    return datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds")


def find_packets(inbox: Path) -> list[Path]:
    return sorted(inbox.glob("product_recap__*.json"))


def validate(packet: dict[str, Any], path: Path, root: Path) -> tuple[bool, str]:
    if packet.get("schema") != SCHEMA:
        return False, f"schema_mismatch: expected {SCHEMA}, got {packet.get('schema')!r}"
    repo = packet.get("product_repo")
    if not repo or not is_emit_eligible(root, repo):
        return False, (
            f"repo_not_registered: {repo!r} — register it in "
            f".aios/workbench/registry.json (aios init / ASC-0181). "
            f"registered: {sorted(registered_repos(root))}"
        )
    consent = packet.get("consent")
    if consent != CONSENT_EXACT:
        return False, "consent_missing_or_mismatch (Invariant 6)"
    for required in ("sprint_id", "sprint_subject", "operator_signed_by", "evidence_refs", "capabilities_used"):
        if not packet.get(required):
            return False, f"missing_required_field: {required}"
    if not isinstance(packet["evidence_refs"], list) or len(packet["evidence_refs"]) == 0:
        return False, "evidence_refs_must_be_nonempty_list (Invariant 5)"
    if not isinstance(packet["capabilities_used"], list):
        return False, "capabilities_used_must_be_list"
    blob = json.dumps(packet, ensure_ascii=False)
    for marker in FORBIDDEN_MARKERS:
        if marker in blob:
            return False, f"forbidden_marker: {marker!r} (Invariant 7)"
    if SECRET_PATTERN.search(blob):
        return False, "secret_pattern_detected (Invariant 7)"
    return True, "ok"


def render_markdown(packet: dict[str, Any]) -> str:
    repo = packet["product_repo"]
    sprint_id = packet["sprint_id"]
    subject = packet["sprint_subject"]
    caps = ", ".join(packet["capabilities_used"])
    refs = "\n".join(f"- {ref}" for ref in packet["evidence_refs"])
    files = packet.get("files_touched") or []
    files_block = "\n".join(f"- `{f}`" for f in files) if files else "- (none recorded)"
    commit = packet.get("commit_sha") or "(none recorded)"
    return f"""# Product Recap — {repo} / {sprint_id}

- product_repo: {repo}
- sprint_id: {sprint_id}
- subject: {subject}
- commit_sha: {commit}
- capabilities_used: {caps}
- operator_signed_by: {packet["operator_signed_by"]}
- consent: verified
- ingested_at: {now_iso()}
- schema: {SCHEMA}

## Evidence Refs (provenance chain)

{refs}

## Files Touched

{files_block}

## Origin

Emitted by `{repo}` operator under ASC-0173 consent-gated recap surface.
This record is a MemoryOS DRAFT. Acceptance requires explicit review
(DNA Invariant 2 — no auto-accept).
"""


def upsert_capability_observations(
    obs_path: Path,
    packet: dict[str, Any],
) -> dict[str, Any]:
    """Append observations to a per-repo capability observation file.

    The file is a small JSON catalog usable by CapabilityOS's --catalog flag.
    Each observation card describes one capability the product repo used,
    cited to the packet path.
    """
    repo = packet["product_repo"]
    if obs_path.exists():
        catalog = json.loads(obs_path.read_text(encoding="utf-8"))
    else:
        catalog = {
            "contract": "capabilityos.catalog.v1",
            "capabilities": [],
        }
    by_id: dict[str, dict[str, Any]] = {c["id"]: c for c in catalog["capabilities"]}
    for capability_name in packet["capabilities_used"]:
        cap_id = f"cap_{repo}_{_slug(capability_name)}"
        existing = by_id.get(cap_id)
        evidence_ref = f".aios/inbox/myworld/product_recap__{repo}__{packet['sprint_id']}.json"
        if existing is None:
            existing = {
                "id": cap_id,
                "name": f"{repo} observed: {capability_name}",
                "kind": "tool",
                "description": (
                    f"Capability `{capability_name}` observed in product repo "
                    f"`{repo}` via emit-based recap packets (ASC-0173). "
                    "Recommendation-only — does not execute."
                ),
                "domains": [repo, capability_name, "product_repo_observation"],
                "actions": ["observe"],
                "inputs": ["product_recap_packet"],
                "outputs": ["observation_record"],
                "risk": "low",
                "cost": "free",
                "latency": "fast",
                "privacy": "local",
                "requires_network": False,
                "executes_tools": False,
                "status": "active",
                "evidence_refs": [evidence_ref],
                "observation_count": 1,
                "first_seen_at": now_iso(),
                "last_seen_at": now_iso(),
                "observed_sprints": [packet["sprint_id"]],
            }
            catalog["capabilities"].append(existing)
            by_id[cap_id] = existing
        else:
            if evidence_ref not in existing["evidence_refs"]:
                existing["evidence_refs"].append(evidence_ref)
            existing["observation_count"] = int(existing.get("observation_count", 0)) + 1
            existing["last_seen_at"] = now_iso()
            sprints = existing.setdefault("observed_sprints", [])
            if packet["sprint_id"] not in sprints:
                sprints.append(packet["sprint_id"])
    obs_path.parent.mkdir(parents=True, exist_ok=True)
    obs_path.write_text(json.dumps(catalog, indent=2, ensure_ascii=False), encoding="utf-8")
    return catalog


def _slug(s: str) -> str:
    return re.sub(r"[^a-z0-9_]+", "_", s.lower()).strip("_")


def process_packet(packet_path: Path, root: Path, apply: bool) -> dict[str, Any]:
    try:
        packet = json.loads(packet_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        return {"path": str(packet_path), "ok": False, "reason": f"invalid_json: {exc}"}

    ok, reason = validate(packet, packet_path, root)
    receipt: dict[str, Any] = {
        "path": str(packet_path),
        "ok": ok,
        "reason": reason,
        "schema": packet.get("schema"),
        "product_repo": packet.get("product_repo"),
        "sprint_id": packet.get("sprint_id"),
        "ingested_at": now_iso(),
    }

    if not ok:
        if apply:
            rejected_dir = root / ".aios" / "rejected" / "myworld"
            rejected_dir.mkdir(parents=True, exist_ok=True)
            new_path = rejected_dir / packet_path.name
            shutil.move(str(packet_path), str(new_path))
            (new_path.with_suffix(".reject.json")).write_text(
                json.dumps(receipt, indent=2, ensure_ascii=False), encoding="utf-8"
            )
            receipt["moved_to"] = str(new_path)
        return receipt

    repo = packet["product_repo"]
    sprint_id = packet["sprint_id"]
    import_md_dir = root / "docs" / "imports"
    import_md_path = import_md_dir / f"product_recap__{repo}__{sprint_id}.md"
    obs_path = root / ".aios" / "capability_observations" / f"{repo}_capabilities.json"

    if apply:
        import_md_dir.mkdir(parents=True, exist_ok=True)
        import_md_path.write_text(render_markdown(packet), encoding="utf-8")
        upsert_capability_observations(obs_path, packet)
        processed_dir = root / ".aios" / "processed" / "myworld"
        processed_dir.mkdir(parents=True, exist_ok=True)
        new_path = processed_dir / packet_path.name
        shutil.move(str(packet_path), str(new_path))
        receipt["moved_to"] = str(new_path)
        receipt["memoryos_import_markdown"] = str(import_md_path.relative_to(root))
        receipt["capabilityos_observation_catalog"] = str(obs_path.relative_to(root))
        (new_path.with_suffix(".receipt.json")).write_text(
            json.dumps(receipt, indent=2, ensure_ascii=False), encoding="utf-8"
        )
    else:
        receipt["memoryos_import_markdown"] = str(import_md_path.relative_to(root))
        receipt["capabilityos_observation_catalog"] = str(obs_path.relative_to(root))
        receipt["dry_run"] = True
    return receipt


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Ingest aios.product_recap.v1 packets")
    parser.add_argument("--inbox", default=".aios/inbox/myworld")
    parser.add_argument("--root", default=".", help="myworld repo root")
    parser.add_argument("--apply", action="store_true", help="actually write outputs and move packets")
    parser.add_argument("--json", action="store_true", help="emit JSON output")
    args = parser.parse_args(argv)

    root = Path(args.root).resolve()
    inbox = (root / args.inbox).resolve() if not Path(args.inbox).is_absolute() else Path(args.inbox)
    if not inbox.exists():
        print(f"inbox not found: {inbox}", file=sys.stderr)
        return 2

    receipts = [process_packet(p, root, args.apply) for p in find_packets(inbox)]
    summary = {
        "schema": "aios.ingest_product_recap.v1",
        "ran_at": now_iso(),
        "inbox": str(inbox),
        "apply": args.apply,
        "packets_seen": len(receipts),
        "packets_ok": sum(1 for r in receipts if r["ok"]),
        "packets_rejected": sum(1 for r in receipts if not r["ok"]),
        "receipts": receipts,
    }
    if args.json:
        print(json.dumps(summary, indent=2, ensure_ascii=False))
    else:
        for r in receipts:
            status = "OK " if r["ok"] else "REJ"
            print(f"{status} {r['path']}: {r['reason']}")
        print(
            f"-- {summary['packets_seen']} seen, "
            f"{summary['packets_ok']} ok, "
            f"{summary['packets_rejected']} rejected, "
            f"apply={args.apply}"
        )
    return 0 if all(r["ok"] for r in receipts) else 1


if __name__ == "__main__":
    sys.exit(main())
