#!/usr/bin/env python3
"""aios setup — turnkey, idempotent AIOS deployment provisioning.

Founder requirement (2026-05-17): everything AIOS needs — local models,
helper catalog, MCP delegation config, the always-on service — must be set
up automatically on deploy, not by hand. One command → a complete,
self-maintaining, sovereign personal AIOS (1인 1 AIOS).

Reads docs/AIOS_DEPLOY_MANIFEST.md's intent and provisions it idempotently:
a retried `apply` converges to the same final state (skips what is present).

  aios setup plan          show what is present vs missing
  aios setup apply         provision minimal models + config + service + verify
  aios setup apply --full  also pull the recommended large models
"""

from __future__ import annotations

import argparse
import json
import shutil
import subprocess
import sys
import urllib.request
from pathlib import Path
from typing import Any

OLLAMA_TAGS = "http://127.0.0.1:11434/api/tags"

MINIMAL_MODELS = ["qwen3:1.7b", "qwen3:8b", "nomic-embed-text"]
RECOMMENDED_MODELS = ["qwen3:30b-a3b", "deepseek-coder-v2:16b"]

# (destination relative to root, template relative to root)
CONFIG_FILES = [
    (".aios/helpers/catalog.json", "deploy/helpers_catalog.json"),
    (".aios/helpers/model_tiers.json", "deploy/model_tiers.json"),
    (".mcp.json", "deploy/mcp.json"),
]


def device_profile(root: Path) -> dict[str, Any]:
    """Consult the device-profile plugin so setup is capability-aware — it
    pulls the recommended models only where the host can actually run them,
    instead of relying on a hand-passed --full flag."""
    script = root / "scripts" / "aios_device_profile.py"
    if not script.exists():
        return {}
    proc = subprocess.run([sys.executable, script.as_posix(), "--root", root.as_posix(),
                           "recommend", "--json"], capture_output=True, text=True, timeout=60)
    try:
        return json.loads(proc.stdout)
    except ValueError:
        return {}


def installed_models() -> list[str]:
    try:
        with urllib.request.urlopen(OLLAMA_TAGS, timeout=10) as r:
            return [m.get("name", "") for m in json.loads(r.read()).get("models", [])]
    except Exception:  # noqa: BLE001
        return []


def ollama_bin(root: Path) -> str:
    local = root / "hivemind" / ".local" / "ollama" / "bin" / "ollama"
    return str(local) if local.exists() else "ollama"


def model_present(name: str, installed: list[str]) -> bool:
    return any(name == m or m.startswith(name + ":") or name == m.split(":")[0] for m in installed)


def assess(root: Path, full: bool) -> dict[str, Any]:
    installed = installed_models()
    wanted = MINIMAL_MODELS + (RECOMMENDED_MODELS if full else [])
    models = [{"model": m, "present": model_present(m, installed),
               "set": "minimal" if m in MINIMAL_MODELS else "recommended"}
              for m in MINIMAL_MODELS + RECOMMENDED_MODELS]
    config = [{"file": dst, "present": (root / dst).exists(), "template": tpl,
               "template_present": (root / tpl).exists()}
              for dst, tpl in CONFIG_FILES]
    service = (root / ".aios" / "run" / "aios_round_controller.pid").exists() or \
              (Path.home() / ".config" / "systemd" / "user" / "aios.service").exists()
    return {"installed_models": installed, "wanted": wanted, "models": models,
            "config": config, "service_installed": service}


def cmd_plan(root: Path, full: bool, json_mode: bool) -> int:
    a = assess(root, full)
    if json_mode:
        print(json.dumps({"schema": "aios.setup.plan.v1", **a}, indent=2, ensure_ascii=False))
        return 0
    print("AIOS deploy plan" + (" (--full)" if full else ""))
    print("  models:")
    for m in a["models"]:
        want = m["model"] in a["wanted"]
        mark = "present" if m["present"] else ("WILL PULL" if want else "optional, skip")
        print(f"    [{mark:14s}] {m['model']} ({m['set']})")
    print("  config:")
    for c in a["config"]:
        print(f"    [{'present' if c['present'] else 'WILL COPY':14s}] {c['file']}")
    print(f"  service: {'installed' if a['service_installed'] else 'WILL INSTALL'}")
    return 0


