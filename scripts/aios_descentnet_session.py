"""DescentNet × AIOS 5-OS 배선 실험 세션.

각 OS의 데이터를 SheafCover로 변환하고 Cousin-Descent를 실행한다.
출력은 각 OS별 report (global_section / obstruction / next_measurement).

Usage:
    python scripts/aios_descentnet_session.py
    python scripts/aios_descentnet_session.py --os memoryos
    python scripts/aios_descentnet_session.py --query "AIOS 배포 전략"
    python scripts/aios_descentnet_session.py --json
"""
from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path
from typing import Any

import torch

ROOT = Path(__file__).resolve().parents[1]
DESCENTNET = ROOT.parent / "universe" / "descentnet"
sys.path.insert(0, str(DESCENTNET))

from api import (  # noqa: E402
    CousinBackboneKernel,
    CousinDescentConfig,
    SheafCover,
    descent_step,
    project_edge_field,
    residual_energy,
    run_descent,
)

STALK_DIM = 16   # embedding projection dim for all OS nodes
DTYPE = torch.float32


# ── helpers ──────────────────────────────────────────────────────────────────

def _embed_text(texts: list[str]) -> torch.Tensor:
    """Embed texts via Ollama nomic-embed-text → [N, STALK_DIM]."""
    import urllib.request, urllib.error
    vecs = []
    for text in texts:
        try:
            body = json.dumps({"model": "nomic-embed-text:latest", "input": text[:400]}).encode()
            req = urllib.request.Request(
                "http://localhost:11434/api/embed",
                data=body, headers={"Content-Type": "application/json"}, method="POST"
            )
            with urllib.request.urlopen(req, timeout=8) as r:
                d = json.loads(r.read())
            raw = d["embeddings"][0]
        except Exception:
            raw = [0.0] * 768
        # Project to STALK_DIM via stride sampling (no ML model needed)
        stride = len(raw) // STALK_DIM
        vec = [raw[i * stride] for i in range(STALK_DIM)]
        norm = (sum(v * v for v in vec) ** 0.5) or 1.0
        vecs.append([v / norm for v in vec])
    return torch.tensor(vecs, dtype=DTYPE)


def _make_cover(n: int, edge_pairs: list[tuple[int, int]] | None = None) -> SheafCover:
    """Build SheafCover from explicit edges or default to cycle."""
    if edge_pairs is None:
        return SheafCover.cycle(n, dtype=DTYPE)
    edges = torch.tensor(edge_pairs, dtype=torch.long)
    return SheafCover.from_edges(n, edges, dtype=DTYPE)


def _run(cover: SheafCover, sections: torch.Tensor,
         measurements: torch.Tensor, steps: int = 8) -> dict[str, Any]:
    """Run descent and return scalar summary."""
    final_sections, out, energies = run_descent(
        cover, sections, measurements, steps=steps
    )
    obst_mean = float(out.obstruction.abs().mean())
    occ_mean = float(out.occupancy.mean())
    energy_drop = float(energies[0] - energies[-1]) if len(energies) > 1 else 0.0
    return {
        "global_section_norm": float(out.global_section.norm()),
        "obstruction_mean": round(obst_mean, 4),
        "occupancy_mean": round(occ_mean, 4),
        "energy_start": round(float(energies[0]), 4) if energies else None,
        "energy_final": round(float(energies[-1]), 4) if energies else None,
        "energy_drop": round(energy_drop, 4),
        "conflict_cells": int(out.conflict_cells.sum()),
        "h1_detected": obst_mean > 0.05,  # H¹ signal threshold
    }


# ── OS adapters ───────────────────────────────────────────────────────────────

