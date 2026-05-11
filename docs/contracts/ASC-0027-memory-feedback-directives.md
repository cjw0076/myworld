---
contract_id: ASC-0027
slug: memory-feedback-directives
status: closed
goal: Make accepted MemoryOS context produce explicit next-run feedback directives and have Hive render them into context_pack.md.
created: 2026-05-12 02:36 KST
accepted: 2026-05-12 02:36 KST by codex acting operator
closed: 2026-05-12 02:40 KST
supersedes: none
---

# ASC-0027 Memory Feedback Directives

## Goal

MemoryOS already selects accepted memories for Hive and Hive already records
`accepted_memories_used`. The feedback is still mostly passive: the next run
gets grouped memory rows, but not a concise "how should this shape the next
run" directive surface.

This contract adds a small, reviewable feedback layer:

- MemoryOS `context build` emits `feedback_directives[]` derived from selected
  accepted memory objects.
- Hive's MemoryOS bridge renders those directives into `context_pack.md` and
  records a directive count in the run-local memory context artifact.

## Scope

repos:

- `memoryOS`
- `hivemind`
- `myworld`

allowed_files:

- `memoryOS/memoryos/cli.py`
- `memoryOS/tests/test_sprint4.py`
- `memoryOS/docs/HIVE_INTEGRATION.md`
- `memoryOS/docs/JSON_SCHEMAS.md`
- `memoryOS/docs/AGENT_WORKLOG.md`
- `hivemind/hivemind/memory_bridge.py`
- `hivemind/tests/test_production_hardening.py`
- `hivemind/docs/AGENT_WORKLOG.md`
- `hivemind/.ai-runs/shared/comms_log.md`
- `docs/contracts/ASC-0027-memory-feedback-directives.md`
- `docs/contracts/README.md`
- `docs/AIOS_AGENT_LEDGER.md`
- `docs/goals/AIOS-GOAL-0001-make-something-great.md`
- `docs/goals/AIOS-GOAL-0001-evolution.md`

forbidden_files:

- `CapabilityOS/**`
- `memoryOS/data/**`
- `hivemind/data/**`
- `.aios/**`
- `.runs/**`
- `.ai-runs/**` except `hivemind/.ai-runs/shared/comms_log.md`
- `raw_exports/**`
- `exports/**`
- `logs/**`
- `weights/**`
- `**/*secret*`
- `**/*credential*`
- `.env`
- `.env.*`

## Design Decisions

- Feedback directives are derived output, not new accepted memory. They do not
  mutate MemoryOS ledgers.
- Directives use already-selected accepted memory content and IDs. They must
  not add raw refs, private paths, transcript bodies, or logs.
- Hive renders directives as a dedicated context section; it does not reinterpret
  MemoryOS review status or write MemoryOS stores.
- The directive surface is small and deterministic so it can be used by future
  provider prompts without extra manual relay.

## Per-OS Responsibility

- **memoryos.must_produce**:
  - `feedback_directives[]` in `context build` JSON;
  - tests proving selected accepted memories generate directives;
  - docs/schema notes.
- **hive_mind.must_produce**:
  - render directives in `context_pack.md`;
  - persist directive count in the memory context artifact;
  - tests proving the bridge preserves directives.
- **capabilityos.must_produce**: no source change.
- **myworld.must_produce**: contract, dispatch, closeout, goal update, and
  ledger entry.
- **operator.must_produce**: release only after both child repos pass their
  targeted tests and monitor is clear.

## Verification Gate

```bash
cd /home/user/workspaces/jaewon/myworld/memoryOS
python -m pytest tests/test_sprint4.py::ContextBuildTest::test_context_build_emits_feedback_directives -v

cd /home/user/workspaces/jaewon/myworld/hivemind
python -m pytest tests/test_production_hardening.py::ProductionHardeningTest::test_memoryos_context_bridge_records_trace_and_selected_ids -v
```

Expected evidence:

- MemoryOS context JSON includes `feedback_directives[]` with selected memory
  ids, types, and concise directive strings.
- Hive `context_pack.md` includes a `## Feedback Directives` section.
- Hive run-local memory context report includes `feedback_directives_count`.
- Existing accepted memory ID extraction still works.

## Stop Conditions

- `memory_mutation`: context build writes new memory/review/source records
  beyond the existing RetrievalTrace.
- `raw_ref_leak`: directives include raw refs, local paths, transcripts, or log
  bodies.
- `hive_store_write`: Hive writes directly to MemoryOS ledgers.
- `capability_scope_creep`: CapabilityOS files are modified.
- `test_gate_failed`: either child repo targeted test fails.
- `monitor_blocked`: myworld monitor is blocked after collect/release.

## Work Packets

### WP-0027-A — Codex@memoryOS adds feedback directives

- target_agent: codex
- target_repo: memoryOS
- status: done
- issued: 2026-05-12
- accepted: 2026-05-12 02:36 KST
- closed: 2026-05-12 02:39 KST
- depends_on: ASC-0001, ASC-0023
- brief: |
    Add deterministic `feedback_directives[]` to context build output from
    selected accepted memory objects. Keep it derived and privacy-safe.
- result: MemoryOS commit `06caf78`; dispatch result passed.

### WP-0027-B — Codex@hivemind renders feedback directives

- target_agent: codex
- target_repo: hivemind
- status: done
- issued: 2026-05-12
- accepted: 2026-05-12 02:36 KST
- closed: 2026-05-12 02:39 KST
- depends_on: WP-0027-A
- brief: |
    Render MemoryOS feedback directives into Hive `context_pack.md` and record a
    directive count in the run-local memory context report.
- result: Hive commit `0d8557e`; dispatch result passed.

## Receipts

Closed 2026-05-12 02:40 KST by `codex@myworld` acting operator.

- Dispatch:
  - `.aios/inbox/memoryOS/asc-0027.memoryOS.json`
  - `.aios/inbox/hivemind/asc-0027.hivemind.json`
  - `.aios/outbox/memoryOS/asc-0027.memoryOS.result.json`
  - `.aios/outbox/hivemind/asc-0027.hivemind.result.json`
- Implementation:
  - MemoryOS commit `06caf78` (`Add MemoryOS feedback directives`)
  - Hive commit `0d8557e` (`Render MemoryOS feedback directives`)
- Verification:
  - MemoryOS `python -m pytest
    tests/test_sprint4.py::ContextBuildTest::test_context_build_emits_feedback_directives
    -v` passed.
  - Hive `python -m pytest
    tests/test_production_hardening.py::ProductionHardeningTest::test_memoryos_context_bridge_records_trace_and_selected_ids
    -v` passed.
  - Additional focused MemoryOS context shape tests passed 3/3 before child
    commit.
  - `python scripts/aios_dispatch.py watch --repo memoryOS --dispatch-id
    asc-0027 --once` and `--repo hivemind` both wrote passed result packets.
  - `python scripts/aios_dispatch.py collect --repo memoryOS` and
    `--repo hivemind` collected both result packets.
  - `python scripts/aios_dispatch.py release --dispatch-id asc-0027 --reason
    asc_0027_memory_feedback_directives_verified` succeeded.
  - `python scripts/aios_monitor.py assess --json` returned `health=clear`.
- Stop conditions triggered: none.
