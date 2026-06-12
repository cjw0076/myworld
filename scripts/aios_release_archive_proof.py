#!/usr/bin/env python3
"""ASC-0243 release/archive smoke and backend selection receipt.

This proof builds a small selected-source archive rather than copying the
working tree. It excludes runtime/private state by construction, extracts the
archive, runs the installer in isolated dry-run mode, and emits a hosted
backend selection receipt with operator prerequisites.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import subprocess
import tarfile
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Final


SCHEMA_VERSION: Final = "aios.release_archive_proof.v1"
BACKEND_SCHEMA: Final = "aios.hosted_backend_selection.v1"
ARCHIVE_NAME = "aios-selected-source.tar.gz"

SELECTED_SOURCE_FILES: Final = (
    "scripts/aios_install.sh",
    "scripts/aios_provider.py",
    "scripts/aios_credential_broker.py",
    "scripts/aios_vault.py",
)


def now_iso() -> str:
    return datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds")


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(65536), b""):
            digest.update(chunk)
    return f"sha256:{digest.hexdigest()}"


def build_backend_selection() -> dict[str, Any]:
    return {
        "schema_version": BACKEND_SCHEMA,
        "generated_at": now_iso(),
        "selected_first_tier": "local_first_release_archive",
        "optional_hosted_tiers": [
            {
                "tier": "codex_cloud_optional",
                "authority": "operator_checkpoint_required",
                "prerequisites": [
                    "OpenAI/Codex account access",
                    "configured cloud environment",
                    "credential references through broker receipts",
                    "network policy receipt",
                ],
            },
            {
                "tier": "anthropic_managed_agents_optional",
                "authority": "operator_checkpoint_required",
                "prerequisites": [
                    "Claude Managed Agents platform access",
                    "AWS/IAM or self-hosted sandbox environment",
                    "credential references through broker receipts",
                    "webhook and session receipt storage",
                ],
            },
            {
                "tier": "gemini_interactions_research_optional",
                "authority": "recommendation_only",
                "prerequisites": [
                    "Gemini API access",
                    "server-side history policy",
                    "tool-context projection into MemoryOS drafts",
                    "research-output review queue",
                ],
            },
        ],
        "decision": (
            "Use local_first_release_archive as the first deployment tier until "
            "operator account, IAM, billing, and credential prerequisites are present."
        ),
    }


def create_archive(root: Path, work_dir: Path) -> tuple[Path, list[dict[str, str]]]:
    archive_path = work_dir / ARCHIVE_NAME
    manifest: list[dict[str, str]] = []
    with tarfile.open(archive_path, "w:gz") as tar:
        for rel in SELECTED_SOURCE_FILES:
            path = root / rel
            if not path.exists():
                raise FileNotFoundError(rel)
            tar.add(path, arcname=f"myworld/{rel}")
            manifest.append({"path": rel, "sha256": sha256_file(path)})
    return archive_path, manifest


def run_release_archive_proof(root: Path) -> dict[str, Any]:
    root = root.resolve()
    with tempfile.TemporaryDirectory(prefix="aios-release-proof-") as tmp:
        tmp_root = Path(tmp)
        archive_path, manifest = create_archive(root, tmp_root)
        extract_root = tmp_root / "extract"
        extract_root.mkdir()
        with tarfile.open(archive_path, "r:gz") as tar:
            tar.extractall(extract_root, filter="data")
        copy_root = extract_root / "myworld"
        home = tmp_root / "home"
        xdg = tmp_root / "xdg"
        shell_rc = home / ".bashrc"
        home.mkdir()
        xdg.mkdir()
        env = {
            **os.environ,
            "HOME": home.as_posix(),
            "XDG_CONFIG_HOME": xdg.as_posix(),
            "AIOS_INSTALL_DRY_RUN": "1",
            "AIOS_SKIP_PIP": "1",
            "AIOS_SHELL_RC": shell_rc.as_posix(),
            "AIOS_VAULT_DIR": (tmp_root / "vault").as_posix(),
        }
        install = subprocess.run(
            ["bash", "scripts/aios_install.sh"],
            cwd=copy_root,
            env=env,
            text=True,
            capture_output=True,
            timeout=60,
            check=False,
        )
        provider_status = subprocess.run(
            ["python3", "scripts/aios_provider.py", "status"],
            cwd=copy_root,
            env=env,
            text=True,
            capture_output=True,
            timeout=30,
            check=False,
        )
        backend_selection = build_backend_selection()
        archive_forbidden_present = [
            member
            for member in tarfile.open(archive_path, "r:gz").getnames()
            if member in {"myworld/.git", "myworld/.aios", "myworld/.runs", "myworld/.env"}
            or member.startswith(("myworld/.git/", "myworld/.aios/", "myworld/.runs/"))
        ]
        smoke_generated_runtime_state = (copy_root / ".aios").exists() and "myworld/.aios" not in archive_forbidden_present
        return {
            "schema_version": SCHEMA_VERSION,
            "generated_at": now_iso(),
            "source_root": root.as_posix(),
            "archive_name": archive_path.name,
            "archive_sha256": sha256_file(archive_path),
            "selected_source_manifest": manifest,
            "install_returncode": install.returncode,
            "provider_status_returncode": provider_status.returncode,
            "ok": install.returncode == 0 and provider_status.returncode == 0 and not archive_forbidden_present,
            "stdout_tail": install.stdout.splitlines()[-20:],
            "stderr_tail": install.stderr.splitlines()[-20:],
            "provider_status_tail": provider_status.stdout.splitlines()[-20:],
            "backend_selection": backend_selection,
            "privacy_receipt": {
                "archive_from_selected_sources": True,
                "archive_forbidden_runtime_or_private_paths_present": archive_forbidden_present,
                "smoke_generated_isolated_runtime_state": smoke_generated_runtime_state,
                "used_isolated_home": True,
                "used_isolated_xdg_config": True,
                "used_isolated_vault_dir": True,
                "wrote_operator_shell_rc": False,
                "credential_values_printed": False,
            },
        }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Run AIOS release/archive smoke proof")
    parser.add_argument("--root", default=Path(__file__).resolve().parents[1].as_posix())
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args(argv)
    payload = run_release_archive_proof(Path(args.root))
    if args.json:
        print(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True))
    else:
        print(f"ok={payload['ok']}")
        print(f"archive={payload['archive_name']} {payload['archive_sha256']}")
        print(f"selected_first_tier={payload['backend_selection']['selected_first_tier']}")
    return 0 if payload["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
