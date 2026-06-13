---
contract_id: ASC-0264
slug: memoryos-serving-memory-lifecycle
status: closed
goal: Implement the MemoryOS per-user serving memory lifecycle with draft-first review, retrieval isolation, export receipts, and append-only deletion requests.
created: 2026-06-13T20:00:00+09:00
accepted: 2026-06-13T20:00:00+09:00
closed: 2026-06-13T20:13:00+09:00
human_approved: true
origin: ASC-0260/ASC-0261 release gate marks MemoryOS per-user memory lifecycle as partial and owner-bound to memoryOS.
depends_on:
  - ASC-0237
  - ASC-0260
  - ASC-0261
  - ASC-0262
---

# ASC-0264 MemoryOS Serving Memory Lifecycle

## Decision

MemoryOS is the most important OS for real AIOS serving. It owns per-user
memory namespaces, draft review, retrieval traces, export receipts, and
append-only deletion requests. MyWorld must not store private serving memory in
shared control-plane docs.

This contract turns ASC-0260 Slice 5 into an executable owner-bound packet for
`memoryOS`.

## Plain Language

In plain language: build the user's private memory shelf. New notes go onto a
review shelf first. The system may search only that user's shelf. Export and
removal are recorded as user-visible requests, not hidden data changes.

## Counter-Default Branch

The common default is "store useful facts and retrieve them later." That is not
enough for serving users. The counter-default branch is to assume every memory
record is untrusted and private until user review, namespace checks, and
retrieval traces prove otherwise.

## Cross-Domain Frame

Library lending records are the useful analogy: a librarian can see the right
account for the current patron, but an account mix-up is a serious incident and
corrections must preserve audit history. Serving memory should use the same
posture.

## Scope

repos:

- `memoryOS`

allowed_files:

- `memoryOS/memoryos/serving_memory.py`
- `memoryOS/tests/test_serving_memory.py`
- `memoryOS/docs/**`

forbidden_files:

- `.env`
- `.env.*`
- provider auth files
- credential vault contents
- raw provider logs
- private history stores
- raw user exports
- `hivemind/**`
- `CapabilityOS/**`
- `GenesisOS/**`
- `apps/**`
- `uri/**`
- unrelated child repo source files

## Substrate / Surface / Knowledge Gate

- schema_version: `aios.boundary_classifier.v1`
- layer: `memory_review_lifecycle`
- owner_repo: `memoryOS`
- substrate_level: `runtime`
- surface_type: `dispatch`
- knowledge_scope: `memoryos_context`
- authority: `execute_with_receipt`
- required_receipts:
  - `aios.serving_memory_draft.v1`
  - `aios.serving_memory_review.v1`
  - `aios.export_request.v1`
  - `aios.deletion_request.v1`

## Required Work

Implement a serving-memory primitive that supports:

- per-user namespaces keyed by explicit `user_id`;
- draft-first memory records that cannot become `accepted` without explicit
  user review evidence;
- retrieval scoped by `user_id`, with retrieval traces that prove why records
  were returned;
- export request receipts for user-visible data portability;
- deletion request receipts that preserve an append-only audit trail while
  marking records unavailable to normal retrieval;
- no raw provider transcript import as accepted memory.

## Per-OS Responsibility

### MemoryOS

must_produce:

- `memoryOS/memoryos/serving_memory.py`
- `memoryOS/tests/test_serving_memory.py`
- focused test evidence for namespace isolation, draft review, export, deletion request, and retrieval trace

### Hive Mind

must_produce:

- no implementation in this contract; future worker receipts can feed MemoryOS

### CapabilityOS

must_produce:

- no implementation in this contract; future route policy may decide what memories a connector can use

### GenesisOS

must_produce:

- no implementation in this contract; future prelaunch review challenges memory risks

## Acceptance Evidence

- `aios_retrieve`-equivalent serving retrieval for `user_id=A` cannot return
  records tagged `user_id=B`.
- A memory draft requires explicit user review before `status=accepted`.
- Export emits `aios.export_request.v1` receipt.
- Deletion emits `aios.deletion_request.v1` and does not physically destroy the
  audit record.
- Tests prove raw memory body is not exposed through support/admin summary
  helpers.

## Verification Gate

```bash
cd memoryOS
python -m pytest tests/test_serving_memory.py -q
python -m py_compile memoryos/serving_memory.py tests/test_serving_memory.py
git diff --check
```

## Stop Conditions

- `cross_user_memory_visible`
- `auto_accept_without_user_review`
- `deletion_request_destroys_record`
- `raw_provider_history_auto_accepted`
- `support_summary_exposes_memory_body`
- `child_repo_implementation_without_owner_contract`

## Return Packet

Write `.aios/outbox/memoryOS/asc-0264.memoryOS.result.json` with:

- changed files;
- test commands and outcomes;
- remaining gaps;
- stop conditions triggered, if any.

## Result

Claude executed the owner-bound packet through `scripts/aios_child_watcher.sh`
as `claude@memoryOS`. Codex verified and committed the repo-local changes after
Claude left them uncommitted.

Evidence:

- dispatch result: `.aios/outbox/memoryOS/asc-0264.memoryOS.result.json`
- child commit: `memoryOS` `dd8acba Add serving memory lifecycle`
- changed child files:
  - `memoryOS/memoryos/serving_memory.py`
  - `memoryOS/tests/test_serving_memory.py`
  - `memoryOS/docs/AGENT_WORKLOG.md`
- verification:
  - `python -m pytest tests/test_serving_memory.py -q` passed 22/22 in `memoryOS`
  - `python -m py_compile memoryos/serving_memory.py tests/test_serving_memory.py` passed
  - `git diff --check` passed in `memoryOS`

Release gate delta:

- `memoryos_user_lifecycle`: `partial` -> `met`
