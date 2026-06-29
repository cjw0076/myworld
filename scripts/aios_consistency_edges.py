#!/usr/bin/env python3
"""aios_consistency_edges — live-agent few-shot signed consistency edges over memory.

The H1 gate (scripts/aios_h1_gate.py) found that real AIOS memory has 0/1438 records
carrying typed relative-measurement structure: prose memory has no m_ij = val_j - val_i
schema, so the sheaf/H1 backbone has nothing to act on AS-IS.

This module tests the founder's counter-thesis: a LIVE AGENT can INDUCE the missing
structure by JUDGING PAIRS of memory nodes. The agent IS the restriction map. Instead of
a scalar difference, the agent emits a SIGN for each near pair:
    supports  -> +1   (the two notes agree / reinforce)
    contradicts-> -1   (the two notes make opposing claims)
    unrelated -> 0     (no logical bearing; dropped from the signed subgraph)

If the resulting SIGNED graph has frustrated cycles (product of signs around a cycle = -1),
that is genuine non-trivial H1 over the O(1)/sign sheaf — an obstruction the agent INDUCED,
justifying a sheaf backbone for THAT edge type. (Frustration is computed in
aios_h1_agent_edges.py.)

Reuses aios_semantic_fs for the node store, embeddings, cosine, and append-only journals
(DNA #3: append-only; the agent never rewrites a judgment, it appends). Privacy (DNA #7):
only the local summary text is judged; file content stays on disk.

Layout: <AIOS_FS_ROOT>/consistency_edges.jsonl — append-only signed typed edges
        {"src","dst","relation","sign","confidence","ts"}
"""
from __future__ import annotations

import json
import os
import sys
import time
from pathlib import Path

_SCRIPTS = str(Path(__file__).resolve().parent)
if _SCRIPTS not in sys.path:
    sys.path.insert(0, _SCRIPTS)
import aios_semantic_fs as SF  # noqa: E402  (reuse node store / embed / cosine / journals)

_REL_TO_SIGN = {"supports": 1, "contradicts": -1, "unrelated": 0}


def _edges_path() -> Path:
    return SF._root() / "consistency_edges.jsonl"


def _node_text(node: dict | None) -> str:
    """Local-only text the agent judges (capped summary; content stays on disk, DNA #7)."""
    return (node or {}).get("summary", "") if node else ""


def candidate_pairs(nodes: list[dict], near_k: int = 4, max_pairs: int = 200) -> list[tuple[str, str]]:
    """Top-`near_k` embedding-nearest OTHER node per node, deduped as unordered pairs,
    capped at `max_pairs`. ONLY semantically-near pairs — judging distant (trivially
    unrelated) pairs wastes the agent. Nodes without embeddings are skipped."""
    embedded = [n for n in nodes if n.get("embedding") and n.get("id")]
    pairs: set[tuple[str, str]] = set()
    for n in embedded:
        nid, nemb = n["id"], n["embedding"]
        sims = [
            (SF._cosine(nemb, o["embedding"]), o["id"])
            for o in embedded
            if o["id"] != nid
        ]
        sims.sort(key=lambda s: (-s[0], s[1]))  # nearest first, deterministic tie-break
        for _, oid in sims[:near_k]:
            pairs.add(tuple(sorted((nid, oid))))
    return sorted(pairs)[:max_pairs]


def _llm_judge(text_a: str, text_b: str) -> dict | None:
    """Judge a pair via the local LLM (ollama localhost:11434). Strict-JSON few-shot.
    Returns {"relation","confidence"} or None on ANY failure (mirrors SF._embed's degrade
    contract — never crash). Minimal urllib, like aios_agent_behavior._embed_batch."""
    import urllib.request

    model = os.environ.get("AIOS_CONSISTENCY_MODEL", "qwen3-coder:30b")
    prompt = (
        "You compare two memory notes and decide their logical relation.\n"
        'Reply with STRICT JSON only: {"relation": "supports|contradicts|unrelated", '
        '"confidence": 0.0-1.0}.\n'
        "supports = they agree or one reinforces the other.\n"
        "contradicts = they make opposing claims about the same thing.\n"
        "unrelated = different topics, no logical bearing.\n\n"
        'Note 1: "The deadline is Friday." Note 2: "We must submit by Friday." '
        '-> {"relation":"supports","confidence":0.9}\n'
        'Note 1: "Use Postgres." Note 2: "We decided against Postgres." '
        '-> {"relation":"contradicts","confidence":0.9}\n'
        'Note 1: "Cats sleep a lot." Note 2: "The API returns JSON." '
        '-> {"relation":"unrelated","confidence":0.95}\n\n'
        f"Note 1: {text_a[:500]}\nNote 2: {text_b[:500]}\nJSON:"
    )
    try:
        body = json.dumps(
            {"model": model, "prompt": prompt, "stream": False, "format": "json"}
        ).encode()
        req = urllib.request.Request(
            "http://localhost:11434/api/generate",
            data=body, headers={"Content-Type": "application/json"}, method="POST",
        )
        with urllib.request.urlopen(req, timeout=30) as r:
            resp = json.loads(r.read())["response"]
        parsed = json.loads(resp)
        rel = str(parsed.get("relation", "")).strip().lower()
        if rel not in _REL_TO_SIGN:
            return None
        return {"relation": rel, "confidence": float(parsed.get("confidence", 0.0))}
    except Exception:  # noqa: BLE001  (timeout / connection / parse — degrade, never crash)
        return None


