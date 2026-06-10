---
contract_id: ASC-0040
slug: on-prem-evolving-application
status: closed
goal: Package the local AIOS control app, snapshot refresh, monitor write, static server, and round-controller status into one repeatable local command.
created: 2026-05-12 18:30 KST
accepted: 2026-05-12 18:30 KST by codex acting operator
closed: 2026-05-12 18:35 KST
---

# ASC-0040 On-Prem Evolving Application

## Why Now

ASC-0039 created a local visual control surface. The next step is making it
feel like an on-premises application instead of a pile of commands. This
contract packages refresh, monitor, static serving, and loop status behind one
local command while preserving myworld's control-plane boundary.

## AIOS Inputs Used

- MemoryOS context build:
  `trace_id=rtrace_02e5c1e5e56a02d5`, selected accepted memory
  `mem_90b5cfe6570e6ee2`.
- CapabilityOS route:
  `cap_capabilityos_recommendation`, `cap_hivemind_execution_harness`,
  `cap_memoryos_import_run`, and `cap_memoryos_context_build` were the
  local-first recommendation-only routes.
- Hive Mind dry-run:
  `run_20260512_182859_370b96`, `route_source=heuristic_fast`, prepared
  planner/reviewer artifacts.

## Scope

repos:

- `myworld`

allowed_files:

- `scripts/aios_local_app.py`
- `tests/test_aios_local_app.py`
- `docs/AIOS_CONTROL_APP.md`
- `docs/AIOS_WORK_DISPATCH.md`
- `docs/contracts/ASC-0040-on-prem-evolving-application.md`
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
- `.aios/state/**`
- `.env`
- unreviewed source-dump paths

## Responsibilities

### myworld.must_produce

- `scripts/aios_local_app.py` with:
  - `refresh`: write monitor assessment and control app snapshot.
  - `start`: start a local static server for `apps/control/`.
  - `stop`: stop that server.
  - `status`: report server, control snapshot, monitor, and round-controller
    state.
  - `up`: refresh, start server, and report the local URL.
- Tests for refresh/status/start/stop behavior using temporary roots.
- Documentation showing how to run the local on-prem control app.

### child repos

- No source role in this contract. They remain existing local repos observed by
  myworld.

## Verification Gate

```bash
python -m py_compile scripts/aios_local_app.py scripts/aios_control_snapshot.py
python -m unittest tests/test_aios_local_app.py tests/test_aios_control_snapshot.py
python scripts/aios_local_app.py refresh --json
python scripts/aios_local_app.py status --json
python -m unittest discover -s tests -p 'test_aios_*.py'
python scripts/aios_monitor.py assess --json
```

Pass criteria:

- One command can refresh the monitor and control snapshot.
- One command can start and stop the local static control server.
- `status --json` includes URL, PID/running state, snapshot path, monitor
  health, and round-controller state.
- No child repo source changes.
- Full tests pass and monitor remains clear.

## Stop Conditions

- `child_repo_source_edit`
- `runtime_state_committed`
- `server_orphaned`
- `snapshot_refresh_failed`
- `monitor_not_clear`
- `verification_gate_failed`

## Receipts

- implementation:
  - `scripts/aios_local_app.py` adds `refresh`, `start`, `stop`, `status`, and
    `up`.
  - `tests/test_aios_local_app.py` covers refresh and local server lifecycle.
  - `docs/AIOS_CONTROL_APP.md` documents the on-prem local app commands.
  - `docs/AIOS_WORK_DISPATCH.md` records the local control application entry
    point.
- dispatch evidence:
  - `asc-0040` sent to `myworld`, watched, collected, and released with reason
    `asc_0040_on_prem_local_app_verified`.
  - result packet:
    `.aios/outbox/myworld/asc-0040.myworld.result.json`.
- verification:
  - `python -m py_compile scripts/aios_local_app.py scripts/aios_control_snapshot.py`
    passed.
  - `python -m unittest tests/test_aios_local_app.py tests/test_aios_control_snapshot.py`
    passed.
  - `python scripts/aios_local_app.py refresh --json` refreshed monitor and
    control snapshot.
  - `python scripts/aios_local_app.py status --json` reported monitor clear,
    round controller running, and server status.
  - full myworld suite passed 74/74.
  - `python scripts/aios_monitor.py assess --write --json` returned
    `health=clear`.
  - local control server started on `http://127.0.0.1:8765/`.
- learned:
  - ASC-0040 briefly made monitor report pending results while the contract was
    active. Watch/collect/release returned monitor health to clear.

## Work Packets

### WP-0040-A — Codex@myworld packages the local control app

- target_agent: codex
- target_repo: myworld
- status: done
- issued: 2026-05-12
- accepted: 2026-05-12
- closed: 2026-05-12
- depends_on: ASC-0039
- brief: |
    Add `scripts/aios_local_app.py`, tests, and docs so the AIOS control app
    can be refreshed, served, stopped, and inspected through one local command.
    Do not edit child repo source or commit `.aios` runtime state.
- result: `.aios/outbox/myworld/asc-0040.myworld.result.json`;
  `scripts/aios_local_app.py`; local control server running at
  `http://127.0.0.1:8765/`; full tests passed 74/74; monitor clear.
