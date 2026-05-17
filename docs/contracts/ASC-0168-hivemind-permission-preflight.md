---
contract_id: ASC-0168
slug: hivemind-permission-preflight
status: closed
goal: Let Hive Mind consume CapabilityOS constraint-break routes as operator permission preflights before execution.
created: 2026-05-14 13:05 KST
accepted: 2026-05-14 13:05 KST
closed: 2026-05-14 13:12 KST
acceptance_authority: founder delegated continuation under active AIOS evolution goal.
origin: ASC-0167 made CapabilityOS produce high-freedom unblock options, but founder clarified actual execution must belong to Hive Mind.
---

# ASC-0168 Hive Mind Permission Preflight

## Scope

repos:

- `hivemind`
- `myworld`

allowed_files:

- `hivemind/hivemind/permission_preflight.py`
- `hivemind/hivemind/hive.py`
- `hivemind/tests/fixtures/constraint_break_route.json`
- `hivemind/tests/test_permission_preflight.py`
- `hivemind/docs/AGENT_WORKLOG.md`
- `docs/contracts/ASC-0168-hivemind-permission-preflight.md`
- `docs/contracts/README.md`
- `docs/AIOS_AGENT_LEDGER.md`
- `docs/AGENT_WORKLOG.md`

forbidden_files:

- `CapabilityOS/**`
- `memoryOS/**`
- `GenesisOS/**`
- `.env`
- `.env.*`
- provider credentials
- raw private exports
- private chat transcripts

## Requirements

- Add a Hive Mind preflight that accepts a CapabilityOS
  `capabilityos.constraint_break_route.v1` JSON file.
- Output a Hive-owned receipt with `executor=hivemind`.
- Preserve the permission questions as operator checkpoints.
- Do not execute provider commands in this preflight.
- Block/hold if the route asks CapabilityOS to execute tools.

## Verification Gate

```bash
cd hivemind
python -m unittest tests/test_permission_preflight.py
python -m hivemind.hive permission-preflight --route-json tests/fixtures/constraint_break_route.json --json
```

## Stop Conditions

- `capabilityos_execution_requested`
- `permission_questions_missing`
- `hive_executor_missing`
- `verification_gate_failed`

## Work Packet

### WP-0168-A — Hive consumes constraint-break route as permission preflight

- target_agent: codex
- target_repo: hivemind
- status: accepted
- issued: 2026-05-14
- accepted: 2026-05-14
- closed: pending
- brief: |
    Add a non-executing Hive preflight that consumes the CapabilityOS
    constraint-break route, emits operator permission checkpoints, and proves
    Hive Mind remains the executor.
- result: pending

## Result

status: closed

Implemented Hive Mind permission preflight for
`capabilityos.constraint_break_route.v1` routes. The preflight emits
`hivemind.permission_preflight.v1`, preserves CapabilityOS permission
questions as operator checkpoints, fixes `executor=hivemind`, refuses immediate
execution, and blocks if the CapabilityOS route asks CapabilityOS to execute
tools.

Verification:

```bash
cd hivemind
python -m unittest tests/test_permission_preflight.py
python -m hivemind.hive permission-preflight --route-json tests/fixtures/constraint_break_route.json --json
```

Observed result:

- unittest passed 3/3.
- CLI output returned `status=operator_checkpoint_required`,
  `executor=hivemind`, `execution_policy.execute_now=false`,
  `requires_operator_grant=true`, and no stop conditions.
- Child watcher returned `held` for the Hive packet because the implementation
  files were already dirty before the watcher executed; MyWorld collected both
  Hive and MyWorld result packets, and the manual verification gate above is
  the closeout evidence.
- Release wrote MemoryOS draft `mem_030055a087ee7981` through explicit
  founder-delegated authority override.

No CapabilityOS, MemoryOS, GenesisOS, provider credential, `.env`, raw private
export, or private transcript files were modified.
