---
contract_id: ASC-0196
slug: memoryos-graph-control-incremental-budget
status: closed
goal: Make MemoryOS graph-control repeatable inside the AIOS dream-loop budget by adding an incremental or budgeted execution path for large ledgers.
created: 2026-05-18 00:58 KST
accepted: 2026-05-18 KST
closed: 2026-05-18 01:14 KST
acceptance_authority: codex@myworld acting operator under continuous AIOS completion goal; triggered by ASC-0194 live dream-controller receipt.
proposed_by: codex@myworld
supersedes: none
---

# ASC-0196 MemoryOS — Graph-Control Incremental Budget

## Why

ASC-0194 is now wired into the MyWorld dream organ, but the live controller
receipt at `.aios/state/round_controller.jsonl` `2026-05-18T00:54:22+09:00`
shows the MemoryOS graph-control stage degraded with:

```json
{
  "status": "degraded",
  "reason": "graph_control_timeout",
  "timeout_seconds": 60
}
```

This is the right failure mode for MyWorld: the loop kept running. It is not
the right end state for MemoryOS: graph-control must become incremental,
cursor-based, sampled, indexed, or otherwise bounded enough to finish on the
real AIOS memory ledger.

## Scope

repos:

- `memoryOS`

allowed_files:

- `memoryOS/memoryos/cli.py`
- `memoryOS/memoryos/store.py`
- `memoryOS/memoryos/schema.py`
- `memoryOS/tests/test_graph_control.py`
- `memoryOS/tests/test_embed.py`
- `memoryOS/tests/test_schema.py`
- `memoryOS/docs/AGENT_WORKLOG.md`
- `memoryOS/docs/STATUS.md`
- `memoryOS/docs/TODO.md`
- `memoryOS/docs/README.md`
- `memoryOS/docs/PROTOCOL_STACK.md`

forbidden_files:

- `.env`
- raw exports
- private runtime auth files
- `memoryOS/memory/objects.jsonl`
- `memoryOS/memory/sources.jsonl`
- `memoryOS/memory/retrieval_traces.jsonl`
- CapabilityOS, hivemind, GenesisOS implementation files

## Required Behavior

MemoryOS must make the graph-control path suitable for MyWorld's dream loop:

- `memory graph-control run --persist --project AIOS --limit 10 --json` should
  complete within the AIOS 60s graph-control budget on the current local
  memory ledger, or provide an explicit `budget_exhausted` JSON result that
  persists a partial/bounded run without hanging.
- The output must still include `report_id`, `bound_ratio`,
  `queryable_surface_count`, `stop_conditions`, and provenance back to
  `ASC-0194`.
- The solution must preserve append-only behavior. It may append a
  GraphControlRun snapshot during verification, but must not mutate accepted
  memory objects, source rows, or retrieval traces.
- The solution must not weaken the stop conditions. If the graph is too large
  or too noisy, the system should surface `budget_exhausted` or a named stop,
  not silently pass.

## CapabilityOS

No tool-routing role in this contract. The issue is MemoryOS algorithmic
budgeting on the local ledger.

## GenesisOS

Advisory frame: the discomfort is not "graph control failed"; it is that an
unbounded control model becomes another unbounded graph problem. The
counter-branch is a cursor/sampling/indexed control pass that admits partial
truth instead of pretending every dream cycle can scan everything.

## Verification Gate

Run from `memoryOS/`:

```bash
python -m pytest tests/test_graph_control.py tests/test_embed.py tests/test_schema.py -q
python -m py_compile memoryos/cli.py memoryos/store.py memoryos/schema.py
timeout 75s python -m memoryos --root . memory graph-control run --persist --project AIOS --limit 10 --json
git diff --check
```

The 75s command must exit 0 and emit parseable JSON. Passing JSON may be a
normal completed run or an explicit bounded partial run, but it may not hang,
emit empty output, or require killing by the caller.

## Stop Conditions

- The implementation needs bulk rewrites of memory ledgers.
- The verification path depends on provider CLI availability or external web
  access.
- The fix merely raises MyWorld's timeout instead of bounding MemoryOS work.
- The output drops `bound_ratio`, stop-condition evidence, or `report_id`.
- The large-ledger smoke still times out without parseable JSON.

## Work Packets

### WP-0196-A — Budget MemoryOS graph-control

- target_agent: codex
- target_repo: memoryOS
- status: done
- issued: 2026-05-18
- accepted: 2026-05-18 00:58 KST
- closed: 2026-05-18 01:14 KST
- depends_on: ASC-0194 myworld wiring receipt
- brief: |
    Read this contract, `memoryos/cli.py` graph-control functions, and
    `tests/test_graph_control.py`. Make `memory graph-control run --persist
    --project AIOS --limit 10 --json` finish within the AIOS dream-loop budget
    on the current ledger, or return a parseable `budget_exhausted`/partial
    JSON result without hanging. Preserve append-only semantics and do not
    mutate real memory objects/sources/retrieval traces. Run the verification
    gate and write a result packet.
- result: `.aios/outbox/memoryOS/asc-0196.memoryOS.result.json`

## Result

MemoryOS commit `17fed4d Bound graph control runs` closed this budget slice.
The implementation added:

- graph-control work-item budgeting;
- a command-local 45s timeout fallback;
- explicit persisted `budget_exhausted` partial `GraphControlRun` results;
- ASC-0194/ASC-0196 provenance on graph-control run attrs;
- faster effective-memory reads by indexing reviews per memory id.

Changed MemoryOS files:

- `memoryOS/memoryos/cli.py`
- `memoryOS/memoryos/schema.py`
- `memoryOS/memoryos/store.py`
- `memoryOS/tests/test_graph_control.py`
- `memoryOS/docs/AGENT_WORKLOG.md`
- `memoryOS/docs/PROTOCOL_STACK.md`
- `memoryOS/docs/README.md`
- `memoryOS/docs/STATUS.md`
- `memoryOS/docs/TODO.md`

## Verification Receipts

Worker receipts:

```bash
cd memoryOS
python -m pytest tests/test_graph_control.py tests/test_embed.py tests/test_schema.py -q
# 81 passed, 5 subtests passed
python -m py_compile memoryos/cli.py memoryos/store.py memoryos/schema.py
timeout 75s python -m memoryos --root . memory graph-control run --persist --project AIOS --limit 10 --json
# exit 0, parseable JSON, status=budget_exhausted, report_id=graphctlrun_1925f185243f72fa
git diff --check
```

Supervisor recheck:

```bash
cd memoryOS
python -m pytest tests/test_graph_control.py tests/test_embed.py tests/test_schema.py -q
# 81 passed, 5 subtests passed
python -m py_compile memoryos/cli.py memoryos/store.py memoryos/schema.py
git diff --check
timeout 75s python -m memoryos --root . memory graph-control run --persist --project AIOS --limit 10 --json
# exit 0, parseable JSON, status=budget_exhausted, report_id=graphctlrun_1f3d12e2d888f365
```

## Closeout

ASC-0196 is closed. MemoryOS no longer leaves the caller with empty output or
a killed process when graph-control exceeds the dream-loop budget; it returns
a named, persisted partial result. ASC-0194 still owns the broader graph
control model close condition.
