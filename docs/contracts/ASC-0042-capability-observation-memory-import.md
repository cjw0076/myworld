---
contract_id: ASC-0042
slug: capability-observation-memory-import
status: closed
goal: Convert CapabilityOS observations into MemoryOS draft review candidates without auto-accepting capability claims.
created: 2026-05-12 18:57 KST
accepted: 2026-05-12 18:57 KST by codex acting operator
closed: 2026-05-12 19:08 KST
---

# ASC-0042 Capability Observation Memory Import

## Why Now

ASC-0026 made CapabilityOS recommendations observation-aware, and ASC-0041
proved that evidence receipts can become MemoryOS review candidates without
auto-acceptance. The next step is to make capability performance evidence
reviewable in MemoryOS as draft memory, while preserving CapabilityOS as a
recommendation-only router.

## AIOS Inputs Used

- MemoryOS context build:
  `trace_id=rtrace_0b0ca4ff4d1e0653`, selected accepted memory
  `mem_90b5cfe6570e6ee2`.
- CapabilityOS route:
  `cap_capabilityos_recommendation`, `cap_memoryos_import_run`,
  `cap_hivemind_execution_harness`, `cap_memoryos_context_build`, and
  `cap_web_research_route`.
- Hive Mind dry-run:
  `run_20260512_185731_652abf`, `route_source=heuristic_fast`, prepared
  planner/executor/reviewer artifacts.

## Scope

repos:

- `myworld`

allowed_files:

- `scripts/aios_capability_observation_memory_review.py`
- `tests/test_aios_capability_observation_memory_review.py`
- `docs/evidence/ASC-0042-capability-observations.json`
- `docs/evidence/ASC-0042-capability-memory-candidates.json`
- `docs/evidence/ASC-0042-capability-review-run/run_state.json`
- `docs/evidence/ASC-0042-capability-review-run/memory_drafts.json`
- `docs/evidence/ASC-0042-capability-review-run/transcript.md`
- `docs/AIOS_WORK_DISPATCH.md`
- `docs/contracts/ASC-0042-capability-observation-memory-import.md`
- `docs/contracts/README.md`
- `docs/goals/AIOS-GOAL-0001-make-something-great.md`
- `docs/goals/AIOS-GOAL-0001-evolution.md`
- `docs/AIOS_AGENT_LEDGER.md`

forbidden_files:

- `hivemind/**`
- `memoryOS/**`
- `CapabilityOS/**`
- `uri/**`
- `.aios/logs/**`
- `.aios/state/**`
- `.aios/inbox/**`
- `.aios/outbox/**`
- `.env`
- raw export paths

## Responsibilities

### myworld.must_produce

- A converter that calls CapabilityOS `observe-results` locally, writes an
  observation snapshot, and builds capability-level MemoryOS review candidates.
- Selection rules:
  - include only known `cap_*` observations with `outcome=passed`;
  - require contract ids and evidence refs;
  - roll up observations by capability id instead of importing every event;
  - keep gaps as `operator_review_only`.
- A candidate JSON envelope with `auto_accept=false`,
  `memoryos_target_status=draft`, `review_required=true`, and provenance for
  each rollup.
- A Hive-run-compatible bundle so MemoryOS `import-run --dry-run --json` can
  verify the draft path.

### memoryos.must_produce

- No source change. Existing `import-run --dry-run --json` is the verification
  authority for the generated bundle.

### capabilityos.must_produce

- No source change. Existing `observe-results` is the observation authority.

### hive_mind.must_produce

- No source change. Hive dry-run provides planning evidence.

## Verification Gate

```bash
python -m py_compile scripts/aios_capability_observation_memory_review.py
python scripts/aios_capability_observation_memory_review.py --root . validate docs/evidence/ASC-0042-capability-memory-candidates.json --json
cd memoryOS && python -m memoryos.cli --root /home/user/workspaces/jaewon/myworld import-run /home/user/workspaces/jaewon/myworld/docs/evidence/ASC-0042-capability-review-run --dry-run --json
python -m unittest tests/test_aios_capability_observation_memory_review.py
python -m unittest discover -s tests -p 'test_aios_*.py'
python scripts/aios_monitor.py assess --json
```

Pass criteria:

- Observation snapshot uses `capabilityos.observe_results.v1`.
- Candidates are capability rollups, not per-event memory spam.
- Every candidate remains `status=draft`, `evidence_state=unreviewed`,
  `review_required=true`, and `auto_accept=false`.
- MemoryOS dry-run plans three draft memory objects and does not write accepted
  memory.
- Full tests pass and monitor remains clear.

## Stop Conditions

- `observation_payload_invalid`
- `unknown_capability_selected`
- `non_passed_observation_selected`
- `candidate_without_contract_or_evidence`
- `auto_accept_requested`
- `memoryos_import_dry_run_failed`
- `child_repo_source_edit`
- `verification_gate_failed`

## Receipts

- implementation:
  - `scripts/aios_capability_observation_memory_review.py` builds and
    validates `aios.capability_observation_memory_review.v1`.
  - `tests/test_aios_capability_observation_memory_review.py` covers rollup
    selection, draft-only candidates, and MemoryOS dry-run compatibility.
  - `docs/evidence/ASC-0042-capability-observations.json` records the local
    CapabilityOS observation snapshot.
  - `docs/evidence/ASC-0042-capability-memory-candidates.json` contains three
    capability rollup candidates.
  - `docs/evidence/ASC-0042-capability-review-run/` contains the
    Hive-run-compatible import bundle.
- dispatch evidence:
  - `asc-0042` sent to `myworld`, watched, collected, and released with reason
    `asc_0042_capability_observation_memory_import_verified`.
  - result packet:
    `.aios/outbox/myworld/asc-0042.myworld.result.json`.
- verification:
  - focused ASC-0042 tests passed 4/4.
  - MemoryOS `import-run --dry-run --json` returned `status=dry_run_ok` and
    planned three memory objects.
  - full myworld suite passed 83/83.
  - final `python scripts/aios_monitor.py assess --write --json` returned
    `health=clear`.

## Work Packets

### WP-0042-A — Codex@myworld builds capability observation review candidates

- target_agent: codex
- target_repo: myworld
- status: done
- issued: 2026-05-12
- accepted: 2026-05-12
- closed: 2026-05-12
- depends_on: ASC-0026, ASC-0041
- brief: |
    Read CapabilityOS observation output from local result packets, roll passed
    observations up by capability, emit MemoryOS draft review candidates with
    provenance, and verify MemoryOS dry-run compatibility. Do not edit child
    repo source and do not auto-accept capability claims.
- result: `.aios/outbox/myworld/asc-0042.myworld.result.json`;
  `docs/evidence/ASC-0042-capability-memory-candidates.json`;
  `docs/evidence/ASC-0042-capability-review-run/`; full tests passed 83/83;
  monitor clear.
