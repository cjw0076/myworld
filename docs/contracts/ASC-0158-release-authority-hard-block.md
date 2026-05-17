---
contract_id: ASC-0158
slug: release-authority-hard-block
status: closed
goal: Prevent AIOS dispatch release from proceeding when authority verification returns a hard denial.
created: 2026-05-14 11:43 KST
accepted: 2026-05-14 11:43 KST
closed: 2026-05-14 11:49 KST
acceptance_authority: founder delegated continuation under active AIOS maturation goal.
origin: ASC-0157 closeout observed `release` returning ok=true and writing memory even though authority.allowed=false for codex without operator citizenship.
---

# ASC-0158 Release Authority Hard Block

DNA references: Invariant 1 (decide before acting), Invariant 4 (named exit),
Invariant 5 (provenance chain), Invariant 6 (operator override remains
possible).

## Scope

repos:

- `myworld`

allowed_files:

- `scripts/aios_dispatch.py`
- `tests/test_aios_dispatch.py`
- `docs/contracts/ASC-0158-release-authority-hard-block.md`
- `docs/contracts/README.md`
- `docs/AGENT_WORKLOG.md`
- `docs/AIOS_AGENT_LEDGER.md`

forbidden_files:

- `hivemind/**`
- `memoryOS/**`
- `CapabilityOS/**`
- `GenesisOS/**`
- `.env`
- `.env.*`
- provider credentials
- raw private exports

## AIOS Role Evidence

### MemoryOS

- context_pack: `not_required`
- retrieval_trace: `not_required`
- accepted_memory_ids: `not_required`
- draft_memory_policy: `closeout_draft_only_after_authorized_release`

### CapabilityOS

- route: `not_required`
- recommended_tools: `not_required`
- fallback_plan: `not_required`
- authority: `recommendation_only`

### GenesisOS

- branch_set: `not_required`
- assumption_mutations: `authority_must_bind_not_only_record`
- semantic_alignment_notes: `release means authorized state transition`
- authority: `advisory_only`

### Hive Mind

- execution_plan: `codex@myworld narrow implementation`
- provider_route: `codex_cli`
- verification_receipt: `pending`
- degraded_or_fallback_receipt: `not_required`

## Per-OS Responsibility

### myworld.must_produce

- `release` blocks hard authority denial before writing release transition or
  memory closeout.
- `--override-authority` remains the named operator bypass and is recorded.
- Tests for denied and override release paths.

## Verification Gate

```bash
python -m py_compile scripts/aios_dispatch.py
python -m unittest tests/test_aios_dispatch.py
python -m unittest discover -s tests -p 'test_aios_*.py'
python scripts/aios_monitor.py assess --json
```

Pass criteria:

- Hard authority denial returns non-zero and `ok=false`.
- No `released` transition or memory writeback occurs under hard denial.
- Explicit `--override-authority` can release and records the override.

## Stop Conditions

- `hard_denial_releases_dispatch`
- `hard_denial_writes_memory`
- `override_unrecorded`
- `verification_gate_failed`

## Receipts

- watcher result: `.aios/outbox/myworld/asc-0158.myworld.result.json`
- monitor closeout: `python scripts/aios_monitor.py assess --json` returned
  `health=watch` and `alerts=0` after collecting the watcher result.

## Work Packets

### WP-0158-A — codex@myworld binds release to authority

- target_agent: codex
- target_repo: myworld
- status: done
- issued: 2026-05-14
- accepted: 2026-05-14
- closed: 2026-05-14
- depends_on: ASC-0157
- brief: |
    Change dispatch release so hard authority denial blocks the state
    transition and memory writeback unless `--override-authority` is present.
- result: `.aios/outbox/myworld/asc-0158.myworld.result.json`
