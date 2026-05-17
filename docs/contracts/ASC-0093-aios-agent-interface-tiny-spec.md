---
contract_id: ASC-0093
slug: aios-agent-interface-tiny-spec
status: closed
goal: Supersede held ASC-0088 with the Hive-selected B1 path: a tiny substrate-neutral AIOS Agent Interface spec in one markdown file, without buffer/sync infrastructure.
created: 2026-05-13 KST
proposed_by: codex@myworld
accepted: 2026-05-13 KST by codex acting founder-delegated AIOS operator
closed: 2026-05-13 KST by codex@myworld
acceptance_authority: founder delegated Codex to act as AIOS founder/operator and keep developing AIOS through AIOS contracts.
origin: ASC-0089 Hive debate unanimously selected `pick_B1` and rejected ASC-0088's B5 full spec + buffer/sync direction.
supersedes: ASC-0088 if accepted
depends_on:
  - ASC-0089
---

# ASC-0093 AIOS Agent Interface Tiny Spec

## Why Now

ASC-0088 is held because its B5 design tries to introduce a full standalone
spec plus observation buffer and sync infrastructure before AIOS has proven the
minimal protocol. ASC-0089 ran a five-round Hive deliberation and selected B1:
define the protocol first, in one small substrate-neutral markdown file.

This contract implements only Layer 0 from ASC-0089:

```text
Layer 0: protocol definition
Layer 1: prompt/template delivery later
Layer 2: validator/library later
Layer 3: buffer/sync infrastructure only if scale demands
```

## Scope

repos:

- `myworld`

allowed_files:

- `docs/AIOS_AGENT_INTERFACE.md`
- `tests/test_aios_agent_interface_spec.py`
- `docs/contracts/ASC-0093-aios-agent-interface-tiny-spec.md`
- `docs/contracts/ASC-0088-aios-universal-agent-interface.md`
- `docs/contracts/README.md`
- `docs/AIOS_AGENT_LEDGER.md`

forbidden_files:

- `scripts/aios_observation_buffer.py`
- `scripts/aios_observation_sync.py`
- `tests/test_aios_observation_buffer.py`
- `tests/test_aios_observation_sync.py`
- `hivemind/**`, `memoryOS/**`, `CapabilityOS/**`, `GenesisOS/**`, `uri/**`
- `_from_desktop/**`, `dain/**`, `minyoung/**`
- `.env`, `.env.*`

## Per-OS Responsibility

### myworld.must_produce

- `docs/AIOS_AGENT_INTERFACE.md`, target 50-80 lines and hard cap 100 lines.
- Embedded YAML schema block with:
  - `spec_version`
  - `agent_id`
  - `substrate`
  - `observed_at`
  - `context`
  - `event_type`
  - `summary`
  - `evidence_refs`
  - `privacy_class`
  - `recommended_route`
- Canonical observation path rule:
  - if `AIOS_ROOT` is known: `$AIOS_ROOT/.aios/observation_buffer/<agent_id>/`
  - if offline: `~/.aios/observation_buffer/<agent_id>/`
- Field semantics with one compact example.
- Evidence reference taxonomy: `contract`, `dispatch_result`, `run_artifact`,
  `source_file`, `external_source`, `operator_turn`.
- Known limitations: no sync daemon, no delivery templates, no validator
  guarantee, retention policy unresolved.
- `tests/test_aios_agent_interface_spec.py` checking line cap, required schema
  fields, known limitations, and absence of buffer/sync implementation claims.

### child repos

- No source change.

## Verification Gate

```bash
python -m unittest tests/test_aios_agent_interface_spec.py
python -m unittest discover -s tests -p 'test_aios_*.py'
python scripts/aios_monitor.py assess --json
```

Pass criteria:

- Tiny spec exists and is under 100 lines.
- All DR-1 through DR-7 from ASC-0089 are represented.
- No buffer/sync script or test is created.
- ASC-0088 status is changed only after this contract is accepted and
  implemented.

## Stop Conditions

- `b5_scope_creep`: buffer/sync infrastructure appears in implementation.
- `spec_exceeds_cap`: spec exceeds 100 lines.
- `schema_missing_required_field`
- `known_limitations_missing`
- `asc0088_modified_before_acceptance`
- `verification_gate_failed`

## Receipts

- implementation: `docs/AIOS_AGENT_INTERFACE.md` and
  `tests/test_aios_agent_interface_spec.py`.
- superseded: `docs/contracts/ASC-0088-aios-universal-agent-interface.md`
  now points to ASC-0093.
- dispatch receipt: `.aios/outbox/myworld/asc-0093.myworld.result.json`
  with `status=passed`.
- verification:
  - `python -m unittest tests/test_aios_agent_interface_spec.py` passed 4/4.
  - `python -m unittest discover -s tests -p 'test_aios_*.py'` passed 189/189.
  - `python scripts/aios_dispatch.py collect --repo myworld` collected the
    result packet.
  - `python scripts/aios_monitor.py assess --json` returned `health=clear`
    after collection.

## Work Packets

### WP-0093-A - codex@myworld implements tiny spec

- target_agent: codex
- target_repo: myworld
- status: done
- closed: 2026-05-13 KST
- depends_on: ASC-0089
- brief: |
    Implement the B1 tiny AIOS Agent Interface spec selected by ASC-0089.
    Do not add observation buffer/sync infrastructure. Add a focused test that
    enforces the line cap, required schema fields, known limitations, and no
    B5 infrastructure claims. After passing verification, mark ASC-0088
    superseded and close this contract.
- result: `.aios/outbox/myworld/asc-0093.myworld.result.json`