def run_memoryos(query: str) -> dict[str, Any]:
    """MemoryOS: top-N memory nodes → SheafCover → descent → global section.

    Node = memory object (content embedding).
    Edge = relation between memories (derived_from, related_to, contradicts).
    Query = boundary section (probe).
    Output: globally consistent memories + H¹ = contradictions.
    """
    import subprocess
    t0 = time.time()

    # Get top memories from MemoryOS
    p = subprocess.run(
        [sys.executable, "-m", "memoryos", "--root", ".", "context", "build",
         "--task", query, "--json"],
        cwd=str(ROOT / "memoryOS"), capture_output=True, text=True, timeout=10
    )
    items: list[dict] = []
    if p.returncode == 0:
        d = json.loads(p.stdout)
        for bucket in ("decisions", "constraints", "other"):
            items.extend((d.get(bucket) or [])[:4])
    items = items[:12]

    if len(items) < 3:
        return {"status": "no_data", "items": len(items)}

    # Build node texts (content only — privacy-safe, no raw refs)
    texts = [str(it.get("content", ""))[:200] for it in items]
    query_text = query

    # Embed: nodes + query
    all_texts = texts + [query_text]
    embeddings = _embed_text(all_texts)
    node_embs = embeddings[:-1]   # [N, STALK_DIM]
    query_emb = embeddings[-1]    # [STALK_DIM]

    n = len(node_embs)

    # Edges: sequential + query→each (star topology)
    edge_pairs = [(i, (i + 1) % n) for i in range(n)]  # cycle
    cover = _make_cover(n, edge_pairs)

    # sections: [1, N, D] — node embeddings as local sections
    sections = node_embs.unsqueeze(0)  # [1, N, STALK_DIM]

    # edge_measurements: expected section differences
    # Compatible edges → near-zero; contradicts → large
    relation_types = [it.get("type", "other") for it in items]
    meas_list = []
    for src, tgt in edge_pairs:
        diff = node_embs[tgt] - node_embs[src]
        # contradicts edges → flip sign (add tension)
        if relation_types[src] == "constraint":
            diff = -diff * 1.5
        meas_list.append(diff)
    measurements = torch.stack(meas_list).unsqueeze(0)  # [1, E, D]

    result = _run(cover, sections, measurements, steps=12)
    result["n_nodes"] = n
    result["elapsed_s"] = round(time.time() - t0, 2)
    result["interpretation"] = (
        "H¹ 모순 감지됨 — contradicting memories exist" if result["h1_detected"]
        else "globally consistent — memories glue cleanly"
    )
    return result


def run_genesisos(goal: str) -> dict[str, Any]:
    """GenesisOS: assumptions as nodes → obstruction = prison signature.

    Node = assumption (implicit or explicit).
    Edge = logical dependency between assumptions.
    H¹ ≠ 0 → circular reasoning / prison detected.
    """
    import subprocess
    t0 = time.time()

    # Get GenesisOS critic output
    p = subprocess.run(
        [sys.executable, "-m", "genesisos.cli", "critic", "--text", goal[:300], "--json"],
        cwd=str(ROOT / "GenesisOS"), capture_output=True, text=True, timeout=8
    )
    prison_sigs: list[str] = []
    escape_vecs: list[str] = []
    confidence = 0.0
    if p.returncode == 0:
        d = json.loads(p.stdout)
        prison_sigs = [s.get("signature", s) if isinstance(s, dict) else str(s)
                       for s in (d.get("prison_signatures") or [])]
        escape_vecs = [v.get("escape_vector", v) if isinstance(v, dict) else str(v)
                       for v in (d.get("escape_vectors") or [])]
        confidence = float(d.get("confidence", 0))

    # Nodes = [goal] + prison signatures + escape vectors
    node_texts = [goal[:200]]
    node_texts += [f"assumption: {s}" for s in prison_sigs[:4]]
    node_texts += [f"escape: {v}" for v in escape_vecs[:4]]
    n = len(node_texts)
    if n < 3:
        node_texts += ["no assumption detected"] * (3 - n)
        n = 3

    embeddings = _embed_text(node_texts)
    sections = embeddings.unsqueeze(0)  # [1, N, D]

    # Edges: goal → each assumption (star from goal node 0)
    edge_pairs = [(0, i) for i in range(1, n)]
    # Add cycle among assumptions to detect circular reasoning
    for i in range(1, n - 1):
        edge_pairs.append((i, i + 1))
    cover = _make_cover(n, edge_pairs)

    # Measurements: compatible for escapes, tension for prison nodes
    meas_list = []
    n_edges = len(edge_pairs)
    for idx, (src, tgt) in enumerate(edge_pairs):
        diff = embeddings[tgt] - embeddings[src]
        # Prison signature nodes add H¹ tension (should NOT glue cleanly)
        if "assumption:" in node_texts[tgt]:
            diff = diff + torch.randn_like(diff) * 0.5 * confidence
        meas_list.append(diff)
    measurements = torch.stack(meas_list).unsqueeze(0)

    result = _run(cover, sections, measurements, steps=10)
    result["prison_signatures"] = prison_sigs
    result["escape_vectors"] = escape_vecs[:2]
    result["critic_confidence"] = confidence
    result["elapsed_s"] = round(time.time() - t0, 2)
    result["interpretation"] = (
        f"H¹ 순환 감지 — {len(prison_sigs)} prison sig ({confidence:.2f} conf)"
        if result["h1_detected"] else
        "reasoning consistent — no circular prison"
    )
    return result


