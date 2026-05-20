#!/usr/bin/env python3
"""ASC-0211 L4 — frontier surface (CLI variant).

Reads the AIOS control snapshot's `frontier_queue` block (populated by
the 3 L3 routines: discomfort_inject, frontier_question, boundary_probe)
and prints it. Compact and operator-readable. Designed to be runnable
*offline* by a peer who wants to see what L3 has queued before
returning to chat.

Pair with `scripts/aios_control_snapshot.py` (which produces the
underlying snapshot) and any chat/Control-Center UI that wishes to
render the same data (e.g., apps/control's renderAnticipatorySurface).

Schema consumed: aios.frontier_queue.v1 (see aios_control_snapshot.py).
"""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent


KIND_LABEL = {
    "aios_discomfort_inject": "DISCOMFORT",
    "aios_frontier_question": "FRONTIER",
    "aios_boundary_probe": "PROBE",
}


def load_frontier_queue(snapshot_path: Path | None = None,
                        regenerate: bool = False) -> dict:
    if regenerate or snapshot_path is None or not snapshot_path.exists():
        r = subprocess.run(
            [sys.executable, str(REPO_ROOT / "scripts" / "aios_control_snapshot.py")],
            capture_output=True, text=True, check=False,
        )
        if r.returncode != 0:
            raise SystemExit(f"snapshot generation failed: {r.stderr[:500]}")
        snap = json.loads(r.stdout)
    else:
        snap = json.loads(snapshot_path.read_text(encoding="utf-8"))
    return snap.get("frontier_queue", {})


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description="ASC-0211 L4 frontier surface (CLI)")
    p.add_argument("--snapshot",
                   type=Path,
                   default=REPO_ROOT / "apps" / "control" / "aios-control-snapshot.json",
                   help="path to existing snapshot json")
    p.add_argument("--regenerate", action="store_true",
                   help="ignore snapshot file; regenerate via aios_control_snapshot.py")
    p.add_argument("--origin", default=None,
                   help="filter by origin (aios_discomfort_inject / aios_frontier_question / aios_boundary_probe)")
    p.add_argument("--limit", type=int, default=10)
    p.add_argument("--json", action="store_true")
    args = p.parse_args(argv)

    fq = load_frontier_queue(args.snapshot, regenerate=args.regenerate)
    drafts = fq.get("drafts", [])
    if args.origin:
        drafts = [d for d in drafts if d.get("origin") == args.origin]
    drafts = drafts[: args.limit]

    if args.json:
        print(json.dumps({
            "schema_version": fq.get("schema_version"),
            "queued": fq.get("queued"),
            "by_origin": fq.get("by_origin"),
            "drafts": drafts,
        }, indent=2, ensure_ascii=False))
    else:
        print(f"# AIOS frontier queue — ASC-0211 L3 transcendence drafts")
        print(f"queued: {fq.get('queued', 0)}   by_origin: {fq.get('by_origin', {})}")
        if not drafts:
            print("(empty)")
        for d in drafts:
            label = KIND_LABEL.get(d.get("origin", ""), d.get("origin", "?"))
            kind = d.get("kind", "")
            target = d.get("target", "") or ""
            content = (d.get("content") or "").replace("\n", " ")
            print(f"\n[{label}/{kind}] target={target}")
            print(f"  {content[:280]}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
