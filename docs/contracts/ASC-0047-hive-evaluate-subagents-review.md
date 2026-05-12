---
contract_id: ASC-0047
slug: hive-evaluate-subagents-review
status: closed
goal: Add a first-class Hive evaluation command that runs verifier, product evaluator, and actual-user persona checks into durable run artifacts.
created: 2026-05-12 20:50 KST
accepted: 2026-05-12 20:50 KST by codex acting operator
closed: 2026-05-12 21:03 KST
supersedes: none
---

# ASC-0047 Hive Evaluate Subagents Review

## Why Now

ASC-0046 made the goal-evolution loop select the concrete unchecked Hive TODO
`myworld/hivemind/docs/TODO.md#hive-evaluate` instead of repeating a broad
radar-gap source. This contract closes that TODO by making Hive produce a
durable, inspectable review artifact from the three established review
personas: verifier, product evaluator, and actual-user persona.

This is current-surface work, not a new scheduler. It codifies an internal
evaluation command over existing run state, validation, and inspect reports so
future AIOS rounds can ask Hive to judge a run without relying on chat memory.

## AIOS Inputs

- MemoryOS context: `rtrace_4fe9704b72d1a1c1`
- Accepted memory used: `mem_90b5cfe6570e6ee2`
- CapabilityOS top route: `cap_hivemind_execution_harness`
- Supporting routes: `cap_memoryos_import_run`,
  `cap_memoryos_context_build`, `cap_capabilityos_recommendation`,
  `cap_web_research_route`
- Hive planning dry-run: `run_20260512_204728_7ad911`

## Scope

repos:

- `hivemind`
- `myworld`

allowed_files:

- `hivemind/hivemind/evaluation.py`
- `hivemind/hivemind/hive.py`
- `hivemind/hivemind/run_validation.py`
- `hivemind/tests/test_evaluation.py`
- `hivemind/docs/TODO.md`
- `hivemind/docs/AGENT_WORKLOG.md`
- `hivemind/.ai-runs/shared/comms_log.md`
- `docs/contracts/ASC-0047-hive-evaluate-subagents-review.md`
- `docs/contracts/README.md`
- `docs/goals/AIOS-GOAL-0001-evolution.md`
- `docs/AIOS_AGENT_LEDGER.md`

forbidden_files:

- `memoryOS/**`
- `CapabilityOS/**`
- `uri/**`
- `.aios/logs/**`
- `.aios/state/**`
- `.env`
- `.runs/**`
- raw export paths
- provider transcript bodies
- private memory store data

## Responsibilities

### hive_mind.must_produce

- A first-class `hive evaluate` command that reads an existing run and writes
  a durable `artifacts/evaluation_report.json`.
- A compatible `hive subagents review` alias for the same evaluation surface.
- The report schema must include `schema_version`,
  `kind=hive_evaluation_report`, `run_id`, `overall_status`,
  `paths_hidden`, `reviews[]`, and `artifact`.
- `reviews[]` must include records for `hive.verifier`,
  `hive.product_evaluator`, and `persona.actual_user`.
- The command must update run state artifact references and append an allowed
  run event without storing raw provider output or private source bodies.
- Focused tests for artifact creation, persona coverage, CLI JSON output,
  alias behavior, and path hiding.

### memoryos.must_produce

- No source change. MemoryOS provided context to select this slice and remains
  out of implementation scope.

### capabilityos.must_produce

- No source change. CapabilityOS provided route evidence only.

### myworld.must_produce

- Contract, dispatch/result collection, README index update, goal closeout, and
  ledger entry after verification passes.

### operator.must_produce

- Acting operator release only if the Hive command is durable, path-hidden by
  default, and the full Hive test suite passes.

## Verification Gate

```bash
cd hivemind && python -m pytest tests/test_evaluation.py -v
cd hivemind && python -m hivemind.hive --root /tmp/asc-0047-evaluate-smoke run "evaluate smoke" --json
cd hivemind && python -m hivemind.hive --root /tmp/asc-0047-evaluate-smoke evaluate --run <RUN_ID> --json
cd hivemind && python -m hivemind.hive --root /tmp/asc-0047-evaluate-smoke subagents review --run <RUN_ID> --json
cd hivemind && python -m pytest
python -m unittest discover -s tests -p 'test_aios_*.py'
python scripts/aios_monitor.py assess --json
```

