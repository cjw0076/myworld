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


class _HarvestedMcp(McpSource):
    """An app source HARVESTED from a provider's MCP config — not hand-written.
    The protocol is imported automatically; binding pull() to live MCP calls is the
    one remaining per-source step (bound=False until then)."""
    def __init__(self, name: str, origin: str):
        self.name = name
        self.origin = origin           # which provider it was wired into
        self.bound = False
        self.category = "apps"

    def available(self) -> bool:
        return True                    # it is wired into a provider — harvested/discoverable

    def pull(self, limit: int = 50) -> list[dict]:
        # Protocol harvested; live pull binds to the MCP server's resources/tools.
        # Returns [] until bound (honest) — binding is one small step per source.
        return []


_HARVESTED_SKILLS = 0


def harvest_provider_adapters() -> dict:
    """Read the MCP servers + skills already wired into the provider CLIs
    (claude ~/.claude.json, codex ~/.codex/config.toml, antigravity) and auto-register
    a source adapter per MCP — so you don't hand-write adapters, you HARVEST the
    protocols the providers already expose. Returns a summary."""
    global _HARVESTED_SKILLS
    harvested = {"mcp": [], "skills": 0}
    # 1. claude — reuse the capability scanner (reads ~/.claude.json mcpServers + skills)
    try:
        sp = str(ROOT / "scripts")
        if sp not in sys.path:
            sys.path.insert(0, sp)
        import aios_capability_scanner as CS  # noqa: PLC0415
        for m in CS.scan_mcps():
            nm = str(m.get("name", "")).strip()
            if nm:
                register(_HarvestedMcp(nm, origin="claude"))
                harvested["mcp"].append(nm)
        _HARVESTED_SKILLS = len(CS.scan_skills())
        harvested["skills"] = _HARVESTED_SKILLS
    except Exception:  # noqa: BLE001
        pass
    # 2. codex — ~/.codex/config.toml [mcp_servers.<name>]
    try:
        import tomllib  # noqa: PLC0415
        cfg = Path.home() / ".codex" / "config.toml"
        if cfg.exists():
            data = tomllib.loads(cfg.read_text(encoding="utf-8"))
            for nm in (data.get("mcp_servers") or {}):
                register(_HarvestedMcp(f"codex:{nm}", origin="codex"))
                harvested["mcp"].append(f"codex:{nm}")
    except Exception:  # noqa: BLE001
        pass
    # 3. antigravity — config path varies; extensible hook (add reader when located).
    return harvested


def _default_registry() -> None:
    """Built-in human-native folders (AIOS_SOURCES_DIR, default ~/.aios/sources/)
    + auto-harvested app adapters from the providers' MCP configs."""
    base = Path(os.environ.get("AIOS_SOURCES_DIR", str(Path.home() / ".aios" / "sources")))
    register(FileSource("diary",  base / "diary",  category="personal"))
    register(FileSource("notes",  base / "notes",  category="docs"))
    register(FileSource("journal", base / "journal", category="personal"))
    harvest_provider_adapters()


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
             "available": a.available(),
             "origin": getattr(a, "origin", "builtin"),
             "harvested": isinstance(a, _HarvestedMcp)} for a in SOURCES.values()]


# ── CLI ────────────────────────────────────────────────────────────────────────

def main(argv: list[str] | None = None) -> int:
    import argparse
    import json
    p = argparse.ArgumentParser(prog="aios sources",
        description="Pluggable memory sources — attach any app/data source to the ledger.")
    sub = p.add_subparsers(dest="cmd")
    sub.add_parser("list")
    sub.add_parser("harvest")
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

    if args.cmd == "harvest":
        out = harvest_provider_adapters()
        out["schema"] = "aios.source_harvest.v1"
        print(json.dumps(out, ensure_ascii=False, indent=2))
        return 0

    if args.cmd == "ingest":
        opt_in = frozenset(c.strip() for c in args.opt_in.split(",") if c.strip())
        out = ingest_source(args.source, ROOT, opt_in, limit=args.limit, apply=args.apply)
        print(json.dumps(out, ensure_ascii=False, indent=2))
        return 0 if out.get("status") == "ok" else 1

    # default: list
    print(head)
    for s in list_sources():
        mark = "✓" if s["available"] else "·"
        tail = ""
        if s["harvested"]:
            tail = f"   harvested←{s['origin']}"
        elif not s["available"]:
            tail = "   (not configured)"
        print(f"  {mark} {s['name']:<16} [{s['category']}/{s['kind']}]{tail}")
    if _HARVESTED_SKILLS:
        print(f"  + {_HARVESTED_SKILLS} skills wired into providers (capability spine)")
    print("  harvest pulls adapters from providers' MCP configs — no hand-writing.")
    print("  attach a custom app: subclass SourceAdapter/McpSource + register().")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
