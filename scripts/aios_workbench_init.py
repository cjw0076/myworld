#!/usr/bin/env python3
"""aios init — register a repo as an AIOS workbench product repo (ASC-0181 Packet B).

Run from inside a developer's repo (or pass --repo-dir). It:
  1. registers the repo slug in `.aios/workbench/registry.json` (myworld side)
  2. writes a `.aios-workbench.json` config in the developer's repo so
     `aios emit-recap` can resolve the slug without re-typing it

The developer's repo keeps full execution authority — `aios init` only makes
the repo emit-eligible (ASC-0174 Authority Model: the developer holds
record/schema/participation/override authority for their own repo).
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from aios_workbench_registry import load_registry, register_repo  # noqa: E402

WORKBENCH_CONFIG = ".aios-workbench.json"
SLUG_RE = re.compile(r"^[a-z][a-z0-9_-]{1,38}[a-z0-9]$")


def now_iso() -> str:
    return datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds")


def default_slug(repo_dir: Path) -> str:
    raw = repo_dir.resolve().name.lower()
    cleaned = re.sub(r"[^a-z0-9_-]+", "-", raw).strip("-")
    return cleaned or "myproject"


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description="Register a repo as an AIOS workbench product repo")
    p.add_argument("--root", default=".", help="AIOS control-plane (myworld) root")
    p.add_argument("--repo-dir", default=".", help="the developer's repo directory")
    p.add_argument("--repo", default="", help="repo slug (default: derived from repo dir name)")
    p.add_argument("--note", default="", help="optional note for the registry entry")
    p.add_argument("--json", action="store_true", help="emit JSON")
    args = p.parse_args(argv)

    root = Path(args.root).resolve()
    repo_dir = Path(args.repo_dir).resolve()
    slug = args.repo or default_slug(repo_dir)

    if not SLUG_RE.match(slug):
        msg = f"invalid repo slug {slug!r} — use lowercase letters, digits, - and _ (3-40 chars)"
        print(f"error: {msg}", file=sys.stderr)
        return 2

    register_repo(root, slug, kind="product_repo", note=args.note or f"workbench init from {repo_dir}")

    config = {
        "schema": "aios.workbench_config.v1",
        "repo": slug,
        "aios_root": root.as_posix(),
        "initialized_at": now_iso(),
    }
    config_path = repo_dir / WORKBENCH_CONFIG
    config_path.write_text(json.dumps(config, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")

    registered = sorted(load_registry(root).get("repos", {}).keys())
    result = {
        "schema": "aios.workbench_init.v1",
        "status": "ok",
        "repo": slug,
        "repo_dir": repo_dir.as_posix(),
        "config": config_path.as_posix(),
        "aios_root": root.as_posix(),
        "registered_repos": registered,
        "next": f"emit a recap: aios emit-recap --repo {slug} --sprint <id> --subject <text> --caps <a,b> --evidence <ref>",
    }
    if args.json:
        print(json.dumps(result, indent=2, ensure_ascii=False))
    else:
        print(f"registered '{slug}' as an AIOS workbench product repo")
        print(f"  config:           {config_path}")
        print(f"  registered repos: {', '.join(registered)}")
        print(f"  next: {result['next']}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
