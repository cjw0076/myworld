---
contract_id: ASC-0250
slug: build-runtime-isolation-finish-forward
status: closed
goal: Finish ASC-0249 build/runtime profile isolation from the existing partial Claude changes by adding missing tests, closeout evidence, and a clean handoff to the end-user serving interface work.
created: 2026-06-13T15:07:00+09:00
accepted: 2026-06-13T15:07:00+09:00
closed: 2026-06-13T15:24:00+09:00
human_approved: true
origin: ASC-0249 produced useful partial changes but both Claude runs were manually isolated after long no-output windows and no Claude result packet.
---

# ASC-0250 Build/Runtime Isolation Finish-Forward

## Why Now

AIOS is being built while local AIOS agents are also active on the same
machine. ASC-0249 correctly identified this as a boundary problem and partial
code now exists:

- `scripts/aios_dispatch.py` exposes `runtime_profile=build_control` and a
  local `.aios/runtime_profile.json` profile file.
- `scripts/aios_round_controller.py` can block live child watcher execution
  unless the active profile or an explicit run flag allows it.
- `scripts/aios_monitor.py` can surface a stale lease after a dispatch result
  as a build/runtime isolation risk.

Existing verification passed:

```bash
python3 -m unittest tests.test_aios_dispatch tests.test_aios_child_watcher tests.test_aios_round_controller tests.test_aios_monitor -v
python3 -m py_compile scripts/aios_dispatch.py scripts/aios_round_controller.py scripts/aios_monitor.py
bash -n scripts/aios_child_watcher.sh
git diff --check
```

However, ASC-0249 cannot be closed yet because the partial changes have no
dedicated ASC-0249 tests, no Claude-authored closeout packet, and no final
ledger decision.

This contract delegates the finish-forward to Claude. Codex should verify and
collect, not directly fill in the implementation.

## Scope

repos:

- `myworld`

allowed_existing_dirty:

- `scripts/aios_dispatch.py`
- `scripts/aios_monitor.py`
- `scripts/aios_round_controller.py`

allowed_files:

- `scripts/aios_dispatch.py`
- `scripts/aios_round_controller.py`
- `scripts/aios_child_watcher.sh`
- `scripts/aios_monitor.py`
- `tests/test_aios_dispatch.py`
- `tests/test_aios_round_controller.py`
- `tests/test_aios_child_watcher.py`
- `tests/test_aios_monitor.py`
- `docs/contracts/ASC-0249-build-runtime-isolation-boundary.md`
- `docs/contracts/ASC-0250-build-runtime-isolation-finish-forward.md`
- `docs/AIOS_AGENT_LEDGER.md`
- `docs/AGENT_WORKLOG.md`

forbidden_files:

- `.env`
- `.env.*`
- provider auth files
- private vault contents
- raw provider logs
- private history stores
- child repo implementation files
- `uri/**`
- `CapabilityOS/**`
- `artifacts/**`
- `gemini/**`
- `gemini-cli/**`
- `1.md`

## Required Work For Claude

Finish the existing partial implementation without broadening scope.

Minimum requirements:

1. Preserve the current profile schema unless a test proves a defect:
   - `schema_version=aios.runtime_profile.v1`
   - profiles: `build_control`, `live_agent_runtime`
   - local file: `.aios/runtime_profile.json`
   - default: `build_control`
2. Add dedicated tests proving:
   - default profile is `build_control`;
   - profile file and environment override behavior is deterministic;
   - build-control mode blocks live child execution unless explicitly allowed;
   - live-runtime profile permits child watcher execution path;
   - stale lease after a result packet is reported by monitor;
   - ASC-0248 lease collision tests remain green.
3. Make status output useful but not noisy:
   - `aios_dispatch.py status` shows active profile and live child block state;
   - `aios_round_controller.py status` shows the same profile boundary.
4. Ensure monitor health returns to `watch` after the stale lease is cleared.
5. Write a proper result packet for ASC-0250 with status, changed files,
   profile schema, tests, and remaining gaps.
