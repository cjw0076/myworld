#!/usr/bin/env python3
"""ASC-0205 CC4 — external knowledge -> memoryOS draft organ.

Bridges `aios_primitives.web` (which writes `aios.web_research_receipt.v1`)
into a `aios.memory_draft_review_request.v1` packet that memoryOS can ingest
as a draft (status=draft, review_status=needs_more_evidence).

Draft-first invariant: never auto-accepts. The packet always lands as a
review-request, and the operator (or memoryOS reviewer agent) decides.

Usage
-----

    python scripts/aios_external_knowledge_organ.py \\
        --topic "Hermes Agent memory model" \\
        --url https://github.com/NousResearch/hermes-agent \\
        --claim "Hermes Agent uses FTS5 session search + LLM summarization for cross-session recall" \\
        --claim "Hermes spawns isolated subagents for parallel workstreams" \\
        --publisher "GitHub README (NousResearch/hermes-agent)" \\
        --memory-type observation \\
        --confidence 0.55

Each invocation writes:
1. one web research receipt under `.aios/primitives/web_receipts/<rid>.json`
2. one memory-draft review-request packet per claim under
   `.aios/inbox/memoryOS/<draft_id>.memoryOS.json`

When `--dispatch` is passed, the packet path is also handed to
`memoryos --root <memoryOS> drafts import-review-request` directly (skipping
the watcher hop). Otherwise the existing AIOS child_watcher / dispatch
machinery will pick the packet up.
"""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
import uuid
from datetime import datetime, timezone
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
if str(HERE) not in sys.path:
    sys.path.insert(0, str(HERE))

from aios_primitives import web as aios_web  # noqa: E402


SCHEMA = "aios.memory_draft_review_request.v1"
DEFAULT_MEMORY_TYPE = "observation"
DEFAULT_CONFIDENCE = 0.5
ALLOWED_TYPES = {
    "observation",
    "claim",
    "decision",
    "task",
    "question",
    "constraint",
    "assumption",
    "preference",
    "artifact",
    "reflection",
    "user_pattern",
}


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")


def _slug(topic: str) -> str:
    out = []
    for ch in topic.lower().strip():
        if ch.isalnum():
            out.append(ch)
        elif out and out[-1] != "-":
            out.append("-")
    s = "".join(out).strip("-")
    return s[:48] or "topic"


def build_packets(
    topic: str,
    url: str,
    claims: list[str],
    publisher: str | None,
    memory_type: str,
    confidence: float,
    project: str,
    root: Path,
) -> tuple[Path, list[Path]]:
    """Return (receipt_path, [packet_paths_one_per_claim])."""
    if memory_type not in ALLOWED_TYPES:
        raise ValueError(f"memory_type must be one of {sorted(ALLOWED_TYPES)}")
    if not claims:
        raise ValueError("at least one --claim required")

    receipt = aios_web.fetch(
        url=url,
        claims=claims,
        publisher=publisher,
        source_type="external_system_documentation",
        root=root,
    )
    receipt_path = Path(receipt["path"])
    # source_artifact ref must be repo-relative for memoryOS resolver
    source_ref = receipt_path.relative_to(root).as_posix()

    inbox = root / ".aios" / "inbox" / "memoryOS"
    inbox.mkdir(parents=True, exist_ok=True)

    slug = _slug(topic)
    packet_paths: list[Path] = []
    for idx, claim in enumerate(claims):
        draft_id = f"ext:{slug}:{idx}"
        request_id = "mdrev-ext-" + uuid.uuid4().hex[:12]
        packet = {
            "schema_version": SCHEMA,
            "request_id": request_id,
            "dispatch_id": request_id,
            "contract_id": "ASC-0205",
            "contract_path": "docs/contracts/ASC-0205-aios-completion-north-star.md",
            "target_repo": "memoryOS",
            "agent": "memoryOS-reviewer",
            "goal": f"Review external-knowledge draft from {publisher or url} ({topic}).",
            "source_artifact": source_ref,
            "draft_id": draft_id,
            "return_to": f".aios/outbox/memoryOS/{request_id}.memoryOS.result.json",
            "review_policy": {"auto_accept": False, "draft_first": True},
            "draft": {
                "type": memory_type,
                "origin": "external_knowledge_organ",
                "status": "draft",
                "confidence": confidence,
                "content": claim,
                "raw_refs": [source_ref, url],
                "provenance": {
                    "source": "aios_external_knowledge_organ",
                    "topic": topic,
                    "publisher": publisher,
                    "url": url,
                    "captured_at": _now_iso(),
                    "receipt_id": receipt["receipt_id"],
                },
                "project": project,
            },
            "scope": {"allowed_files": [], "forbidden_files": [".env"]},
            "created_at": _now_iso(),
        }
        packet_path = inbox / f"{request_id}.memoryOS.json"
        packet_path.write_text(json.dumps(packet, indent=2, ensure_ascii=False), encoding="utf-8")
        packet_paths.append(packet_path)

    return receipt_path, packet_paths


