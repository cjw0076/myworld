---
contract_id: ASC-0052
slug: aios-native-runtime-entrypoint
status: closed
goal: Provide one AIOS-native runtime entrypoint that wraps monitor, readiness, round control, primitive events, and repo-goal intake so Claude/Codex CLIs become replaceable substrates rather than the user-facing loop.
created: 2026-05-12 23:24 KST
accepted: 2026-05-12 23:24 KST by codex acting operator (founder directive)
acceptance_authority: codex@myworld acting operator per founder directive "마지막에 남는 것은 Claude Cli도, Codex Cli도 아닌 ... AIOS만 남는거야"
closed: 2026-05-12 23:44 KST
---

# ASC-0052 AIOS Native Runtime Entrypoint

## Why Now

ASC-0050 extracted Claude/Codex operator primitives into AIOS-owned code. The
next step is to stop making the operator remember which script to call for
monitor, readiness, round controller, primitive events, and repo-goal intake.

This contract creates the first `aios_runtime` surface: a local, deterministic
entrypoint that says "AIOS is running" and advances one bounded control-plane
iteration without naming Claude or Codex as the product interface.

## Required Reading

- `docs/AIOS_DEFINITION.md`
- `docs/AIOS_BUILD_METHOD.md`
- `docs/AIOS_AGENT_SELF_LOOP.md`
- `docs/AIOS_OPERATOR_PLAYBOOK.md`
- `docs/AIOS_PRIMITIVES.md`
- `scripts/aios_round_controller.py`
- `scripts/aios_repo_goal.py`
- `scripts/aios_primitives/events.py`

## Scope

repos:

- `myworld`

allowed_files:

- `scripts/aios_runtime.py`
- `tests/test_aios_runtime.py`
- `docs/AIOS_RUNTIME.md`
- `docs/AIOS_WORK_DISPATCH.md`
- `docs/contracts/ASC-0052-aios-native-runtime-entrypoint.md`
- `docs/contracts/README.md`
- `docs/goals/AIOS-GOAL-0001-make-something-great.md`
- `docs/goals/AIOS-GOAL-0001-evolution.md`
- `docs/AIOS_AGENT_LEDGER.md`

forbidden_files:

- `hivemind/**`
- `memoryOS/**`
- `CapabilityOS/**`
- `uri/**`
- `.aios/state/**`
- `.aios/logs/**`
- `.aios/primitives/**`
- `.env`
- raw export paths

## Responsibilities

- **myworld.must_produce**:
  - `python scripts/aios_runtime.py status --json`: aggregate monitor
    assessment, readiness level, round-controller status, dispatch summary, and
    primitive event count/last event into one JSON object.
  - `python scripts/aios_runtime.py step --json`: run one bounded control-plane
    round and emit an `aios.runtime.step` primitive event with the recommended
    next action.
  - `python scripts/aios_runtime.py run --max-rounds N --interval-seconds N --json`:
    run a bounded foreground loop for repeatable verification without relying
    on chat continuation.
  - `python scripts/aios_runtime.py submit-goal --repo <repo> --kind <kind> --goal <text> --json`:
    submit a repo-originated goal through the existing repo-goal protocol.
  - `docs/AIOS_RUNTIME.md`: explain that this is the AIOS-facing entrypoint,
    while Claude/Codex/provider CLIs are interchangeable substrates behind it.
  - Tests covering JSON shape, subprocess failure capture, primitive event
    emission, bounded loop behavior, and submit-goal delegation.
- **hivemind.must_produce**: no source role in this contract.
- **memoryos.must_produce**: no source role in this contract.
- **capabilityos.must_produce**: no source role in this contract.

## Verification Gate

```bash
python -m py_compile scripts/aios_runtime.py
python -m unittest tests/test_aios_runtime.py
python scripts/aios_runtime.py status --json
python scripts/aios_runtime.py step --json
python scripts/aios_runtime.py run --max-rounds 1 --interval-seconds 0 --json
python -m unittest discover -s tests -p 'test_aios_*.py'
python scripts/aios_monitor.py assess --json
```

Pass criteria:

- `status`, `step`, and bounded `run` return JSON without chat context.
- `step` emits a primitive runtime event.
- The runtime does not execute child repo source edits directly.
- Full myworld tests pass.
- Monitor remains clear after dispatch release.

## Stop Conditions

- `runtime_executes_child_repo_edit`: runtime directly edits child repo source.
- `runtime_unbounded_default`: default command starts an infinite loop.
- `runtime_hides_failed_step`: subprocess failure is omitted from JSON.
- `runtime_bypasses_policy`: runtime sends or releases dispatch without
  existing policy/dispatch scripts.
- `runtime_writes_runtime_state_to_git`: `.aios/**` state is committed.
- `primitive_event_missing`: `step` succeeds without an
  `aios.runtime.step` primitive event.
- `verification_gate_failed`

## Receipts

Closed 2026-05-12 23:44 KST by `codex@myworld`.

- Implemented:
  - `scripts/aios_runtime.py`
  - `tests/test_aios_runtime.py`
  - `docs/AIOS_RUNTIME.md`
- Runtime surface:
  - `status --json` aggregates monitor, readiness, dispatch summary,
    round-controller status, and primitive event summary.
  - `step --json` runs one bounded round and emits `aios.runtime.step`.
  - `run --max-rounds N --interval-seconds N --json` runs a bounded foreground
    loop.
  - `submit-goal --repo <repo> --kind <kind> --goal <text> --json` delegates
    to repo-goal intake.
- Verification:
  - `python -m py_compile scripts/aios_runtime.py` passed.
  - `python -m unittest tests/test_aios_runtime.py` passed 5/5.
  - `python scripts/aios_runtime.py status --json` returned
    `aios.runtime.status.v1`.
  - `python scripts/aios_runtime.py step --json` returned
    `aios.runtime.step.v1` and emitted a primitive event.
  - `python scripts/aios_runtime.py run --max-rounds 1 --interval-seconds 0 --json`
    returned `aios.runtime.run.v1`.
  - `python -m unittest discover -s tests -p 'test_aios_*.py'` passed 125/125.
- Stop conditions triggered: none.

## Work Packets

### WP-0052-A — Codex@myworld builds the AIOS-native runtime entrypoint

- target_agent: codex
- target_repo: myworld
- status: accepted
- closed: 2026-05-12 23:44 KST
- issued: 2026-05-12 23:24 KST
- brief: |
    Implement `scripts/aios_runtime.py`, `tests/test_aios_runtime.py`, and
    `docs/AIOS_RUNTIME.md`. Keep the runtime as an orchestrator over existing
    AIOS scripts and primitive events. Do not replace Hive/MemoryOS/CapabilityOS
    ownership or execute child repo edits directly.
- result: implemented, verified, and ready for dispatch release.
