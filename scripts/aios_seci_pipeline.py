#!/usr/bin/env python3
"""AIOS SECI Knowledge Pipeline (Nonaka-Takeuchi adapted for agent cognition).

SECI = Socialization → Externalization → Combination → Internalization

  S: ingest_sessions()       — harvest tacit tool-use patterns from agent sessions
  E: _externalize_patterns() — top behavior patterns → MemoryOS draft proposals
  C: auto_reviewer.run()     — review & promote/reject drafts
  I: predict_behavior()      — promoted memories shape future tool selection

This script closes the E gap: behavior data now feeds MemoryOS, not just
the local akashic graph. C and I already exist; S is aios_agent_behavior.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
MEMORYOS_ROOT = ROOT / "memoryOS"
sys.path.insert(0, str(ROOT / "scripts"))
sys.path.insert(0, str(MEMORYOS_ROOT))


# ── helpers ───────────────────────────────────────────────────────────────────

def _load_behavior():
    import importlib.util
    spec = importlib.util.spec_from_file_location(
        "aios_agent_behavior", ROOT / "scripts" / "aios_agent_behavior.py"
    )
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def _load_memoryos():
    """Load MemoryOS write_draft function. Returns None if unavailable."""
    try:
        from memoryos.mcp import tool_memory_write_draft
        return tool_memory_write_draft
    except ImportError:
        return None


def _load_auto_reviewer():
    """Load MemoryOS auto_reviewer. Returns None if unavailable."""
    try:
        from memoryos.auto_reviewer import auto_review
        return auto_review
    except ImportError:
        return None


# ── S — Socialization ─────────────────────────────────────────────────────────

def phase_s(provider: str = "claude", opt_in: frozenset | None = None,
             dry_run: bool = False) -> list[dict]:
    """Harvest tacit tool-use patterns from agent sessions (already implemented)."""
    b = _load_behavior()
    opt = opt_in or frozenset({"code", "docs", "web", "memory", "competition"})
    memories = b.ingest_sessions(provider, opt)
    return memories if isinstance(memories, list) else []


# ── E — Externalization ───────────────────────────────────────────────────────

def _pattern_to_draft(pattern: dict) -> dict[str, Any]:
    """Convert a top behavior pattern → MemoryOS draft payload."""
    tools = list((pattern.get("tool_freq") or {}).keys())[:5]
    loop_type = pattern.get("loop_type", "unknown")
    category = pattern.get("category", "unknown")
    content_lines = pattern.get("content", "")[:200]

    content = (
        f"Agent behavior pattern: category={category} loop_type={loop_type}\n"
        f"Top tools observed: {', '.join(tools) or 'none'}\n"
        f"Context snippet: {content_lines}"
    )
    return {
        "memory_type": "capability",
        "content": content,
        "project": "aios",
        "origin": "assistant",
        "confidence": 0.55,
        "raw_refs": [pattern.get("id", "")],
        "source_run_id": pattern.get("id"),
    }


def phase_e(memories: list[dict], *, dry_run: bool = False,
            max_drafts: int = 5) -> list[str]:
    """Externalize top behavior patterns → MemoryOS drafts.

    Returns list of created draft IDs (or dry-run placeholders).
    """
    write_draft = _load_memoryos()
    if write_draft is None:
        print("  [E] MemoryOS unavailable — skipping externalization", file=sys.stderr)
        return []

    # Select top patterns: clean (not doom_loop), highest tool diversity
    clean = [m for m in memories if m.get("loop_type") != "doom_loop"]
    top = sorted(
        clean,
        key=lambda m: len(set((m.get("tool_freq") or {}).keys())),
        reverse=True,
    )[:max_drafts]

    draft_ids: list[str] = []
    for pat in top:
        payload = _pattern_to_draft(pat)
        if dry_run:
            draft_ids.append(f"dry:{pat.get('id', '?')[:12]}")
            print(f"  [E dry] would draft: {payload['content'][:80]}", file=sys.stderr)
            continue
        result = write_draft(MEMORYOS_ROOT, **payload)
        if result.get("status") == "ok":
            draft_ids.append(result.get("id", "?"))
        else:
            print(f"  [E] draft failed: {result.get('error', result)}", file=sys.stderr)

    return draft_ids


# ── C — Combination ───────────────────────────────────────────────────────────

def phase_c(*, dry_run: bool = False) -> dict[str, Any]:
    """Combine + review memory drafts → promote/reject via auto_reviewer."""
    auto_review = _load_auto_reviewer()
    if auto_review is None:
        print("  [C] auto_reviewer unavailable", file=sys.stderr)
        return {"accepted": [], "rejected": [], "queued": []}

    result = auto_review(MEMORYOS_ROOT, dry_run=dry_run)
    return {
        "accepted": getattr(result, "accepted", []),
        "rejected": getattr(result, "rejected", []),
        "queued": getattr(result, "queued", []),
    }


# ── I — Internalization ───────────────────────────────────────────────────────

def phase_i(context: str, candidates: list[str]) -> dict[str, Any]:
    """Use promoted memories to predict next tool (internalization verification)."""
    b = _load_behavior()
    try:
        result = b.predict_behavior(context=context, candidates=candidates, top_k=3)
        return result
    except Exception as exc:
        return {"error": str(exc)}


# ── Full SECI cycle ───────────────────────────────────────────────────────────

def run_cycle(provider: str = "claude", dry_run: bool = False,
              verify_context: str = "just read a file, need to make a change") -> dict[str, Any]:
    """Run one full SECI cycle and return a structured report."""
    print(f"[SECI] Starting cycle provider={provider} dry_run={dry_run}", file=sys.stderr)

    # S
    print("[SECI] S — Socialization: ingesting sessions...", file=sys.stderr)
    memories = phase_s(provider=provider, dry_run=dry_run)
    print(f"  [S] ingested {len(memories)} behavior patterns", file=sys.stderr)

    # E
    print("[SECI] E — Externalization: creating MemoryOS drafts...", file=sys.stderr)
    draft_ids = phase_e(memories, dry_run=dry_run)
    print(f"  [E] created {len(draft_ids)} drafts: {draft_ids}", file=sys.stderr)

    # C
    print("[SECI] C — Combination: running auto_reviewer...", file=sys.stderr)
    review = phase_c(dry_run=dry_run)
    print(
        f"  [C] accepted={len(review['accepted'])} rejected={len(review['rejected'])} "
        f"queued={len(review['queued'])}",
        file=sys.stderr,
    )

    # I
    print("[SECI] I — Internalization: verifying predict_behavior...", file=sys.stderr)
    prediction = phase_i(
        context=verify_context,
        candidates=["Edit", "Read", "Write", "Bash", "WebSearch"],
    )
    ranked = prediction.get("ranked") or [{}]
    top = ranked[0]
    print(f"  [I] top prediction: {top.get('action')} score={top.get('score')}", file=sys.stderr)

    return {
        "schema_version": "aios.seci.v1",
        "s_patterns_ingested": len(memories),
        "e_drafts_created": len(draft_ids),
        "e_draft_ids": draft_ids,
        "c_accepted": len(review["accepted"]),
        "c_rejected": len(review["rejected"]),
        "c_queued": len(review["queued"]),
        "i_top_action": top.get("action"),
        "i_top_score": top.get("score"),
        "i_method": prediction.get("method"),
        "cycle_complete": True,
    }


# ── CLI ───────────────────────────────────────────────────────────────────────

def main() -> None:
    import argparse
    parser = argparse.ArgumentParser(description="AIOS SECI Knowledge Pipeline")
    parser.add_argument("--provider", default="claude", choices=["claude", "codex", "gemini", "ollama"])
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--phase", choices=["s", "e", "c", "i", "all"], default="all")
    parser.add_argument("--json", action="store_true", dest="json_out")
    args = parser.parse_args()

    if args.phase == "all":
        result = run_cycle(provider=args.provider, dry_run=args.dry_run)
    elif args.phase == "s":
        mems = phase_s(provider=args.provider, dry_run=args.dry_run)
        result = {"s_patterns_ingested": len(mems)}
    elif args.phase == "e":
        mems = phase_s(provider=args.provider, dry_run=True)
        ids = phase_e(mems, dry_run=args.dry_run)
        result = {"e_drafts_created": len(ids), "e_draft_ids": ids}
    elif args.phase == "c":
        result = phase_c(dry_run=args.dry_run)
    else:  # i
        pred = phase_i("just read a file", ["Edit", "Read", "Bash"])
        result = {"i_ranked": pred.get("ranked", [])[:3]}

    if args.json_out:
        print(json.dumps(result, ensure_ascii=False, indent=2))
    else:
        for k, v in result.items():
            print(f"{k}: {v}")


if __name__ == "__main__":
    main()
