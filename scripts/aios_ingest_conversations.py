#!/usr/bin/env python3
"""aios ingest-conversations — load the operator's own conversation history
into their AIOS's MemoryOS.

Founder question (2026-05-17): is MemoryOS set up so an agent can read in my
data / conversation records? MemoryOS already HAS the importers (ChatGPT,
Claude, Gemini, KakaoTalk exports) but only as a CLI; there was no
agent-callable ingest path. This wires one.

For an AIOS to be the operator's own individuated AI, it needs the
operator's actual conversation history as memory. This makes that an
explicit, privacy-gated, agent-callable step.

Privacy (DNA Invariant 7 — founder-inviolable): conversation records are
private-gated. Ingesting them into the operator's OWN local MemoryOS is
correct — it is their own AIOS's memory. This tool runs a redaction
preview FIRST and refuses without `--consent`. The imported private
memory must never flow to dispatch, the federation, or shared artifacts —
that boundary is enforced elsewhere (the distilled-pattern schema rejects
raw); this tool only does the local ingest.
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path

CONSENT = "I authorize ingesting my own conversation history into my local AIOS MemoryOS."


def run_memoryos(root: Path, args: list[str]) -> subprocess.CompletedProcess:
    return subprocess.run([sys.executable, "-m", "memoryos", *args],
                          cwd=root / "memoryOS", capture_output=True, text=True)


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description="Ingest the operator's conversation history into MemoryOS")
    p.add_argument("--root", default=".")
    p.add_argument("paths", nargs="+", help="conversation export files (ChatGPT/Claude/Gemini/KakaoTalk)")
    p.add_argument("--consent", action="store_true",
                   help=f'required — confirms: "{CONSENT}"')
    p.add_argument("--apply", action="store_true", help="actually import (default: redaction preview only)")
    p.add_argument("--json", action="store_true")
    args = p.parse_args(argv)

    root = Path(args.root).resolve()
    # resolve export paths relative to cwd, pass absolute to memoryos
    abs_paths = [str(Path(pp).resolve()) for pp in args.paths]
    missing = [pp for pp in abs_paths if not Path(pp).exists()]
    if missing:
        print(f"error: files not found: {missing}", file=sys.stderr)
        return 2

    # 1. privacy gate — redaction preview always runs first
    preview = run_memoryos(root, ["import", "--redaction-preview", "--json", *abs_paths])
    preview_out = preview.stdout.strip()

    if not args.consent:
        result = {
            "schema": "aios.ingest_conversations.v1",
            "status": "consent_required",
            "redaction_preview": preview_out[:2000],
            "note": f'private data — re-run with --consent to confirm: "{CONSENT}"',
        }
        print(json.dumps(result, indent=2, ensure_ascii=False) if args.json
              else f"redaction preview done. private data — re-run with --consent.\n{preview_out[:800]}")
        return 0

    if not args.apply:
        result = {"schema": "aios.ingest_conversations.v1", "status": "preview_only",
                  "redaction_preview": preview_out[:2000],
                  "note": "consent given; re-run with --apply to import"}
        print(json.dumps(result, indent=2, ensure_ascii=False) if args.json
              else f"consent ok. re-run with --apply to import.\n{preview_out[:800]}")
        return 0

    # 2. real import — into the operator's own local MemoryOS, as drafts
    imp = run_memoryos(root, ["import", *abs_paths])
    ok = imp.returncode == 0
    result = {
        "schema": "aios.ingest_conversations.v1",
        "status": "imported" if ok else "import_failed",
        "files": abs_paths,
        "memoryos_output": (imp.stdout or imp.stderr).strip()[:1500],
        "boundary": "imported into the operator's OWN local MemoryOS as drafts (Invariant 2). "
                    "This private memory must not leave the machine (Invariant 7).",
    }
    if args.json:
        print(json.dumps(result, indent=2, ensure_ascii=False))
    else:
        print(f"{result['status']}: {len(abs_paths)} file(s)")
        print(result["memoryos_output"])
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
