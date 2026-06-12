#!/usr/bin/env python3
"""Fresh-copy packaging smoke for AIOS.

The proof copies the current working tree into a temporary checkout-like
directory while excluding runtime/private state, then runs the installer in
dry-run mode with an isolated HOME/profile. It proves installability without
touching the operator's real shell profile, credentials, provider auth files,
or package environment.
"""

from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Final


SCHEMA_VERSION: Final = "aios.packaging_proof.v1"
EXCLUDED_NAMES: Final = {
    ".git",
    ".aios",
    ".runs",
    ".local",
    ".next",
    ".vercel",
    ".agent",
    "__pycache__",
    ".pytest_cache",
    "node_modules",
    "artifacts",
    "benchmark",
    "data",
    "memory",
    "ontology",
    "tmp",
    "ui",
    "uri",
    "gemini-cli",
    "gemini",
}


def now_iso() -> str:
    return datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds")


def ignore_runtime(_dir: str, names: list[str]) -> set[str]:
    return {name for name in names if name in EXCLUDED_NAMES or name.endswith(".pyc")}


def run_packaging_proof(root: Path) -> dict[str, Any]:
    root = root.resolve()
    with tempfile.TemporaryDirectory(prefix="aios-packaging-") as tmp:
        tmp_root = Path(tmp)
        copy_root = tmp_root / "myworld"
        shutil.copytree(root, copy_root, ignore=ignore_runtime)
        source_runtime_state_copied = (copy_root / ".aios").exists()
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
        result = subprocess.run(
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
        touched_real_home = "AIOS_ROOT" in (Path.home() / ".bashrc").read_text(encoding="utf-8", errors="ignore") if (Path.home() / ".bashrc").exists() else False
        return {
            "schema_version": SCHEMA_VERSION,
            "generated_at": now_iso(),
            "source_root": root.as_posix(),
            "copy_root_name": copy_root.name,
            "install_returncode": result.returncode,
            "provider_status_returncode": provider_status.returncode,
            "ok": result.returncode == 0 and provider_status.returncode == 0,
            "dry_run": True,
            "excluded_runtime_state": sorted(EXCLUDED_NAMES),
            "stdout_tail": result.stdout.splitlines()[-20:],
            "stderr_tail": result.stderr.splitlines()[-20:],
            "provider_status_tail": provider_status.stdout.splitlines()[-20:],
            "privacy_receipt": {
                "used_isolated_home": True,
                "used_isolated_xdg_config": True,
                "used_isolated_vault_dir": True,
                "copied_git_dir": (copy_root / ".git").exists(),
                "copied_aios_runtime_state": source_runtime_state_copied,
                "generated_isolated_runtime_state": (copy_root / ".aios").exists() and not source_runtime_state_copied,
                "wrote_operator_shell_rc": False,
                "operator_shell_rc_had_aios_root_before_or_after": touched_real_home,
            },
        }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Run AIOS fresh-copy packaging proof")
    parser.add_argument("--root", default=Path(__file__).resolve().parents[1].as_posix())
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args(argv)
    payload = run_packaging_proof(Path(args.root))
    if args.json:
        print(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True))
    else:
        print(f"ok={payload['ok']}")
        print(f"install_returncode={payload['install_returncode']}")
        print(f"provider_status_returncode={payload['provider_status_returncode']}")
    return 0 if payload["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
