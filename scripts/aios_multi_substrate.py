#!/usr/bin/env python3
"""
aios_multi_substrate.py — Unified multi-substrate AIOS execution pipeline.

The repeatable, production-grade AIOS workflow:
  1. Fan out task to ALL available providers simultaneously
  2. Collect responses with timeout isolation
  3. Detect disagreements (disagreement = signal, not noise)
  4. Synthesize: agreement zones → high confidence; disagreements → investigate
  5. Emit structured result to event bus

Usage:
  python3 scripts/aios_multi_substrate.py run --task "your task here"
  python3 scripts/aios_multi_substrate.py run --task "..." --providers gemini,local
  python3 scripts/aios_multi_substrate.py run --task "..." --emit   # write to event bus

This is the core of 'ultrathink': structured multi-perspective synthesis
rather than single frozen-model reasoning.
"""

import argparse
import concurrent.futures
import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))

from aios_provider import call_gemini, call_local_llm, call_claude, _gemini_available

DEFAULT_TIMEOUT = 60
DEFAULT_PROVIDERS = ["gemini", "local"]  # claude requires API key


# ── per-provider runner ───────────────────────────────────────────────────────

def _run_provider(provider: str, model: str | None, prompt: str, timeout: int) -> dict:
    """Run one provider arm and return its result dict."""
    if provider == "gemini":
        return call_gemini(prompt, model=model, timeout=timeout)
    elif provider == "local":
        from aios_provider import DEFAULT_LOCAL_MODEL
        return call_local_llm(prompt, model=model or DEFAULT_LOCAL_MODEL, timeout=timeout)
    elif provider == "claude":
        return call_claude(prompt, model=model, timeout=timeout)
    else:
        return {"provider": provider, "ok": False, "error": f"unknown provider: {provider}", "text": ""}


# ── synthesis ─────────────────────────────────────────────────────────────────

def _llm_synthesize(task: str, texts: dict[str, str]) -> str | None:
    """
    True ultrathink synthesis: use an available LLM to reason across all arms.
    Returns the synthesis text, or None if no synthesizer available.
    """
    if not texts:
        return None

    arms_block = "\n\n".join(
        f"=== {provider.upper()} ===\n{text}" for provider, text in texts.items()
    )
    synthesis_prompt = f"""You are a synthesis engine. You received responses from {len(texts)} AI models on the same task.

TASK: {task}

RESPONSES:
{arms_block}

Your job (answer in Korean):
1. What do all models AGREE on? (high confidence)
2. Where do they DISAGREE or diverge? (investigate further)
3. What is the synthesized answer that incorporates the best of all responses?
4. Which response should be trusted most and why?

Be concise. Focus on the DIFFERENCES between responses — agreement is less interesting than disagreement."""

    # Try local first (free, private), then gemini
    result = call_local_llm(synthesis_prompt, timeout=90)
    if result["ok"] and len(result["text"]) > 50:
        return f"[synthesized by local]\n{result['text']}"
    result = call_gemini(synthesis_prompt, timeout=60)
    if result["ok"] and len(result["text"]) > 50:
        return f"[synthesized by gemini]\n{result['text']}"
    return None


