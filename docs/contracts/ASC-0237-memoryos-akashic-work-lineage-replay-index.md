---
contract_id: ASC-0237
slug: memoryos-akashic-work-lineage-replay-index
status: closed
goal: Give MemoryOS a durable Akashic work-lineage and replay checkpoint index for cross-session, cross-device AIOS work without storing raw private provider history.
created: 2026-06-12T23:58:00+09:00
closed: 2026-06-13T00:04:00+09:00
origin: ASC-0235 world readiness gate reports durable work lineage and Akashic observability as partial.
---

# ASC-0237 MemoryOS Akashic Work-Lineage Replay Index

## Why Now

`scripts/aios_world_readiness.py --json` currently reports:

- `ready_for_world_deployment=false`
- `durable_work_lineage=partial`
- `akashic_observability=partial`

AIOS has useful local pieces: `scripts/aios_work.py`,
`scripts/aios_checkpoint.py`, `scripts/aios_ingest_session.py`, event logs,
ledgers, and MemoryOS retrieval traces. The missing world-deployment primitive
is a single durable index that can answer:

```text
For this user goal, what happened across every session, provider, tool call,
checkpoint, pause, resume, result, memory draft, and verifier receipt?
```

The answer must be queryable after a session ends and portable enough to move
between devices or hosted workers. It must not copy raw provider transcripts,
credentials, `.env` content, private exports, or private history stores into a
shared artifact.

## Scope

repos:

- `memoryOS`
- `myworld`

allowed_files:

- `memoryOS/docs/**`
- `memoryOS/tests/**`
- `memoryOS/memoryos/**`
- `docs/contracts/ASC-0237-memoryos-akashic-work-lineage-replay-index.md`
- `docs/AIOS_AGENT_LEDGER.md`

forbidden_files:

- `.env`
- `.env.*`
- raw provider logs
- raw private history stores
- provider auth files
- credential vault contents
- accepted MemoryOS records without review
- child repo source files outside `memoryOS` unless a follow-up contract names
  the owner

## Substrate / Surface / Knowledge Gate

- schema_version: `aios.boundary_classifier.v1`
- layer: `memory_knowledge_route`
- owner_repo: `memoryOS`
- substrate_level: `none`
- surface_type: `contract`
- knowledge_scope: `memoryos_context`
- authority: `draft_only`
- required_receipts:
  - `akashic_index_schema`
  - `privacy_filter_receipt`
  - `replay_checkpoint_receipt`
  - `memory_draft_review_queue_receipt`

## Required Work

MemoryOS should define and implement an append-only `aios.akashic_work_index.v1`
artifact that links, at minimum:

- `work_id`
- `goal`
- `session_ids`
- `parent_work_id`
- `provider_run_ids`
- `tool_call_ids`
- `checkpoint_refs`
- `pause_resume_events`
- `verification_refs`
- `memory_draft_ids`
- `retrieval_trace_ids`
- `capability_observation_refs`
- `genesis_branch_refs`
- `privacy_redaction_receipt`
- `source_artifact_refs`

The index should store references, compact summaries, hashes, statuses, and
safe metadata. It should not store raw private content.

## Acceptance Tests

The MemoryOS implementation should prove:

1. A work item with two sessions and one resume checkpoint can be indexed.
2. The replay index can reconstruct status and next action without chat
   context.
3. Raw prompt/output bodies are excluded or redacted.
4. A MemoryOS draft is created or queued for review only when the artifact is
   meant to become durable knowledge.
5. Invalid rows or missing referenced artifacts degrade into structured
   warnings rather than silent success.

## MyWorld Verification Gate

After MemoryOS returns a result packet, MyWorld should run:

```bash
python3 scripts/aios_world_readiness.py --json
python3 -m unittest tests.test_aios_world_readiness -v
git diff --check
```

Pass criteria:

- `durable_work_lineage` moves from `partial` to `met`, or the result packet
  explains the remaining blocker with a concrete follow-up contract.
- `akashic_observability` moves from `partial` to `met`, or the result packet
  explains the remaining blocker with a concrete follow-up contract.
- No raw private/provider/credential data is introduced.

## Result

MemoryOS now has `memoryOS/memoryos/akashic_ledger.py` implementing
`aios.akashic_work_index.v1` as an append-only reference index. The artifact
stores safe metadata and references for work lineage, provider runs, tool
calls, checkpoints, pause/resume events, verification refs, memory drafts,
retrieval traces, capability observations, Genesis branches, source artifacts,
privacy redaction receipts, status, and next action.

Privacy behavior is explicit: raw body fields such as `raw_prompt`,
`raw_output`, `raw_transcript`, `provider_stdout`, and `provider_stderr` are
rejected, and secret-like strings degrade into privacy findings instead of
being accepted silently.

Evidence:

- `memoryOS/tests/test_akashic_ledger.py` covers reconstructability, raw-body
  rejection, secret-like rejection, and append idempotency.
- `python -m pytest tests/test_akashic_ledger.py -q` passed in `memoryOS`.
- `python -m py_compile memoryos/akashic_ledger.py` passed in `memoryOS`.
- `scripts/aios_world_readiness.py --json` now reports
  `durable_work_lineage=met` and `akashic_observability=met`.

World readiness delta:

- `durable_work_lineage`: `partial` -> `met`
- `akashic_observability`: `partial` -> `met`
- remaining blocker: `cloud_execution_isolation` needs hosted filesystem,
  process, network, package, timeout, quota, and credential-reference receipts
  under `ASC-0240`.

## Stop Conditions

- `raw_provider_history_leak`
- `credential_value_in_prompt_or_doc`
- `memoryos_accepts_without_review`
- `replay_claim_without_checkpoint_refs`
- `akashic_index_contains_raw_private_body`
- `child_repo_implementation_without_owner_scope`

## Return Packet

MemoryOS should write a result packet to:

```text
.aios/outbox/memoryOS/asc-0237.memoryOS.result.json
```

with:

- `status`: `passed`, `needs_more_evidence`, or `blocked`
- `changed_files`
- `evidence`
- `privacy_receipt`
- `world_readiness_delta`
- `next`

## Next

Continue with `ASC-0240` for Hive cloud/runtime isolation receipts. The
credential boundary is tracked separately by `ASC-0236` and is already met at
the MyWorld readiness marker level; it still needs broader provider adoption
before the final world-deployment claim.