def dispatch_to_memoryos(memoryos_root: Path, packet_path: Path) -> dict:
    """Run `memoryos drafts import-review-request` against a packet."""
    cmd = [
        sys.executable, "-m", "memoryos",
        "--root", str(memoryos_root),
        "drafts", "import-review-request",
        str(packet_path),
        "--reviewer", "external_knowledge_organ",
        "--note", "draft-first import via aios_external_knowledge_organ",
        "--json",
    ]
    r = subprocess.run(cmd, capture_output=True, text=True, check=False)
    out = {"returncode": r.returncode, "stdout": r.stdout, "stderr": r.stderr}
    if r.stdout.strip():
        try:
            out["envelope"] = json.loads(r.stdout)
        except json.JSONDecodeError:
            out["envelope"] = None
    return out


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description="ASC-0205 CC4 external-knowledge organ")
    p.add_argument("--topic", required=True, help="short topic name (slugified for draft_id)")
    p.add_argument("--url", required=True)
    p.add_argument("--claim", action="append", default=[], required=True,
                   help="paraphrased claim; repeat for multiple draft rows")
    p.add_argument("--publisher", default=None)
    p.add_argument("--memory-type", default=DEFAULT_MEMORY_TYPE)
    p.add_argument("--confidence", type=float, default=DEFAULT_CONFIDENCE)
    p.add_argument("--project", default="AIOS")
    p.add_argument("--root", type=Path, default=ROOT,
                   help="myworld root (defaults to repo root)")
    p.add_argument("--dispatch", action="store_true",
                   help="also run memoryos drafts import-review-request immediately")
    p.add_argument("--memoryos-root", type=Path, default=ROOT / "memoryOS")
    p.add_argument("--json", action="store_true")
    args = p.parse_args(argv)

    receipt_path, packet_paths = build_packets(
        topic=args.topic,
        url=args.url,
        claims=args.claim,
        publisher=args.publisher,
        memory_type=args.memory_type,
        confidence=args.confidence,
        project=args.project,
        root=args.root,
    )

    out = {
        "schema_version": "aios.external_knowledge_organ.v1",
        "topic": args.topic,
        "url": args.url,
        "receipt_path": receipt_path.as_posix(),
        "packets": [pp.as_posix() for pp in packet_paths],
        "dispatched": [],
    }
    if args.dispatch:
        for pp in packet_paths:
            out["dispatched"].append({"packet": pp.as_posix(),
                                       "result": dispatch_to_memoryos(args.memoryos_root, pp)})
    if args.json:
        print(json.dumps(out, indent=2, ensure_ascii=False))
    else:
        print(f"receipt: {out['receipt_path']}")
        for pp in out["packets"]:
            print(f"packet: {pp}")
        if args.dispatch:
            for d in out["dispatched"]:
                print(f"dispatched: {d['packet']} rc={d['result']['returncode']}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
