#!/usr/bin/env python3
"""aios device-profile — detect the host's capability and recommend the
runnable AIOS combination.

Founder requirement (2026-05-17): "lay a base that runs at roughly this
device's performance level, but build a plugin that figures out what
combination this system can run." AIOS must not assume one machine — it must
self-detect what it can actually run on whatever it is deployed to.

This is the gate the rest of AIOS consults instead of a static `--full`
flag: `aios setup`, the round controller's dream step, and the phase-2
adapter-evolution organ all read this profile to decide what to enable.

  aios device-profile detect       raw detected host resources
  aios device-profile recommend    the runnable combination + profile name

Pure standard library — runs before any dependency (psutil/torch) is
installed, because deciding whether to install them is part of its job.
"""

from __future__ import annotations

import argparse
import importlib.util
import json
import os
import shutil
import subprocess
import sys
import urllib.request
from pathlib import Path
from typing import Any

OLLAMA_TAGS = "http://127.0.0.1:11434/api/tags"

# Rough resident footprint of each local model (GB) — used to decide which
# tier a device can hold. Conservative; Ollama mmaps so real RSS is lower.
MODEL_FOOTPRINT_GB = {
    "nomic-embed-text": 0.3,
    "qwen3:1.7b": 2.0,
    "qwen3:8b": 6.0,
    "deepseek-coder:6.7b": 5.0,
    "deepseek-coder-v2:16b": 10.0,
    "qwen3:30b-a3b": 20.0,
}


def _meminfo() -> dict[str, float]:
    info: dict[str, float] = {}
    try:
        for line in Path("/proc/meminfo").read_text().splitlines():
            key, _, rest = line.partition(":")
            kb = rest.strip().split()[0]
            info[key] = round(int(kb) / (1024 * 1024), 1)  # GB
    except (OSError, ValueError, IndexError):
        pass
    return info


def _detect_gpus() -> list[dict[str, Any]]:
    """NVIDIA GPUs via nvidia-smi. Empty list means no usable CUDA GPU."""
    try:
        proc = subprocess.run(
            ["nvidia-smi", "--query-gpu=name,memory.total,memory.free",
             "--format=csv,noheader,nounits"],
            capture_output=True, text=True, timeout=15,
        )
    except (OSError, subprocess.TimeoutExpired):
        return []
    if proc.returncode != 0:
        return []
    gpus: list[dict[str, Any]] = []
    for line in proc.stdout.strip().splitlines():
        parts = [p.strip() for p in line.split(",")]
        if len(parts) >= 3:
            try:
                gpus.append({"name": parts[0],
                             "vram_total_gb": round(int(parts[1]) / 1024, 1),
                             "vram_free_gb": round(int(parts[2]) / 1024, 1)})
            except ValueError:
                continue
    return gpus


def _ollama_models() -> list[str]:
    try:
        with urllib.request.urlopen(OLLAMA_TAGS, timeout=10) as r:
            return [m.get("name", "") for m in json.loads(r.read()).get("models", [])]
    except Exception:  # noqa: BLE001
        return []


def _has(mod: str) -> bool:
    try:
        return importlib.util.find_spec(mod) is not None
    except (ImportError, ValueError):
        return False


def detect(root: Path) -> dict[str, Any]:
    mem = _meminfo()
    gpus = _detect_gpus()
    free_bytes = shutil.disk_usage(root).free
    return {
        "ram_total_gb": mem.get("MemTotal", 0.0),
        "ram_available_gb": mem.get("MemAvailable", 0.0),
        "cpu_cores": os.cpu_count() or 1,
        "gpus": gpus,
        "gpu_count": len(gpus),
        "vram_total_gb": round(sum(g["vram_total_gb"] for g in gpus), 1),
        "disk_free_gb": round(free_bytes / (1024 ** 3), 1),
        "ollama_up": bool(_ollama_models()),
        "ollama_models": _ollama_models(),
        "training_stack": {m: _has(m) for m in ("torch", "transformers", "peft")},
        "psutil_present": _has("psutil"),
    }


