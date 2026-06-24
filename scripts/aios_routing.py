#!/usr/bin/env python3
"""aios_routing — the one capability spine (renewal Cycle 7).

A single source of truth for the "what kind of task is this, and which model
should run it?" decision, shared by every runner. Before this, the head
(`_auto_provider`) and the harness (`classify_horizon`) each had their own
complexity heuristic; they now both consult `classify_horizon` here.

Research basis (arXiv 2509.09677): reasoning models evade self-conditioning and
run far longer, so long-horizon work should route to a heavier reasoning model.
"""
from __future__ import annotations

import json
import urllib.request

# Local model tiers, best-available-first. Long-horizon → reasoning model.
LONG_HORIZON_MODELS = ["qwen3:30b-a3b", "qwen3:8b", "qwen3-coder:30b"]
SHORT_HORIZON_MODELS = ["qwen3:8b", "qwen3:4b", "qwen3:1.7b"]

# Multi-step / planning-heavy signals (EN + KO).
HORIZON_SIGNALS = (
    "then", "after", "next", "finally", "step", "steps", "refactor", "migrate",
    "implement", "integrate", "debug", "build", "design", "analyze and", "pipeline",
    "그리고", "그다음", "단계", "구현", "리팩터", "마이그레이션", "분석하고", "빌드",
)


def classify_horizon(task: str) -> str:
    """'long' if the task looks multi-step / planning-heavy, else 'short'.
    The single horizon judgment every runner shares."""
    t = task.lower()
    score = sum(1 for s in HORIZON_SIGNALS if s in t)
    score += t.count(" and ") + t.count("그리고")
    return "long" if (score >= 2 or len(task) > 160) else "short"


# Domain partition keys for sparse memory activation (runtime: scope to the task's
# domain; sleep/train: full). Keyword → domain; first match wins, else None=general.
DOMAIN_SIGNALS = {
    "finance":   ("fraud", "transaction", "credit", "risk score", "basel", "fico", "payment"),
    "hr":        ("attrition", "employee", "retention", "churn", "workforce", "hiring", "headcount"),
    "logistics": ("inventory", "demand forecast", "supply chain", "eoq", "sku", "warehouse"),
    "farm":      ("crop", "yield", "soil", "irrigation", "harvest", "farm"),
    "energy":    ("grid", "load forecast", "power", "electricity", "kwh", "energy"),
    "security":  ("intrusion", "threat", "cyber", "vulnerability", "malware", "exploit"),
    "code":      ("code", "function", "bug", "refactor", "implement", "debug", "script",
                  "파일", "코드", "함수", "버그", "구현", "리팩터"),
}


def classify_domain(task: str) -> str | None:
    """Map a task to its domain partition key, or None (general → full activation).
    Used to keep runtime memory recall sparse (only the relevant partition)."""
    t = task.lower()
    for domain, kws in DOMAIN_SIGNALS.items():
        if any(k in t for k in kws):
            return domain
    return None


def _installed_models(base_url: str) -> set[str]:
    try:
        host = base_url.split("/v1")[0].rstrip("/")
        with urllib.request.urlopen(f"{host}/api/tags", timeout=4) as r:
            return {m["name"] for m in json.loads(r.read()).get("models", [])}
    except Exception:  # noqa: BLE001
        return set()


def select_model_by_horizon(task: str, base_url: str) -> str:
    """Pick a reasoning model for long-horizon tasks, a fast one for short — among
    installed models. Falls back to qwen3:8b."""
    prefs = LONG_HORIZON_MODELS if classify_horizon(task) == "long" else SHORT_HORIZON_MODELS
    installed = _installed_models(base_url)
    for m in prefs:
        if not installed or m in installed:
            return m
    return "qwen3:8b"


def executable_clis() -> set[str]:
    """CLI providers AIOS can actually EXECUTE — derived from the adapter registry
    (aios_adapters.SPECS) so 'write an adapter → it becomes routable' holds with no
    edit here. Part of the one capability spine: the single 'what can we route to?'
    answer, shared by onboard and any other routing decision. Falls back to the
    known CLI adapters if aios_adapters can't be imported."""
    try:
        import aios_adapters  # noqa: PLC0415
        return {s.binary for s in aios_adapters.SPECS.values() if s.binary != "ollama"}
    except Exception:  # noqa: BLE001
        return {"claude", "codex", "gemini"}
