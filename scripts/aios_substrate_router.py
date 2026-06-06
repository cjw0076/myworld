#!/usr/bin/env python3
"""Substrate router / provider-failover gate (panel item #2).

The moat condition the founder named: AIOS must survive LLM-provider churn with
no hard dependency on any one model. This routes a generation request across an
ordered list of substrates and falls back on failure, so a flow keeps producing
value even if the preferred model is down/unloaded/gone.

Core tier = LOCAL ollama models (always up, free, private) — that alone gives
churn-survival. Hosted providers can extend the chain, but local-first is the
property that matters. Returns which substrate served + the full fallback trail
(provenance: you can see what was tried).

Schema: aios.substrate_router.v1
Usage: python scripts/aios_substrate_router.py --prompt "..." [--prefer m1,m2]
"""
from __future__ import annotations

import argparse
import json
import urllib.error
import urllib.request

OLLAMA = "http://127.0.0.1:11434"
# default local fallback chain (best agentic coder → general → coder backup)
DEFAULT_CHAIN = ["qwen3-coder:30b", "qwen3:30b-a3b", "deepseek-coder-v2:16b"]


def list_local_models() -> list[str]:
    try:
        with urllib.request.urlopen(f"{OLLAMA}/api/tags", timeout=5) as r:
            return [m["name"] for m in json.loads(r.read()).get("models", [])]
    except Exception:
        return []


def generate_local(model: str, prompt: str, timeout: int = 180) -> str:
    body = json.dumps({"model": model, "prompt": prompt, "stream": False}).encode()
    req = urllib.request.Request(
        f"{OLLAMA}/api/generate", data=body, headers={"Content-Type": "application/json"}
    )
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return json.loads(r.read()).get("response", "").strip()


def generate(prompt: str, prefer: list[str] | None = None, timeout: int = 180) -> dict:
    """Try substrates in order; return the first non-empty result + the trail."""
    available = set(list_local_models())
    chain = prefer or DEFAULT_CHAIN
    trail: list[dict] = []
    for model in chain:
        if available and model not in available:
            trail.append({"substrate": model, "result": "not installed"})
            continue
        try:
            text = generate_local(model, prompt, timeout=timeout)
        except Exception as exc:  # noqa: BLE001 — any failure → fall back
            trail.append({"substrate": model, "result": f"error: {str(exc)[:80]}"})
            continue
        if text:
            trail.append({"substrate": model, "result": "ok"})
            return {"ok": True, "substrate": model, "text": text, "trail": trail}
        trail.append({"substrate": model, "result": "empty"})
    return {"ok": False, "substrate": None, "text": "", "trail": trail}


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--prompt", required=True)
    p.add_argument("--prefer", help="comma-separated model chain")
    p.add_argument("--json", action="store_true")
    return p


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    chain = [m.strip() for m in args.prefer.split(",")] if args.prefer else None
    res = generate(args.prompt, prefer=chain)
    if args.json:
        print(json.dumps(res, ensure_ascii=False, indent=2))
    else:
        served = res["substrate"] or "NONE (all substrates failed)"
        trail = " → ".join(f"{t['substrate']}:{t['result']}" for t in res["trail"])
        print(f"[served by: {served}]  trail: {trail}\n")
        print(res["text"])
    return 0 if res["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