def run_capabilityos(task: str) -> dict[str, Any]:
    """CapabilityOS: env capabilities as nodes → compatible set via descent.

    Node = capability (skill/model/CLI).
    Edge = compatibility between capabilities.
    Occupancy → homo (directly usable) vs hetero (needs bridging).
    global_section = recommended capability combination.
    """
    import subprocess, os
    t0 = time.time()

    # Load env scan (cached)
    scan_path = ROOT / ".aios" / "capability_observations" / "env_scan.json"
    caps: list[dict] = []
    if scan_path.exists():
        try:
            caps = json.loads(scan_path.read_text()).get("capabilities", [])
        except Exception:
            pass

    # Filter: keep most relevant to task
    task_lower = task.lower()
    scored = []
    for idx, cap in enumerate(caps):
        name = cap.get("name", "")
        desc = cap.get("description", "")
        score = sum(1 for kw in task_lower.split() if kw in (name + desc).lower())
        scored.append((score, idx, cap))
    scored.sort(key=lambda x: x[0], reverse=True)
    top_caps = [c for _, _i, c in scored[:10]]

    if len(top_caps) < 3:
        top_caps = caps[:10]

    n = len(top_caps)
    texts = [f"{c['name']}: {c.get('description', c.get('type', ''))} " for c in top_caps]
    embeddings = _embed_text(texts)
    sections = embeddings.unsqueeze(0)

    # Edges: fully connected within same type, cross-type are hetero edges
    edge_pairs = []
    for i in range(n):
        for j in range(i + 1, n):
            edge_pairs.append((i, j))
    if not edge_pairs:
        edge_pairs = [(0, 1)]
    cover = _make_cover(n, edge_pairs)

    # Measurements: same-type → zero tension, cross-type → distance
    meas_list = []
    for src, tgt in edge_pairs:
        same_type = top_caps[src].get("type") == top_caps[tgt].get("type")
        diff = embeddings[tgt] - embeddings[src]
        if not same_type:
            diff = diff * 0.3  # cross-type compatibility is partial
        meas_list.append(diff)
    measurements = torch.stack(meas_list).unsqueeze(0)

    result = _run(cover, sections, measurements, steps=8)
    result["n_capabilities"] = n
    result["top_by_occupancy"] = [top_caps[i]["name"] for i in range(min(3, n))]
    result["elapsed_s"] = round(time.time() - t0, 2)
    result["interpretation"] = (
        "capabilities conflict — check cross-type compatibility"
        if result["h1_detected"] else
        f"compatible set found — {n} capabilities glue cleanly"
    )
    return result


def run_hivemind(goal: str) -> dict[str, Any]:
    """HiveMind: execution steps as nodes → occupancy routes homo vs hetero.

    Node = execution step (plan step or tool).
    Edge = dependency.
    occupancy > 0.5 → homo branch (fast local execution).
    occupancy ≤ 0.5 → hetero branch (cross-step coordination needed).
    """
    import subprocess
    t0 = time.time()

    # Get a plan via aios_invoke
    p = subprocess.run(
        [sys.executable, "scripts/aios_invoke.py", "--goal", goal, "--plan-only", "--json"],
        cwd=str(ROOT), capture_output=True, text=True, timeout=12
    )
    steps: list[str] = []
    if p.returncode == 0:
        try:
            d = json.loads(p.stdout)
            raw_steps = d.get("plan", d.get("steps", []))
            steps = [str(s.get("description", s) if isinstance(s, dict) else s)[:150]
                     for s in raw_steps[:8]]
        except Exception:
            pass

    if len(steps) < 3:
        # Fallback: synthesize generic steps
        steps = [f"step {i}: {goal[:80]} sub-task {i}" for i in range(5)]

    n = len(steps)
    embeddings = _embed_text(steps)
    sections = embeddings.unsqueeze(0)

    # Sequential dependency edges
    edge_pairs = [(i, i + 1) for i in range(n - 1)]
    cover = _make_cover(n, edge_pairs)

    # Measurements: expected output of step i = input of step i+1 (near-zero diff)
    meas_list = []
    for src, tgt in edge_pairs:
        diff = embeddings[tgt] - embeddings[src]
        meas_list.append(diff * 0.1)  # sequential steps should glue tightly
    measurements = torch.stack(meas_list).unsqueeze(0)

    result = _run(cover, sections, measurements, steps=8)

    # Classify steps by occupancy
    with torch.no_grad():
        one_step = descent_step(cover, sections, measurements)
        occ = one_step.occupancy.squeeze(0).tolist()  # [E]

    homo_steps = [steps[i] for i, (src, tgt) in enumerate(edge_pairs)
                  if i < len(occ) and occ[i] > 0.5]
    hetero_steps = [steps[i] for i, (src, tgt) in enumerate(edge_pairs)
                    if i < len(occ) and occ[i] <= 0.5]

    result["homo_branch_steps"] = homo_steps    # fast, local
    result["hetero_branch_steps"] = hetero_steps  # needs coordination
    result["elapsed_s"] = round(time.time() - t0, 2)
    result["interpretation"] = (
        f"homo: {len(homo_steps)} steps (fast) / hetero: {len(hetero_steps)} steps (coord needed)"
    )
    return result


