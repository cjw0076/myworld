---
contract_id: ASC-0223
slug: memoryos-product-domain-seed-review
status: closed
created: 2026-06-05T01:34:00+09:00
accepted: 2026-06-05T01:34:00+09:00
closed: 2026-06-05T01:43:00+09:00
accepted_by: codex_delegated_operator
human_approved: true
goal: Turn the observed URI product-domain MemoryOS gap into a draft-first review task, using the existing clean-room sourcing seed without accepting memory or erasing local evidence.
origin: active thread goal "자율개발"; Claude absorption-delta observation that MemoryOS returned null for product-domain URI tasks; `memoryOS/.tmp_uri_cleanroom_seed.md` exists as an untracked product-domain memory candidate.
---

# ASC-0223 MemoryOS Product-Domain Seed Review

DNA references: Invariant 1 (decide before acting), Invariant 2 (draft-first
memory), Invariant 3 (no record destroyed), Invariant 5 (provenance chain),
Invariant 7 (private-gated data stays out of dispatch and prompt artifacts).

## Decision

AIOS should not keep improving only the control plane while MemoryOS returns
null on real product-domain tasks. The next autonomous-development slice is to
route the existing URI clean-room sourcing seed through MemoryOS as a
draft/review candidate, not as accepted memory.

This contract intentionally does not commit, delete, or rewrite the current
untracked MemoryOS seed from MyWorld. MemoryOS owns the review lifecycle and
must decide whether the seed becomes a review request, a draft memory, or a
rejected/held artifact.

## Scope

repos:

- `myworld`
- `memoryOS`

allowed_files:

- `docs/contracts/ASC-0223-memoryos-product-domain-seed-review.md`
- `docs/AGENT_WORKLOG.md`
- `docs/AIOS_AGENT_LEDGER.md`
- `.aios/inbox/memoryOS/asc-0223.memoryOS.json`
- `.aios/outbox/memoryOS/asc-0223.memoryOS.result.json`
- `memoryOS/.tmp_uri_cleanroom_seed.md`
- `memoryOS/docs/AGENT_WORKLOG.md`
- MemoryOS draft/review artifacts produced by existing MemoryOS commands

forbidden_files:

- `.env`
- `.env.*`
- provider auth files
- raw exports
- private history stores
- MemoryOS accepted-memory stores unless the review lifecycle explicitly
  produces a reviewed acceptance record
- URI source files
- Hive execution harnesses
- CapabilityOS route bindings

## AIOS Role Evidence

### MemoryOS

- context_pack: required from current MemoryOS repo state
- retrieval_trace: if a retrieval command exists for URI product-domain memory,
  run it before and after draft/review handling; otherwise state the missing
  command as a gap
- accepted_memory_ids: none at dispatch time
- draft_memory_policy: draft/review only; no auto-acceptance

### CapabilityOS

- route: local MemoryOS CLI / repo-local review path
- recommended_tools: existing MemoryOS import/review commands and tests
- fallback_plan: if the current temp seed cannot be imported safely, write a
  result packet explaining why and leave the seed untouched
- authority: recommendation only

### GenesisOS

- branch_set: DeepIdeaChamber smoke generated 5 speculative branches for this
  gap on 2026-06-05
- assumption_mutations: Genesis critic flagged `assumption-silent` and
  `time-frozen`
- semantic_alignment_notes: product-domain memory must not collapse draft
  memory into accepted memory
- authority: advisory only

### Hive Mind

- execution_plan: MemoryOS owner performs narrow review/import/hold and returns
  a result packet
- provider_route: no external provider required
- verification_receipt: MemoryOS tests or command receipts plus result packet
- degraded_or_fallback_receipt: required if review/import cannot run safely

### 5-Persona Use

- Hive / Wrapper: bounded dispatch/result packet only
- MemoryOS / Retriever: primary owner; product-domain retrieval gap
- CapabilityOS / Router: local MemoryOS route only
- GenesisOS / Philosophy: DeepIdeaChamber/critic surfaced risk framing
- MyWorld / Sovereign: accepted this contract and preserves operator override

## Required Behavior

MemoryOS must:

- Inspect the current untracked `memoryOS/.tmp_uri_cleanroom_seed.md` without
  deleting it first.
- Treat its content as a draft/review candidate, not accepted memory.
- Preserve provenance to URI source references as pointers only.
- Avoid copying private/raw source bodies into shared artifacts.
- Produce one result packet at `.aios/outbox/memoryOS/asc-0223.memoryOS.result.json`.