def _synthesize(results: list[dict], task: str, use_llm: bool = True) -> dict:
    """
    Ultrathink synthesis: LLM-based cross-model reasoning.
    Falls back to heuristic if no synthesizer available.
    """
    successes = [r for r in results if r.get("ok")]
    failures = [r for r in results if not r.get("ok")]

    if not successes:
        return {
            "ok": False,
            "synthesis": None,
            "agreement_zones": [],
            "disagreements": [],
            "failed_providers": [r["provider"] for r in failures],
            "recommendation": "all providers failed — check provider availability",
        }

    texts = {r["provider"]: r["text"] for r in successes}

    # Attempt true LLM-based synthesis (ultrathink)
    llm_synthesis = None
    if use_llm and len(successes) >= 2:
        llm_synthesis = _llm_synthesize(task, texts)

    # Heuristic fallback: keyword overlap for agreement zones
    agreement_zones = _find_agreement(list(texts.values())) if len(successes) >= 2 else []
    disagreements = _find_disagreements(texts)

    # Build synthesis text
    if llm_synthesis:
        synthesis_text = llm_synthesis
        synthesis_method = "llm"
    else:
        primary_provider = max(successes, key=lambda r: len(r.get("text", "")))["provider"]
        synthesis_text = "\n\n".join(
            f"[{p}] {t[:600]}" for p, t in texts.items()
        )
        synthesis_method = "heuristic"

    confidence = (
        "high" if llm_synthesis and len(successes) >= 2 and not disagreements else
        "medium" if len(successes) >= 2 else
        "low"
    )

    return {
        "ok": True,
        "task": task,
        "providers_used": [r["provider"] for r in successes],
        "providers_failed": [r["provider"] for r in failures],
        "synthesis_method": synthesis_method,
        "synthesis": synthesis_text,
        "raw_responses": texts,
        "agreement_zones": agreement_zones,
        "disagreements": disagreements,
        "confidence": confidence,
    }


def _find_agreement(texts: list[str]) -> list[str]:
    word_sets = [set(t.lower().split()) for t in texts]
    common_words = word_sets[0]
    for ws in word_sets[1:]:
        common_words &= ws
    stop = {"the", "a", "an", "is", "are", "was", "were", "and", "or", "but", "in", "on",
            "at", "to", "for", "of", "with", "it", "this", "that", "be", "have", "do",
            "이", "은", "는", "이다", "있다", "하다", "수", "을", "를", "의", "에"}
    significant = [w for w in common_words if w not in stop and len(w) > 3]
    return [f"shared concepts: {', '.join(sorted(significant)[:8])}"] if significant else []


def _find_disagreements(texts: dict[str, str]) -> list[str]:
    disagreements = []
    if len(texts) < 2:
        return []
    lengths = {p: len(t) for p, t in texts.items()}
    avg_len = sum(lengths.values()) / len(lengths)
    for provider, length in lengths.items():
        if avg_len > 0 and (length < avg_len * 0.15 or length > avg_len * 4):
            disagreements.append(
                f"{provider} length ({length}ch) diverges from avg ({int(avg_len)}ch) — check confidence"
            )
    uncertainty_markers = ["i don't know", "uncertain", "cannot", "hallucin", "모르", "불확실"]
    for provider, text in texts.items():
        for marker in uncertainty_markers:
            if marker in text.lower():
                disagreements.append(f"{provider}: uncertainty marker '{marker}' detected")
                break
    return disagreements


# ── event bus emission ────────────────────────────────────────────────────────

def _emit_result(root: Path, synthesis: dict) -> None:
    bus_path = root / ".aios" / "primitives" / "events.jsonl"
    bus_path.parent.mkdir(parents=True, exist_ok=True)
    record = {
        "schema_version": "aios.primitive_event.v1",
        "kind": "multi_substrate",
        "name": "aios-multi-substrate-result",
        "ts_iso": datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds"),
        "payload": {
            "task_snippet": synthesis.get("task", "")[:100],
            "providers_used": synthesis.get("providers_used", []),
            "providers_failed": synthesis.get("providers_failed", []),
            "confidence": synthesis.get("confidence", "unknown"),
            "agreement_zones": synthesis.get("agreement_zones", []),
            "disagreements": synthesis.get("disagreements", []),
        },
    }
    with bus_path.open("a", encoding="utf-8") as f:
        f.write(json.dumps(record, ensure_ascii=False) + "\n")


# ── commands ──────────────────────────────────────────────────────────────────