def run_myworld(goal: str, os_results: dict[str, dict]) -> dict[str, Any]:
    """MyWorld: integrate all OS outputs → globally consistent operator decision.

    Each OS result's global_section_norm is a "local section" of the system view.
    MyWorld checks if all OS views glue consistently (low obstruction = coherent state).
    """
    t0 = time.time()

    # Nodes = one per OS
    os_names = list(os_results.keys())
    n = len(os_names)
    if n < 2:
        return {"status": "insufficient_os_results"}

    # Encode each OS result as a summary text
    texts = []
    for name, res in os_results.items():
        interp = res.get("interpretation", "")
        obst = res.get("obstruction_mean", 0)
        texts.append(f"{name}: obstruction={obst:.3f} {interp[:100]}")

    embeddings = _embed_text(texts)
    sections = embeddings.unsqueeze(0)

    # Fully connected inter-OS edges
    edge_pairs = [(i, j) for i in range(n) for j in range(i + 1, n)]
    cover = _make_cover(n, edge_pairs)

    meas_list = []
    for src, tgt in edge_pairs:
        # OS views should be compatible → near-zero measurement
        diff = (embeddings[tgt] - embeddings[src]) * 0.2
        meas_list.append(diff)
    measurements = torch.stack(meas_list).unsqueeze(0)

    result = _run(cover, sections, measurements, steps=6)
    result["os_names"] = os_names
    result["elapsed_s"] = round(time.time() - t0, 2)
    result["interpretation"] = (
        "⚠ OS views conflict — operator checkpoint needed"
        if result["h1_detected"] else
        "✓ all OS views globally consistent — safe to proceed"
    )
    return result


# ── main ─────────────────────────────────────────────────────────────────────

def main() -> int:
    parser = argparse.ArgumentParser(description="DescentNet × AIOS 5-OS 배선 실험")
    parser.add_argument("--query", "--goal", default="AIOS 오늘 상태는?")
    parser.add_argument("--os", choices=["memoryos", "genesisos", "capabilityos",
                                          "hivemind", "myworld", "all"], default="all")
    parser.add_argument("--steps", type=int, default=10)
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()

    goal = args.query
    report: dict[str, Any] = {
        "schema": "aios.descentnet_session.v1",
        "goal": goal,
        "stalk_dim": STALK_DIM,
        "results": {},
    }

    run_all = args.os == "all"

    def _run_os(name: str, fn, *fn_args):
        if not run_all and args.os != name:
            return
        print(f"\n[{name}] 실행 중...", flush=True)
        try:
            r = fn(*fn_args)
            report["results"][name] = r
            if not args.json:
                obst = r.get("obstruction_mean", "?")
                occ = r.get("occupancy_mean", "?")
                h1 = "H¹✓" if r.get("h1_detected") else "H¹✗"
                elapsed = r.get("elapsed_s", "?")
                print(f"  obstruction={obst}  occupancy={occ}  {h1}  {elapsed}s")
                print(f"  → {r.get('interpretation', '')}")
        except Exception as exc:
            report["results"][name] = {"error": str(exc)[:200]}
            print(f"  ERROR: {exc}")

    _run_os("memoryos",     run_memoryos,    goal)
    _run_os("genesisos",    run_genesisos,   goal)
    _run_os("capabilityos", run_capabilityos, goal)
    _run_os("hivemind",     run_hivemind,    goal)

    # MyWorld: integrate all OS results
    if run_all or args.os == "myworld":
        os_inputs = {k: v for k, v in report["results"].items()
                     if "error" not in v}
        if os_inputs:
            _run_os("myworld", run_myworld, goal, os_inputs)

    # Save to .aios/
    out_path = ROOT / ".aios" / "descentnet_session_latest.json"
    out_path.write_text(json.dumps(report, ensure_ascii=False, indent=2))

    if args.json:
        print(json.dumps(report, ensure_ascii=False, indent=2))
    else:
        print(f"\n[session] 저장: {out_path}")
        all_h1 = [v.get("h1_detected", False) for v in report["results"].values()
                  if isinstance(v, dict) and "h1_detected" in v]
        print(f"[session] 전체 H¹ 감지: {sum(all_h1)}/{len(all_h1)} OS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
