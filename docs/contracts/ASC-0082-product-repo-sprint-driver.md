---
contract_id: ASC-0082
slug: product-repo-sprint-driver
status: proposed
goal: Turn product-repo goals into AIOS-owned sprint packets with Genesis divergence, MemoryOS context, CapabilityOS route, Hive execution, verification receipts, and feedback learning.
created: 2026-05-13T10:11:37+09:00
accepted:
closed:
origin: ASC-0058 goal inbox processor promoted repo-originated goal packets.
---

# ASC-0082 Product Repo Sprint Driver

## Why Now

Lower repos submitted AIOS-relevant goal or friction packets that map to this
theme. This draft is proposed only. The operator must accept it before any
dispatch or implementation.

## Source Goal Packets

- `rg_20260513T000227_df826a9c9753` from `myworld`: AIOS must take over Uri Sprint 008 execution instead of direct Codex editing
- `rg_20260512T231440_275ad0cbe16f` from `uri`: Prioritize Uri app/platform development through the AIOS loop
- `rg_20260512T231440_48e8f936dd28` from `uri`: AIOS should be the user-facing operator, not manual Codex-driven artifact bookkeeping
- `rg_20260512T231440_d7ef0e2827d5` from `uri`: Add an AIOS sprint driver for product repos
- `rg_20260512T232722_dfe8a632e712` from `uri`: Add agent_surface_before_agent_execution CapabilityOS route
- `rg_20260512T235155_fbce5ac1c64a` from `uri`: Record Codex provider loop gap from Uri development
- `rg_20260513T000243_0681433a5d43` from `uri`: Execute Uri Sprint 008 through AIOS rather than direct Codex editing
- `rg_20260513T023404_d4b2a7050165` from `uri`: Uri Sprint 011: make /memory tangible as a friendly human resource MemoryOS by deriving local strength, relationship, project, evidence, and role drafts from saved traces.
- `rg_20260513T091711_e5ad21c49f43` from `uri`: Uri Sprint 012: ship self-ingest preview-consent surface without real connectors.

## Source Evidence

- `rg_20260512T231440_275ad0cbe16f` evidence: `uri/docs/AGENT_WORKLOG.md`
- `rg_20260512T231440_275ad0cbe16f` evidence: `uri/hive/packets/URI-005-sprint-004-campus-graph-platform.md`
- `rg_20260512T231440_48e8f936dd28` evidence: `uri/docs/AGENT_WORKLOG.md`
- `rg_20260512T231440_48e8f936dd28` evidence: `docs/AIOS_REPO_GOAL_LOOP.md`
- `rg_20260512T231440_d7ef0e2827d5` evidence: `uri/capabilities/campus-graph-platform-routing-2026-05-12.md`
- `rg_20260512T232722_dfe8a632e712` evidence: `uri/capabilities/avatar-agent-surface-routing-2026-05-12.md`
- `rg_20260512T235155_fbce5ac1c64a` evidence: `uri/docs/AGENT_WORKLOG.md`
- `rg_20260512T235155_fbce5ac1c64a` evidence: `uri/capabilities/agent-guidance-surface-routing-2026-05-12.md`
- `rg_20260513T000243_0681433a5d43` evidence: `uri/hive/packets/URI-010-sprint-008-claude-followup-after-agent-guidance.md`
- `rg_20260513T000243_0681433a5d43` evidence: `uri/docs/AGENT_WORKLOG.md`
- `rg_20260513T023404_d4b2a7050165` evidence: `uri/hive/packets/URI-013-sprint-010-local-telemetry-seed.md`
- `rg_20260513T023404_d4b2a7050165` evidence: `uri/memory/drafts/2026-05-13-friendly-campus-human-resource-memoryos.md`
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
- `docs/contracts/ASC-0082-product-repo-sprint-driver.md`
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
