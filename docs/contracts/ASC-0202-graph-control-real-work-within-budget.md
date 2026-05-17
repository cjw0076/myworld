---
contract_id: ASC-0202
slug: graph-control-real-work-within-budget
status: accepted
goal: Make MemoryOS graph-control actually govern the live store — it currently budget-exhausts at the score step with total_memories=0 and does zero real work on the 198K-node graph.
created: 2026-05-18 KST
accepted: 2026-05-18 KST
acceptance_authority: claude@myworld operator — ASC-0194 verification follow-on; the named exit of ASC-0194 is not met until graph-control does real work.
origin: Operator verification of ASC-0194. The Graph Control Model is implemented (7 steps, wired into the dream organ, 4 unit tests pass on seeded fixtures) but on the real MemoryOS store every run reports `status: budget_exhausted`, `total_memories: 0`, every step `skipped` — it governs nothing. ASC-0196 ("incremental budget") was closed but the symptom persists empirically.
---

# ASC-0202 Graph-Control: Real Work Within Budget

DNA references: Invariant 4 (named exit — a stage that always budget-exhausts
at step 1 is stuck, not bounded), Invariant 8 (verify before claiming done).

## Scope

repos: `memoryOS` — codex@memoryOS owns the diagnosis and mechanism.

## The problem (operator-verified)

`python -m memoryos --root . memory graph-control run --json` on the live
store (198,790 nodes / 44 MemoryObjects):

- `status: budget_exhausted` after the 45s budget;
- `score` step `status: partial`, `total_memories: 0`;
- every other step (`resolve_merge`, `invalidate`, `consolidate`,
  `community_layer`, `decay_prune`) `status: skipped`,
  `reason: budget_exhausted`;
- `queryable_surface_count: 0`, `reclaimed_count: 0` — zero governance.

The model works on `test_graph_control.py`'s seeded fixtures but does no
real work on the actual store. ASC-0196 added an incremental path but the
run still exhausts the budget before processing anything.

## Required outcome

1. **Diagnose** why the score step consumes the whole budget while
   `total_memories` is 0 — is it an unbounded scan over the 198K-node graph,
   an expensive count, or a query that never reaches the MemoryObjects?
2. **Make graph-control complete real work within the dream budget** — at
   least one full cycle that processes a bounded, non-zero chunk of memories
   through all 7 steps and reports a non-vacuous `bound_ratio` and a
   `reclaimed_count` ≥ 0 from actual merges/decays, not from an empty graph.
3. The incremental cursor must make *progress* — a second run continues from
   where the first stopped, so repeated dream cycles converge.

## Named Exit

Closed when: a graph-control run on the live store reports
`total_memories > 0`, completes (or makes bounded progress on) all 7 steps
without budget-exhausting at step 1, and a follow-up run demonstrably
advances the cursor.

## Stop Conditions

- If the live store genuinely has 0 governable memories, say so explicitly
  with evidence — do not report `budget_exhausted` to mask an empty query.

## Work Packets

### codex@memoryOS

Diagnose the score-step budget exhaustion; make graph-control process a
bounded non-zero chunk within budget; prove cursor progress across two runs.
Report the two run records as evidence.
