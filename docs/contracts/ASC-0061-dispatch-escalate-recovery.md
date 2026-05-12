---
contract_id: ASC-0061
slug: dispatch-escalate-recovery
status: accepted
goal: When a dispatch is escalated by action policy, allow the operator's `release` to actually deliver the inbox packet so the contract can proceed — instead of the current dead-end where escalated dispatches never write to inbox even after release.
created: 2026-05-13 KST
accepted: 2026-05-13 KST by claude acting operator
closed:
acceptance_authority: claude@myworld (operator) per founder directive.
origin: ASC-0037 incident (2026-05-12 15:47) where operator release of an escalated dispatch did not retry the inbox write — claude had to manually craft the result packet with policy_override evidence.
---

# ASC-0061 Dispatch Escalate Recovery

## Why Now

Current state machine for `aios_dispatch.py send` when policy escalates:
1. send → policy.escalate → no inbox written
2. operator runs `release --reason ...` → state becomes `released`
3. ... but no inbox packet exists, so watcher cannot run, no result
   packet is generated
4. The dispatch is stuck in `released` state without execution

Fix: `release` should, when state was `escalated`, retry the inbox
write with an `operator_override` flag bypassing the policy gate.
The override is recorded in dispatch events for audit. If the second
write also fails (e.g. schema invalid), surface clearly.

## Scope

repos:

- `myworld`

allowed_files:

- `scripts/aios_dispatch.py`
- `tests/test_aios_dispatch.py`
- `docs/AIOS_WORK_DISPATCH.md`
- `docs/contracts/ASC-0061-dispatch-escalate-recovery.md`
- `docs/contracts/README.md`
- `docs/AIOS_AGENT_LEDGER.md`

forbidden_files:

- `hivemind/**`, `memoryOS/**`, `CapabilityOS/**`, `uri/**`
- `.env`

## Per-OS Responsibility

### myworld.must_produce

- `aios_dispatch.py release` updated:
  - If the dispatch's last state was `escalated` AND no inbox packet
    exists, attempt one inbox write with `operator_override=true`
    bypassing the policy gate.
  - Records `dispatch.recovery` event with reason and operator id.
  - If the override write also fails, leaves state `released` and
    surfaces `release_recovery_failed` event for monitor to pick up.
- New regression test: simulate escalate → release → verify inbox
  packet written with override flag.
- Docs: extend `AIOS_WORK_DISPATCH.md` with the recovery semantics.

### child repos

- No source change.

## Verification Gate

```bash
python -m py_compile scripts/aios_dispatch.py
python -m unittest tests/test_aios_dispatch.py
python -m unittest discover -s tests -p 'test_aios_*.py'
python scripts/aios_monitor.py assess --json
```

Pass criteria:

- Escalate→release path produces inbox packet with `operator_override`.
- Override is logged in dispatch events.
- Existing release semantics for non-escalated dispatches unchanged.

## Stop Conditions

- `release_silent_no_op`: release of escalated dispatch must do something.
- `override_without_audit`: override must be recorded.
- `override_bypasses_invariants`: override CANNOT skip schema validation
  or hard-ban path checks — only the policy gate.
- `child_repo_scope_leak`
- `verification_gate_failed`

## Receipts

Pending.

## Work Packets

### WP-0061-A — codex@myworld adds release recovery path

- target_agent: codex
- target_repo: myworld
- status: accepted
- brief: |
    Add the recovery path to release. Audit the override. Test both
    escalate-then-release and normal release paths.
- result: pending
