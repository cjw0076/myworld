#!/usr/bin/env python3
"""
aios_checkpoint.py — Session state checkpoint / resume for AIOS.

Writes a structured checkpoint at Stop, reads the latest at SessionStart.
Allows any session to re-meet context from the previous one.

Usage:
  python3 scripts/aios_checkpoint.py write [--goal GOAL] [--notes TEXT]
  python3 scripts/aios_checkpoint.py show [--latest] [--lean]
  python3 scripts/aios_checkpoint.py list
  python3 scripts/aios_checkpoint.py resume <checkpoint_id>

Schema: aios.checkpoint.v1
Location: .aios/checkpoints/YYYY-MM-DDTHH-MM-SS.json
"""

import argparse
import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

SCHEMA = "aios.checkpoint.v1"
CHECKPOINT_DIR_REL = ".aios/checkpoints"
WORK_INTAKE_REL = "docs/WORK_INTAKE.md"
LEDGER_REL = "docs/AIOS_AGENT_LEDGER.md"
CONTRACTS_REL = "docs/contracts"
GOAL_FILE_REL = ".aios/current_goal.txt"


def _root() -> Path:
    r = os.environ.get("CLAUDE_PROJECT_DIR") or os.environ.get("AIOS_ROOT")
    if r:
        return Path(r)
    here = Path(__file__).resolve().parent.parent
    if (here / ".aios").exists():
        return here
    return Path.cwd()


def _now_iso() -> str:
    return datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds")


def _now_slug() -> str:
    return datetime.now().strftime("%Y-%m-%dT%H-%M-%S")


# ── readers ───────────────────────────────────────────────────────────────────

def _read_goal(root: Path) -> str:
    p = root / GOAL_FILE_REL
    if p.exists():
        return p.read_text(encoding="utf-8").strip()
    return "(no goal set)"


def _read_backlog(root: Path) -> list[dict]:
    p = root / WORK_INTAKE_REL
    if not p.exists():
        return []
    items = []
    in_table = False
    for line in p.read_text(encoding="utf-8").splitlines():
        if "| ID |" in line or "| ---- |" in line or "| ~~" in line:
            continue
        if line.startswith("| WORK-"):
            parts = [c.strip() for c in line.split("|") if c.strip()]
            if len(parts) >= 4:
                items.append({
                    "id": parts[0],
                    "title": parts[1],
                    "type": parts[2],
                    "priority": parts[3],
                    "status": "open",
                })
    return items


def _read_recent_ledger(root: Path, n: int = 3) -> list[str]:
    p = root / LEDGER_REL
    if not p.exists():
        return []
    lines = p.read_text(encoding="utf-8").splitlines()
    entries = []
    entry_lines: list[str] = []
    for line in lines:
        if line.startswith("## ") and "ENTRY" in line.upper():
            if entry_lines:
                entries.append(" ".join(l.strip() for l in entry_lines[:3] if l.strip()))
            entry_lines = [line]
        elif entry_lines:
            entry_lines.append(line)
    if entry_lines:
        entries.append(" ".join(l.strip() for l in entry_lines[:3] if l.strip()))
    return entries[-n:]


def _count_open_contracts(root: Path) -> int:
    d = root / CONTRACTS_REL
    if not d.exists():
        return 0
    count = 0
    for f in d.iterdir():
        if f.name.startswith("ASC-") and f.suffix == ".md":
            text = f.read_text(encoding="utf-8")
            if "status: proposed" in text or "status: accepted" in text:
                count += 1
    return count


def _read_events_tail(root: Path, n: int = 5) -> list[str]:
    p = root / ".aios" / "primitives" / "events.jsonl"
    if not p.exists():
        return []
    lines = p.read_text(encoding="utf-8").strip().splitlines()
    results = []
    for line in lines[-n:]:
        try:
            rec = json.loads(line)
            results.append(f"{rec.get('ts_iso','?')} {rec.get('name','?')}")
        except Exception:
            results.append(line[:80])
    return results


# ── write ─────────────────────────────────────────────────────────────────────

def cmd_write(args) -> None:
    root = _root()
    cp_dir = root / CHECKPOINT_DIR_REL
    cp_dir.mkdir(parents=True, exist_ok=True)

    slug = _now_slug()
    goal = args.goal or _read_goal(root)
    notes = args.notes or ""

    checkpoint = {
        "schema_version": SCHEMA,
        "id": f"chk-{slug}",
        "ts_iso": _now_iso(),
        "goal": goal,
        "notes": notes,
        "backlog": _read_backlog(root),
        "recent_ledger": _read_recent_ledger(root),
        "open_contracts": _count_open_contracts(root),
        "recent_events": _read_events_tail(root),
        "context_refs": {
            "work_intake": str(root / WORK_INTAKE_REL),
            "ledger": str(root / LEDGER_REL),
            "contracts_dir": str(root / CONTRACTS_REL),
            "harness": str(root / ".claude" / "AIOS_HARNESS.md"),
        },
    }

    out_path = cp_dir / f"{slug}.json"
    out_path.write_text(json.dumps(checkpoint, ensure_ascii=False, indent=2))

    # keep only the 20 most recent checkpoints
    all_cp = sorted(cp_dir.glob("*.json"))
    for old in all_cp[:-20]:
        old.unlink(missing_ok=True)

    print(f"checkpoint written: {out_path.name}")
    if args.verbose:
        print(json.dumps(checkpoint, ensure_ascii=False, indent=2))


