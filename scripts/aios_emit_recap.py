#!/usr/bin/env python3
"""aios emit-recap — generic product-repo recap emitter (ASC-0181 Packet A).

The repo-parameterized counterpart of uri's TypeScript hook
(`uri/scripts/aios-emit-recap.ts`). Any repo registered in the workbench
registry (`.aios/workbench/registry.json`) can emit an `aios.product_recap.v1`
packet — uri is no longer special.

Usage:
  python scripts/aios_emit_recap.py --repo myproject --sprint MYP-007 \\
    --subject "added retrieval cache" --caps python,sqlite \\
    --evidence "git:abc1234" [--files a.py,b.py] [--commit abc1234] [--dry-run]

The emitted packet always carries the exact ASC-0173 consent string; the
registry controls *who may emit*, never *whether consent is required*.
"""

from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from aios_workbench_registry import is_emit_eligible, registered_repos  # noqa: E402

SCHEMA = "aios.product_recap.v1"
CONSENT_EXACT = (
    "I authorize AIOS to ingest this packet as a MemoryOS draft "
    "and CapabilityOS observation."
)


def now_iso() -> str:
    return datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds")


def git_short_sha(repo_dir: Path) -> str | None:
    try:
        r = subprocess.run(
            ["git", "-C", str(repo_dir), "rev-parse", "--short", "HEAD"],
            capture_output=True, text=True, check=False,
        )
        if r.returncode == 0:
            return r.stdout.strip()
    except OSError:
        pass
    return None


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description="Emit an aios.product_recap.v1 packet")
    p.add_argument("--repo", required=True, help="product repo slug (must be registered)")
    p.add_argument("--sprint", required=True, help="sprint/work id")
    p.add_argument("--subject", required=True, help="one-line subject")
    p.add_argument("--caps", required=True, help="comma-separated capabilities used")
    p.add_argument("--evidence", action="append", default=[], help="evidence ref (repeatable)")
    p.add_argument("--files", default="", help="comma-separated files touched")
    p.add_argument("--commit", default="", help="commit sha (default: git HEAD if available)")
    p.add_argument("--signed-by", default="", help="operator handle")
    p.add_argument("--root", default=".", help="myworld repo root")
    p.add_argument("--repo-dir", default=".", help="the product repo's own dir (for git sha)")
    p.add_argument("--dry-run", action="store_true")
    args = p.parse_args(argv)

    root = Path(args.root).resolve()

    if not is_emit_eligible(root, args.repo):
        print(
            f"error: repo {args.repo!r} is not registered. "
            f"Run `aios init` (ASC-0181 Packet B) or add it to "
            f".aios/workbench/registry.json. registered: {sorted(registered_repos(root))}",
            file=sys.stderr,
        )
        return 2

    if not re.match(r"^[A-Za-z0-9][A-Za-z0-9_.-]*$", args.sprint):
        print(f"error: --sprint {args.sprint!r} has invalid characters", file=sys.stderr)
        return 2

    caps = [c.strip() for c in args.caps.split(",") if c.strip()]
    files = [f.strip() for f in args.files.split(",") if f.strip()]
    evidence = list(args.evidence)
    if not evidence:
        print("error: at least one --evidence is required (DNA Invariant 5)", file=sys.stderr)
        return 2
    if not caps:
        print("error: --caps must list at least one capability", file=sys.stderr)
        return 2

    commit = args.commit or git_short_sha(Path(args.repo_dir).resolve()) or ""
    signed_by = args.signed_by or "workbench operator (aios_emit_recap.py)"

    packet = {
        "schema": SCHEMA,
        "product_repo": args.repo,
        "sprint_id": args.sprint,
        "sprint_subject": args.subject,
        "commit_sha": commit or None,
        "files_touched": files,
        "capabilities_used": caps,
        "operator_signed_by": signed_by,
        "consent": CONSENT_EXACT,
        "evidence_refs": evidence,
    }

    inbox = root / ".aios" / "inbox" / "myworld"
    dest = inbox / f"product_recap__{args.repo}__{args.sprint}.json"

    if args.dry_run:
        print(json.dumps(packet, indent=2, ensure_ascii=False))
        print(f"# would write: {dest}")
        return 0

    inbox.mkdir(parents=True, exist_ok=True)
    dest.write_text(json.dumps(packet, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(f"wrote {dest}")
    print(f"next: python scripts/aios_ingest_product_recap.py --apply")
    return 0


if __name__ == "__main__":
    sys.exit(main())
