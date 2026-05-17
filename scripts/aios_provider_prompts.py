#!/usr/bin/env python3
"""Bootstrap provider-specific AIOS prompt files with safe marker merges."""

from __future__ import annotations

import argparse
from dataclasses import dataclass
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import re
from typing import Any


SCHEMA_VERSION = "aios.provider_prompts.v1"
PROMPT_VERSION = "asc-0087.v1"
BEGIN_RE = re.compile(r"<!-- AIOS BEGIN v=([^ ]+) generated_at=([^ ]+) -->")
END_MARKER = "<!-- AIOS END -->"
TEMPLATE_DIR = Path(__file__).resolve().parent / "templates" / "provider_prompts"


@dataclass(frozen=True)
class Provider:
    name: str
    detect_paths: tuple[str, ...]
    target: str
    template: str
    idiom: str
    experimental: bool = False
    default_bootstrap: bool = False


PROVIDERS: tuple[Provider, ...] = (
    Provider("claude", (".claude",), ".claude/CLAUDE.md", "CLAUDE.md.tmpl", "Claude Code", default_bootstrap=True),
    Provider("codex", (".codex", ".config/codex"), ".codex/AGENTS.md", "AGENTS.md.tmpl", "Codex CLI"),
    Provider("gemini", (".gemini",), ".gemini/AIOS.md", "GEMINI.md.tmpl", "Gemini CLI", experimental=True),
    Provider("cursor", (".cursor",), ".cursorrules", "CURSORRULES.tmpl", "Cursor", experimental=True),
    Provider("aider", (".aider.conf.yml", ".aider.model.settings.yml", ".aider"), "CONVENTIONS.md", "AIDER_CONVENTIONS.md.tmpl", "Aider", experimental=True),
)


def now_iso() -> str:
    fixed = os.environ.get("AIOS_PROVIDER_PROMPTS_TIMESTAMP")
    if fixed:
        return fixed
    return datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds")


def root_dir(value: str | None) -> Path:
    return Path(value or Path(__file__).resolve().parents[1]).expanduser().resolve()


def home_dir(value: str | None) -> Path:
    return Path(value or os.environ.get("HOME", "~")).expanduser().resolve()


def load_template(name: str, seen: set[str] | None = None) -> str:
    seen = seen or set()
    if name in seen:
        raise ValueError(f"recursive template include: {name}")
    seen.add(name)
    path = TEMPLATE_DIR / name
    if not path.exists() and not name.endswith(".tmpl"):
        path = TEMPLATE_DIR / f"{name}.tmpl"
    text = path.read_text(encoding="utf-8")

    def replace(match: re.Match[str]) -> str:
        return load_template(match.group(1).strip(), seen)

    return re.sub(r"\{\{include ([^}]+)\}\}", replace, text)


def render_provider(provider: Provider, *, root: Path) -> str:
    body = load_template(provider.template).strip()
    generated_at = now_iso()
    return (
        f"<!-- AIOS BEGIN v={PROMPT_VERSION} generated_at={generated_at} -->\n"
        f"<!-- source_root={root.as_posix()} provider={provider.name} -->\n\n"
        f"{body}\n\n"
        f"{END_MARKER}\n"
    )


def marker_span(text: str) -> tuple[int, int, str | None] | None:
    begin = BEGIN_RE.search(text)
    if not begin:
        return None
    end = text.find(END_MARKER, begin.end())
    if end == -1:
        return None
    return begin.start(), end + len(END_MARKER), begin.group(1)


def merge_text(existing: str | None, block: str) -> tuple[str, str, bool]:
    if existing is None:
        return block, "create", True
    span = marker_span(existing)
    if span:
        start, end, _version = span
        next_text = existing[:start] + block.rstrip("\n") + existing[end:]
        if not next_text.endswith("\n"):
            next_text += "\n"
        return next_text, "replace_marker", next_text != existing
    prefix = existing if existing.endswith("\n") else existing + "\n"
    return prefix + "\n" + block, "append_marker", True


def provider_detected(provider: Provider, home: Path, cwd: Path) -> bool:
    base = cwd if provider.name in {"cursor", "aider"} else home
    return any((base / rel).exists() for rel in provider.detect_paths)


def provider_target(provider: Provider, home: Path, cwd: Path) -> Path:
    base = cwd if provider.name in {"cursor", "aider"} else home
    return (base / provider.target).resolve()


