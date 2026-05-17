#!/usr/bin/env python3
"""AIOS workbench repo registry — ASC-0181 Packet A.

A repo is emit-eligible iff it is registered in
`.aios/workbench/registry.json`. This replaces the hardcoded
`ALLOWED_REPOS = {"uri"}` so any developer repo can become a product repo
(`aios init`, ASC-0181 Packet B) without editing source.

Shared by `aios_ingest_product_recap.py` and `aios_ingest_server.py`.
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

REGISTRY_SCHEMA = "aios.workbench_registry.v1"
# Core AIOS repos are always known to the ingest transport, registered or not.
CORE_REPOS = ("myworld", "hivemind", "memoryOS", "CapabilityOS", "GenesisOS")


def registry_path(root: Path) -> Path:
    return root / ".aios" / "workbench" / "registry.json"


def load_registry(root: Path) -> dict:
    path = registry_path(root)
    if not path.exists():
        return {"schema": REGISTRY_SCHEMA, "repos": {}}
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {"schema": REGISTRY_SCHEMA, "repos": {}}
    if not isinstance(data, dict) or "repos" not in data:
        return {"schema": REGISTRY_SCHEMA, "repos": {}}
    return data


def registered_repos(root: Path) -> set[str]:
    """Repo slugs that are emit-eligible (registered as product repos)."""
    return set(load_registry(root).get("repos", {}).keys())


def known_repos(root: Path) -> set[str]:
    """Repos the ingest transport will route: core repos + registered repos."""
    return set(CORE_REPOS) | registered_repos(root)


def is_emit_eligible(root: Path, repo: str) -> bool:
    """A repo may emit product_recap packets iff it is registered."""
    return repo in registered_repos(root)


def register_repo(root: Path, repo: str, *, kind: str = "product_repo", note: str = "") -> dict:
    """Add a repo to the registry. Idempotent — re-registering refreshes the note."""
    data = load_registry(root)
    repos = data.setdefault("repos", {})
    existing = repos.get(repo, {})
    repos[repo] = {
        "kind": kind,
        "note": note or existing.get("note", ""),
        "registered_at": existing.get("registered_at")
        or datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds"),
    }
    data["schema"] = REGISTRY_SCHEMA
    path = registry_path(root)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    return data
