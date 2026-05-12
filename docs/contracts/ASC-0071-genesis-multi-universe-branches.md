---
contract_id: ASC-0071
slug: genesis-multi-universe-branches
status: proposed
goal: Add a GenesisOS mechanism for parallel "universe branches" — same goal explored along N independent reasoning paths simultaneously — so AIOS does not pre-converge on a single solution before evidence justifies it.
created: 2026-05-13 KST
proposed_by: claude@myworld
acceptance_authority: pending founder GO.
origin: founder GenesisOS sub-contract sequence — "multiple-universe branches" is one of GenesisOS's 4 declared responsibilities.
---

# ASC-0071 Genesis Multi-Universe Branches

## Why Now

A single goal can be solved many ways. Today AIOS explores ONE path
(the first contract draft). Genesis adds N parallel branches — each
with different assumption set / approach / scale / risk profile — and
keeps them open in parallel until evidence collapses to one. Like
quantum superposition for contracts.

## Scope

repos:

- `myworld`
- `GenesisOS`

allowed_files:

- `GenesisOS/genesisos/branches.py`
- `GenesisOS/genesisos/cli.py`
- `GenesisOS/tests/test_branches.py`
- `GenesisOS/docs/MULTI_UNIVERSE.md`
- `GenesisOS/seeds/  (read by branch generator)`
- `scripts/aios_genesis_branch.py`
- `tests/test_aios_genesis_branch.py`
- `docs/contracts/ASC-0071-genesis-multi-universe-branches.md`
- `docs/contracts/README.md`
- `docs/AIOS_AGENT_LEDGER.md`

forbidden_files:

- `hivemind/**`, `memoryOS/**`, `CapabilityOS/**`, `uri/**`
- `_from_desktop/**`, `dain/**`, `minyoung/**`
- `.env`

## Per-OS Responsibility

### GenesisOS.must_produce

- `genesisos.branches.Branch` schema:
  `{branch_id, goal, assumption_set, approach, scale, risk, parent_seed_id,
    estimated_cost, estimated_value, alive: bool, collapsed_to: branch_id|null}`
- `branches.fork(goal, n=3, axes=["scale","risk","modality"]) → list[Branch]`
- `branches.snapshot()` — list all alive branches per goal
- `branches.collapse(goal_id, winner_branch_id, reason)` — operator
  declares one branch wins, others marked `collapsed_to`. Append-only.
- Branches persist under `GenesisOS/universes/<goal_id>/<branch_id>.json`.
- `genesisos cli branch fork --goal <text> --n 3` and
  `branch list` and `branch collapse --goal X --winner Y --reason Z`.

### myworld.must_produce

- `scripts/aios_genesis_branch.py` — wrapper. Given an active GOAL
  document, fork branches, present to operator. Operator collapse via
  CLI. Surviving branch becomes the canonical contract path.
- Test for fork→list→collapse flow.

### Hive / Memory / Capability

- No source change. Branches that survive may later become contracts;
  contract drafting itself is the existing autodrafter (ASC-0043).

## Verification Gate

```bash
cd GenesisOS && python -m pytest tests/test_branches.py -v
python -m genesisos.cli branch fork --goal "test goal" --n 3 --json
python -m genesisos.cli branch list --json
python -m genesisos.cli branch collapse --goal "test goal" --winner b-... --reason test --json
cd /home/user/workspaces/jaewon/myworld
python -m unittest tests/test_aios_genesis_branch.py
python -m unittest discover -s tests -p 'test_aios_*.py'
```

Pass criteria:

- Fork generates ≥3 distinct branches with distinct assumption sets.
- List shows all alive branches per goal.
- Collapse leaves only the winner alive; losers marked `collapsed_to`.
- Append-only history.

## Stop Conditions

- `branches_modify_external_state`: branches are pure speculation, no
  side effects until winner is promoted to contract.
- `silent_collapse`: operator must explicitly choose winner; no auto.
- `branch_count_explosion`: cap at N=10 branches per goal.
- `child_repo_scope_leak`
- `verification_gate_failed`

## Receipts

Pending.

## Work Packets

### WP-0071-A — codex@GenesisOS implements branches

- target_agent: codex
- target_repo: GenesisOS
- depends_on: ASC-0065 closed; ASC-0070 for seed → branch lineage.

### WP-0071-B — codex@myworld wrapper

- target_agent: codex
- target_repo: myworld
- depends_on: WP-0071-A
