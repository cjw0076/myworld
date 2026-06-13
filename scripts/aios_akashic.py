#!/usr/bin/env python3
"""
aios_akashic.py — Akashic work-lineage index CLI (git-log style).

Exposes the memoryOS akashic_ledger as a navigable command surface:

  aios_akashic list                    # like: git log --oneline
  aios_akashic show <work_id>          # like: git show <commit>
  aios_akashic append --work-id ...    # like: git commit
  aios_akashic reconstruct <work_id>   # like: git log --follow

Reads from:  memoryOS/memory/akashic_work_index.jsonl
Schema:      aios.akashic_work_index.v1
WORK item:   WORK-20260612-001 (MemoryOS Akashic Records pipeline — CLI slice)
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path


def _root() -> Path:
    r = os.environ.get("CLAUDE_PROJECT_DIR") or os.environ.get("AIOS_ROOT")
    if r:
        return Path(r)
    here = Path(__file__).resolve().parent.parent
    if (here / ".aios").exists():
        return here
    return Path.cwd()


def _memoryos_root(root: Path) -> Path:
    return root / "memoryOS"


def _import_akashic(root: Path):
    mem_root = _memoryos_root(root)
    if str(mem_root) not in sys.path:
        sys.path.insert(0, str(mem_root))
    from memoryos.akashic_ledger import (  # noqa: F401
        AkashicWorkIndex, build_index, append_index, load_indexes, reconstruct,
    )
    return build_index, append_index, load_indexes, reconstruct


# ── list ─────────────────────────────────────────────────────────────────────

def cmd_list(args, root: Path) -> None:
    _, _, load_indexes, _ = _import_akashic(root)
    mem_root = _memoryos_root(root)
    rows = load_indexes(mem_root)
    if not rows:
        if args.json:
            print(json.dumps({"count": 0, "entries": []}, ensure_ascii=False))
        else:
            print("(no akashic entries)")
        return

    if args.json:
        print(json.dumps({
            "count": len(rows),
            "entries": rows if args.verbose else [
                {"id": r.get("id"), "work_id": r.get("work_id"),
                 "status": r.get("status"), "goal": (r.get("goal") or "")[:80],
                 "generated_at": r.get("generated_at")}
                for r in rows
            ]
        }, ensure_ascii=False, indent=2))
        return

    # Human-readable (git log --oneline style)
    for r in rows:
        short_id = (r.get("id") or "?")[:12]
        work_id = r.get("work_id") or "?"
        status = r.get("status") or "?"
        goal = (r.get("goal") or "")[:60]
        print(f"{short_id}  [{status:8s}]  {work_id}  {goal}")


# ── show ─────────────────────────────────────────────────────────────────────

def cmd_show(args, root: Path) -> None:
    _, _, load_indexes, _ = _import_akashic(root)
    mem_root = _memoryos_root(root)
    rows = load_indexes(mem_root)

    work_id = args.work_id
    matches = [r for r in rows if r.get("work_id") == work_id or r.get("id", "").startswith(work_id)]
    if not matches:
        print(json.dumps({"error": f"no entry for {work_id!r}"}, ensure_ascii=False))
        sys.exit(1)

    row = matches[-1]
    if args.json:
        print(json.dumps(row, ensure_ascii=False, indent=2))
        return

    # Human-readable (git show style)
    print(f"work_id:      {row.get('work_id')}")
    print(f"id:           {row.get('id')}")
    print(f"status:       {row.get('status')}")
    print(f"goal:         {row.get('goal')}")
    print(f"generated_at: {row.get('generated_at')}")
    print(f"sessions:     {len(row.get('session_ids') or [])}")
    print(f"checkpoints:  {len(row.get('checkpoint_refs') or [])}")
    print(f"memory_drafts:{len(row.get('memory_draft_ids') or [])}")
    print(f"next_action:  {row.get('next_action') or '—'}")
    arts = row.get("source_artifact_refs") or []
    if arts:
        print(f"artifacts:    {', '.join(arts[:5])}")


# ── append ───────────────────────────────────────────────────────────────────

def cmd_append(args, root: Path) -> None:
    build_index, append_index_fn, _, _ = _import_akashic(root)
    mem_root = _memoryos_root(root)

    payload = {
        "work_id": args.work_id,
        "goal": args.goal,
        "status": args.status or "active",
        "session_ids": args.session_ids or [],
        "checkpoint_refs": args.checkpoint_refs or [],
        "source_artifact_refs": args.source_artifact_refs or [],
        "next_action": args.next_action or "",
    }

    try:
        index = build_index(payload)
    except ValueError as exc:
        print(json.dumps({"error": str(exc)}, ensure_ascii=False))
        sys.exit(1)

    result = append_index_fn(mem_root, index, dry_run=args.dry_run)
    if args.json:
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return

    if args.dry_run:
        print(f"[dry-run] would append: {index.id[:12]}  {args.work_id}")
    elif result.get("duplicate"):
        print(f"[duplicate] {index.id[:12]}  {args.work_id} (already in index)")
    else:
        print(f"[appended] {index.id[:12]}  {args.work_id}")


# ── reconstruct ──────────────────────────────────────────────────────────────

def cmd_reconstruct(args, root: Path) -> None:
    _, _, _, reconstruct_fn = _import_akashic(root)
    mem_root = _memoryos_root(root)

    result = reconstruct_fn(mem_root, args.work_id)
    if args.json:
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return

    print(f"work_id:    {result.get('work_id')}")
    print(f"goal:       {result.get('goal') or '—'}")
    print(f"status:     {result.get('status')}")
    print(f"resumable:  {result.get('resumable')}")
    print(f"sessions:   {result.get('sessions')}")
    print(f"checkpoints:{result.get('checkpoints')}")
    print(f"next_action:{result.get('next_action')}")


# ── main ─────────────────────────────────────────────────────────────────────

def main() -> None:
    parser = argparse.ArgumentParser(
        description="Akashic work-lineage index (git-log style). Reads memoryOS/memory/akashic_work_index.jsonl"
    )
    parser.add_argument("--root", default=None, help="AIOS root directory (default: auto-detect)")
    sub = parser.add_subparsers(dest="cmd")

    # list
    p_list = sub.add_parser("list", help="List all work entries (like: git log --oneline)")
    p_list.add_argument("--json", action="store_true", help="JSON output")
    p_list.add_argument("--verbose", action="store_true", help="Include full JSON per entry")

    # show
    p_show = sub.add_parser("show", help="Show detail for a work entry (like: git show <commit>)")
    p_show.add_argument("work_id", help="work_id or id prefix to show")
    p_show.add_argument("--json", action="store_true", help="JSON output")

    # append
    p_append = sub.add_parser("append", help="Record a new work index entry (like: git commit)")
    p_append.add_argument("--work-id", required=True, dest="work_id", help="Work item ID (e.g. WORK-20260614-001)")
    p_append.add_argument("--goal", required=True, help="Goal text for this work item")
    p_append.add_argument("--status", default="active", choices=["active", "paused", "completed", "running"], help="Work status")
    p_append.add_argument("--session-ids", nargs="*", dest="session_ids", metavar="SESSION_ID", help="Session IDs linked to this work")
    p_append.add_argument("--checkpoint-refs", nargs="*", dest="checkpoint_refs", metavar="REF", help="Checkpoint refs (file paths or IDs)")
    p_append.add_argument("--source-artifact-refs", nargs="*", dest="source_artifact_refs", metavar="REF", help="Source artifact refs")
    p_append.add_argument("--next-action", dest="next_action", default="", help="Next action hint for resume")
    p_append.add_argument("--dry-run", action="store_true", help="Validate without writing")
    p_append.add_argument("--json", action="store_true", help="JSON output")

    # reconstruct
    p_reconstruct = sub.add_parser("reconstruct", help="Reconstruct work lineage (like: git log --follow)")
    p_reconstruct.add_argument("work_id", help="work_id to reconstruct")
    p_reconstruct.add_argument("--json", action="store_true", help="JSON output")

    args = parser.parse_args()
    root = Path(args.root).resolve() if args.root else _root()

    if args.cmd is None:
        parser.print_help()
        return

    dispatch = {
        "list": cmd_list,
        "show": cmd_show,
        "append": cmd_append,
        "reconstruct": cmd_reconstruct,
    }
    dispatch[args.cmd](args, root)


if __name__ == "__main__":
    main()
