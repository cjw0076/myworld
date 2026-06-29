#!/usr/bin/env python3
"""aios_memory_hygiene — per-tenant MEMORY-HYGIENE organ (DRAFT-FIRST review surface).

The founder-confirmed smaller-but-defensible role for the consistency-edge work. This is
NOT a sheaf/H1 pruner (that line is parked — see docs/AIOS_AGENT_INDUCED_H1_RESULTS.md). It
is a read-only hygiene lens over ANY tenant's memory: it scans the active AIOS_FS_ROOT and
EMITS suggestions for a human to review — duplicate clusters, supersession candidates, and
contradiction flags. World-scale: it operates purely on the active per-tenant FS root and
never hardcodes any operator's paths.

DNA #2 (draft-first): it NEVER mutates, deletes, or tombstones memory. Every item it returns
is a draft requiring human review. DNA #7 (privacy): only the local capped summary text and
embedding (already in the index) are read; file content stays on disk.

Reuses aios_semantic_fs (node store, _cosine, _root, _live_nodes) and aios_consistency_edges
(load_signed_edges for the signed support/contradict subgraph). Stdlib only otherwise.
"""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path

_SCRIPTS = str(Path(__file__).resolve().parent)
if _SCRIPTS not in sys.path:
    sys.path.insert(0, _SCRIPTS)
import aios_semantic_fs as SF  # noqa: E402  (reuse node store / cosine / root / journals)
import aios_consistency_edges as CE  # noqa: E402  (reuse signed support/contradict edges)

# Case-insensitive correction cues. "supersed" is a prefix so it catches
# supersede / supersedes / superseded; "정정" = Korean "correction".
_CORRECTION_RE = re.compile(
    r"correction to|supersed|replaces|corrects|retract|정정", re.IGNORECASE
)


def dedup_clusters(threshold: float = 0.92) -> list[dict]:
    """Union-find cluster live nodes whose pairwise embedding cosine >= threshold. Each
    cluster of size>=2 -> {cluster, canonical, duplicates, max_cosine}. canonical = node with
    the longest summary (tie-break newest ts). Degrades to [] when no node has an embedding."""
    nodes = [n for n in SF._live_nodes().values() if n.get("embedding") and n.get("id")]
    if not nodes:
        return []
    ids = [n["id"] for n in nodes]
    by_id = {n["id"]: n for n in nodes}
    parent = {i: i for i in ids}

    def find(x: str) -> str:
        while parent[x] != x:
            parent[x] = parent[parent[x]]
            x = parent[x]
        return x

    def union(a: str, b: str) -> None:
        ra, rb = find(a), find(b)
        if ra != rb:
            parent[ra] = rb

    pair_cos: dict[tuple[str, str], float] = {}
    for i in range(len(nodes)):
        for j in range(i + 1, len(nodes)):
            c = SF._cosine(nodes[i]["embedding"], nodes[j]["embedding"])
            if c >= threshold:
                union(ids[i], ids[j])
                pair_cos[(ids[i], ids[j])] = c

    groups: dict[str, list[str]] = {}
    for i in ids:
        groups.setdefault(find(i), []).append(i)

    out: list[dict] = []
    for members in groups.values():
        if len(members) < 2:
            continue
        canonical = max(
            members,
            key=lambda m: (len(by_id[m].get("summary", "")), by_id[m].get("ts", 0)),
        )
        mset = set(members)
        max_c = max(
            (c for (a, b), c in pair_cos.items() if a in mset and b in mset),
            default=float(threshold),
        )
        out.append({
            "cluster": sorted(members),
            "canonical": canonical,
            "duplicates": sorted(m for m in members if m != canonical),
            "max_cosine": round(max_c, 4),
        })
    out.sort(key=lambda d: d["cluster"][0])
    return out


