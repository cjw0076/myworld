#!/usr/bin/env python3
"""ASC-0211 L3 routine #2 — discomfort injection.

Reads convergence audit results (`aios.convergence_audit.v1`) and, for
contracts that scored *footprint_consensus* OR *mixed* with footprint
>= 2, generates a *negation draft* — a memoryOS draft challenging one
unspoken assumption.

The draft is advisory: `status: draft`, `auto_accept: false`. A peer
must approve. Bypassing this routine is fine — purpose is to *manufacture
discomfort* per [[feedback_discomfort_as_creativity_source]], not to
gate decisions.

Output schema: `aios.discomfort_injection.v1` packets written to
`.aios/inbox/memoryOS/` so the existing memoryOS review flow handles
them like any other draft.
"""
from __future__ import annotations

import argparse
import json
import re
import sys
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parent.parent


# Generic negation templates — kept short so the draft is a *question*,
# not a manifesto. The whole point is to surface discomfort, not assert.
NEGATION_TEMPLATES = [
    "What if {slug} was accepted because both peers wanted to move on, not because it survived adversarial review?",
    "If a third peer (different substrate or human reviewer) re-read {contract_id} cold, what would they reject?",
    "{contract_id} cites no external sources / few memory_id refs. What outside frame would invalidate its claim?",
    "What stop condition in {contract_id} would have triggered if the writer were not the same peer as the closer?",
    "Footprint signature in {contract_id}: rapid close + frame echo. Negation: the closed claim is a *restatement* of the proposing claim, not a *test* of it.",
]


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")


def _pick_template(row: dict[str, Any]) -> str:
    """Choose the most fitting negation template given the row's footprint hits.

    Order matters: more *specific* signatures first. The generic
    "no external sources" template is the catch-all only after the
    specific footprint signatures (auto-close, frame-echo, self-endorse)
    have been ruled out.
    """
    hits = row.get("footprint_hits", {}) or {}
    if "auto_close_under_10min" in hits:
        return NEGATION_TEMPLATES[4]
    if "frame_echo" in hits:
        return NEGATION_TEMPLATES[3]
    if "self_endorsement" in hits:
        return NEGATION_TEMPLATES[1]
    if "no_evidence_refs" in hits or row.get("challenge_hits", {}).get("memory_citation", 0) == 0:
        return NEGATION_TEMPLATES[2]
    return NEGATION_TEMPLATES[0]


def build_drafts(audit: dict[str, Any], min_footprint: int = 2,
                  contract_id_filter: list[str] | None = None) -> list[dict[str, Any]]:
    rows = audit.get("rows", [])
    drafts: list[dict[str, Any]] = []
    for row in rows:
        if contract_id_filter and row.get("contract_id") not in contract_id_filter:
            continue
        verdict = row.get("verdict", "")
        footprint = row.get("footprint_score", 0)
        if verdict == "real_challenge":
            continue
        if verdict == "footprint_consensus" or (verdict == "mixed" and footprint >= min_footprint) or (verdict == "indeterminate" and footprint >= min_footprint):
            template = _pick_template(row)
            question = template.format(
                contract_id=row.get("contract_id") or "<unknown>",
                slug=row.get("slug") or "this contract",
            )
            draft = {
                "schema_version": "aios.memory_draft_review_request.v1",
                "request_id": "discomfort-" + uuid.uuid4().hex[:12],
                "dispatch_id": "discomfort-" + uuid.uuid4().hex[:12],
                "contract_id": "ASC-0211",
                "contract_path": "docs/contracts/ASC-0211-aios-cognitive-prosthesis-layer.md",
                "target_repo": "memoryOS",
                "agent": "aios_discomfort_inject@ASC-0211",
                "goal": f"Discomfort signal against {row.get('contract_id')} — challenge before convergence.",
                "source_artifact": ".aios/outbox/audits/convergence_audit_2026-05-20.json",
                "draft_id": f"discomfort:{row.get('contract_id')}:{uuid.uuid4().hex[:6]}",
                "return_to": f".aios/outbox/memoryOS/discomfort-{row.get('contract_id')}.memoryOS.result.json",
                "review_policy": {"auto_accept": False, "draft_first": True},
                "draft": {
                    "type": "question",
                    "origin": "aios_discomfort_inject",
                    "status": "draft",
                    "confidence": 0.4,
                    "content": question,
                    "raw_refs": [
                        f"docs/contracts/{row.get('path').split('/')[-1] if row.get('path') else ''}",
                        ".aios/outbox/audits/convergence_audit_2026-05-20.json",
                    ],
                    "provenance": {
                        "source": "aios_discomfort_inject",
                        "audit_verdict": verdict,
                        "challenge_score": row.get("challenge_score"),
                        "footprint_score": footprint,
                        "footprint_hits": list((row.get("footprint_hits") or {}).keys()),
                        "generated_at": _now_iso(),
                        "template_index": NEGATION_TEMPLATES.index(template),
                    },
                    "project": "AIOS",
                },
                "scope": {"allowed_files": [], "forbidden_files": [".env"]},
                "created_at": _now_iso(),
            }
            drafts.append(draft)
    return drafts


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description="ASC-0211 L3 routine #2 — discomfort injection")
    p.add_argument("--audit", type=Path, required=True,
                   help="path to aios.convergence_audit.v1 JSON")
    p.add_argument("--min-footprint", type=int, default=2)
    p.add_argument("--contract-id", action="append", default=None,
                   help="restrict to specific contract id(s); repeat")
    p.add_argument("--out-dir", type=Path,
                   default=REPO_ROOT / ".aios" / "inbox" / "memoryOS",
                   help="where to write draft packets")
    p.add_argument("--dry-run", action="store_true",
                   help="print drafts to stdout without writing files")
    p.add_argument("--json", action="store_true")
    args = p.parse_args(argv)

    audit = json.loads(args.audit.read_text(encoding="utf-8"))
    drafts = build_drafts(audit, args.min_footprint, args.contract_id)

    written: list[str] = []
    if not args.dry_run:
        args.out_dir.mkdir(parents=True, exist_ok=True)
        for d in drafts:
            path = args.out_dir / f"{d['request_id']}.memoryOS.json"
            path.write_text(json.dumps(d, indent=2, ensure_ascii=False), encoding="utf-8")
            written.append(path.as_posix())

    out = {
        "schema_version": "aios.discomfort_injection.v1",
        "audit_source": args.audit.as_posix(),
        "drafts_generated": len(drafts),
        "drafts_written": written,
        "dry_run": args.dry_run,
        "drafts": drafts if args.dry_run else None,
    }
    if args.json:
        print(json.dumps(out, indent=2, ensure_ascii=False))
    else:
        print(f"discomfort drafts generated: {len(drafts)}")
        for d in drafts:
            print(f"  {d['draft']['provenance']['audit_verdict']:14} "
                  f"footprint={d['draft']['provenance']['footprint_score']:>2}  "
                  f"{d['draft']['content']}")
        if args.dry_run:
            print("(dry-run: no files written)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