def judge_pair(text_a: str, text_b: str, judge=None) -> dict | None:
    """Return {"relation","sign","confidence"} for the pair, or None on failure.
    `judge` is the TEST/INJECTION seam: a callable(text_a, text_b) -> {"relation",...}.
    Without it, the local LLM judges. relation -> sign mapping lives HERE (single place)."""
    try:
        raw = judge(text_a, text_b) if judge is not None else _llm_judge(text_a, text_b)
    except Exception:  # noqa: BLE001  (an injected/real judge that raises -> None, no crash)
        return None
    if not raw:
        return None
    rel = str(raw.get("relation", "")).strip().lower()
    if rel not in _REL_TO_SIGN:
        return None
    return {"relation": rel, "sign": _REL_TO_SIGN[rel], "confidence": float(raw.get("confidence", 1.0))}


def _judged_keys() -> set[tuple[str, str]]:
    """Unordered (src,dst) keys already judged (any sign) — for idempotent build."""
    keys: set[tuple[str, str]] = set()
    for e in SF._read_jsonl(_edges_path()):
        s, d = e.get("src"), e.get("dst")
        if s and d:
            keys.add(tuple(sorted((s, d))))
    return keys


def build(max_pairs: int = 200, near_k: int = 4, judge=None) -> dict:
    """Lazy/idempotent: judge the not-yet-judged near pairs and APPEND signed typed edges.
    Already-judged pairs are skipped (append-only, DNA #3). Returns a tally."""
    nodes = list(SF._live_nodes().values())
    by_id = {n["id"]: n for n in nodes}
    pairs = candidate_pairs(nodes, near_k=near_k, max_pairs=max_pairs)
    existing = _judged_keys()
    path = _edges_path()
    counts = {"judged": 0, "skipped": 0, "supports": 0, "contradicts": 0, "unrelated": 0}
    for a, b in pairs:
        key = tuple(sorted((a, b)))
        if key in existing:
            counts["skipped"] += 1
            continue
        res = judge_pair(_node_text(by_id.get(a)), _node_text(by_id.get(b)), judge=judge)
        if res is None:  # LLM/parse failure — degrade: do not record, do not crash
            continue
        SF._append(path, {
            "src": a, "dst": b,
            "relation": res["relation"], "sign": res["sign"],
            "confidence": res["confidence"], "ts": int(time.time()),
        })
        existing.add(key)
        counts["judged"] += 1
        counts[res["relation"]] += 1
    return counts


def load_signed_edges() -> list[dict]:
    """Signed subgraph: drop unrelated (sign 0); collapse duplicate (src,dst) last-write-wins."""
    collapsed: dict[tuple[str, str], dict] = {}
    for e in SF._read_jsonl(_edges_path()):
        s, d = e.get("src"), e.get("dst")
        if s and d:
            collapsed[tuple(sorted((s, d)))] = e
    return [e for e in collapsed.values() if e.get("sign", 0) != 0]


# ── CLI ──────────────────────────────────────────────────────────────────────

def main(argv: list[str] | None = None) -> int:
    import argparse
    p = argparse.ArgumentParser(prog="aios consistency-edges",
                                description="Live-agent signed consistency edges over memory.")
    sub = p.add_subparsers(dest="cmd")
    sb = sub.add_parser("build")
    sb.add_argument("--max-pairs", type=int, default=200)
    sb.add_argument("--near-k", type=int, default=4)
    sub.add_parser("stats")
    args = p.parse_args(argv)

    if args.cmd == "build":
        print(json.dumps(build(max_pairs=args.max_pairs, near_k=args.near_k), ensure_ascii=False, indent=2))
    elif args.cmd == "stats":
        signed = load_signed_edges()
        all_edges = SF._read_jsonl(_edges_path())
        print(json.dumps({
            "total_edges": len(all_edges),
            "signed_edges": len(signed),
            "supports": sum(1 for e in signed if e.get("sign") == 1),
            "contradicts": sum(1 for e in signed if e.get("sign") == -1),
            "path": _edges_path().as_posix(),
        }, ensure_ascii=False, indent=2))
    else:
        p.print_help()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