def row_for(provider: Provider, *, home: Path, cwd: Path, root: Path) -> dict[str, Any]:
    target = provider_target(provider, home, cwd)
    existing = target.read_text(encoding="utf-8") if target.exists() else None
    span = marker_span(existing or "")
    block = render_provider(provider, root=root)
    _merged, action, changed = merge_text(existing, block)
    detected = provider_detected(provider, home, cwd)
    enabled = (detected or provider.default_bootstrap) and not provider.experimental
    if provider.experimental:
        action = "skip_experimental"
        changed = False
    elif not enabled:
        action = "skip_not_detected"
        changed = False
    installed_version = span[2] if span else None
    return {
        "name": provider.name,
        "idiom": provider.idiom,
        "detected": detected,
        "experimental": provider.experimental,
        "enabled": enabled,
        "target": target.as_posix(),
        "exists": target.exists(),
        "marker_present": span is not None,
        "installed_version": installed_version,
        "current_version": PROMPT_VERSION,
        "drift": (installed_version != PROMPT_VERSION) if span else enabled,
        "action": action,
        "changed": changed,
    }


def detect(home: Path, cwd: Path, root: Path) -> dict[str, Any]:
    rows = [row_for(provider, home=home, cwd=cwd, root=root) for provider in PROVIDERS]
    return {
        "schema_version": SCHEMA_VERSION,
        "home": home.as_posix(),
        "cwd": cwd.as_posix(),
        "providers": rows,
        "detected": [row["name"] for row in rows if row["detected"]],
    }


def bootstrap(home: Path, cwd: Path, root: Path, *, dry_run: bool) -> dict[str, Any]:
    rows: list[dict[str, Any]] = []
    merges_path = root / ".aios" / "provider_prompts" / "merges.jsonl"
    for provider in PROVIDERS:
        row = row_for(provider, home=home, cwd=cwd, root=root)
        if row["enabled"]:
            target = Path(row["target"])
            existing = target.read_text(encoding="utf-8") if target.exists() else None
            merged, action, changed = merge_text(existing, render_provider(provider, root=root))
            row["action"] = action
            row["changed"] = changed
            if not dry_run and changed:
                target.parent.mkdir(parents=True, exist_ok=True)
                target.write_text(merged, encoding="utf-8")
                if action == "append_marker":
                    merges_path.parent.mkdir(parents=True, exist_ok=True)
                    with merges_path.open("a", encoding="utf-8") as fh:
                        fh.write(json.dumps({"provider": provider.name, "target": target.as_posix(), "action": action, "at": now_iso()}, ensure_ascii=False) + "\n")
        rows.append(row)
    return {
        "schema_version": SCHEMA_VERSION,
        "dry_run": dry_run,
        "home": home.as_posix(),
        "cwd": cwd.as_posix(),
        "providers": rows,
        "writes_planned": sum(1 for row in rows if row["enabled"] and row["changed"]),
        "writes_performed": 0 if dry_run else sum(1 for row in rows if row["enabled"] and row["changed"]),
    }


def status(home: Path, cwd: Path, root: Path) -> dict[str, Any]:
    payload = detect(home, cwd, root)
    payload["status"] = "ok"
    return payload


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Bootstrap AIOS provider prompt files")
    parser.add_argument("--root", help="AIOS control-plane root")
    parser.add_argument("--home", help="home directory to inspect/write; defaults to HOME")
    parser.add_argument("--cwd", help="project cwd for project-local providers; defaults to current cwd")
    sub = parser.add_subparsers(dest="cmd", required=True)
    for name in ("detect", "status"):
        cmd = sub.add_parser(name)
        cmd.add_argument("--json", action="store_true")
    boot = sub.add_parser("bootstrap")
    boot.add_argument("--dry-run", action="store_true")
    boot.add_argument("--json", action="store_true")
    refresh = sub.add_parser("refresh")
    refresh.add_argument("--json", action="store_true")
    return parser


def emit(payload: dict[str, Any], as_json: bool) -> None:
    if as_json:
        print(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True))
    else:
        print(f"{payload['schema_version']} providers={len(payload.get('providers', []))}")


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    root = root_dir(args.root)
    home = home_dir(args.home)
    cwd = Path(args.cwd).expanduser().resolve() if args.cwd else Path.cwd().resolve()
    if args.cmd == "detect":
        emit(detect(home, cwd, root), args.json)
        return 0
    if args.cmd == "status":
        emit(status(home, cwd, root), args.json)
        return 0
    if args.cmd == "bootstrap":
        emit(bootstrap(home, cwd, root, dry_run=args.dry_run), args.json)
        return 0
    if args.cmd == "refresh":
        emit(bootstrap(home, cwd, root, dry_run=False), args.json)
        return 0
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
