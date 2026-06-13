---
contract_id: ASC-0272
slug: memoryos-dream-agora-intake
status: proposed
goal: Build the MemoryOS Gate A Dream Agora intake path so web, research, provider, trace, and failure events become source-backed drafts instead of accepted memory.
created: 2026-06-14T03:20:00+09:00
human_approved: false
parent: ASC-0271
depends_on:
  - ASC-0264
  - ASC-0270
  - ASC-0271
external_baseline:
  - docs/research/AIOS_AGENT_SERVICE_INFRA_DELTA_2026-06-14.md
---

# ASC-0272 MemoryOS Dream Agora Intake

## Decision

MemoryOS is the most important OS for the next AIOS phase. It must absorb all
useful generated knowledge without silently accepting it as truth.

This contract proposes a Gate A, non-UI MemoryOS slice: external web study,
provider output summaries, sandbox traces, route failures, and SMX loser
branches become draft-first MemoryOS records with source receipts and review
status.

## Scope

repos:

- `memoryOS`

allowed_files:

- `memoryOS/memoryos/dream_agora.py`
- `memoryOS/tests/test_dream_agora.py`
- `memoryOS/docs/**`

forbidden_files:

- `.env`
- `.env.*`
- provider auth files
- credential vault contents
- raw provider logs
- raw user exports
- private history stores
- `hivemind/**`
- `CapabilityOS/**`
- `GenesisOS/**`
- `apps/**`
- `uri/**`
- unrelated child repo source files

## Substrate / Surface / Knowledge Gate

- schema_version: `aios.boundary_classifier.v1`
- owner_repo: `memoryOS`
- substrate_level: `runtime`
- surface_type: `dispatch`
- knowledge_scope: `memoryos_context`
- authority: `draft_only`
- required_receipts:
  - `aios.source_receipt.v1`
  - `aios.memory_draft.v1`
  - `aios.failure_memory_draft.v1`
  - `aios.review_queue_projection.v1`

## Required Work

Implement a deterministic draft-intake primitive that:

- accepts source receipts for web research, provider summaries, trace
  summaries, CapabilityOS route observations, and GenesisOS counter-branches;
- creates MemoryOS draft records only, never accepted memory;
- records source type, source time, source url or artifact ref, confidence,
  privacy class, and review status;
- supports negative-evidence and failure-memory drafts;
- rejects raw private provider logs and raw user exports;
- exposes a draft backlog count for release gates and operator review.

## Verification Gate

```bash
cd memoryOS
python3 -m unittest tests.test_dream_agora -v
python3 -m py_compile memoryos/dream_agora.py
git diff --check
```

## Stop Conditions

- `memory_auto_accepts_without_review`
- `source_receipt_missing`
- `raw_provider_output_stored_as_accepted`
- `private_export_ingested_as_shared_memory`
- `draft_backlog_not_observable`

## Dispatch Packet

- target_repo: `memoryOS`
- target_agent: `claude`
- status: not_sent
- reason: proposed Gate A contract awaits operator/delegated release.