def cmd_run(args) -> None:
    task = args.task
    provider_list = [p.strip() for p in args.providers.split(",")]
    timeout = args.timeout
    model_map: dict[str, str | None] = {}

    # Filter to available providers
    available = []
    for p in provider_list:
        if p == "gemini" and not _gemini_available():
            print(f"[skip] gemini: not available", file=sys.stderr)
            continue
        if p == "local":
            from aios_provider import DEFAULT_LOCAL_MODEL
            import urllib.request, urllib.error
            try:
                urllib.request.urlopen("http://localhost:11434/api/tags", timeout=2)
            except Exception:
                print(f"[skip] local: ollama not running", file=sys.stderr)
                continue
        if p == "claude" and not os.environ.get("ANTHROPIC_API_KEY"):
            print(f"[skip] claude: no API key", file=sys.stderr)
            continue
        available.append(p)

    if not available:
        print("ERROR: no providers available", file=sys.stderr)
        sys.exit(1)

    print(f"[aios_multi_substrate] fanning out to: {available}", file=sys.stderr)

    # Fan out in parallel
    results = []
    with concurrent.futures.ThreadPoolExecutor(max_workers=len(available)) as pool:
        futures = {
            pool.submit(_run_provider, p, model_map.get(p), task, timeout): p
            for p in available
        }
        for future in concurrent.futures.as_completed(futures):
            provider = futures[future]
            try:
                result = future.result()
                results.append(result)
                status = "✓" if result["ok"] else "✗"
                print(f"  {status} {provider}: {len(result.get('text',''))} chars", file=sys.stderr)
            except Exception as e:
                results.append({"provider": provider, "ok": False, "error": str(e), "text": ""})
                print(f"  ✗ {provider}: exception {e}", file=sys.stderr)

    # Synthesize
    synthesis = _synthesize(results, task)

    # Emit to event bus
    if args.emit:
        _emit_result(ROOT, synthesis)
        print("[aios_multi_substrate] result emitted to event bus", file=sys.stderr)

    # Output
    if args.json:
        print(json.dumps(synthesis, ensure_ascii=False, indent=2))
    else:
        print(f"\n=== ULTRATHINK: HIVEMIND SYNTHESIS ===")
        print(f"(multi-perspective cross-model analysis — disagreement = signal)")
        print(f"task: {task[:100]}")
        print(f"providers: {synthesis.get('providers_used', [])} | failed: {synthesis.get('providers_failed', [])}")
        print(f"confidence: {synthesis.get('confidence', 'unknown')}")
        if synthesis.get("agreement_zones"):
            print(f"\nagreement zones:")
            for z in synthesis["agreement_zones"]:
                print(f"  • {z}")
        if synthesis.get("disagreements"):
            print(f"\ndisagreements (investigate):")
            for d in synthesis["disagreements"]:
                print(f"  ⚠ {d}")
        method = synthesis.get("synthesis_method", "heuristic")
        synth_text = synthesis.get("synthesis", "")
        if method == "llm" and synth_text:
            print(f"\n--- LLM SYNTHESIS (ultrathink: {method}) ---")
            print(synth_text[:1200])
            if len(synth_text) > 1200:
                print(f"  ... ({len(synth_text)-1200} more chars)")
        print(f"\n--- RAW ARMS ---")
        for provider, text in synthesis.get("raw_responses", {}).items():
            print(f"\n[{provider}]: {text[:350]}")
            if len(text) > 350:
                print(f"  ... ({len(text)-350} more chars)")


# ── main ──────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description="AIOS multi-substrate execution pipeline")
    parser.add_argument("--json", action="store_true")
    sub = parser.add_subparsers(dest="command")

    p_run = sub.add_parser("run", help="Fan task out to multiple providers and synthesize")
    p_run.add_argument("--task", required=True, help="Task/prompt to run")
    p_run.add_argument("--providers", default=",".join(DEFAULT_PROVIDERS),
                       help=f"Comma-separated providers (default: {','.join(DEFAULT_PROVIDERS)})")
    p_run.add_argument("--timeout", type=int, default=DEFAULT_TIMEOUT)
    p_run.add_argument("--emit", action="store_true", help="Emit result to AIOS event bus")

    args = parser.parse_args()
    if args.command is None:
        parser.print_help()
        return
    if args.command == "run":
        cmd_run(args)


if __name__ == "__main__":
    main()
