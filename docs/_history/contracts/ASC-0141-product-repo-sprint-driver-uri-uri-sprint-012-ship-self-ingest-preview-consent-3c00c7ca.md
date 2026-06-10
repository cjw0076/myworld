---
contract_id: ASC-0141
slug: product-repo-sprint-driver-uri-uri-sprint-012-ship-self-ingest-preview-consent-3c00c7ca
status: withdrawn
withdrawn_at: 2026-05-20 KST
withdrawn_reason: ASC-0058 inbox-processor auto-promoted instance (uri-scoped, sprint-012 self-ingest preview consent). 부모 설계 ASC-0082 는 ASC-0205 로 supersede 됨. CC2 가 uri/.aios 와이어업 시 새 packet 으로 재발의.
withdrawal_authority: claude@myworld operator — 2026-05-20 ASC-0205 CC6 정리.
created: 2026-05-14T01:36:47+09:00
accepted:
closed:
origin: ASC-0058 goal inbox processor promoted repo-originated goal packets.
---

# ASC-0141 Product Repo Sprint Driver

## Why Now

Lower repos submitted AIOS-relevant goal or friction packets that map to this
theme. ASC-0115 requires this draft to answer the specific source packet(s)
listed below instead of silently merging them into a broad theme. This draft is
proposed only. The operator must accept it before any dispatch or
implementation.

## Source Goal Packets

- `rg_20260513T091711_e5ad21c49f43` from `uri`: Uri Sprint 012: ship self-ingest preview-consent surface without real connectors.

## Source Evidence

- `rg_20260513T091711_e5ad21c49f43` evidence: `uri/memory/drafts/2026-05-13-self-ingest-consent-surface-design.md`
- `rg_20260513T091711_e5ad21c49f43` evidence: `uri/hive/packets/URI-015-sprint-011-human-resource-memoryos.md`

## Scope

repos:

- `myworld`
- `hivemind`
- `memoryOS`
- `CapabilityOS`
- `GenesisOS`

allowed_files:

- contract-specific files must be narrowed before acceptance
- `docs/contracts/ASC-0141-product-repo-sprint-driver-uri-uri-sprint-012-ship-self-ingest-preview-consent-3c00c7ca.md`
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
