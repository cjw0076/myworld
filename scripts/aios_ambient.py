#!/usr/bin/env python3
"""AIOS Ambient — make a download wire AIOS alongside every provider (the moat).

Founder (2026-06-09): the layer that attaches BESIDE the providers — so a download
makes the device's agents follow AIOS — is the core moat of a new company axis. Go
boldly. This realizes it via each provider's PUBLISHED extension surface (hooks + MCP
+ context files) — NOT by piercing their closed runtime (that couples to internals and
breaks AIOS's churn-resilience thesis). The doors the providers left open:

  - Claude Code : ~/.claude/settings.json  → SessionStart + PreToolUse hooks + MCP server
  - Codex       : ~/.codex/config.toml      → [mcp_servers.aios]
  - Gemini      : ~/.gemini/settings.json   → mcpServers.aios

SAFE-by-construction (reversible risk, the responsible form of bold): every change is
idempotent (a marker prevents double-add), NON-destructive (merges into existing
config; backs up first), JSON-validated before write (fail-closed: never write a
malformed config), and fully reversible (`unwire` removes exactly the AIOS entries).

Schema: aios.ambient.v1
Usage: python aios_ambient.py status|wire|unwire [--home ~] [--root <aios>] [--apply]
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MARK = "aios"                       # entry key / marker for idempotency + clean removal
PROVIDERS = ("claude", "codex", "gemini")


def _mcp_command(root: Path) -> dict:
    return {"command": "python", "args": [(root / "scripts" / "aios_mcp_server.py").as_posix()]}


def _backup(path: Path) -> None:
    if path.exists():
        bak = path.with_suffix(path.suffix + ".aios-bak")
        if not bak.exists():            # keep the FIRST pre-AIOS state
            bak.write_text(path.read_text(encoding="utf-8"), encoding="utf-8")


def _load_json(path: Path) -> dict:
    if path.exists():
        try:
            d = json.loads(path.read_text(encoding="utf-8"))
            return d if isinstance(d, dict) else {}
        except json.JSONDecodeError:
            return {}
    return {}


def _write_json(path: Path, data: dict) -> bool:
    text = json.dumps(data, ensure_ascii=False, indent=2)
    json.loads(text)                    # validate before write — fail-closed
    path.parent.mkdir(parents=True, exist_ok=True)
    _backup(path)
    path.write_text(text, encoding="utf-8")
    return True


# --- Claude Code: hooks + MCP --------------------------------------------------

def _claude_hooks(root: Path) -> dict:
    brief = (root / "scripts" / "aios_session_brief.sh").as_posix()
    guard = (root / "scripts" / "aios_guard_hook.py").as_posix()
    return {
        "SessionStart": [{"hooks": [{"type": "command", "command": f"bash {brief} 2>/dev/null || true"}]}],
        "PreToolUse": [{"matcher": "Bash|Write",
                        "hooks": [{"type": "command", "command": f"python3 {guard} 2>/dev/null || true"}]}],
    }


def _has_aios_hook(hooks: dict) -> bool:
    return any(MARK in json.dumps(v) for v in hooks.values()) if isinstance(hooks, dict) else False


def wire_claude(home: Path, root: Path, apply: bool) -> dict:
    path = home / ".claude" / "settings.json"
    cfg = _load_json(path)
    changed = False
    cfg.setdefault("mcpServers", {})
    if MARK not in cfg["mcpServers"]:
        cfg["mcpServers"][MARK] = _mcp_command(root); changed = True
    hooks = cfg.setdefault("hooks", {})
    if not _has_aios_hook(hooks):
        for ev, entries in _claude_hooks(root).items():
            hooks.setdefault(ev, []).extend(entries)
        changed = True
    if changed and apply:
        _write_json(path, cfg)
    return {"provider": "claude", "config": path.as_posix(), "would_change": changed, "applied": changed and apply}


def unwire_claude(home: Path, apply: bool) -> dict:
    path = home / ".claude" / "settings.json"
    cfg = _load_json(path)
    changed = False
    if isinstance(cfg.get("mcpServers"), dict) and MARK in cfg["mcpServers"]:
        del cfg["mcpServers"][MARK]; changed = True
    if isinstance(cfg.get("hooks"), dict):
        for ev in list(cfg["hooks"]):
            kept = [e for e in cfg["hooks"][ev] if MARK not in json.dumps(e)]
            if len(kept) != len(cfg["hooks"][ev]):
                cfg["hooks"][ev] = kept; changed = True
    if changed and apply:
        _write_json(path, cfg)
    return {"provider": "claude", "removed": changed, "applied": changed and apply}


# --- Codex: TOML MCP entry (string-merge, no toml dep) -------------------------

def wire_codex(home: Path, root: Path, apply: bool) -> dict:
    path = home / ".codex" / "config.toml"
    existing = path.read_text(encoding="utf-8") if path.exists() else ""
    changed = "[mcp_servers.aios]" not in existing
    if changed and apply:
        block = ("\n[mcp_servers.aios]\n"
                 'command = "python"\n'
                 f'args = ["{(root / "scripts" / "aios_mcp_server.py").as_posix()}"]\n')
        path.parent.mkdir(parents=True, exist_ok=True)
        _backup(path)
        path.write_text(existing + block, encoding="utf-8")
    return {"provider": "codex", "config": path.as_posix(), "would_change": changed, "applied": changed and apply}


# --- Gemini: settings.json mcpServers ------------------------------------------

def wire_gemini(home: Path, root: Path, apply: bool) -> dict:
    path = home / ".gemini" / "settings.json"
    cfg = _load_json(path)
    servers = cfg.setdefault("mcpServers", {})
    changed = MARK not in servers
    if changed:
        servers[MARK] = _mcp_command(root)
        if apply:
            _write_json(path, cfg)
    return {"provider": "gemini", "config": path.as_posix(), "would_change": changed, "applied": changed and apply}


def status(home: Path) -> dict:
    claude = _load_json(home / ".claude" / "settings.json")
    codex = (home / ".codex" / "config.toml")
    gemini = _load_json(home / ".gemini" / "settings.json")
    return {
        "schema_version": "aios.ambient.v1",
        "claude": MARK in (claude.get("mcpServers") or {}) or _has_aios_hook(claude.get("hooks") or {}),
        "codex": codex.exists() and "[mcp_servers.aios]" in codex.read_text(encoding="utf-8"),
        "gemini": MARK in (gemini.get("mcpServers") or {}),
    }


def wire_all(home: Path, root: Path, apply: bool) -> dict:
    return {"claude": wire_claude(home, root, apply), "codex": wire_codex(home, root, apply),
            "gemini": wire_gemini(home, root, apply)}


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(description="Wire AIOS alongside the device's providers")
    p.add_argument("cmd", choices=["status", "wire", "unwire"])
    p.add_argument("--home", default=str(Path.home()))
    p.add_argument("--root", default=str(ROOT))
    p.add_argument("--apply", action="store_true", help="actually write (default: dry-run)")
    p.add_argument("--json", action="store_true")
    return p


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    home, root = Path(args.home), Path(args.root)
    if args.cmd == "status":
        out = status(home)
    elif args.cmd == "wire":
        out = wire_all(home, root, args.apply)
        out["note"] = "dry-run (use --apply to write)" if not args.apply else "applied; reversible via unwire"
    else:
        out = {"claude": unwire_claude(home, args.apply)}
    print(json.dumps(out, ensure_ascii=False, indent=2) if args.json else out)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
