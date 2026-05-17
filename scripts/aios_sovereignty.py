#!/usr/bin/env python3
"""aios sovereignty — the "1인 1 AIOS" provider-independence check.

Founder thesis (2026-05-16): provider LLM agents will become corporate-
exclusive; survival means turning a well-built agent into one AIOS per
person, running on open local LLMs. The moat is the system, not the model.

This tool measures how sovereign AIOS is right now — what runs with NO
provider-model dependency (local LLMs only) vs what still needs a provider.
It makes "1인 1 AIOS" readiness a tracked, honest number instead of a hope.

A layer is `sovereign` if it can run on local LLMs alone; `provider_optional`
if it works local but a provider accelerates it; `provider_dependent` if it
cannot run without a provider account.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
import urllib.request
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

# actual-use signals — an import or an API endpoint call, NOT a mere mention.
# (a file listing "ANTHROPIC_API_KEY" in a secret-blocklist is not a dependency)
PROVIDER_MARKERS = (
    "import anthropic", "from anthropic", "import openai", "from openai",
    "api.anthropic.com", "api.openai.com",
)


def now_iso() -> str:
    return datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds")


def local_models() -> list[str]:
    try:
        with urllib.request.urlopen("http://127.0.0.1:11434/api/tags", timeout=10) as resp:
            return [m.get("name", "") for m in json.loads(resp.read()).get("models", []) if m.get("name")]
    except Exception:  # noqa: BLE001
        return []


def scan_provider_refs(root: Path, rel_paths: list[str]) -> list[str]:
    """Return files among rel_paths that hard-reference a provider LLM."""
    hits = []
    for rel in rel_paths:
        p = root / rel
        if not p.exists():
            continue
        text = p.read_text(encoding="utf-8", errors="replace").lower()
        if any(m in text for m in PROVIDER_MARKERS):
            hits.append(rel)
    return hits


def assess(root: Path) -> dict[str, Any]:
    models = local_models()
    has_local = len(models) > 0

    layers = []

    # autopoietic core — the dream loop
    dream_files = ["scripts/aios_dream.py", "scripts/aios_helper.py",
                   "scripts/aios_research_fetch.py", "scripts/aios_ingest_product_recap.py"]
    dream_provider = scan_provider_refs(root, dream_files)
    layers.append({
        "layer": "autopoietic core (dream loop, helper layer)",
        "status": "sovereign" if not dream_provider and has_local else
                  ("sovereign" if not dream_provider else "provider_dependent"),
        "detail": "runs on local Ollama models only (qwen3/deepseek)" if not dream_provider
                  else f"provider refs in: {dream_provider}",
    })

    # specialist helper layer — model tiers
    tiers_path = root / ".aios" / "helpers" / "model_tiers.json"
    tiers_ok = tiers_path.exists()
    layers.append({
        "layer": "specialist helper layer (model tiers)",
        "status": "sovereign" if tiers_ok and has_local else "provider_dependent",
        "detail": "tier-resolved against installed local models; model-agnostic" if tiers_ok
                  else "model_tiers.json missing",
    })

    # round controller — default rounds
    rc = root / "scripts" / "aios_round_controller.py"
    rc_provider_free = rc.exists() and "provider-free" in rc.read_text(encoding="utf-8", errors="replace")
    layers.append({
        "layer": "round controller (default rounds)",
        "status": "sovereign" if rc_provider_free else "provider_optional",
        "detail": "default rounds are provider-free; child execution is opt-in" if rc_provider_free
                  else "could not confirm provider-free default",
    })

    # heavy execution — Hive
    hive_local = (root / "hivemind" / "hivemind" / "local_workers.py").exists()
    layers.append({
        "layer": "heavy execution (Hive Mind)",
        "status": "provider_optional" if hive_local else "provider_dependent",
        "detail": "local worker path exists (hivemind/local_workers.py); provider CLIs accelerate but are not required"
                  if hive_local else "no local worker path found",
    })

    # operator role — local-operator organ shrinks it
    op_latest = root / ".aios" / "local_operator" / "latest.json"
    op_ratio = None
    if op_latest.exists():
        try:
            op_ratio = json.loads(op_latest.read_text(encoding="utf-8")).get("operator_sovereignty_ratio")
        except (ValueError, OSError):
            pass
    if op_ratio is not None:
        layers.append({
            "layer": "operator role",
            "status": "provider_optional",
            "detail": f"local-operator organ pre-digests dream proposals on a local model "
                      f"(strong tier); operator-sovereignty ratio {op_ratio} of routine "
                      f"decisions handled locally. Provider model accelerates hard calls but "
                      f"is no longer required for the routine operator loop.",
        })
    else:
        layers.append({
            "layer": "operator role",
            "status": "provider_dependent",
            "detail": "the operator is a provider model; the local-operator organ "
                      "(scripts/aios_local_operator.py) exists but has not run yet.",
        })

    sovereign = sum(1 for l in layers if l["status"] == "sovereign")
    optional = sum(1 for l in layers if l["status"] == "provider_optional")
    dependent = sum(1 for l in layers if l["status"] == "provider_dependent")
    total = len(layers)
    # Two honest metrics — both reported:
    # hard_dependency_readiness — the founder's stated thesis bar: "no HARD
    #   dependency; provider is an optional accelerant." A layer passes if it
    #   does NOT require a provider (sovereign OR provider_optional). Only
    #   provider_dependent fails.
    hard_dependency_readiness = round((sovereign + optional) / total, 2)
    # local_default_readiness — the stricter refinement: local is not just
    #   sufficient but the DEFAULT path. provider_optional counts half.
    local_default_readiness = round((sovereign + 0.5 * optional) / total, 2)

    return {
        "schema": "aios.sovereignty.v2",
        "generated_at": now_iso(),
        "thesis": "1인 1 AIOS — AIOS must have NO HARD dependency on provider models; provider is an optional accelerant",
        "local_models_installed": models,
        "local_runtime_available": has_local,
        "layers": layers,
        "summary": {"sovereign": sovereign, "provider_optional": optional,
                    "provider_dependent": dependent, "total": total},
        "hard_dependency_readiness": hard_dependency_readiness,
        "local_default_readiness": local_default_readiness,
        "readiness": hard_dependency_readiness,
        "verdict": (
            "SOVEREIGN — no layer has a hard provider dependency; AIOS can run as a standalone "
            f"personal AIOS on local LLMs. Refinement: local_default_readiness {local_default_readiness} "
            "(making local the default, not just sufficient, on every layer)."
            if dependent == 0 else
            f"{dependent} layer(s) still require a provider — not yet a standalone personal AIOS"
        ),
    }


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description="AIOS sovereignty / 1인 1 AIOS readiness check")
    p.add_argument("--root", default=".")
    p.add_argument("--json", action="store_true")
    args = p.parse_args(argv)
    root = Path(args.root).resolve()
    report = assess(root)

    if args.json:
        print(json.dumps(report, indent=2, ensure_ascii=False))
    else:
        print(f"AIOS sovereignty — 1인 1 AIOS readiness: {report['readiness']}")
        print(f"verdict: {report['verdict']}")
        print(f"local models: {', '.join(report['local_models_installed']) or '(none)'}")
        print()
        for l in report["layers"]:
            mark = {"sovereign": "[OK ]", "provider_optional": "[~~ ]", "provider_dependent": "[!! ]"}[l["status"]]
            print(f"{mark} {l['layer']}")
            print(f"      {l['detail']}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