def supersession_suggestions() -> list[dict]:
    """Suggest "newer SUPERSEDES older" drafts when EITHER (a) a signed CONTRADICTS edge
    links two nodes and one is clearly newer by ts, OR (b) a node's summary matches a
    correction cue. Draft only — nothing is acted on."""
    live = SF._live_nodes()
    out: list[dict] = []

    # (a) contradicts edge + a clearly-newer node supersedes the older one
    seen: set[tuple[str, str]] = set()
    for e in CE.load_signed_edges():
        if e.get("sign") != -1:
            continue
        a, b = e.get("src"), e.get("dst")
        na, nb = live.get(a), live.get(b)
        if not na or not nb:
            continue
        ta, tb = na.get("ts", 0), nb.get("ts", 0)
        if ta == tb:
            continue  # not clearly newer — leave for contradiction_flags
        newer, older = (a, b) if ta > tb else (b, a)
        key = (newer, older)
        if key in seen:
            continue
        seen.add(key)
        out.append({
            "supersedes": newer,
            "superseded": older,
            "reason": "contradicts+newer",
            "confidence": round(float(e.get("confidence", 0.5)), 4),
        })

    # (b) correction-text cue — the correcting note supersedes its nearest neighbor (best
    # semantic match), or None when no embedding/neighbor is available
    embedded = [n for n in live.values() if n.get("embedding") and n.get("id")]
    for nid, node in live.items():
        if not _CORRECTION_RE.search(node.get("summary", "")):
            continue
        superseded = None
        if node.get("embedding"):
            cands = [
                (SF._cosine(node["embedding"], o["embedding"]), o["id"])
                for o in embedded
                if o["id"] != nid
            ]
            cands.sort(key=lambda s: (-s[0], s[1]))
            if cands and cands[0][0] > 0:
                superseded = cands[0][1]
        out.append({
            "supersedes": nid,
            "superseded": superseded,
            "reason": "correction-text",
            "confidence": 0.5,
        })

    out.sort(key=lambda s: (s["reason"], s["supersedes"], s["superseded"] or ""))
    return out


def contradiction_flags() -> list[dict]:
    """Return the signed CONTRADICTS edges (sign=-1) as human-review items. Flagged, not
    auto-resolved."""
    return [
        {
            "a": e.get("src"),
            "b": e.get("dst"),
            "confidence": round(float(e.get("confidence", 0.5)), 4),
        }
        for e in CE.load_signed_edges()
        if e.get("sign") == -1
    ]


def hygiene_report(threshold: float = 0.92) -> dict:
    """Per-tenant draft review artifact: the three sections plus counts and the FS root."""
    n_nodes = len(SF._live_nodes())
    dups = dedup_clusters(threshold=threshold)
    supers = supersession_suggestions()
    flags = contradiction_flags()
    return {
        "fs_root": SF._root().as_posix(),
        "n_nodes": n_nodes,
        "dedup_clusters": dups,
        "supersession_suggestions": supers,
        "contradiction_flags": flags,
        "summary": {
            "dedup_clusters": len(dups),
            "supersession_suggestions": len(supers),
            "contradiction_flags": len(flags),
        },
        "note": "DRAFT-ONLY (DNA#2): every item is a suggestion for human review; this "
                "organ never mutates, deletes, or tombstones memory.",
    }


# ── CLI ──────────────────────────────────────────────────────────────────────

def main(argv: list[str] | None = None) -> int:
    import argparse
    p = argparse.ArgumentParser(
        prog="aios hygiene",
        description="Per-tenant memory hygiene (draft-only): dedup / supersession / "
                    "contradiction review items over the active AIOS_FS_ROOT.",
    )
    sub = p.add_subparsers(dest="cmd")
    sr = sub.add_parser("report"); sr.add_argument("--threshold", type=float, default=0.92)
    sd = sub.add_parser("dedup"); sd.add_argument("--threshold", type=float, default=0.92)
    sub.add_parser("supersede")
    sub.add_parser("flags")
    args = p.parse_args(argv)

    if args.cmd == "report":
        print(json.dumps(hygiene_report(threshold=args.threshold), ensure_ascii=False, indent=2))
    elif args.cmd == "dedup":
        print(json.dumps(dedup_clusters(threshold=args.threshold), ensure_ascii=False, indent=2))
    elif args.cmd == "supersede":
        print(json.dumps(supersession_suggestions(), ensure_ascii=False, indent=2))
    elif args.cmd == "flags":
        print(json.dumps(contradiction_flags(), ensure_ascii=False, indent=2))
    else:
        p.print_help()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