6. Update `docs/AIOS_AGENT_LEDGER.md` and `docs/AGENT_WORKLOG.md` with a short
   completion entry.

Do not build the end-user serving interface in this contract. The only serving
interface work allowed here is to leave a clear next-step line saying the
product UI must sit outside the operator Control Center.

## Plain-Language Framing

Finish installing the door between two rooms:

- room one: building AIOS;
- room two: AIOS agents doing live work.

The door already exists in partial form. This contract adds the lock test, the
label on the door, and the receipt that says the door was checked.

## Cross-Domain Frame

### Hospital Triage

A hospital can have surgery rooms and training rooms in the same building, but
the same patient chart must show which room a procedure belongs to. ASC-0250
adds that visible room label for AIOS work.

### Railway Signaling

Two trains may use the same station, but a signal must prevent them from
entering the same track segment blindly. ASC-0248 added the track lease;
ASC-0250 verifies the station mode signal.

### Counter Branch

Counter-default option: revert the partial ASC-0249 changes and wait for a
clean rewrite. Rejected for now because the partial implementation already
passes the full focused gate and exposes the exact boundary AIOS needs.

## Assumptions

- Assumption 1: the existing partial changes are useful but incomplete.
- Assumption 2: tests and result packets are required before closeout.
- Assumption 3: end-user serving UI must not reuse the operator Control Center
  as-is.

Negated checks:

- Do not treat a no-output provider run as success.
- Do not leave a stale lease as a clean close.
- Do not mark ASC-0249/ASC-0250 closed without dedicated tests.
- Do not edit child repos or private runtime stores.

## Verification Gate

Claude must run:

```bash
python3 -m unittest tests.test_aios_dispatch tests.test_aios_child_watcher tests.test_aios_round_controller tests.test_aios_monitor -v
python3 -m py_compile scripts/aios_dispatch.py scripts/aios_round_controller.py scripts/aios_monitor.py
bash -n scripts/aios_child_watcher.sh
git diff --check
python3 scripts/aios_dispatch.py status
python3 scripts/aios_round_controller.py status
python3 scripts/aios_monitor.py assess --json
```

Pass criteria:

- Focused tests pass.
- ASC-0249-specific tests exist and fail if the profile boundary regresses.
- `build_control` is the default and live child execution is visibly blocked.
- `live_agent_runtime` or explicit per-run allowance opens the door visibly.
- Stale provider-session evidence is reported by monitor while present and
  clears after the lease is removed.
- No result claims end-user serving readiness.

## AIOS Role Evidence

### MemoryOS

- source_context: ASC-0249 failed/partial result and runtime profile evidence.
- draft_policy: no accepted memory mutation in this slice.

### CapabilityOS

- route: local control-plane profile and monitor primitives first.
- local helper route: `cap_helper_operator_review` classified the partial
  ASC-0249 state as `NEEDS-REVIEW`; `cap_helper_consolidate` was consulted as
  non-authoritative local context.

### GenesisOS

- challenge: boundary work must not become a new way to hide live execution.
- authority: advisory only.

### Hive Mind

- execution_plan: Claude completes tests and closeout; Codex verifies,
  collects, and pushes only when evidence is complete.

## Work Packets

### WP-0250-A — Claude finish-forward

- target_repo: `myworld`
- target_agent: `claude`
- status: closed
- instruction: Work with the existing dirty ASC-0249 changes. Add the missing
  tests and closeout evidence. Do not build the serving UI in this slice.
- result: `.aios/outbox/myworld/asc-0250.myworld.result.json` reported
  `status=passed`; Codex independently verified the gate and collected it.

## Stop Conditions

- `provider_backpressure_no_progress`
- `runtime_profile_test_gap`
- `stale_lease_after_closeout`
- `serving_ui_scope_creep`
- `test_gate_failed`
- `scope_violation`
- `privacy_violation`
