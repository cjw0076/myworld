---
contract_id: ASC-0039
slug: visual-control-application
status: closed
goal: Create the first local visualization-first AIOS control surface from generated myworld state snapshots.
created: 2026-05-12 18:13 KST
accepted: 2026-05-12 18:13 KST by codex acting operator
closed: 2026-05-12 18:24 KST
---

# ASC-0039 Visual Control Application

## Why Now

ASC-0038 made lower repos able to submit goals and friction to myworld. The
next operator bottleneck is perception: the control plane has contracts,
dispatches, repo loops, MemoryOS traces, CapabilityOS routes, Hive runs, stop
conditions, and learning records, but they are spread across files and CLI
outputs.

This contract creates the first local visual control surface. It is deliberately
small: a static app plus a snapshot generator. It does not yet create the final
packaged on-prem product.

## AIOS Inputs Used

- MemoryOS context build:
  `trace_id=rtrace_c0619c4194e7535b`, selected accepted memory
  `mem_90b5cfe6570e6ee2`.
- CapabilityOS route:
  `cap_capabilityos_recommendation`, `cap_memoryos_context_build`,
  `cap_hivemind_execution_harness`, and `cap_memoryos_import_run` were the
  local-first recommendation-only routes.
- Hive Mind dry-run:
  `run_20260512_181228_aef902`, `route_source=heuristic_fast`, prepared
  planner/executor/reviewer artifacts.

## Scope

repos:

- `myworld`

allowed_files:

- `apps/control/index.html`
- `apps/control/styles.css`
- `apps/control/app.js`
- `apps/control/aios-control-data.js`
- `scripts/aios_control_snapshot.py`
- `tests/test_aios_control_snapshot.py`
- `docs/AIOS_CONTROL_APP.md`
- `docs/contracts/ASC-0039-visual-control-application.md`
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

- `scripts/aios_control_snapshot.py` that reads current control-plane files
  and emits `aios.control_snapshot.v1`.
- `apps/control/` static app that can be opened locally and renders:
  - active goal and goal-evolution recommendation;
  - contract status counts and latest contracts;
  - dispatch status counts and latest dispatches;
  - repo loop health for hivemind, memoryOS, and CapabilityOS;
  - latest MemoryOS trace, CapabilityOS route IDs, and Hive run ID when present;
  - stop-condition and learning/next-action lanes.
- `docs/AIOS_CONTROL_APP.md` documenting snapshot refresh and local opening.
- tests covering snapshot shape and generated data file.

### child repos

- No role in this contract. They remain data sources through existing
  contracts, result packets, and repo status only.

## Verification Gate

```bash
python -m py_compile scripts/aios_control_snapshot.py
python -m unittest tests/test_aios_control_snapshot.py
python scripts/aios_control_snapshot.py --write-json apps/control/aios-control-snapshot.json --write-js apps/control/aios-control-data.js --json
python scripts/aios_control_snapshot.py --check-app-js apps/control/app.js --json
python -m unittest discover -s tests -p 'test_aios_*.py'
python scripts/aios_monitor.py assess --json
```

Pass criteria:

- Snapshot JSON includes goals, contracts, dispatches, repos, AIOS inputs,
  stop lanes, and next actions.
- Static app reads `window.AIOS_CONTROL_SNAPSHOT` and renders without a build
  step.
- UI files stay local and dependency-free.
- Full tests pass and monitor remains clear.

## Stop Conditions

- `snapshot_reads_logs`: snapshot reads `.aios/logs` bodies.
- `child_repo_source_edit`: implementation changes child repo source.
- `runtime_state_committed`: `.aios/state` files are staged.
- `dependency_sprawl`: contract adds a framework or package manager before the
  static surface proves useful.
- `verification_gate_failed`

## Receipts

- implementation:
  - `scripts/aios_control_snapshot.py` emits `aios.control_snapshot.v1` and
    writes JSON plus browser-readable JS data.
  - `apps/control/index.html`, `apps/control/styles.css`, and
    `apps/control/app.js` render the local control surface without a build
    step.
  - `apps/control/aios-control-snapshot.json` and
    `apps/control/aios-control-data.js` contain the refreshed local snapshot.
  - `docs/AIOS_CONTROL_APP.md` documents refresh and open commands.
- dispatch evidence:
  - `asc-0039` sent to `myworld`, watched, collected, and released with reason
    `asc_0039_visual_control_application_verified`.
  - result packet:
    `.aios/outbox/myworld/asc-0039.myworld.result.json`.
- verification:
  - `python -m py_compile scripts/aios_control_snapshot.py` passed.
  - `python -m unittest tests/test_aios_control_snapshot.py` passed 3/3.
  - `python scripts/aios_control_snapshot.py --check-app-js apps/control/app.js --json`
    returned `ok=true`.
  - `python -m unittest discover -s tests -p 'test_aios_*.py'` passed 72/72.
  - `python scripts/aios_monitor.py assess --write --json` returned
    `health=clear`.
- learned:
  - The dispatch watcher allows Python verification commands, not direct
    `node`. JS validation now runs through `scripts/aios_control_snapshot.py`
    so the control-plane watcher remains the verification entry point.

## Work Packets

### WP-0039-A — Codex@myworld builds static visual control surface

- target_agent: codex
- target_repo: myworld
- status: done
- issued: 2026-05-12
- accepted: 2026-05-12
- closed: 2026-05-12
- depends_on: ASC-0038
- brief: |
    Build a dependency-free local control app in `apps/control/` plus
    `scripts/aios_control_snapshot.py` and focused tests. Use existing
    myworld state as read-only input. Do not edit child repo source.
- result: `.aios/outbox/myworld/asc-0039.myworld.result.json`;
  `apps/control/index.html`; `scripts/aios_control_snapshot.py`; full tests
  passed 72/72; monitor clear.
