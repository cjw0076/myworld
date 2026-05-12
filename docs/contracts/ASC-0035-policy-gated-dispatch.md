---
contract_id: ASC-0035
slug: policy-gated-dispatch
status: closed
goal: Wire the action policy into dispatch creation and sending so checkpoint-required packets are blocked before inbox delivery.
created: 2026-05-12 15:17 KST
accepted: 2026-05-12 15:17 KST
closed: 2026-05-12 15:24 KST
---

# ASC-0035 Policy-Gated Dispatch

## Why Now

ASC-0034 created a machine-checkable action policy, but dispatch still needed
to enforce it. AIOS cannot be a durable control plane if autonomous rounds can
write packets first and ask policy questions later.

This contract binds dispatch creation and sending to that policy surface.

## Scope

repos:

- `myworld`

allowed_files:

- `docs/AIOS_WORK_DISPATCH.md`
- `scripts/aios_dispatch.py`
- `scripts/aios_loop.py`
- `tests/test_aios_dispatch.py`
- `tests/test_aios_loop.py`
- `docs/contracts/ASC-0035-policy-gated-dispatch.md`
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

## Responsibilities

### myworld.must_produce

- `aios_dispatch.py send` evaluates action policy before writing an inbox
  packet.
- `aios_loop.py once --apply` uses the same policy gate before autonomous
  packet delivery.
- Allowed packets include the evaluated `action_policy` payload.
- Non-allowed decisions append a dispatch event and leave the inbox unchanged.
- Regression tests cover allowed dispatch and checkpoint-required dispatch.
- Dispatch documentation describes the pre-send policy gate.

### child repos

- No source changes. Child repos consume only packets that pass this control
  plane gate.

### operator

- Codex and Claude may act as delegated operators for this myworld-only
  contract because scope is local and verification is test-bound.
- Close only after tests pass, the contract is dogfooded through dispatch, and
  monitor assessment is clear.

## Verification Gate

```bash
python -m py_compile scripts/aios_dispatch.py scripts/aios_loop.py scripts/aios_action_policy.py
python -m unittest tests/test_aios_dispatch.py tests/test_aios_loop.py tests/test_aios_action_policy.py
python -m unittest tests/test_aios_instruction_index.py tests/test_aios_loop_policy.py tests/test_aios_doc_scout.py tests/test_aios_readiness.py tests/test_aios_dispatch.py tests/test_aios_loop.py tests/test_aios_monitor.py tests/test_aios_goal_evolution.py tests/test_aios_child_watcher.py tests/test_aios_round_controller.py tests/test_aios_web_research_receipt.py tests/test_aios_institution_readiness.py tests/test_aios_action_policy.py
python scripts/aios_monitor.py assess --json
```

Pass criteria:

- Accepted local dispatches write packets with `action_policy.decision=allow`.
- Checkpoint-required dispatches record `escalated`, `held`, or `stopped`
  before inbox delivery.
- The autonomous loop and manual dispatch command share the same policy
  decision surface.
- Full myworld tests pass and monitor remains clear.

## Stop Conditions

- `policy_gate_not_called_before_inbox_write`
- `non_allowed_policy_packet_written_to_inbox`
- `manual_send_and_loop_policy_drift`
- `policy_blocks_all_local_dispatch`
- `child_repo_scope_leak`
- `missing_dispatch_event_for_blocked_packet`

## Receipts

- Implementation: `scripts/aios_dispatch.py`, `scripts/aios_loop.py`,
  `tests/test_aios_dispatch.py`, `tests/test_aios_loop.py`, and
  `docs/AIOS_WORK_DISPATCH.md`.
- Initial dogfood false positive: dispatch `asc-0035` escalated with
  `human_checkpoint_required:external_effect` because a verification file path
  contained `web`. The contract treated this as a valid feedback signal and
  tightened dispatch text matching to phrase boundaries.
- Dogfood dispatch:
  `.aios/inbox/myworld/asc-0035-policy-gate-dogfood.myworld.json`.
- Result packet:
  `.aios/outbox/myworld/asc-0035-policy-gate-dogfood.myworld.result.json`.
- Release: `python scripts/aios_dispatch.py release --dispatch-id
  asc-0035-policy-gate-dogfood --reason
  asc_0035_policy_gated_dispatch_verified`.
- Verification:
  - `python -m py_compile scripts/aios_dispatch.py scripts/aios_loop.py scripts/aios_action_policy.py` passed.
  - `python -m unittest tests/test_aios_dispatch.py tests/test_aios_loop.py tests/test_aios_action_policy.py` passed 21/21.
  - Full myworld suite passed 59/59 in the dogfood watcher result.
  - Final `python scripts/aios_monitor.py assess --json` returned
    `health=clear`.

## Work Packets

### WP-0035-A — Codex@myworld implements policy-gated dispatch

- target_agent: codex
- target_repo: myworld
- status: done
- issued: 2026-05-12
- accepted: 2026-05-12
- closed: 2026-05-12
- depends_on: ASC-0034
- brief: |
    Wire `scripts/aios_action_policy.py` into manual dispatch send and the
    autonomous control-plane loop. Keep scope local to myworld. Add regression
    tests and update dispatch documentation. Do not edit child repo source.
- result: `.aios/outbox/myworld/asc-0035-policy-gate-dogfood.myworld.result.json`
