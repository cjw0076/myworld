---
contract_id: ASC-0263
slug: hivemind-serving-worker-resume
status: closed
goal: Implement the Hivemind hosted worker queue/resume slice for real end-user AIOS serving, with per-user execution receipts and no duplicate sensitive action on retry.
created: 2026-06-13T20:00:00+09:00
accepted: 2026-06-13T20:00:00+09:00
closed: 2026-06-13T20:13:00+09:00
human_approved: true
origin: ASC-0260/ASC-0261 release gate marks Hivemind hosted worker queue/resume as partial and owner-bound to hivemind.
depends_on:
  - ASC-0240
  - ASC-0255
  - ASC-0260
  - ASC-0261
  - ASC-0262
---

# ASC-0263 Hivemind Serving Worker Resume

## Decision

Hivemind owns the real end-user serving worker substrate. MyWorld may dispatch
the work but must not implement the worker from the control plane.

This contract turns the ASC-0260 Slice 4 planning record into an executable
owner-bound packet for `hivemind`.

## Plain Language

In plain language: build the job runner that can stop and continue a user's
agent task without losing track of what already happened, without reading
another user's job, and without putting secrets in logs.

## Counter-Default Branch

The common default is "make a queue and retry failed jobs." That is not enough
for serving users. The counter-default branch is to treat every retry as
dangerous until the worker proves which stages are already complete and which
actions are safe to repeat.

## Cross-Domain Frame

Railway signaling is the useful analogy: a train can pause and resume, but the
switch state and occupied blocks must be known before movement is allowed.
The worker should behave the same way for user jobs and sensitive actions.

## Scope

repos:

- `hivemind`

allowed_files:

- `hivemind/hivemind/serving_worker.py`
- `hivemind/tests/test_serving_worker.py`
- `hivemind/docs/**`

forbidden_files:

- `.env`
- `.env.*`
- provider auth files
- credential vault contents
- raw provider logs
- private history stores
- `memoryOS/**`
- `CapabilityOS/**`
- `GenesisOS/**`
- `apps/**`
- `uri/**`
- unrelated child repo source files

## Substrate / Surface / Knowledge Gate

- schema_version: `aios.boundary_classifier.v1`
- layer: `execution_substrate`
- owner_repo: `hivemind`
- substrate_level: `runtime`
- surface_type: `direct_hive_execution`
- knowledge_scope: `memoryos_context`
- authority: `execute_with_receipt`
- required_receipts:
  - `aios.serving_worker_run.v1`
  - `aios.serving_worker_resume.v1`
  - `duplicate_sensitive_action_prevention_test`
  - `per_user_workspace_receipt`

## Required Work

Implement a Hivemind serving worker primitive that can enqueue, start, pause,
resume, retry, and close user-scoped serving jobs.

The worker must:

- carry `user_id`, `session_id`, `job_id`, and `workspace_ref` in every receipt;
- record stage completion before retry/resume so completed sensitive stages are
  not executed twice;
- produce refusal/degraded receipts instead of running when a user/session scope
  is missing;
- keep provider credential references as references only, never raw values;
- reject cross-user resume attempts even if the caller knows another `job_id`;
- be deterministic enough for unit tests without live provider calls.

## Per-OS Responsibility

### Hive Mind

must_produce:

- `hivemind/hivemind/serving_worker.py`
- `hivemind/tests/test_serving_worker.py`
- focused test evidence for resume, retry, cross-user denial, and credential redaction

### MemoryOS

must_produce:

- no implementation in this contract; future work consumes worker receipts

### CapabilityOS

must_produce:

- no implementation in this contract; future work provides consent/rate decisions

### GenesisOS

must_produce:

- no implementation in this contract; future work challenges launch assumptions

## Acceptance Evidence

- `hivemind/hivemind/serving_worker.py` exists and exposes a small documented
  API for queue/resume receipts.
- `hivemind/tests/test_serving_worker.py` proves two interrupted jobs resume
  from recorded receipts without duplicate sensitive actions.
- Tests prove `user_id=A` cannot resume/read `user_id=B` worker state.
- Tests prove provider credential values are rejected or redacted from receipts.
- No live provider or network call is required for the test suite.

## Verification Gate

```bash
cd hivemind
python -m pytest tests/test_serving_worker.py -q
python -m py_compile hivemind/serving_worker.py tests/test_serving_worker.py
git diff --check
```

## Stop Conditions

- `duplicate_sensitive_action_on_retry`
- `cross_user_worker_state_access`
- `provider_credentials_in_receipt`
- `live_provider_call_in_unit_test`
- `worker_state_outside_user_workspace`
- `child_repo_implementation_without_owner_contract`

## Return Packet

Write `.aios/outbox/hivemind/asc-0263.hivemind.result.json` with:

- changed files;
- test commands and outcomes;
- remaining gaps;
- stop conditions triggered, if any.

## Result

Claude executed the owner-bound packet through `scripts/aios_child_watcher.sh`
as `claude@hivemind`.

Evidence:

- dispatch result: `.aios/outbox/hivemind/asc-0263.hivemind.result.json`
- child commit: `hivemind` `7295e9e Add serving worker queue/resume with per-user isolation`
- changed child files:
  - `hivemind/hivemind/serving_worker.py`
  - `hivemind/tests/test_serving_worker.py`
- verification:
  - `python -m pytest tests/test_serving_worker.py -q` passed 28/28 in `hivemind`
  - `python -m py_compile hivemind/serving_worker.py tests/test_serving_worker.py` passed
  - `git diff --check` passed in `hivemind`

Release gate delta:

- `hivemind_worker_resume`: `partial` -> `met`
