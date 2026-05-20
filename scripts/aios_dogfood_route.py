#!/usr/bin/env python3
"""ASC-0214 — AIOS Dogfooding Gap routine.

Reads memory directory for `reference_*.md` memos and contracts
directory. For each reference memo with NO contract citation:
- compute `staleness_days` (now - file mtime, in days).
- if staleness_days >= --threshold-days, surface as a "stale-uncited
  candidate" → emit a proposal entry that lists the memo and a
  pre-filled "what action would this knowledge force" prompt.

Two modes:
- default (dry-run): print/JSON a list of candidates. No file mutation.
- `--act`: write `.aios/inbox/myworld/dogfood-NNNN.myworld.json` packets
  so the AIOS dispatch flow can pick them up; or, with `--ledger`,
  append a ledger entry stating an explicit decision (contract OR
  reject) per memo — operator marks which.

DNA: Invariant 1 (advisory only — `--act` only stages, never auto-
accepts), Invariant 2 (draft-first — no graph mutation), Invariant 6
(operator override — operator picks per memo).

Schema: `aios.dogfood_route.v1`.
"""
from __future__ import annotations

import argparse
import json
import re
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_MEMORY_DIR = Path(
    "/home/user/.claude/projects/-home-user-workspaces-jaewon-myworld/memory"
)
DEFAULT_CONTRACTS_DIR = REPO_ROOT / "docs" / "contracts"


def _memo_slug(memo: Path) -> str:
    return memo.stem.replace("_", "-")


def _read_memo(memo: Path) -> tuple[str, str]:
    """Return (description, first_body_line)."""
    text = memo.read_text(encoding="utf-8", errors="replace")
    m = re.search(r"^description:\s*(.+)$", text, re.M)
    desc = m.group(1).strip() if m else ""
    body = text.split("---", 2)[-1] if text.startswith("---") else text
    first = ""
    for line in body.splitlines():
        s = line.strip()
        if s and not s.startswith("#"):
            first = s[:200]
            break
    return desc[:200], first


def contracts_corpus(contracts_dir: Path) -> str:
    out: list[str] = []
    for p in contracts_dir.glob("ASC-*.md"):
        try:
            out.append(p.read_text(encoding="utf-8", errors="replace").lower())
        except Exception:
            continue
    return "\n".join(out)


def uncited_references(memory_dir: Path, corpus: str) -> list[Path]:
    res = []
    for memo in sorted(memory_dir.glob("reference_*.md")):
        slug = _memo_slug(memo).lower()
        slug_alt = memo.stem.lower()
        if slug not in corpus and slug_alt not in corpus:
            res.append(memo)
    return res


def memo_staleness_days(memo: Path) -> float:
    return (time.time() - memo.stat().st_mtime) / 86400.0


def candidate_from_memo(memo: Path) -> dict[str, Any]:
    desc, first = _read_memo(memo)
    staleness = memo_staleness_days(memo)
    return {
        "memo": memo.name,
        "slug": _memo_slug(memo),
        "description": desc,
        "first_line": first,
        "staleness_days": round(staleness, 2),
        "proposed_action_prompt": (
            f"Reference {memo.stem} ({desc[:120]}) has not been cited by any "
            f"contract. Decide one of: (a) propose a new ASC contract that "
            f"acts on this knowledge; (b) ledger-reject with reason; "
            f"(c) keep stale (explicit). Pick within 7 days."
        ),
    }


def write_inbox_packet(root: Path, candidate: dict[str, Any]) -> Path:
    inbox = root / ".aios" / "inbox" / "myworld"
    inbox.mkdir(parents=True, exist_ok=True)
    import uuid
    rid = "dogfood-" + uuid.uuid4().hex[:12]
    packet = {
        "schema_version": "aios.dogfood_route.v1",
        "request_id": rid,
        "contract_id": "ASC-0214",
        "contract_path": "docs/contracts/ASC-0214-aios-dogfooding-gap.md",
        "target_repo": "myworld",
        "agent": "aios_dogfood_route@ASC-0214",
        "goal": f"Decide action for uncited reference memo {candidate['memo']}",
        "candidate": candidate,
        "review_policy": {"auto_accept": False, "draft_first": True},
        "created_at": datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z"),
    }
    path = inbox / f"{rid}.myworld.json"
    path.write_text(json.dumps(packet, indent=2, ensure_ascii=False), encoding="utf-8")
    return path


def append_ledger(root: Path, candidates: list[dict[str, Any]]) -> Path | None:
    """Append an audit-friendly entry to docs/AIOS_AGENT_LEDGER.md."""
    ledger = root / "docs" / "AIOS_AGENT_LEDGER.md"
    if not ledger.exists():
        return None
    entry_lines = [
        "",
        "## " + datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC") +
        " — claude@myworld — ASC-0214 dogfood-route stale-uncited surfacing",
        "",
    ]
    for c in candidates:
        entry_lines.append(
            f"- **{c['memo']}** ({c['staleness_days']:.1f}d stale) — {c['description'][:120]}"
        )
    entry_lines.append("")
    entry_lines.append(
        "  Each above requires explicit operator decision within 7 days: "
        "(a) new ASC contract / (b) ledger-reject reason / (c) explicit keep-stale."
    )
    entry_lines.append("")
    text = "\n".join(entry_lines)
    with ledger.open("a", encoding="utf-8") as f:
        f.write(text)
    return ledger


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description="ASC-0214 dogfood-route — uncited memo surfacing")
    p.add_argument("--memory-dir", type=Path, default=DEFAULT_MEMORY_DIR)
    p.add_argument("--contracts-dir", type=Path, default=DEFAULT_CONTRACTS_DIR)
    p.add_argument("--threshold-days", type=float, default=0.0,
                   help="surface only memos staler than this; default 0 (all uncited)")
    p.add_argument("--act", action="store_true",
                   help="write inbox packet per stale candidate")
    p.add_argument("--ledger", action="store_true",
                   help="append a summary entry to docs/AIOS_AGENT_LEDGER.md")
    p.add_argument("--json", action="store_true")
    args = p.parse_args(argv)

    corpus = contracts_corpus(args.contracts_dir)
    uncited = uncited_references(args.memory_dir, corpus)
    candidates: list[dict[str, Any]] = []
    for memo in uncited:
        c = candidate_from_memo(memo)
        if c["staleness_days"] >= args.threshold_days:
            candidates.append(c)

    written: list[str] = []
    ledger_path: Path | None = None
    if args.act:
        for c in candidates:
            written.append(write_inbox_packet(REPO_ROOT, c).as_posix())
    if args.ledger:
        ledger_path = append_ledger(REPO_ROOT, candidates)

    out = {
        "schema_version": "aios.dogfood_route.v1",
        "uncited_total": len(uncited),
        "candidates_after_threshold": len(candidates),
        "threshold_days": args.threshold_days,
        "inbox_packets_written": written,
        "ledger_appended_to": ledger_path.as_posix() if ledger_path else None,
        "candidates": candidates,
    }
    if args.json:
        print(json.dumps(out, indent=2, ensure_ascii=False))
    else:
        print(f"uncited: {len(uncited)}, after_threshold(>= {args.threshold_days}d): {len(candidates)}")
        for c in candidates:
            print(f"\n• {c['memo']}  (stale {c['staleness_days']:.1f}d)")
            print(f"  {c['description'][:160]}")
        if written:
            print(f"\nwrote {len(written)} inbox packets")
        if ledger_path:
            print(f"appended to {ledger_path}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
