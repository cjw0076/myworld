#!/usr/bin/env python3
"""aios dispatch-reconcile — reconcile dispatch packet state with contract reality.

The 2026-05-17 internal audit found audit gap #6: `.aios/inbox/<repo>/` holds
106+ dispatch packets in a "sent but never collected" state while their
contracts are long closed. Dispatch state and contract state have drifted —
`dispatch status` and the self-model both surface stale packets as if work
were pending.

This organ reconciles them: for each inbox packet it reads `contract_id`,
finds the contract, and if the contract is **closed**, the packet is stale —
the work it dispatched is done. Stale packets are *archived* (moved to
`.aios/archive/inbox/<repo>/`), never deleted (DNA Invariant 3, append-only
audit). Packets for open or missing contracts are left untouched for operator
review — the organ only acts on the definitively-resolved case.

  aios dispatch-reconcile run            archive stale packets
  aios dispatch-reconcile run --dry-run  report only, move nothing

Idempotent: a second run finds nothing left to reconcile.
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


def now_iso() -> str:
    return datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds")


def contract_status(root: Path, contract_id: str) -> str | None:
    """Read a contract's frontmatter status. None if the contract is absent."""
    if not contract_id:
        return None
    matches = sorted((root / "docs" / "contracts").glob(f"{contract_id}-*.md"))
    if not matches:
        return None
    for line in matches[0].read_text(encoding="utf-8", errors="replace").splitlines():
        m = re.match(r"\s*status:\s*([A-Za-z_]+)", line)
        if m:
            return m.group(1).lower()
    return None


def reconcile(root: Path, dry_run: bool) -> dict[str, Any]:
    inbox = root / ".aios" / "inbox"
    archived: list[dict[str, str]] = []
    kept: list[dict[str, str]] = []
    if inbox.exists():
        for repo_dir in sorted(inbox.iterdir()):
            if not repo_dir.is_dir():
                continue
            for packet in sorted(repo_dir.glob("*.json")):
                try:
                    data = json.loads(packet.read_text(encoding="utf-8"))
                except (ValueError, OSError):
                    kept.append({"packet": packet.name, "reason": "unparseable"})
                    continue
                cid = data.get("contract_id") or data.get("contract")
                status = contract_status(root, str(cid) if cid else "")
                if status == "closed":
                    dest = root / ".aios" / "archive" / "inbox" / repo_dir.name
                    if not dry_run:
                        dest.mkdir(parents=True, exist_ok=True)
                        shutil.move(packet.as_posix(), (dest / packet.name).as_posix())
                    archived.append({"packet": packet.name, "repo": repo_dir.name,
                                     "contract": str(cid), "contract_status": "closed"})
                else:
                    kept.append({"packet": packet.name, "repo": repo_dir.name,
                                 "contract": str(cid),
                                 "reason": f"contract {status or 'missing'} — left for review"})

    summary = {
        "schema": "aios.dispatch_reconcile.v1",
        "ran_at": now_iso(),
        "dry_run": dry_run,
        "archived_stale": len(archived),
        "kept_active": len(kept),
        "archived": archived,
        "kept": kept,
        "note": "stale packets (contract closed) archived to .aios/archive/inbox/ "
                "— append-only, never deleted; open/missing-contract packets left "
                "for operator review",
    }
    return summary


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description="AIOS dispatch reconciliation")
    p.add_argument("--root", default=".")
    p.add_argument("action", nargs="?", default="run", choices=["run"])
    p.add_argument("--dry-run", action="store_true")
    p.add_argument("--json", action="store_true")
    args = p.parse_args(argv)
    root = Path(args.root).resolve()

    result = reconcile(root, args.dry_run)
    if args.json:
        print(json.dumps(result, indent=2, ensure_ascii=False))
        return 0

    verb = "would archive" if args.dry_run else "archived"
    print(f"dispatch reconcile — {verb} {result['archived_stale']} stale packet(s), "
          f"{result['kept_active']} active kept")
    for a in result["archived"][:15]:
        print(f"  stale: {a['repo']}/{a['packet']} ({a['contract']} closed)")
    if result["archived_stale"] > 15:
        print(f"  ... and {result['archived_stale'] - 15} more")
    return 0


if __name__ == "__main__":
    sys.exit(main())
