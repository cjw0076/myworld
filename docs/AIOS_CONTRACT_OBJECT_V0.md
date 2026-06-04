# AIOS ContractObject v0

**Status**: runtime-object spec, not an ASC contract.  
**Purpose**: turn contracts from markdown governance artifacts into executable
AIOS process objects.

## Frame

AIOS should not grow by writing more contracts about itself. It should compile
a user goal into a governed runtime object, use provider CLIs and local tools
inside delegated device authority, finish the task, and learn from the trace.

`ContractObject v0` is the minimum object for that loop.

Schema implementation:

- `scripts/aios_contract_object.py`
- schema version: `aios.contract_object.v0`
- tests: `tests/test_aios_contract_object.py`

## Required Fields

- `schema_version`: fixed `aios.contract_object.v0`
- `contract_id`: runtime id, usually `co-*`
- `goal`: user-visible outcome
- `state`: `proposed`, `accepted`, `running`, `waiting_user`, `verified`,
  `closed`, or `blocked`
- `workspace_root`: root used for relative authority decisions
- `authority_scope`: delegated non-filesystem authority
- `filesystem_scope`: allowed and denied read/write/move/delete paths
- `provider_routes`: provider CLI/local model routes allowed for this object
- `memory_inputs`: memory ids or context refs used before execution
- `capability_route`: chosen tools, forbidden tools, and route reason
- `genesis_challenge`: pre-close or pre-plan challenge question
- `steps`: executable step graph
- `actions`: state transitions and planned-vs-actual notes
- `receipts`: evidence from executed steps
- `evals`: checks required before verification/close
- `user_checkpoints`: checkpoints hit during execution
- `memory_effects`: draft-first writeback targets
- `next_state`: recommended next state

## Authority Model

Device authority is delegated, not blind root access.

Default personal-task posture:

- network off unless explicitly needed
- reads limited to user-approved input roots
- writes limited to user-approved output roots
- denied paths override allowed paths
- deletion disabled in v0
- file mutation requires a user checkpoint
- memory writeback is draft-first

## First Specimen

The first outside-domain specimen is privacy-gated personal file organization:

```bash
python scripts/aios_contract_object.py specimen personal-files \
  --input-root /path/to/input \
  --output-root /path/to/output \
  --deny-path /path/to/input/private
```

This emits a `ContractObject` that does not touch files. It records the intended
process:

1. inventory metadata only
2. local clustering
3. user reviews the organization plan
4. write manifest
5. user approves file mutation
6. apply approved moves, no deletion
7. verify layout
8. user reviews memory writeback

This specimen is the bridge from schema to runtime. The next kernel step is a
runner that executes only authorized steps and records receipts.
