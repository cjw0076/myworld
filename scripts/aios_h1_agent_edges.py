#!/usr/bin/env python3
"""aios_h1_agent_edges — frustration / H1 on the agent-induced SIGNED consistency graph.

Companion to scripts/aios_h1_gate.py. The H1 gate showed real prose memory carries NO
relative-measurement structure (0/1438). aios_consistency_edges.py lets a live agent INDUCE
structure by judging near pairs and emitting a SIGN (+1 supports / -1 contradicts). This
module asks whether that induced SIGNED graph has non-trivial H1: a FRUSTRATED cycle whose
sign-product is -1, which cannot be consistently 2-colored / oriented (a real obstruction
over the O(1)/sign sheaf). Non-trivial H1 => the sheaf backbone is justified for THIS edge
type. Trivial H1 (balanced) => the agent's judgments are globally consistent, no obstruction.

Math note (honest): we compute frustration DIRECTLY over GF(2) via fundamental cycles, not
via descentnet's real coboundary. descentnet's identity-restriction coboundary, reformulated
with a signed incidence, has cokernel dim = E - V + (#balanced components) — which counts ALL
cycles for a balanced graph (holonomy +1) and does NOT equal the frustration index. The spec
quantity "number of independent cycles with sign-product -1" maps exactly and only to GF(2)
fundamental-cycle frustration. We still mirror aios_h1_gate's shape: build the graph, count
independent cycles (E - V + C), and take holonomy (sign-product) around each.

The fundamental-cycle frustration COUNT is basis-dependent; the VERDICT (count > 0, i.e. the
signed graph is unbalanced) is basis-invariant. That binary is the gate.

CLI: python3 scripts/aios_h1_agent_edges.py  -> runs on the real consistency_edges.jsonl,
prints the verdict dict as JSON, and writes docs/aios_h1_agent_edges_results.json.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

_SCRIPTS = str(Path(__file__).resolve().parent)
if _SCRIPTS not in sys.path:
    sys.path.insert(0, _SCRIPTS)


def _simple_signed(edges: list[dict]) -> dict[tuple[str, str], int]:
    """Collapse to a simple signed graph: sorted-pair key -> sign; drop sign 0 and self-loops;
    last-write-wins on duplicates."""
    out: dict[tuple[str, str], int] = {}
    for e in edges:
        u, v, s = e.get("src"), e.get("dst"), e.get("sign", 0)
        if not u or not v or u == v or s == 0:
            continue
        out[tuple(sorted((u, v)))] = 1 if s > 0 else -1
    return out


def build_signed_graph(edges: list[dict]):
    """Return (nodes:set, adj:dict[node -> list[(other, sign)]]) for the signed subgraph."""
    signed = _simple_signed(edges)
    nodes: set[str] = set()
    adj: dict[str, list[tuple[str, int]]] = {}
    for (u, v), s in signed.items():
        nodes.add(u)
        nodes.add(v)
        adj.setdefault(u, []).append((v, s))
        adj.setdefault(v, []).append((u, s))
    return nodes, adj


def _frustrated_triangles(signed: dict[tuple[str, str], int], adj_set: dict[str, set[str]],
                          limit: int = 10) -> list[tuple[str, str, str]]:
    """Direct (basis-free) example triples a-b-c that are pairwise-signed with product -1."""
    tris: list[tuple[str, str, str]] = []
    seen: set[tuple[str, str, str]] = set()
    for (u, v), s_uv in signed.items():
        for w in adj_set.get(u, set()) & adj_set.get(v, set()):
            tri = tuple(sorted((u, v, w)))
            if tri in seen:
                continue
            seen.add(tri)
            s_uw = signed[tuple(sorted((u, w)))]
            s_vw = signed[tuple(sorted((v, w)))]
            if s_uv * s_uw * s_vw == -1:
                tris.append(tri)
                if len(tris) >= limit:
                    return tris
    return tris


def frustration_h1(edges: list[dict]) -> dict:
    """Frustration index = number of independent cycles whose sign-product is -1
    (= dim H1 over GF(2) of the signed coboundary, w.r.t. the fundamental-cycle basis).

    Method: spanning forest via union-find -> non-tree edges are the independent cycles
    (count = E - V + C). Gauge g(node) in {+1,-1} propagated along tree edges; a non-tree
    edge (u,v,s) closes a fundamental cycle with sign-product s*g(u)*g(v); -1 == frustrated.
    """
    signed = _simple_signed(edges)
    nodes: set[str] = set()
    adj_set: dict[str, set[str]] = {}
    for (u, v) in signed:
        nodes.add(u)
        nodes.add(v)
        adj_set.setdefault(u, set()).add(v)
        adj_set.setdefault(v, set()).add(u)

    n_nodes = len(nodes)
    n_edges = len(signed)

    # union-find spanning forest: split edges into tree vs non-tree (independent cycles)
    parent = {n: n for n in nodes}

    def find(x: str) -> str:
        root = x
        while parent[root] != root:
            root = parent[root]
        while parent[x] != root:  # path compression
            parent[x], x = root, parent[x]
        return root

    tree_edges: list[tuple[str, str, int]] = []
    nontree: list[tuple[str, str, int]] = []
    for (u, v), s in signed.items():
        ru, rv = find(u), find(v)
        if ru != rv:
            parent[ru] = rv
            tree_edges.append((u, v, s))
        else:
            nontree.append((u, v, s))

    components = len({find(n) for n in nodes})
    n_independent_cycles = n_edges - n_nodes + components  # == len(nontree)

    # gauge g(node) = product of signs along the spanning-tree path from its root
    tree_adj: dict[str, list[tuple[str, int]]] = {}
    for (u, v, s) in tree_edges:
        tree_adj.setdefault(u, []).append((v, s))
        tree_adj.setdefault(v, []).append((u, s))
    gauge: dict[str, int] = {}
    for start in nodes:
        if start in gauge:
            continue
        gauge[start] = 1
        stack = [start]
        while stack:
            cur = stack.pop()
            for nxt, s in tree_adj.get(cur, ()):  # noqa: B007
                if nxt not in gauge:
                    gauge[nxt] = gauge[cur] * s
                    stack.append(nxt)

    frustrated = 0
    for (u, v, s) in nontree:
        if s * gauge[u] * gauge[v] == -1:  # fundamental-cycle sign-product
            frustrated += 1

    tris = _frustrated_triangles(signed, adj_set)

    return {
        "n_nodes": n_nodes,
        "n_signed_edges": n_edges,
        "n_independent_cycles": n_independent_cycles,
        "frustrated_cycle_count": frustrated,
        "dim_h1_estimate": frustrated,
        "frustrated_triangles": [list(t) for t in tris],
        "verdict": "NON_TRIVIAL_H1" if frustrated > 0 else "TRIVIAL_H1",
        "method": "direct_signed_cycle_gf2",
    }


def main(argv: list[str] | None = None) -> int:
    import aios_consistency_edges as CE  # noqa: PLC0415
    result = frustration_h1(CE.load_signed_edges())
    print(json.dumps(result, ensure_ascii=False, indent=2))
    out = Path(__file__).resolve().parent.parent / "docs" / "aios_h1_agent_edges_results.json"
    try:
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
        print(f"\nJSON results -> {out}")
    except Exception as exc:  # noqa: BLE001
        print(f"\n(could not write results file: {exc})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
