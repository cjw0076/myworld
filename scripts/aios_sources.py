#!/usr/bin/env python3
"""aios_sources — pluggable source-adapter framework for the personal memory ledger.

Attach ANY app or data source as a memory source. The framework owns the common
pipeline — pull → privacy gate (opt-in per category) → normalize → write to the
LOCAL ledger as a draft, with provenance — so each adapter only implements `pull()`.

Privacy (DNA #7): rich content goes ONLY to the local, sovereign ledger, opt-in
per source category, draft-first. Never to the global AkashicRecord (which stays
tool-names-only). The operator can always review/reject drafts.

Add an app: subclass SourceAdapter (or McpSource), implement available()+pull(),
register() it. That's the whole contract — "all app sources pluggable".

Schema: aios.source_ingest.v1
"""
from __future__ import annotations

import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


# ── Adapter contract ───────────────────────────────────────────────────────────

class SourceAdapter:
    """One memory source. Subclass + implement available() and pull()."""
    name: str = "base"
    category: str = "data"          # opt-in bucket: docs/apps/social/creative/personal/code
    kind: str = "generic"

    def available(self) -> bool:
        """Is this source reachable/configured on this machine?"""
        return False

    def pull(self, limit: int = 50) -> list[dict]:
        """Return raw items: [{content, ref, tags}]. The adapter decides what is
        safe to surface; the framework still gates by opt-in + keeps it local."""
        return []


class FileSource(SourceAdapter):
    """Human-native data: a folder of notes/diary/markdown/text. Fully local."""
    kind = "file"

    def __init__(self, name: str, directory: str | Path, category: str = "personal"):
        self.name = name
        self.category = category
        self.dir = Path(directory).expanduser()

    def available(self) -> bool:
        return self.dir.exists()

    def pull(self, limit: int = 50) -> list[dict]:
        items: list[dict] = []
        if not self.dir.exists():
            return items
        for f in sorted(self.dir.rglob("*")):
            if len(items) >= limit:
                break
            if f.is_file() and f.suffix.lower() in (".md", ".txt", ".markdown"):
                try:
                    txt = f.read_text(encoding="utf-8", errors="replace").strip()
                except OSError:
                    continue
                if txt:
                    items.append({"content": txt[:2000], "ref": f"file:{f.name}",
                                  "tags": [self.name, f.suffix.lstrip(".")]})
        return items


class McpSource(SourceAdapter):
    """Template for app sources (Notion/Slack/Figma/Gmail/…) pulled via their MCP
    server. A concrete app adapter subclasses this, sets name/category, checks the
    MCP is wired in available(), and calls the MCP tool in pull(). One subclass per
    app — that's how 'all app sources' plug in. (Base is inert until subclassed.)"""
    kind = "mcp"
    category = "apps"

    def available(self) -> bool:
        return False


# ── Registry ───────────────────────────────────────────────────────────────────

SOURCES: dict[str, SourceAdapter] = {}


def register(adapter: SourceAdapter) -> None:
    SOURCES[adapter.name] = adapter


def _default_registry() -> None:
    """Built-in sources. Human-native folders are configured via AIOS_SOURCES_DIR
    (default ~/.aios/sources/<name>/). App adapters register themselves as added."""
    base = Path(os.environ.get("AIOS_SOURCES_DIR", str(Path.home() / ".aios" / "sources")))
    register(FileSource("diary",  base / "diary",  category="personal"))
    register(FileSource("notes",  base / "notes",  category="docs"))
    register(FileSource("journal", base / "journal", category="personal"))


_default_registry()


# ── Common ingest pipeline (privacy-gated, local, draft-first) ──────────────────

def ingest_source(name: str, root: Path, opt_in: frozenset[str],
                  limit: int = 50, apply: bool = False) -> dict:
    """Pull from one source → privacy gate (opt-in) → write to the LOCAL ledger as
    drafts with provenance. Dry-run by default; pass apply=True to write."""
    adapter = SOURCES.get(name)
    if adapter is None:
        return {"status": "unknown_source", "source": name, "known": sorted(SOURCES)}
    if not adapter.available():
        return {"status": "unavailable", "source": name,
                "hint": f"source not reachable/configured ({adapter.kind})"}
    if adapter.category not in opt_in:
        return {"status": "skipped_opt_in", "source": name, "category": adapter.category,
                "hint": f"add '{adapter.category}' to --opt-in to ingest this source"}
    items = adapter.pull(limit)
    written = 0
    if apply:
        sp = str(ROOT / "scripts")
        if sp not in sys.path:
            sys.path.insert(0, sp)
        import aios_local_memory as LM  # noqa: PLC0415 — local ledger write
        for it in items:
            content = (it.get("content") or "").strip()
            if not content:
                continue
            tags = list(it.get("tags") or []) + [f"source:{name}", f"ref:{it.get('ref','')}"[:60]]
            LM.write(root, content[:2000], tags=tags)   # local, draft, provenance-tagged
            written += 1
    return {
        "schema": "aios.source_ingest.v1",
        "status": "ok",
        "source": name, "category": adapter.category, "kind": adapter.kind,
        "found": len(items), "written": written,
        "mode": "applied (local ledger, draft)" if apply else "dry-run (use --apply to write)",
    }


def list_sources() -> list[dict]:
    return [{"name": a.name, "category": a.category, "kind": a.kind,
             "available": a.available()} for a in SOURCES.values()]


# ── CLI ────────────────────────────────────────────────────────────────────────

def main(argv: list[str] | None = None) -> int:
    import argparse
    import json
    p = argparse.ArgumentParser(prog="aios sources",
        description="Pluggable memory sources — attach any app/data source to the ledger.")
    sub = p.add_subparsers(dest="cmd")
    sub.add_parser("list")
    ing = sub.add_parser("ingest")
    ing.add_argument("source")
    ing.add_argument("--opt-in", default="personal,docs",
                     help="comma-separated categories to allow (privacy gate)")
    ing.add_argument("--limit", type=int, default=50)
    ing.add_argument("--apply", action="store_true", help="write to the local ledger (default: dry-run)")
    args = p.parse_args(argv)

    try:
        import aios_sigil  # noqa: PLC0415
        head = aios_sigil.badge("AIOS") + " sources"
    except Exception:  # noqa: BLE001
        head = "✦ AIOS sources"

    if args.cmd == "ingest":
        opt_in = frozenset(c.strip() for c in args.opt_in.split(",") if c.strip())
        out = ingest_source(args.source, ROOT, opt_in, limit=args.limit, apply=args.apply)
        print(json.dumps(out, ensure_ascii=False, indent=2))
        return 0 if out.get("status") == "ok" else 1

    # default: list
    print(head)
    for s in list_sources():
        mark = "✓" if s["available"] else "·"
        print(f"  {mark} {s['name']:<10} [{s['category']}/{s['kind']}]"
              + ("" if s["available"] else "   (not configured)"))
    print("  attach an app: subclass SourceAdapter/McpSource + register() — see aios_sources.py")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
