---
contract_id: ASC-0033
slug: sovereign-ai-governance-readiness
status: closed
goal: Define and validate the next AIOS readiness layer for accountable enterprise-scale and sovereign-AI governance.
created: 2026-05-12 14:35 KST
accepted: 2026-05-12 14:35 KST
closed: 2026-05-12 14:37 KST
---

# ASC-0033 Sovereign AI Governance Readiness

## Why Now

The operator expanded the final target: AIOS should evolve until one operating
system can coordinate the functional surface of a large enterprise and a
sovereign AI governance stack. The current L6 readiness proves repeatable
cross-OS execution. It does not yet measure institutional authority, resource
governance, audit, rollback, or human checkpoint requirements.

ASC-0033 adds that higher readiness model. It is a governance and validation
surface, not a claim of real-world sovereignty or permission to bypass law,
privacy, or human authority.

## Scope

repos:

- `myworld`

allowed_files:

- `docs/AIOS_GOVERNANCE_MODEL.md`
- `scripts/aios_institution_readiness.py`
- `tests/test_aios_institution_readiness.py`
- `docs/contracts/ASC-0033-sovereign-ai-governance-readiness.md`
- `docs/contracts/README.md`
- `docs/goals/AIOS-GOAL-0001-make-something-great.md`
- `docs/goals/AIOS-GOAL-0001-evolution.md`
- `docs/AIOS_AGENT_LEDGER.md`

forbidden_files:

- `hivemind/**`
- `memoryOS/**`
- `CapabilityOS/**`
- `uri/**`
- `.aios/logs/**`
- `.env`
- raw export paths

## Responsibilities

### myworld.must_produce

- A governance model document defining post-L6 readiness levels.
- A machine-checkable institution readiness evaluator.
- Tests proving the evaluator blocks overclaiming when authority, audit, or
  checkpoint evidence is missing.
- Contract closeout and ledger entry.

### hive_mind.must_produce

- No source change. Future governance contracts may require Hive execution
  receipts with authority and rollback metadata.

### memoryos.must_produce

- No source change. Future governance contracts may require MemoryOS review
  records for policy, precedent, and institutional memory.

### capabilityos.must_produce

- No source change. Future governance contracts may require resource/capability
  risk budgets and tool authority maps.

## Governance Readiness Target

The new readiness layer must distinguish:

- L6 repeatable AIOS loop.
- L7 accountable authority.
- L8 resource and capability governance.
- L9 organizational multi-workstream governance.
- L10 sovereign-scale simulation readiness with explicit human/legal
  checkpoints.

## Verification Gate

```bash
python -m unittest tests/test_aios_institution_readiness.py
python scripts/aios_institution_readiness.py --json
python -m unittest tests/test_aios_instruction_index.py tests/test_aios_loop_policy.py tests/test_aios_doc_scout.py tests/test_aios_readiness.py tests/test_aios_dispatch.py tests/test_aios_loop.py tests/test_aios_monitor.py tests/test_aios_goal_evolution.py tests/test_aios_child_watcher.py tests/test_aios_round_controller.py tests/test_aios_web_research_receipt.py tests/test_aios_institution_readiness.py
python scripts/aios_monitor.py assess --json
```

Pass criteria:

- The evaluator reports schema `aios.institution_readiness.v1`.
- The current repo reaches at least L7 after this contract.
- It does not claim L10 without explicit human/legal checkpoint evidence.
- Full myworld tests pass and monitor remains clear.

## Stop Conditions

- `sovereignty_overclaim`: output claims real-world legal authority or
  political sovereignty.
- `governance_without_checkpoint`: high-authority actions can proceed without
  human checkpoint rules.
- `audit_gap`: readiness can pass without ledger/evidence artifacts.
- `resource_authority_gap`: capability/resource use has no bounded policy.
- `child_repo_scope_leak`: this contract edits child repo source.

## Receipts

- Implementation: `docs/AIOS_GOVERNANCE_MODEL.md`,
  `scripts/aios_institution_readiness.py`, and
  `tests/test_aios_institution_readiness.py`.
- Dispatch: `.aios/inbox/myworld/asc-0033.myworld.json`.
- Result packet: `.aios/outbox/myworld/asc-0033.myworld.result.json`.
- Release: `python scripts/aios_dispatch.py release --dispatch-id asc-0033
  --reason asc_0033_sovereign_ai_governance_readiness_verified`.
- Verification:
  - `python -m unittest tests/test_aios_institution_readiness.py` passed 3/3.
  - Full myworld suite with institution readiness tests passed 50/50.
  - `python scripts/aios_institution_readiness.py --json` returned
    `schema_version=aios.institution_readiness.v1` and blocked real-world
    authority claims with `ready_for_real_world_authority=false`.
  - Final closeout check after status flip reached L10 sovereign-scale
    simulation readiness while preserving `sovereignty_claimed=false`.
  - Final `python scripts/aios_monitor.py assess --json` returned
    `health=clear`.

## Work Packets

### WP-0033-A — Codex@myworld implements governance readiness layer

- target_agent: codex
- target_repo: myworld
- status: accepted
- issued: 2026-05-12
- accepted: 2026-05-12
- closed: 2026-05-12
- depends_on: ASC-0029, ASC-0030, ASC-0031
- brief: |
    Add a post-L6 governance readiness model and evaluator for AIOS as an
    accountable enterprise-scale and sovereign-AI operating stack. Keep this as
    a readiness/audit surface. Do not edit child repos or claim real-world
    authority.
- result: `.aios/outbox/myworld/asc-0033.myworld.result.json`
