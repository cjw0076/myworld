---
contract_id: ASC-0167
slug: capabilityos-permissioned-constraint-break-route
status: closed
goal: Add a CapabilityOS route that proposes high-freedom constraint-breaking options, asks the user for permission, and assigns actual execution to Hive Mind.
created: 2026-05-14 13:00 KST
accepted: 2026-05-14 13:00 KST
closed: 2026-05-14 13:03 KST
acceptance_authority: founder delegated continuation under active AIOS evolution goal.
origin: Founder clarified that Hive Mind should be the actual executor while GenesisOS and CapabilityOS should freely loosen provider/CLI constraints, surface unblock options, and ask the user what is allowed.
---

# ASC-0167 CapabilityOS Permissioned Constraint-Break Route

## Plain Language

When AIOS gets blocked by provider rules, missing tools, limited permissions,
network access, or normal agent habits, CapabilityOS should not just say
"blocked." It should propose bounded ways to loosen the constraint and ask the
user what is allowed. Hive Mind remains the executor.

## Scope

repos:

- `CapabilityOS`
- `myworld`

allowed_files:

- `CapabilityOS/capabilityos/catalog.py`
- `CapabilityOS/capabilityos/cli.py`
- `CapabilityOS/tests/test_cli.py`
- `CapabilityOS/docs/AGENT_WORKLOG.md`
- `docs/contracts/ASC-0167-capabilityos-permissioned-constraint-break-route.md`
- `docs/contracts/README.md`
- `docs/AIOS_AGENT_LEDGER.md`
- `docs/AGENT_WORKLOG.md`

forbidden_files:

- `hivemind/**`
- `memoryOS/**`
- `GenesisOS/**`
- `.env`
- `.env.*`
- provider credentials
- raw private exports
- private chat transcripts

## Requirements

- Add a recommendation-only CapabilityOS CLI route, e.g.
  `python -m capabilityos.cli constraint-break --task ... --blocker ... --json`.
- The route must set executor to `hivemind`.
- The route must not execute tools, install dependencies, call web/network, or
  mutate external systems.
- The route must produce:
  - high-freedom unblock options,
  - permission questions for the user,
  - risk notes,
  - stop conditions,
  - explicit no-secret-storage policy.
- Tests must prove that user permission is requested before risky actions.

## Verification Gate

```bash
cd CapabilityOS
python -m unittest tests/test_cli.py
python -m capabilityos.cli constraint-break --task "AIOS provider is blocked by CLI rules" --blocker "provider PIN gate" --json
```

Pass criteria:

- Output contract is `capabilityos.constraint_break_route.v1`.
- `execution_policy.executor` is `hivemind`.
- `capabilityos_executes_tools` is false.
- Permission questions are non-empty and include user-granted allowances.
- No secret or PIN value appears in the contract, docs, tests, or output.

## Stop Conditions

- `capabilityos_executes_instead_of_hive`
- `permission_question_missing`
- `secret_written_to_repo`
- `unsafe_unbounded_action`
- `verification_gate_failed`

## Work Packet

### WP-0167-A — CapabilityOS constraint-break route

- target_agent: codex
- target_repo: CapabilityOS
- status: closed
- issued: 2026-05-14
- accepted: 2026-05-14
- closed: 2026-05-14 13:03 KST
- brief: |
    Implement a recommendation-only route that helps AIOS escape provider/tool
    constraints by proposing high-freedom unblock options and asking the user
    for permission. Do not execute. Hive Mind is the executor.
- result: passed. CapabilityOS now exposes
    `capabilityos.constraint_break_route.v1` through
    `python -m capabilityos.cli constraint-break --task ... --blocker ...
    --json`.

## Receipts

- verification:
  - `cd CapabilityOS && python -m unittest tests/test_cli.py` passed 14/14.
  - `cd CapabilityOS && python -m capabilityos.cli constraint-break --task
    "AIOS provider is blocked by CLI rules" --blocker "provider PIN gate"
    --json` emitted `contract=capabilityos.constraint_break_route.v1`,
    `execution_policy.executor=hivemind`,
    `capabilityos_executes_tools=false`, non-empty permission questions, and
    `privacy_policy.do_not_store` containing `pins`, `tokens`, and `api_keys`.
