---
contract_id: ASC-0157
slug: contract-seed-os-evidence-slots
status: closed
goal: Make AIOS-generated contract seeds carry explicit MemoryOS, CapabilityOS, GenesisOS, and Hive evidence slots by default.
created: 2026-05-14 11:34 KST
accepted: 2026-05-14 11:34 KST
closed: 2026-05-14 11:41 KST
acceptance_authority: founder delegated continuation under active AIOS maturation goal.
origin: Control Center and ask flows are now usable, but generated seeds can still look like plain governance unless they reserve concrete OS evidence surfaces.
---

# ASC-0157 Contract Seed OS Evidence Slots

DNA references: Invariant 1 (decide before acting), Invariant 2
(draft-first memory), Invariant 4 (named exit), Invariant 5 (provenance
chain), Invariant 6 (operator override remains possible).

## Scope

repos:

- `myworld`

allowed_files:

- `scripts/aios_local_app.py`
- `scripts/aios_ask.py`
- `scripts/aios_contract_autodraft.py`
- `scripts/aios_goal_inbox_processor.py`
- `tests/test_aios_local_app.py`
- `tests/test_aios_ask.py`
- `tests/test_aios_contract_autodraft.py`
- `tests/test_aios_goal_inbox_processor.py`
- `docs/AIOS_SMART_CONTRACT.md`
- `docs/contracts/README.md`
- `docs/contracts/ASC-0157-contract-seed-os-evidence-slots.md`
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
- generated private chat transcripts

## Per-OS Responsibility

### myworld.must_produce

- A canonical AIOS role evidence section for generated contract seeds.
- Seed generator updates for ask, reviewed-session promotion, goal evolution
  autodraft, and goal inbox promotion.
- Tests proving new seeds reserve explicit OS evidence fields without starting
  execution.

### MemoryOS.must_produce

- Reserved evidence slots for context pack, retrieval trace, accepted memory
  ids, and draft memory policy.
- No accepted memory write during seed generation.

### CapabilityOS.must_produce

- Reserved evidence slots for route, recommended tools, fallback plan, and
  recommendation-only authority.
- No tool execution during seed generation.

### GenesisOS.must_produce

- Reserved evidence slots for branch set, assumption mutations, semantic
  alignment notes, and advisory-only authority.

### Hive Mind.must_produce

- Reserved evidence slots for execution plan, provider route, verification
  receipt, and fallback/degraded receipt.

## Verification Gate

```bash
python -m py_compile scripts/aios_local_app.py scripts/aios_ask.py scripts/aios_contract_autodraft.py scripts/aios_goal_inbox_processor.py
python -m unittest tests/test_aios_local_app.py tests/test_aios_ask.py tests/test_aios_contract_autodraft.py tests/test_aios_goal_inbox_processor.py
python -m unittest discover -s tests -p 'test_aios_*.py'
python scripts/aios_monitor.py assess --json
```

Pass criteria:

- Generated seeds include a `## AIOS Role Evidence` section.
- The section names MemoryOS, CapabilityOS, GenesisOS, and Hive Mind.
- Seed generation remains planning-only and does not execute child repo work.
- Monitor has no blocking alerts after closeout.

## Stop Conditions

- `seed_generator_executes_work`
- `memory_auto_accepts_during_seed`
- `capability_executes_tool_during_seed`
- `genesis_advice_treated_as_final_truth`
- `hive_verification_slot_missing`
- `verification_gate_failed`

## Receipts

- watcher result: `.aios/outbox/myworld/asc-0157.myworld.result.json`
- monitor closeout: `python scripts/aios_monitor.py assess --json` returned
  `health=watch` and `alerts=0` after the watcher result existed.

## Work Packets

### WP-0157-A — codex@myworld adds OS evidence slots to generated seeds

- target_agent: codex
- target_repo: myworld
- status: done
- issued: 2026-05-14
- accepted: 2026-05-14
- closed: 2026-05-14
- depends_on: ASC-0151
- brief: |
    Add a compact, canonical `## AIOS Role Evidence` section to generated
    contract seeds so future AIOS work starts with MemoryOS, CapabilityOS,
    GenesisOS, and Hive evidence placeholders instead of plain governance
    prose. Keep the end-user interface simple; put detailed semantics in docs.
- result: `.aios/outbox/myworld/asc-0157.myworld.result.json`
