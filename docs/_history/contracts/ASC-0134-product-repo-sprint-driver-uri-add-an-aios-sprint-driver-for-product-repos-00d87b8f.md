---
contract_id: ASC-0134
slug: product-repo-sprint-driver-uri-add-an-aios-sprint-driver-for-product-repos-00d87b8f
status: superseded-by-rewrite
goal: Turn product-repo goals into AIOS-owned sprint packets with Genesis divergence, MemoryOS context, CapabilityOS route, Hive execution, verification receipts, and feedback learning.
created: 2026-05-14T01:36:47+09:00
accepted:
closed:
rewrite_target: ASC-0173 (product-repo execution takeover recast as consent-emit delegation; ASC-0178 reconciliation)
origin: ASC-0058 goal inbox processor promoted repo-originated goal packets.
---

# ASC-0134 Product Repo Sprint Driver

## Why Now

Lower repos submitted AIOS-relevant goal or friction packets that map to this
theme. ASC-0115 requires this draft to answer the specific source packet(s)
listed below instead of silently merging them into a broad theme. This draft is
proposed only. The operator must accept it before any dispatch or
implementation.

## Source Goal Packets

- `rg_20260512T231440_d7ef0e2827d5` from `uri`: Add an AIOS sprint driver for product repos

## Source Evidence

- `rg_20260512T231440_d7ef0e2827d5` evidence: `uri/capabilities/campus-graph-platform-routing-2026-05-12.md`

## Scope

repos:

- `myworld`
- `hivemind`
- `memoryOS`
- `CapabilityOS`
- `GenesisOS`

allowed_files:

- contract-specific files must be narrowed before acceptance
- `docs/contracts/ASC-0134-product-repo-sprint-driver-uri-add-an-aios-sprint-driver-for-product-repos-00d87b8f.md`
- `docs/contracts/README.md`
- `docs/AIOS_AGENT_LEDGER.md`

forbidden_files:

- `.env`
- `.env.*`
- `.aios/goal_inbox/**`
- raw export paths
- broad child-repo source edits before accepted work packets

## Responsibilities

### myworld.must_produce

- A narrowed accepted contract scope with exact files.
- Work packets for every repo that owns implementation.
- Verification receipts linked back to the source goal packets.

### MemoryOS.must_produce

- Context pack or memory draft candidates only if accepted scope requires it.
- No accepted memory without review.

### CapabilityOS.must_produce

- Route or fallback recommendation only if accepted scope requires it.
- No tool/provider binding without an accepted contract.

### Hive Mind.must_produce

- Execution plan, provider route, role capsule, receipt, and verification
  evidence for any implementation packet it owns.

## Verification Gate

```bash
python scripts/aios_sprint_loop.py plan --repo uri --json
python scripts/aios_monitor.py assess --json
```

Pass criteria:

- Contract remains `proposed` until operator acceptance.
- Accepted revision narrows allowed files before dispatch.
- Result packets link back to all source goal ids above.
- Verification evidence exists before closeout.

## Stop Conditions

- `direct_product_repo_edit_from_myworld`
- `missing_memory_context`
- `missing_capability_route`
- `missing_hive_receipt`
- `verification_gate_failed`
- `operator_acceptance_missing`
- `scope_not_narrowed_before_dispatch`
