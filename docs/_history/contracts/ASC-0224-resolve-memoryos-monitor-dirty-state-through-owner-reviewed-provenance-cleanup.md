---
contract_id: ASC-0224
slug: memoryos-provenance-cleanup
status: closed
goal: Resolve a MemoryOS repo-dirty monitor finding through owner-reviewed provenance cleanup without mutating child repo state from MyWorld.
created: 2026-06-05T02:00:22+09:00
accepted: 2026-06-05T02:18:00+09:00
closed: 2026-06-05T04:43:00+09:00
origin: AIOS monitor friction radar cleanup action
promotion_receipt: .aios/promotions/monitor-cleanup-e862eae86110/promotion.json
accepted_by: codex_delegated_operator
human_approved: true
---

# ASC-0224 MemoryOS Provenance Cleanup

## Why Now

The AIOS monitor reports a child-repo dirty finding that is already linked to
prior dispatch context. This seed turns that visible evidence into a
MemoryOS-owned cleanup/review contract.

- owner: `memoryOS`
- monitor_need: `hold_for_repo_owner_triage`
- monitor_reason: A child repo has uncommitted changes that need owner review before new work is stacked on it.
- promotion_receipt: `.aios/promotions/monitor-cleanup-e862eae86110/promotion.json`

## Dirty Entries

- `?? .tmp_uri_cleanroom_seed.md`

## Related Dispatch Context

- `asc-0223` contract=`ASC-0223` status=`closed` latest=`released` reason=`closed_partial: concurrent MemoryOS evidence shows URI seed accepted; watcher held due pending_concurrent_work; provenance cleanup remains MemoryOS-local`
- `mdrev-207d05a6c64b6513` contract=`unknown` status=`unknown` latest=`collected` reason=``
- `mdrev-6811d9802bfff477` contract=`unknown` status=`unknown` latest=`collected` reason=``
- `asc-0202` contract=`ASC-0202` status=`closed` latest=`passed` reason=`invalid_repos`
- `asc-0194` contract=`ASC-0194` status=`closed` latest=`skipped` reason=`invalid_repos`

## Scope

repos:

- `memoryOS`
- `myworld`

allowed_files:

- `memoryOS/.tmp_uri_cleanroom_seed.md`
- MemoryOS provenance/source-artifact records needed to resolve the dirty entry
- MemoryOS repo-local worklog
- `.aios/outbox/memoryOS/*.result.json`
- MyWorld ledger/worklog closeout after MemoryOS returns evidence

allowed_existing_dirty:

- `memoryOS/.tmp_uri_cleanroom_seed.md`

forbidden_files:

- `.env`
- `.env.*`
- provider auth files
- raw exports
- private history stores
- URI implementation files unless a separate accepted URI contract authorizes them
- MyWorld rewriting MemoryOS accepted-memory state directly

## Required Work

- Inspect the dirty entries without deleting them first.
- Decide whether each entry is an intended source artifact, should be migrated
  to a checked-in provenance artifact, or should remain held for operator
  review.
- Preserve pointer-only source references; do not copy private/raw source
  bodies into committed artifacts.
- Return a result packet with `passed`, `held`, or `failed`, including evidence
  and the exact files touched.

## Verification Gate

```bash
git -C memoryOS status --short --branch
python scripts/aios_monitor.py assess --json
```

## Stop Conditions

- `memoryos_owner_not_ready`
- `dirty_entry_deleted_before_receipt`
- `private_source_leak`
- `accepted_memory_rewritten_from_myworld`
- `uri_scope_leak`
- `provider_auth_or_env_touched`

## Work Packets

### WP-0224-A — MemoryOS provenance cleanup

- target_agent: codex
- target_repo: memoryOS
- status: done
- issued: 2026-06-05
- depends_on: `ASC-0223` concurrent MemoryOS evidence and
  `mem_0c66b6db9ac73100`
- brief: |
    Treat `memoryOS/.tmp_uri_cleanroom_seed.md` as pre-existing cleanup input,
    not orphan work. Inspect it without deleting it first. Decide whether the
    source artifact should remain temp/local, be migrated to a checked-in
    MemoryOS provenance artifact, or remain held for operator review. Preserve
    pointer-only source references. Do not rewrite accepted-memory stores from
    MyWorld. Return a result packet with passed/held/failed status and evidence.
- result: passed via `.aios/outbox/memoryOS/asc-0224.memoryOS.result.json`;
  MemoryOS commit `0b3e973` pushed to `origin/main`.

## Dispatch Gate

```bash
python scripts/aios_dispatch.py create docs/contracts/ASC-0224-resolve-memoryos-monitor-dirty-state-through-owner-reviewed-provenance-cleanup.md --dispatch-id asc-0224
python scripts/aios_dispatch.py send --repo memoryOS --agent codex --dispatch-id asc-0224
test -f .aios/inbox/memoryOS/asc-0224.memoryOS.json
```

This contract uses `allowed_existing_dirty` to classify
`memoryOS/.tmp_uri_cleanroom_seed.md` as the explicit cleanup input for this
dispatch. Other overlapping dirty work must still hold as
`pending_concurrent_work`.

## Closeout

- result: `passed`
- collected: 2026-06-05T04:39:59+09:00
- memoryOS_commit: `0b3e973`
- memoryOS_push: `origin/main`
- evidence:
  - child watcher executed `codex` and returned
    `.aios/outbox/memoryOS/asc-0224.memoryOS.result.json` with no stop
    conditions.
  - `memoryOS/.tmp_uri_cleanroom_seed.md` no longer appears in
    `git -C memoryOS status --short --branch`.
  - MemoryOS migrated the pointer-only seed into
    `memoryOS/docs/provenance/asc-0224-uri-cleanroom-seed.md` and logged the
    owner decision in `memoryOS/docs/AGENT_WORKLOG.md`.
  - `python scripts/aios_monitor.py assess --json` reports health `watch` and
    no `repo_dirty` findings after the MemoryOS commit/push.
- caveat: `memoryos doctor --json` found a pre-existing invalid JSONL row in
  `memoryOS/memory/retrieval_traces.jsonl` line 11827; this was outside
  ASC-0224 scope and was not modified.
