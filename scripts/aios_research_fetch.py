#!/usr/bin/env python3
"""aios research-fetch — the autonomous web-fetch executor (search→absorb organ).

Closes the search→absorb loop: the dream organ produces a research queue
(`.aios/dream/research_queue.json`) of open questions; this executor fetches
real web evidence for each via the Tavily search API and writes it as
MemoryOS-importable markdown — so AIOS absorbs fresh external knowledge
without the operator running the searches.

Secret handling (DNA Invariant 7): the Tavily key is read from
`.aios/secrets/tavily.key` (gitignored) or the `TAVILY_API_KEY` env var.
It is never written into any committed artifact, dispatch packet, or prompt.

Boundary: this executor performs read-only outbound search calls and writes
DRAFT research notes. It does not accept memory, does not act — the absorb
pipeline produces MemoryOS drafts for review (Invariant 2, draft-first).
"""

from __future__ import annotations

import argparse
import json
import re
import sys
import urllib.request
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

TAVILY_URL = "https://api.tavily.com/search"
SECRET_REL = ".aios/secrets/tavily.key"
QUEUE_REL = ".aios/dream/research_queue.json"
IMPORTS_REL = "docs/imports"


def now_iso() -> str:
    return datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds")


def load_key(root: Path) -> str | None:
    import os

    env = os.environ.get("TAVILY_API_KEY")
    if env:
        return env.strip()
    secret = root / SECRET_REL
    if secret.exists():
        return secret.read_text(encoding="utf-8").strip()
    return None


def slug(text: str) -> str:
    s = re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-")
    return (s[:60] or "question").rstrip("-")


def tavily_search(key: str, query: str, *, max_results: int = 5) -> tuple[bool, Any]:
    body = json.dumps({
        "query": query,
        "search_depth": "basic",
        "max_results": max_results,
        "include_answer": True,
    }).encode("utf-8")
    req = urllib.request.Request(
        TAVILY_URL, data=body,
        headers={"Content-Type": "application/json", "Authorization": f"Bearer {key}"},
    )
    try:
        with urllib.request.urlopen(req, timeout=60) as resp:
            return True, json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace")[:200]
        return False, f"http_{exc.code}: {detail}"
    except Exception as exc:  # noqa: BLE001
        return False, f"fetch_failed: {exc}"


def render_research_note(question: str, payload: dict[str, Any]) -> str:
    answer = payload.get("answer") or "(no synthesized answer)"
    results = payload.get("results", []) or []
    lines = [
        f"# Research Note — {question}",
        "",
        f"- fetched_at: {now_iso()}",
        "- source: Tavily search API (autonomous search→absorb organ)",
        "- status: DRAFT — MemoryOS review required (DNA Invariant 2)",
        "",
        "## Synthesized answer",
        "",
        answer,
        "",
        "## Sources (provenance — DNA Invariant 5)",
        "",
    ]
    for r in results:
        title = r.get("title", "(untitled)")
        url = r.get("url", "")
        content = (r.get("content", "") or "").strip().replace("\n", " ")
        lines.append(f"### {title}")
        lines.append(f"- url: {url}")
        lines.append(f"- score: {r.get('score', 'NA')}")
        lines.append("")
        lines.append(content[:700])
        lines.append("")
    lines += [
        "## Origin",
        "",
        "Open question surfaced by the AIOS dream/consolidation organ; fetched",
        "by the autonomous search→absorb executor. This note is a draft memory",
        "candidate — acceptance requires explicit MemoryOS review.",
    ]
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description="AIOS autonomous research fetch (search→absorb)")
    p.add_argument("--root", default=".")
    p.add_argument("--queue", default=QUEUE_REL, help="research queue JSON path")
    p.add_argument("--question", default=None, help="fetch a single ad-hoc question instead of the queue")
    p.add_argument("--max-results", type=int, default=5)
    p.add_argument("--limit", type=int, default=5, help="max queue items to fetch this run")
    p.add_argument("--json", action="store_true")
    args = p.parse_args(argv)

    root = Path(args.root).resolve()
    key = load_key(root)
    if not key:
        print(f"error: no Tavily key — set TAVILY_API_KEY or write {SECRET_REL}", file=sys.stderr)
        return 2

    if args.question:
        questions = [args.question]
    else:
        queue_path = root / args.queue
        if not queue_path.exists():
            print(f"error: research queue not found: {queue_path} (run `aios dream` first)", file=sys.stderr)
            return 2
        queue = json.loads(queue_path.read_text(encoding="utf-8"))
        questions = [it.get("question", "") for it in queue.get("items", []) if it.get("question")]
        questions = questions[: args.limit]

    if not questions:
        if args.json:
            print(json.dumps({"schema": "aios.research_fetch.v1", "fetched": 0,
                              "failed": 0, "receipts": []}, ensure_ascii=False))
        else:
            print("no questions to fetch")
        return 0

    imports_dir = root / IMPORTS_REL
    imports_dir.mkdir(parents=True, exist_ok=True)
    receipts = []
    for q in questions:
        ok, payload = tavily_search(key, q, max_results=args.max_results)
        if not ok:
            receipts.append({"question": q, "ok": False, "reason": str(payload)})
            continue
        note_path = imports_dir / f"research__{slug(q)}.md"
        note_path.write_text(render_research_note(q, payload), encoding="utf-8")
        receipts.append({
            "question": q,
            "ok": True,
            "results": len(payload.get("results", []) or []),
            "note": str(note_path.relative_to(root)),
        })

    summary = {
        "schema": "aios.research_fetch.v1",
        "ran_at": now_iso(),
        "fetched": sum(1 for r in receipts if r["ok"]),
        "failed": sum(1 for r in receipts if not r["ok"]),
        "receipts": receipts,
        "next": "absorb the notes: cd memoryOS && python -m memoryos import ../docs/imports/research__*.md",
    }
    if args.json:
        print(json.dumps(summary, indent=2, ensure_ascii=False))
    else:
        for r in receipts:
            mark = "OK " if r["ok"] else "ERR"
            tail = r.get("note", r.get("reason", ""))
            print(f"{mark} {r['question'][:60]} -> {tail}")
        print(f"-- fetched {summary['fetched']}, failed {summary['failed']}")
    return 0 if all(r["ok"] for r in receipts) else 1


if __name__ == "__main__":
    sys.exit(main())