def cmd_apply(root: Path, full: bool, json_mode: bool) -> int:
    a = assess(root, full)
    steps: list[dict[str, Any]] = []

    # 1. models — pull missing wanted models (idempotent: skip present)
    obin = ollama_bin(root)
    for m in a["models"]:
        if m["model"] not in a["wanted"]:
            continue
        if m["present"]:
            steps.append({"step": f"model:{m['model']}", "status": "already_present"})
            continue
        proc = subprocess.run([obin, "pull", m["model"]], capture_output=True, text=True, timeout=3600)
        steps.append({"step": f"model:{m['model']}",
                      "status": "pulled" if proc.returncode == 0 else "pull_failed",
                      "detail": (proc.stderr or "")[-200:]})

    # 2. config — copy missing config from deploy/ templates (idempotent)
    for dst, tpl in CONFIG_FILES:
        dst_p, tpl_p = root / dst, root / tpl
        if dst_p.exists():
            steps.append({"step": f"config:{dst}", "status": "already_present"})
        elif tpl_p.exists():
            dst_p.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(tpl_p, dst_p)
            steps.append({"step": f"config:{dst}", "status": "copied_from_template"})
        else:
            steps.append({"step": f"config:{dst}", "status": "template_missing", "detail": tpl})

    # 3. service — install the always-on round controller (idempotent)
    if a["service_installed"]:
        steps.append({"step": "service", "status": "already_installed"})
    else:
        inst = root / "scripts" / "aios_install.py"
        if inst.exists():
            proc = subprocess.run([sys.executable, inst.as_posix(), "--root", root.as_posix(),
                                   "install", "--json"], capture_output=True, text=True, timeout=120)
            steps.append({"step": "service",
                          "status": "installed" if proc.returncode == 0 else "install_failed",
                          "detail": (proc.stderr or proc.stdout or "")[-200:]})
        else:
            steps.append({"step": "service", "status": "installer_missing"})

    # 4. verify — run the completion check
    verify = root / "scripts" / "aios_completion.py"
    completion = None
    if verify.exists():
        proc = subprocess.run([sys.executable, verify.as_posix(), "--root", root.as_posix(), "--json"],
                              capture_output=True, text=True, timeout=120)
        if proc.returncode == 0:
            try:
                completion = json.loads(proc.stdout)
            except ValueError:
                pass

    failed = [s for s in steps if s["status"].endswith(("_failed", "_missing"))]
    result = {
        "schema": "aios.setup.apply.v1",
        "full": full,
        "steps": steps,
        "completion_verdict": (completion or {}).get("verdict", "completion check unavailable"),
        "status": "ok" if not failed else "partial",
        "failed_steps": [s["step"] for s in failed],
    }
    if json_mode:
        print(json.dumps(result, indent=2, ensure_ascii=False))
    else:
        for s in steps:
            print(f"  [{s['status']:22s}] {s['step']}")
        print(f"-- setup {result['status']}")
        print(f"   {result['completion_verdict']}")
    return 0 if not failed else 1


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description="AIOS turnkey deployment setup")
    p.add_argument("--root", default=".")
    p.add_argument("action", nargs="?", default="plan", choices=["plan", "apply"])
    p.add_argument("--full", action="store_true", help="also pull the recommended large models")
    p.add_argument("--json", action="store_true")
    args = p.parse_args(argv)
    root = Path(args.root).resolve()

    # Capability-aware: on a workstation/standard-class host, pull the
    # recommended models automatically — the device can run them, so the
    # operator should not have to remember --full.
    prof = device_profile(root)
    full = args.full
    if not full and prof.get("profile") in ("workstation", "standard"):
        full = True
        if not args.json:
            print(f"device profile: {prof['profile'].upper()} — "
                  f"auto-enabling --full (recommended models)")
    elif prof and not args.json:
        print(f"device profile: {prof.get('profile', '?').upper()} — "
              f"minimal model set")

    if args.action == "plan":
        return cmd_plan(root, full, args.json)
    return cmd_apply(root, full, args.json)


if __name__ == "__main__":
    sys.exit(main())
