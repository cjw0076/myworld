---
contract_id: ASC-0224
slug: memoryos-provenance-cleanup
status: proposed
goal: Resolve a MemoryOS repo-dirty monitor finding through owner-reviewed provenance cleanup without mutating child repo state from MyWorld.
created: 2026-06-05T02:00:22+09:00
accepted:
closed:
origin: AIOS monitor friction radar cleanup action
promotion_receipt: .aios/promotions/monitor-cleanup-e862eae86110/promotion.json
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
- `myworld` only for result collection and ledger closeout

allowed_files:

- MemoryOS provenance/source-artifact records needed to resolve the dirty entry
- MemoryOS repo-local worklog
- `.aios/outbox/memoryOS/*.result.json`
- MyWorld ledger/worklog closeout after MemoryOS returns evidence

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
