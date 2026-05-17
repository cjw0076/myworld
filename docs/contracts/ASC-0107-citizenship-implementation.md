---
contract_id: ASC-0107
slug: citizenship-implementation
status: closed
goal: Implement agent citizenship — operator vs child-agent vs reviewer vs critic vs researcher vs outsider — using ASC-0090 (proposed) registry foundation plus role-based authority gates. Establishes WHO has WHAT authority in AIOS-as-Government.
created: 2026-05-13 KST
accepted: 2026-05-13 KST by claude acting operator (founder GO sequence)
closed: 2026-05-13 21:31 KST by codex acting founder-delegated operator
acceptance_authority: claude@myworld (operator) per founder direct delegation.
origin: founder reframe AIOS=Government implies citizenship structure. Currently AIOS uses social-convention strings (claude@myworld, codex@hivemind) — no formal citizenship. ASC-0090 proposed identity registry; ASC-0107 builds the authority gates on top.
---

# ASC-0107 Citizenship Implementation

## Why Now

In current AIOS:
- Anyone can write a contract acceptance_authority field
- No verification that "claude@myworld" is actually claude
- No role gating — codex@hivemind can in theory accept a myworld-only
  contract as operator
- No distinction between full citizen (operator pair), permanent
  resident (child-OS agents), visitor (peer swarm), foreign tool
  (substrate)

ASC-0090 (proposed, not yet built) defines the registry. ASC-0107
builds the authority gates that USE the registry.

Per founder Government metaphor: government without citizenship = no
rule of law. Anyone can claim to be anyone.

## Required Reading

- `docs/contracts/ASC-0090-agent-identity-registry.md` (must close first)
- `docs/AIOS_DNA.md` (after ASC-0105) — invariant 6 (operator override)
  needs "operator" defined
- `docs/AIOS_GOVERNANCE_MODEL.md`

## Scope

repos:

- `myworld`

allowed_files:

- `scripts/aios_authority.py`
- `scripts/aios_dispatch.py`
- `scripts/aios_action_policy.py`
- `tests/test_aios_authority.py`
- `tests/test_aios_dispatch.py`
- `tests/test_aios_action_policy.py`
- `docs/AIOS_CITIZENSHIP.md`
- `docs/contracts/ASC-0107-citizenship-implementation.md`
- `docs/contracts/README.md`
- `docs/AGENT_WORKLOG.md`
- `docs/AIOS_AGENT_LEDGER.md`

forbidden_files:

- `~/.aios/agents.json` (read-only by this contract; ASC-0090 owns)
- child repos
- `_from_desktop/**`, `dain/**`, `minyoung/**`
- `.env`

## Per-OS Responsibility

### myworld.must_produce

`scripts/aios_authority.py`:
- citizenship classes (per ASC-0088 dialogue role taxonomy):
  - `operator` — full AIOS authority (claude@myworld, codex@myworld)
  - `child_agent` — repo-local authority (codex@hivemind etc.)
  - `reviewer` — review-only (drafts approve/reject)
  - `critic` — advisory only (Genesis tools)
  - `researcher` — evidence collection
  - `outsider` — observation only
- `verify_authority(agent_id, action) → allowed|denied`
  - reads ASC-0090 registry
  - checks role.capabilities includes action
  - returns reason for denial
- decision matrix:
  - `release_dispatch` → operator only
  - `flip_status_to_accepted` → operator only
  - `commit_to_child_repo` → child_agent of that repo (or operator)
  - `accept_memory_draft` → reviewer or operator
  - `propose_contract` → any citizen + outsider (gate is review)
  - `flip_status_to_held|stopped` → operator only
  - `bind_capability` → forbidden (DNA Inv 1: decide before acting)

Integration:
- `aios_dispatch.py release` calls `verify_authority(current_agent, "release_dispatch")`
- `aios_action_policy.py` consumes citizenship as input alongside scope
- soft-fail in V1: log denial, continue (operator can still override)
  with `--override-authority --reason <slug>`
- hard-fail in V2 — separate contract

`docs/AIOS_CITIZENSHIP.md`:
- defines all 6 classes with examples
- decision matrix (action → required citizenship)
- override procedure + audit trail

### child repos: no change

## Verification Gate

```bash
python -m py_compile scripts/aios_authority.py
python -m unittest tests/test_aios_authority.py
# new agent registers
python scripts/aios_agent_registry.py register --id test_outsider --substrate ollama --capabilities outsider --json
python scripts/aios_authority.py verify --agent test_outsider --action release_dispatch --json
# expect: allowed=false, reason cites required citizenship
python scripts/aios_authority.py verify --agent test_outsider --action propose_contract --json
# expect: allowed=true
python -m unittest tests/test_aios_dispatch.py tests/test_aios_action_policy.py
python -m unittest discover -s tests -p 'test_aios_*.py'
```

Pass criteria:

- 6 citizenship classes defined
- Decision matrix enforced for at least: release_dispatch, flip_status,
  accept_memory_draft, bind_capability
- Soft-fail in V1 with audit log
- Override path exists with explicit reason

## Stop Conditions

- `citizenship_breaks_existing_workflow`: V1 must be soft-fail; existing
  ad-hoc strings still work with warning
- `authority_lookup_failure`: if registry unavailable, degrade gracefully
  (default: allow with warning, NOT default-deny)
- `citizenship_excludes_founder`: founder always has all authorities
- `bind_capability_allowed`: never — violates DNA Inv 1
- `child_repo_scope_leak`
- `verification_gate_failed`

## Receipts

- dependency: ASC-0090 closed and seeded agent registry.
- dispatch: `.aios/inbox/myworld/asc-0107.myworld.json`
- result: `.aios/outbox/myworld/asc-0107.myworld.result.json`
- log: `.aios/logs/asc-0107.myworld.log`
- authority_audit: `.aios/state/authority.jsonl`
- verification: full `python -m unittest discover -s tests -p 'test_aios_*.py'`
  passed 301/301.
- memory_writeback: release wrote MemoryOS draft `mem_123026e80e205898`.

## Work Packets

### WP-0107-A — codex@myworld implements authority gates

- target_agent: codex
- target_repo: myworld
- status: done
- depends_on: ASC-0090 closed (registry exists)
- brief: implement aios_authority.py with 6 classes + decision matrix.
  Wire into dispatch.release + action_policy. Soft-fail V1. Tests cover
  all matrix cells. Document in CITIZENSHIP.md.
- result: `.aios/outbox/myworld/asc-0107.myworld.result.json`
