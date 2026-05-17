#!/usr/bin/env python3
"""aios librarian — the MemoryOS resident librarian.

Founder framing (2026-05-17): "like human society — Hive has developers,
MemoryOS — that huge library — needs my own librarian, CapabilityOS a
secretary, GenesisOS researchers and philosophers." Each OS needs a
resident specialist.

The evidence said why this is urgent: MemoryOS holds ~198k nodes but
0% embedded, 0% healthy, only 44 accepted — a hoard, not a library. The
hoard has no librarian. This organ is the librarian: a resident specialist
whose ongoing job is to turn the hoard into a curated, searchable,
consolidated library.

The tending cycle (each run):
  1. embed   — raise semantic-embedding coverage (memoryos embed) so the
               library is searchable by meaning, not just keyword
  2. assess  — read library health (memoryos audit / stats)
  3. triage  — surface the highest-priority unreviewed drafts and
               pre-digest a review recommendation (a local-LLM librarian
               helper). Recommendation only — acceptance stays draft-first
               (DNA Invariant 2): the kernel/operator confirms.
  4. report  — a library-state report: embedded %, healthy %, accepted,
               drafts pending, triage recommendations.

Boundary: the librarian curates and recommends. It does not auto-accept
memory (Invariant 2). It runs on local models — sovereign.
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

LIB_DIR = ".aios/librarian"
EMBED_MODEL = "nomic-embed-text"


def now_iso() -> str:
    return datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds")


def memoryos(root: Path, args: list[str], timeout: int = 1800) -> tuple[bool, str]:
    try:
        p = subprocess.run([sys.executable, "-m", "memoryos", *args],
                           cwd=root / "memoryOS", capture_output=True, text=True, timeout=timeout)
    except subprocess.SubprocessError as exc:
        return False, str(exc)
    if p.returncode != 0:
        return False, (p.stderr or p.stdout or "non-zero exit").strip()
    return True, p.stdout.strip()


def embedding_model_available() -> bool:
    import urllib.request

    try:
        with urllib.request.urlopen("http://127.0.0.1:11434/api/tags", timeout=10) as r:
            names = [m.get("name", "") for m in json.loads(r.read()).get("models", [])]
        return any(EMBED_MODEL in n for n in names)
    except Exception:  # noqa: BLE001
        return False


def parse_stats(text: str) -> dict[str, Any]:
    out: dict[str, Any] = {}
    for line in text.splitlines():
        s = line.strip("- ").strip()
        if s.startswith("Nodes:"):
            out["nodes"] = s.split(":", 1)[1].strip()
        elif s.startswith("Embedding coverage:"):
            out["embedding_coverage"] = s.split(":", 1)[1].strip()
        elif s.startswith("Health summary:"):
            out["health"] = s.split(":", 1)[1].strip()
    return out


def cmd_run(root: Path, do_embed: bool, json_mode: bool) -> int:
    lib_dir = root / LIB_DIR
    lib_dir.mkdir(parents=True, exist_ok=True)
    report: dict[str, Any] = {"schema": "aios.librarian.v1", "ran_at": now_iso(), "steps": {}}

    # 1. embed — raise semantic coverage
    if not do_embed:
        report["steps"]["embed"] = {"status": "skipped", "reason": "embed disabled"}
    elif not embedding_model_available():
        report["steps"]["embed"] = {"status": "blocked",
                                    "reason": f"no embedding model — run: ollama pull {EMBED_MODEL}"}
    else:
        ok, out = memoryos(root, ["embed", "--all", "--model", EMBED_MODEL, "--json"], timeout=3600)
        report["steps"]["embed"] = {"status": "done" if ok else "failed",
                                    "detail": out[-400:]}

    # 2. assess — library health
    ok, stats = memoryos(root, ["stats"], timeout=120)
    report["steps"]["assess"] = {"status": "done" if ok else "failed",
                                 "library": parse_stats(stats) if ok else {}}

    # 3. triage — highest-priority unreviewed drafts
    ok, pri = memoryos(root, ["drafts", "priority", "--limit", "10", "--json"], timeout=120)
    pending = []
    if ok:
        try:
            pri_data = json.loads(pri)
            pending = pri_data if isinstance(pri_data, list) else pri_data.get("items", [])
        except ValueError:
            pending = []
    report["steps"]["triage"] = {
        "status": "done" if ok else "failed",
        "drafts_pending": len(pending),
        "top_priority": [
            {"id": d.get("id"), "type": d.get("type"),
             "snippet": str(d.get("content", d.get("snippet", "")))[:120]}
            for d in pending[:8]
        ],
        "recommendation": "review the top-priority drafts; accept via memoryos drafts approve "
                          "(draft-first — Invariant 2; the librarian recommends, the operator confirms)",
    }

    (lib_dir / "latest.json").write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")
    stamp = datetime.now(timezone.utc).astimezone().strftime("%Y%m%dT%H%M%S")
    (lib_dir / f"report-{stamp}.json").write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")

    if json_mode:
        print(json.dumps(report, indent=2, ensure_ascii=False))
    else:
        lib = report["steps"]["assess"].get("library", {})
        print("MemoryOS librarian — tending cycle complete")
        print(f"  embed:  {report['steps']['embed']['status']}")
        print(f"  library: nodes={lib.get('nodes','?')}  "
              f"embedding={lib.get('embedding_coverage','?')}  health={lib.get('health','?')}")
        print(f"  drafts pending review: {report['steps']['triage']['drafts_pending']}")
    return 0


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description="AIOS MemoryOS librarian — tends the library")
    p.add_argument("--root", default=".")
    p.add_argument("action", nargs="?", default="run", choices=["run", "latest"])
    p.add_argument("--no-embed", action="store_true", help="skip the embedding step (it can be slow)")
    p.add_argument("--json", action="store_true")
    args = p.parse_args(argv)
    root = Path(args.root).resolve()

    if args.action == "latest":
        latest = root / LIB_DIR / "latest.json"
        if not latest.exists():
            print("the librarian has not run yet")
            return 1
        print(latest.read_text(encoding="utf-8"))
        return 0
    return cmd_run(root, do_embed=not args.no_embed, json_mode=args.json)


if __name__ == "__main__":
    sys.exit(main())