# ── show ──────────────────────────────────────────────────────────────────────

def _load_latest(root: Path) -> dict | None:
    cp_dir = root / CHECKPOINT_DIR_REL
    if not cp_dir.exists():
        return None
    candidates = sorted(cp_dir.glob("*.json"))
    if not candidates:
        return None
    return json.loads(candidates[-1].read_text(encoding="utf-8"))


def _format_lean(cp: dict) -> str:
    lines = [
        "## Checkpoint resume (from last session)",
        f"saved: {cp.get('ts_iso', '?')}  id: {cp.get('id','?')}",
        f"goal: {cp.get('goal', '?')}",
    ]
    backlog = cp.get("backlog", [])
    if backlog:
        lines.append(f"backlog: {len(backlog)} items open")
        for item in backlog[:5]:
            lines.append(f"  [{item['priority']}] {item['id']} — {item['title']}")
        if len(backlog) > 5:
            lines.append(f"  ... +{len(backlog)-5} more")
    open_c = cp.get("open_contracts", 0)
    if open_c:
        lines.append(f"open contracts: {open_c}")
    notes = cp.get("notes", "")
    if notes:
        lines.append(f"notes: {notes}")
    recent_ev = cp.get("recent_events", [])
    if recent_ev:
        lines.append("recent events:")
        for e in recent_ev:
            lines.append(f"  {e}")
    return "\n".join(lines)


def cmd_show(args) -> None:
    root = _root()

    if args.latest or not hasattr(args, "checkpoint_id") or not args.checkpoint_id:
        cp = _load_latest(root)
        if not cp:
            print("No checkpoints found.")
            return
    else:
        cp_dir = root / CHECKPOINT_DIR_REL
        matches = list(cp_dir.glob(f"*{args.checkpoint_id}*.json"))
        if not matches:
            print(f"No checkpoint matching '{args.checkpoint_id}'")
            return
        cp = json.loads(matches[0].read_text(encoding="utf-8"))

    if args.lean:
        print(_format_lean(cp))
    else:
        print(json.dumps(cp, ensure_ascii=False, indent=2))


# ── list ──────────────────────────────────────────────────────────────────────

def cmd_list(args) -> None:
    root = _root()
    cp_dir = root / CHECKPOINT_DIR_REL
    if not cp_dir.exists() or not list(cp_dir.glob("*.json")):
        print("No checkpoints.")
        return
    for f in sorted(cp_dir.glob("*.json"))[-10:]:
        try:
            cp = json.loads(f.read_text(encoding="utf-8"))
            backlog_n = len(cp.get("backlog", []))
            print(f"{cp.get('id','?'):30s}  {cp.get('ts_iso','?')}  backlog={backlog_n}  goal: {cp.get('goal','?')[:50]}")
        except Exception:
            print(f.name)


# ── resume (inject into session context) ─────────────────────────────────────

def cmd_resume(args) -> None:
    root = _root()
    cp_dir = root / CHECKPOINT_DIR_REL
    if not cp_dir.exists():
        return
    cp_id = getattr(args, "checkpoint_id", None)
    if cp_id:
        matches = list(cp_dir.glob(f"*{cp_id}*.json"))
        cp = json.loads(matches[0].read_text(encoding="utf-8")) if matches else None
    else:
        cp = _load_latest(root)
    if not cp:
        print("No checkpoint to resume from.")
        return
    # Output a system-message for the Stop hook format (or additionalContext)
    summary = _format_lean(cp)
    print(json.dumps({
        "hookSpecificOutput": {
            "hookEventName": "SessionStart",
            "additionalContext": summary,
        }
    }, ensure_ascii=False))


# ── main ──────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description="AIOS session checkpoint manager")
    sub = parser.add_subparsers(dest="command")

    p_write = sub.add_parser("write", help="Save current session state")
    p_write.add_argument("--goal", help="Override current goal text")
    p_write.add_argument("--notes", help="Free-text notes to carry forward")
    p_write.add_argument("--verbose", action="store_true")

    p_show = sub.add_parser("show", help="Show a checkpoint")
    p_show.add_argument("checkpoint_id", nargs="?", help="Checkpoint ID (partial match)")
    p_show.add_argument("--latest", action="store_true", help="Show most recent")
    p_show.add_argument("--lean", action="store_true", help="Compact summary")

    sub.add_parser("list", help="List recent checkpoints")

    p_resume = sub.add_parser("resume", help="Emit checkpoint as session context")
    p_resume.add_argument("checkpoint_id", nargs="?", help="Checkpoint ID (partial); defaults to latest")

    args = parser.parse_args()
    if args.command is None:
        parser.print_help()
        return

    dispatch = {
        "write": cmd_write,
        "show": cmd_show,
        "list": cmd_list,
        "resume": cmd_resume,
    }
    dispatch[args.command](args)


if __name__ == "__main__":
    main()
