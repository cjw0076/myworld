---
contract_id: ASC-0083
slug: research-to-sprint-context-primitive
status: proposed
goal: Convert public research receipts into sprint context, MemoryOS draft candidates, CapabilityOS route notes, and Hive execution hints without manual bookkeeping.
created: 2026-05-13T10:11:37+09:00
accepted:
closed:
origin: ASC-0058 goal inbox processor promoted repo-originated goal packets.
---

# ASC-0083 Research To Sprint Context Primitive

## Why Now

Lower repos submitted AIOS-relevant goal or friction packets that map to this
theme. This draft is proposed only. The operator must accept it before any
dispatch or implementation.

## Source Goal Packets

- `rg_20260512T232721_69034977db01` from `uri`: Add research_to_sprint_context primitive to AIOS

## Source Evidence

- `rg_20260512T232721_69034977db01` evidence: `uri/research/public-sources/uri-aios-growth-intel-2026-05-12.md`

## Scope

repos:

- `myworld`
- `memoryOS`
- `CapabilityOS`
- `hivemind`

allowed_files:

- contract-specific files must be narrowed before acceptance
- `docs/contracts/ASC-0083-research-to-sprint-context-primitive.md`
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
python scripts/aios_doc_scout.py --root /home/user/workspaces/jaewon --json
python scripts/aios_monitor.py assess --json
```

Pass criteria:

- Contract remains `proposed` until operator acceptance.
- Accepted revision narrows allowed files before dispatch.
- Result packets link back to all source goal ids above.
- Verification evidence exists before closeout.

## Stop Conditions

- `private_source_ingest`
- `uncited_web_claim`
- `memory_auto_accept`
- `capability_binding_without_review`
- `verification_gate_failed`
- `operator_acceptance_missing`
- `scope_not_narrowed_before_dispatch`
