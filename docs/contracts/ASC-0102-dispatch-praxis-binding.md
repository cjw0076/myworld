---
contract_id: ASC-0102
slug: dispatch-praxis-binding
status: closed
goal: Bind the ASC-0101 production praxis envelope to AIOS dispatch packets so non-trivial work cannot be sent without explicit MemoryOS, CapabilityOS, GenesisOS, Hive, and specialist-assignment evidence.
created: 2026-05-13 KST
accepted: 2026-05-13 KST by Codex under founder instruction to use AIOS for work direction
closed: 2026-05-13 KST
praxis_required: true
praxis_ref: docs/praxis/ASC-0102-dispatch-praxis-binding.json
origin: founder instruction 2026-05-13 KST - "AIOS 사용해서 지시"
---

# ASC-0102 Dispatch Praxis Binding

## Diagnosis

ASC-0101 created the production praxis envelope, but an envelope that is not
attached to dispatch remains advisory. The next control-plane step is to make
AIOS work packets carry validated praxis evidence when a contract explicitly
requires it.

## Scope

repos:

- `myworld`

allowed_files:

- `docs/contracts/ASC-0102-dispatch-praxis-binding.md`
- `docs/praxis/ASC-0102-dispatch-praxis-binding.json`
- `docs/AIOS_WORK_DISPATCH.md`
- `scripts/aios_dispatch.py`
- `scripts/aios_work_praxis.py`
- `tests/test_aios_dispatch.py`
- `tests/test_aios_work_praxis.py`
- `docs/AGENT_WORKLOG.md`

forbidden_files:

- `.env`
- raw exports
- private provider auth files
- child repo implementation files
- UI application files

## Praxis Envelope

Required praxis:

- `docs/praxis/ASC-0102-dispatch-praxis-binding.json`

This contract must dogfood its own rule: `send` should require and attach the
praxis envelope because frontmatter sets `praxis_required: true`.

## Responsibilities

### myworld

must_produce:

- `aios_dispatch.py send --praxis <path>` validates `aios.production_praxis.v1`
  envelopes.
- Contracts with `praxis_required: true` cannot be sent without a valid praxis
  envelope.
- Valid praxis envelopes are copied into the dispatch packet under
  `production_praxis`.
- Invalid praxis envelopes hold the dispatch with explicit `praxis_errors`.
- `docs/AIOS_WORK_DISPATCH.md` documents the new flag and stop condition.

## Verification Gate

```bash
cd .
python -m unittest tests/test_aios_dispatch.py tests/test_aios_work_praxis.py
python scripts/aios_work_praxis.py validate docs/praxis/ASC-0102-dispatch-praxis-binding.json --json
python scripts/aios_monitor.py assess --json
```

## Stop Conditions

- `praxis_required_missing`: production contract requires praxis but no praxis
  JSON is supplied.
- `praxis_invalid`: supplied praxis JSON does not validate.
- `specialist_flattening`: praxis assigns all work to one generic agent.
- `capability_route_missing`: packet lacks CapabilityOS route evidence.
- `memory_context_missing`: packet lacks MemoryOS context evidence.
- `genesis_reframe_missing`: packet lacks GenesisOS friction/alternative frame.
- `hive_gate_missing`: packet lacks verification gate.

## Receipts

- Implemented `scripts/aios_dispatch.py send --praxis <path>`.
- Contracts with `praxis_required: true` now hold with
  `praxis_required_missing` when no praxis envelope is supplied.
- Invalid praxis envelopes hold with `praxis_invalid` and explicit
  `praxis_errors`.
- Valid praxis envelopes are attached to dispatch packets under
  `production_praxis`.
- Updated `docs/AIOS_WORK_DISPATCH.md` to document the praxis gate.
- Dogfood packet `.aios/inbox/myworld/asc-0102.myworld.json` contains:
  - MemoryOS refs including `aios://memory/mem_5012d57c2c4acbf6`
  - CapabilityOS routes for memory context, capability recommendation, and
    Hive execution harness
  - GenesisOS frictions and alternative frames
  - Hive verification gate
  - specialist assignment for Codex, Claude, and local LLM
- Verification passed:
  - `python -m unittest tests/test_aios_dispatch.py tests/test_aios_work_praxis.py`
  - `python scripts/aios_work_praxis.py validate docs/praxis/ASC-0102-dispatch-praxis-binding.json --json`
  - `python scripts/aios_monitor.py assess --json`
