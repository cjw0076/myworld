---
contract_id: ASC-0194
slug: memoryos-graph-control-model
status: accepted
goal: Build the Graph Control Model — a dream-cycle organ that actively governs memoryOS's unbounded knowledge graph (score → merge → invalidate → consolidate → community-layer → decay → bound-check) so the graph stays coherent and bounded as it grows.
created: 2026-05-17 23:30 KST
revised: 2026-05-18 00:10 KST
accepted: 2026-05-18 KST
acceptance_authority: founder GO — "memoryOS로 dispatch, control model 지금 진행, GFM은 downstream".
proposed_by: claude@myworld
escalation: VISION-LEVEL — founder GO requested. This sets memory's core construction method and is the spine of the "memory design decides the next paradigm" thesis.
origin: Founder — "GoEN was unfinished research; for constructing memory nothing beats a graph network; the LLM successor is LGM and it comes down to how well memory is designed." Founder reframe — "mitigation alone won't solve it; we need a model to control the ever-growing graph." External study: docs/research/LGM_AND_MEMORY_GRAPH_CONTROL.md.
---

# ASC-0194 MemoryOS — Graph Control Model

DNA references: Invariant 2 (draft-first — the control model proposes graph
changes; promotion needs review), Invariant 3 (append-only — invalidate, never
delete), Invariant 4 (named exit — SSGM failure modes as stop conditions),
Invariant 8.

## Strategic correction (from the external study)

The founder's instinct is right: graphs are the future of memory and memory
design is the decisive factor. The study sharpens one point. "LGM" as a named
paradigm is not standardized — the real 2024-2026 term is **Graph Foundation
Model (GFM)**, and the load-bearing finding is:

> **A GFM *consumes* a well-governed graph — it does not fix an ungoverned
> one. Govern the graph first; do not pivot to training a graph model.**

So this contract is NOT "train an LGM." It is the **control loop** that makes
memoryOS's graph worth consuming. A GFM is the downstream long-horizon step;
it is worthless on a 198K-node hoard with noisy hubs.

## Why mitigations were not enough

Draft-first / review / dream-placement are passive guards — they keep the
graph from breaking, they do not bound its growth. memoryOS does none of the
three things every production memory system that scales does: **invalidate**
(not blind-append), **abstract** (roll specific nodes into concepts), **decay**
(let unaccessed nodes fade).

## The Graph Control Model — a dream-cycle stage, 7 steps

1. **score** — salience = importance × recency × access-frequency ×
   centrality × provenance, per node/edge.
2. **resolve / merge** — entity resolution: embed, cosine+lexical candidate
   search, local-LLM adjudicates a merge; edge-dedup constrained to the same
   entity pair (bounds cost).
3. **invalidate** — bi-temporal `t_valid` / `t_invalid` (Graphiti model):
   superseded facts are invalidated, never deleted — the current view stays
   clean and the append-only-audit invariant holds.
4. **consolidate** — episodic → semantic: cluster low-level episodic nodes,
   abstract each cluster into one semantic concept node, cold-store the
   episodes.
5. **community-layer** — hierarchical abstraction (Hierarchical Leiden + a
   local-LLM community summary). The single strongest growth bound: the
   *queryable surface* becomes O(communities), not O(nodes) — the graph may
   grow but queries stay bounded.
6. **decay / prune** — access-based decay (retrieval resets the clock;
   Weibull/Ebbinghaus): usage protects, neglect prunes to the cold tier.
7. **validate + bound-check** — emit the **bound ratio** =
   (consolidation + merge reclamation) ÷ (raw ingest); a stop condition fires
   when node growth outpaces reclamation on the queryable surface.

Folded in from the earlier draft: directional-message-passing **structural
retrieval** becomes a retrieval improvement that the community layer enables;
**STDP** edge dynamics become the access-based component of step 1/6.

## Scope (proposed)

repos: `memoryOS` (the control model + schema), `myworld` (round-controller
wiring of the dream-cycle stage).

memoryOS schema additions: per node/edge `salience`, `t_valid`/`t_invalid`,
`tier` (episodic/semantic/community), `consolidated` flag, cold-storage tier.

## Named Exit (proposed)

Closed when: the 7-step control model runs as a dream-cycle stage; the
queryable surface is O(communities); the bound ratio is emitted and ≥1 on the
queryable surface; invalidate/decay are append-only (nothing deleted); a
demonstrated growth-outpaces-reclamation case fires the stop condition.

## Stop Conditions (SSGM failure modes — named)

index bloat · semantic drift · temporal obsolescence · duplicate
proliferation · memory poisoning — any one detected halts auto-consolidation
and surfaces to the operator.

## Founder resolution

GO (2026-05-18). Dispatch to memoryOS; build the control model now; a Graph
Foundation Model is the downstream long-horizon step, out of scope for this
contract.

## Implementation Receipts

### MemoryOS slice — focused verified

- memoryOS commit: `e5ecff6 Add graph control model alpha`
- surfaced commands:
  - `memoryos --root . memory graph-control plan --json`
  - `memoryos --root . memory graph-control run --persist --json`
  - `memoryos --root . memory graph-control list --json`
  - `memoryos --root . memory graph-control show <run_id> --json`
- focused verification passed:
  `python -m pytest tests/test_graph_control.py tests/test_schema.py tests/test_doctor.py tests/test_mcp.py -q`
  and `python -m py_compile memoryos/cli.py memoryos/schema.py memoryos/store.py`.
- full-gate blocker was separated into ASC-0195 and closed by memoryOS commit
  `146b946 Harden embed fallback tests`.

### MyWorld dream-cycle wiring — bounded alpha

- myworld commit candidate: `scripts/aios_dream.py`,
  `scripts/aios_round_controller.py`, `tests/test_aios_dream.py`.
- `aios_dream.py` now calls MemoryOS-owned
  `memory graph-control run --persist --project AIOS --limit 10 --json` as a
  bounded dream-stage hook.
- The stage records `report_id`, `bound_ratio`, queryable-surface counts, stop
  conditions, and halt status when MemoryOS completes.
- The stage records `status=degraded` with `reason=graph_control_timeout` when
  the large memory graph does not finish inside the dream budget. This prevents
  the persistent round controller from hanging or falsely claiming closeout.
- `aios_round_controller.py` passes explicit dream budgets:
  `--consolidate-budget 120 --graph-control-timeout 60 --helper-timeout 150`
  inside the existing 420s controller timeout.
- focused verification passed:
  `python -m unittest tests.test_aios_dream -v`,
  `python -m py_compile scripts/aios_dream.py scripts/aios_round_controller.py`,
  and `git diff --check`.

### Remaining close condition

ASC-0194 remains accepted, not closed. The control model is wired as a
bounded dream-stage alpha, but a large-ledger live run still needs either
MemoryOS performance hardening or a smaller incremental graph-control cursor
before the contract can claim repeatable completion of the dream-cycle stage.