def recommend(root: Path) -> dict[str, Any]:
    d = detect(root)
    ram = d["ram_available_gb"] or d["ram_total_gb"]
    vram = d["vram_total_gb"]
    notes: list[str] = []

    # --- which model tiers the device can hold ---
    runnable = [m for m, gb in MODEL_FOOTPRINT_GB.items() if gb <= max(ram, vram)]
    minimal = {"qwen3:1.7b", "qwen3:8b", "nomic-embed-text"}
    has_minimal = minimal.issubset(set(runnable))
    has_strong = "qwen3:30b-a3b" in runnable
    has_code = "deepseek-coder-v2:16b" in runnable

    # --- dream phase 1 (embed consolidation) — cheap, runs almost anywhere ---
    phase1 = ram >= 2.0
    if not phase1:
        notes.append("phase 1 (embed) needs ~2 GB free RAM — too constrained")

    # --- dream phase 2 (parametric LoRA adapter re-fit) ---
    stack_ok = all(d["training_stack"].values())
    gpu_fast = vram >= 8.0          # QLoRA of an 8B comfortably
    cpu_slow_ok = ram >= 32.0       # CPU re-fit possible but slow
    if gpu_fast and stack_ok:
        phase2 = "gpu"
    elif gpu_fast and not stack_ok:
        phase2 = "gpu_pending_stack"
        notes.append("GPU present but torch/transformers/peft not installed — "
                      "`pip install torch transformers peft` to enable phase 2")
    elif cpu_slow_ok and stack_ok:
        phase2 = "cpu_slow"
        notes.append("no CUDA GPU — phase 2 adapter re-fit will run on CPU (slow); "
                      "gate it to low-traffic hours")
    elif cpu_slow_ok and not stack_ok:
        phase2 = "cpu_pending_stack"
        notes.append("CPU re-fit feasible but torch/peft not installed")
    else:
        phase2 = "off"
        notes.append("device too constrained for phase 2 — phase 1 only")

    # --- disk headroom ---
    if d["disk_free_gb"] < 20:
        notes.append(f"low disk: {d['disk_free_gb']} GB free — model pulls and "
                      "adapter checkpoints may fail; clear space")

    # --- profile name ---
    if vram >= 24 and ram >= 64:
        profile = "workstation"        # full AIOS, fast phase 2
    elif has_strong or ram >= 32:
        profile = "standard"           # full tiers, phase 2 viable
    elif has_minimal:
        profile = "laptop"             # minimal tiers, phase 1, phase 2 off/slow
    else:
        profile = "constrained"        # degraded — fast tier only

    return {
        "schema": "aios.device_profile.v1",
        "profile": profile,
        "detected": d,
        "runnable_models": runnable,
        "tiers": {"minimal": has_minimal, "strong": has_strong, "code": has_code},
        "dream_phase1_embed": phase1,
        "dream_phase2_adapter": phase2,
        "notes": notes or ["device runs the full AIOS combination"],
    }


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description="AIOS device capability profiler")
    p.add_argument("--root", default=".")
    p.add_argument("action", nargs="?", default="recommend",
                   choices=["detect", "recommend"])
    p.add_argument("--json", action="store_true")
    args = p.parse_args(argv)
    root = Path(args.root).resolve()

    result = detect(root) if args.action == "detect" else recommend(root)
    if args.json:
        print(json.dumps(result, indent=2, ensure_ascii=False))
        return 0

    if args.action == "detect":
        print("AIOS device — detected resources")
        for k, v in result.items():
            print(f"  {k}: {v}")
        return 0

    print(f"AIOS device profile: {result['profile'].upper()}")
    d = result["detected"]
    print(f"  RAM {d['ram_total_gb']} GB / {d['cpu_cores']} cores / "
          f"{d['gpu_count']} GPU ({d['vram_total_gb']} GB VRAM) / "
          f"disk {d['disk_free_gb']} GB free")
    print(f"  tiers: {', '.join(t for t, ok in result['tiers'].items() if ok) or 'fast only'}")
    print(f"  dream phase 1 (embed): {'on' if result['dream_phase1_embed'] else 'OFF'}")
    print(f"  dream phase 2 (adapter): {result['dream_phase2_adapter']}")
    for n in result["notes"]:
        print(f"  - {n}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
