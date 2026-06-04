---
contract_id: ASC-0202
slug: graph-control-real-work-within-budget
status: closed
closed: 2026-05-18 KST
closeout_authority: claude@myworld operator — deadlock recovery (no codex@memoryOS process running; the spine contract ASC-0194 was blocked behind this). Diagnosis + fix executed by operator-claude on behalf of codex@memoryOS, commit attributed to codex@memoryOS.
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

## Verification Gate

```bash
cd memoryOS
python -m py_compile memoryos/store.py memoryos/cli.py memoryos/schema.py
python -m unittest tests.test_graph_control tests.test_schema -v
```

## Stop Conditions

- If the live store genuinely has 0 governable memories, say so explicitly
  with evidence — do not report `budget_exhausted` to mask an empty query.

## Work Packets

### codex@memoryOS

Diagnose the score-step budget exhaustion; make graph-control process a
bounded non-zero chunk within budget; prove cursor progress across two runs.
Report the two run records as evidence.

## Implementation Receipts

### Diagnosis (operator-verified)

The score step was never "budget-exhausting" on graph work — it was
**full-scanning the embeddings file**. `store.load_embeddings()`
json-parses every row of `memory/embeddings.jsonl`; on the live store that
is **197,682 vectors and 34.7s**, leaving < 11s of the 45s budget. The
score step's three sub-builders each triggered that scan:

- `_graph_control_filtered_accepted_objects_and_vectors` → `load_embeddings()`
- `build_memory_coverage_plan` / `..._gaps` → `load_memory_coverage_records()`
  → `load_embeddings()` (measured `build_memory_coverage_plan` = 38.3s,
  `build_memory_coverage_queue` = 68.8s)
- `build_memory_cluster_plan`, `build_memory_merge_candidates` → `load_embeddings()`

Only **195 of 197,682** embedding rows are `target_type=memory_object`; the
rest are node embeddings the score step never consumes. `total_memories: 0`
was a *masked symptom* — the SIGALRM fired mid-scan before the 44 accepted
objects were ever counted, exactly the stop condition this contract named.

### Fix (memoryOS)

- `GraphStore.load_embeddings_for_targets(target_ids)` (new) — streams the
  embeddings file, applies a cheap `target_type` substring pre-filter, and
  json-parses only memory-object rows. Backed by a new `_read_jsonl_lines`
  raw-line iterator. 197,682-row scan → **3.6s** (≈10×).
- `_graph_control_filtered_accepted_objects_and_vectors`,
  `build_memory_cluster_plan`, `build_memory_merge_candidates`, and
  `GraphStore.load_memory_coverage_records` routed through the targeted
  loader. `build_memory_coverage_plan` 38.3s → 3.7s;
  `build_memory_coverage_queue` 68.8s → 8.0s.

### Verified outcome — Named Exit met

`memory graph-control run --persist` on the live store (198K nodes):

- **Run 1** — 17.0s, `status: stop_condition`,
  `score.total_memories: 44`, `resolve_merge.candidate_count: 316`,
  `consolidate.cluster_count: 14`, `community_layer.queryable_surface_count: 14`
  (O(communities), not O(nodes)), `bound_ratio: 7.86`,
  `reclaimed_count: 346`, `stop_conditions: [duplicate_proliferation]` — a
  correctly-named SSGM failure mode, not `budget_exhausted`.
- **Run 2** — 19.0s, `previous_total_memories: 0 → 44`,
  `raw_ingest_count: 44 → 0` — the incremental cursor demonstrably advanced.
- `tests/test_graph_control.py` + `tests/test_schema.py` (and embed/cluster
  suites): 81 passed.

memoryOS commit: see `docs/AGENT_WORKLOG.md`. ASC-0194's Named Exit is now
satisfied; ASC-0194 closed in the same operator pass.

### Dispatch closeout

- dispatch result: `.aios/outbox/memoryOS/asc-0202.memoryOS.result.json`
  passed 2026-05-20T16:25:41+09:00 after adding the repo-scoped
  dispatch-safe `Verification Gate`.
- watcher evidence: `python -m py_compile memoryos/store.py memoryos/cli.py
  memoryos/schema.py`; `python -m unittest tests.test_graph_control
  tests.test_schema -v` from `memoryOS/` (16 tests passed).