The result packet must say one of:

- `status=passed`: a draft/review artifact was created and verified.
- `status=held`: the seed is coherent but needs operator review or missing
  source evidence.
- `status=failed`: MemoryOS could not safely process the candidate, with stop
  condition and evidence.

The result must also include a time split:

- 1h: what was made reviewable now
- 1w: what additional product-domain memories should be filled next
- 1y: how to prevent MemoryOS product retrieval from becoming theater again

## Verification Gate

```bash
python scripts/aios_dispatch.py create docs/contracts/ASC-0223-memoryos-product-domain-seed-review.md --dispatch-id asc-0223
python scripts/aios_dispatch.py send --repo memoryOS --agent codex --dispatch-id asc-0223
test -f .aios/inbox/memoryOS/asc-0223.memoryOS.json
```

Closeout gate after MemoryOS returns:

```bash
test -f .aios/outbox/memoryOS/asc-0223.memoryOS.result.json
python scripts/aios_dispatch.py collect --dispatch-id asc-0223
python scripts/aios_monitor.py assess --json
```

## Stop Conditions

- `memory_auto_acceptance`: any product-domain seed is accepted without review.
- `private_source_leak`: private/raw source bodies are copied into committed
  artifacts.
- `seed_destroyed`: the temp seed is deleted before a receipt records how it
  was handled.
- `uri_scope_leak`: URI implementation files are changed under this contract.
- `memoryos_dirty_conflict`: existing uncommitted/ahead MemoryOS work makes it
  impossible to isolate this slice.

## Work Packets

### WP-0223-A — Codex@memoryOS product-domain seed review

- target_agent: codex
- target_repo: memoryOS
- status: done
- issued: 2026-06-05
- accepted: 2026-06-05
- closed: 2026-06-05
- depends_on: `docs/AIOS_CLAUDE_SELF_OBSERVATION_LOG.md` absorption-delta probe
- brief: |
    In MemoryOS, inspect `.tmp_uri_cleanroom_seed.md` as a product-domain
    memory candidate. Do not delete it before recording a receipt. Convert it
    into a draft/review artifact or hold/fail with evidence. Do not accept
    memory silently. Preserve source references as pointers only. Return a
    result packet to `.aios/outbox/memoryOS/asc-0223.memoryOS.result.json`
    with status, evidence, stop conditions, and 1h/1w/1y time split.
- result: `.aios/outbox/memoryOS/asc-0223.memoryOS.result.json` returned
  `status=held`, `failure_category=pending_concurrent_work`, and
  `stop_conditions_triggered=["pending_concurrent_work"]`.

## Receipts

- dispatch packet:
  `.aios/inbox/memoryOS/asc-0223.memoryOS.json`
- result packet:
  `.aios/outbox/memoryOS/asc-0223.memoryOS.result.json`
- dispatch state:
  `python scripts/aios_dispatch.py hold --dispatch-id asc-0223 --reason pending_concurrent_memoryos_seed_work`
- current exit:
  `held` because MemoryOS already has concurrent local work around the exact
  seed file. No MemoryOS seed was deleted, accepted, or rewritten by MyWorld.

## Concurrent MemoryOS Evidence

After the watcher returned `held`, MyWorld verified that the same URI seed had
already moved through a MemoryOS draft/review path outside this dispatch:

- MemoryOS search returned `mem_0c66b6db9ac73100` for
  `URI clean-room sourcing rule`.
- The memory object is `project=URI`, `type=decision`, `base_status=draft`,
  `effective_status=accepted`, and `status=accepted`.
- `latest_review` records `action=approve`, `reviewer=claude@myworld`, and
  `captured_at=2026-06-05T01:28:57+09:00`.
- The memory preserves pointer refs only:
  `uri/src/lib/festival-data.ts`,
  `uri/docs/LEGAL_ETHICAL_GUARDRAILS.md`, and
  `uri/docs/CAMPUS_WIKI_SEED_ULSAN_2026-06-05.md`.

This closes the product-domain retrieval gap for this seed, but the close is
partial for the dispatch contract itself: `asc-0223` did not produce the
requested 1h/1w/1y split because the watcher correctly stopped at
`pending_concurrent_work`.

## Follow-Up

Leave `memoryOS/.tmp_uri_cleanroom_seed.md` untouched until the MemoryOS owner
decides whether the accepted memory's `source_artifact_id` should continue to
point at that temp file or be migrated to a checked-in source artifact. The next
work should be MemoryOS-local provenance cleanup, not MyWorld rewriting
MemoryOS state.
