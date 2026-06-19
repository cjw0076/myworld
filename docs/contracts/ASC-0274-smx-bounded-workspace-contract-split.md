---
contract_id: ASC-0274
slug: smx-bounded-workspace-contract-split
status: closed
accepted: 2026-06-14T03:10:00+09:00
closed: 2026-06-14T03:40:00+09:00
goal: Split Speculative Multiverse Execution into a safe Gate A GenesisOS branch-design contract and a later Hivemind isolated-execution contract gated by serving proof.
created: 2026-06-14T03:20:00+09:00
human_approved: true
parent: ASC-0271
depends_on:
  - ASC-0263
  - ASC-0266
  - ASC-0270
  - ASC-0271
external_baseline:
  - docs/research/AIOS_AGENT_SERVICE_INFRA_DELTA_2026-06-14.md
---

# ASC-0274 SMX Bounded Workspace Contract Split

## Decision

SMX is necessary for explosive idea growth, but execution is dangerous if it
starts before isolation, receipts, and MemoryOS draft rules are proven.

This contract keeps Gate A safe: GenesisOS may design branch schemas and
recombination candidates now. Hivemind workspace execution remains blocked
until a separate accepted execution contract proves isolation receipts and
duplicate-action prevention.

## Scope

repos:

- `GenesisOS`

allowed_files:

- `GenesisOS/genesisos/smx_branch.py`
- `GenesisOS/tests/test_smx_branch.py`
- `GenesisOS/docs/**`

forbidden_files:

- `.env`
- `.env.*`
- provider auth files
- credential vault contents
- raw provider logs
- raw user data
- `hivemind/**`
- `memoryOS/**`
- `CapabilityOS/**`
- `apps/**`
- `uri/**`
- unrelated child repo source files

## Substrate / Surface / Knowledge Gate

- schema_version: `aios.boundary_classifier.v1`
- owner_repo: `GenesisOS`
- substrate_level: `none`
- surface_type: `dispatch`
- knowledge_scope: `multi_model_review`
- authority: `speculative_only`
- required_receipts:
  - `aios.smx_branch_set.v1`
  - `aios.counterfactual_memory_candidate.v1`
  - `smx_execution_blocked_until_isolation_receipt`

## Required Work

Implement a GenesisOS branch-design primitive that:

- takes a goal, uncertainty reason, constraints, and number of branches;
- emits bounded branches with assumptions, risk labels, verification intent,
  and MemoryOS draft disposition;
- marks loser branches as counterfactual draft candidates, not accepted memory;
- refuses to request Hivemind execution without an isolation receipt ref;
- keeps selection authority outside GenesisOS.

## Verification Gate

```bash
cd GenesisOS
python3 -m unittest tests.test_smx_branch -v
python3 -m py_compile genesisos/smx_branch.py
git diff --check
```

## Stop Conditions

- `smx_runs_without_isolation_receipt`
- `genesis_selects_final_truth`
- `losers_auto_accepted_as_memory`
- `winner_overwrites_without_review`
- `hivemind_execution_started_from_gate_a_design`

## Dispatch Packet

- target_repo: `GenesisOS`
- target_agent: `claude`
- status: not_sent
- reason: proposed Gate A design contract awaits operator/delegated release.