Pass criteria:

- `artifacts/evaluation_report.json` exists for the evaluated run.
- JSON output contains all three review personas.
- Default output hides filesystem paths and raw provider/private bodies.
- `hive verify`/run validation accepts the new event taxonomy.
- MyWorld monitor is clear after result collection and release.

## Stop Conditions

- `privacy_violation`: report includes raw provider bodies, private memory
  contents, or non-debug absolute paths by default.
- `schema_drift`: evaluation artifact cannot be consumed as
  `hive_evaluation_report`.
- `persona_gap`: one of verifier, product evaluator, or actual-user persona is
  missing.
- `state_reference_missing`: run state does not reference the durable artifact.
- `validation_taxonomy_gap`: Hive run validation rejects the new event type.
- `capability_scope_creep`: implementation edits CapabilityOS or MemoryOS
  source under this Hive-owned contract.
- `verification_gate_failed`
- `monitor_not_clear`

## Receipts

Closed 2026-05-12 21:03 KST by `codex@myworld` acting operator.

- Dispatch:
  - `.aios/inbox/hivemind/asc-0047.hivemind.json`
  - `.aios/inbox/myworld/asc-0047.myworld.json`
  - `.aios/outbox/hivemind/asc-0047.hivemind.result.json`
  - `.aios/outbox/myworld/asc-0047.myworld.result.json`
- Hive implementation:
  - commit `85abfbe` (`Add evaluation review command`)
  - `hivemind/hivemind/evaluation.py`
  - `hivemind/tests/test_evaluation.py`
- Verification:
  - `cd hivemind && python -m pytest tests/test_evaluation.py -v`
    passed 6/6.
  - `cd hivemind && python -m hivemind.hive --root
    /tmp/asc-0047-evaluate-smoke run "evaluate smoke" --json` created
    `run_20260512_205837_6da3cd`.
  - `cd hivemind && python -m hivemind.hive --root
    /tmp/asc-0047-evaluate-smoke evaluate --run
    run_20260512_205837_6da3cd --json` returned
    `kind=hive_evaluation_report`, `overall_status=passed`,
    `paths_hidden=true`.
  - `cd hivemind && python -m hivemind.hive --root
    /tmp/asc-0047-evaluate-smoke subagents review --run
    run_20260512_205837_6da3cd --json` returned the same report schema with
    three reviews.
  - `cd hivemind && python -m pytest` passed 316/316.
  - `cd hivemind && git diff --check` passed.
- Stop conditions triggered: none.

## Work Packets

### WP-0047-A — Codex@hivemind implements durable evaluation command

- target_agent: codex
- target_repo: hivemind
- status: done
- issued: 2026-05-12
- accepted: 2026-05-12 20:50 KST
- closed: 2026-05-12 21:00 KST
- depends_on: ASC-0046
- brief: |
    Implement a first-class `hive evaluate` command and `hive subagents
    review` alias that read an existing run and write a path-hidden durable
    `artifacts/evaluation_report.json` with verifier, product evaluator, and
    actual-user persona review records. Keep the implementation inside Hive
    owned files only. Add focused tests and update Hive TODO/worklog artifacts.
- result: `.aios/outbox/hivemind/asc-0047.hivemind.result.json`

### WP-0047-B — Codex@myworld collects, verifies, and closes

- target_agent: codex
- target_repo: myworld
- status: done
- issued: 2026-05-12
- accepted: 2026-05-12 20:50 KST
- closed: 2026-05-12 21:03 KST
- depends_on: WP-0047-A
- brief: |
    Create dispatch/result records, run MyWorld verification after Hive closes
    its slice, update the contract index, goal evolution receipt, and ledger.
- result: `.aios/outbox/myworld/asc-0047.myworld.result.json`
