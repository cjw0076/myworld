---
contract_id: ASC-0017
slug: control-plane-monitor-sidecar
status: closed
goal: Keep the MyWorld control-plane observer available as a long-running sidecar.
created: 2026-05-11 23:56 KST
accepted: 2026-05-11 23:56 KST by codex acting operator
closed: 2026-05-11 23:57 KST
supersedes: none
---

# ASC-0017 Control-Plane Monitor Sidecar

## Goal

Make the observer role a first-class control-plane sidecar so it can stay on
while other AIOS loops work.

The observer must continuously watch contracts, dispatch state, child repo
dirty state, generated cache leakage, pending result packets, and reconciled
monitor drift. It must not execute child repo work or mutate runtime dispatch
history.

## Scope

repos:

- `myworld`

allowed_files:

- `scripts/aios_monitor.py`
- `tests/test_aios_monitor.py`
- `docs/AIOS_BUILD_METHOD.md`
- `docs/contracts/ASC-0017-control-plane-monitor-sidecar.md`
- `docs/contracts/README.md`
- `docs/AIOS_AGENT_LEDGER.md`

forbidden_files:

- `.aios/**`
- `hivemind/**`
- `memoryOS/**`
- `CapabilityOS/**`
- `.runs/**`
- `.ai-runs/**`
- `data/**`
- `raw_exports/**`
- `exports/**`
- `logs/**`
- `weights/**`
- `**/*secret*`
- `**/*credential*`
- `.env`
- `.env.*`

## Per-OS Responsibility

- **myworld.must_produce**: sidecar monitor commands, runtime PID/status/stop
  surfaces, durable local snapshots, tests, and documentation.
- **hive_mind.must_produce**: no source change.
- **memoryos.must_produce**: no source change.
- **capabilityos.must_produce**: no source change.
- **operator.must_produce**: accept the sidecar as observer-only automation.

## Design Decision

Add `run`, `start`, `stop`, and `status` subcommands to
`scripts/aios_monitor.py`.

The sidecar writes:

- `.aios/state/monitor.jsonl`
- `.aios/state/monitor.latest.json`
- `.aios/state/monitor_events.jsonl`
- `.aios/run/aios_monitor.pid`
- `.aios/run/aios_monitor.stop`

The sidecar is independent from `aios_pingpong.sh` and should continue to be
available after `.aios/NORTHSTAR_READY`. It is observation-only.

## Verification Gate

```bash
cd /home/user/workspaces/jaewon/myworld
python -m py_compile scripts/aios_monitor.py
python -m unittest tests.test_aios_monitor
python scripts/aios_monitor.py run --iterations 1 --interval 1 --quiet
python scripts/aios_monitor.py status --json
```

Expected evidence:

- bounded sidecar run exits zero;
- monitor log, latest snapshot, and monitor event files are written under
  `.aios/state/`;
- `status --json` reports the latest snapshot and running state;
- no child repo files are modified.

## Stop Conditions

- `observer_mutates_state`: sidecar edits contracts, dispatch history, or child
  repo source.
- `execution_leak`: sidecar starts child watchers or provider agents.
- `no_stop_surface`: sidecar lacks PID/status/stop control.
- `runtime_state_committed`: `.aios/**` artifacts are added to committed scope.

## Receipts

Closed 2026-05-11 23:57 KST by `codex@myworld` acting operator.

- Added monitor sidecar commands to `scripts/aios_monitor.py`:
  - `run --iterations N --interval S`
  - `start --interval S`
  - `stop`
  - `status --json`
- Sidecar writes local-only observer state:
  - `.aios/state/monitor.jsonl`
  - `.aios/state/monitor.latest.json`
  - `.aios/state/monitor_events.jsonl`
  - `.aios/run/aios_monitor.pid`
  - `.aios/run/aios_monitor.stop`
- Documented the sidecar in `docs/AIOS_BUILD_METHOD.md`.
- Added tests for bounded sidecar runs and status snapshots.
- Verification:
  - `python -m py_compile scripts/aios_monitor.py` passed.
  - `python -m unittest tests/test_aios_monitor.py` passed 8/8.
  - `python scripts/aios_monitor.py run --iterations 1 --interval 1 --quiet`
    exited zero.
  - `python scripts/aios_monitor.py status --json` exited zero and reported no
    running sidecar after the bounded run.
  - `python scripts/aios_monitor.py snapshot --json --fail-on-alert` exited
    zero.
- Stop conditions triggered: none.

## Work Packets

### WP-0017-A — Codex@myworld adds monitor sidecar

- target_agent: codex
- target_repo: myworld
- status: done
- issued: 2026-05-11
- accepted: 2026-05-11 23:56 KST
- closed: 2026-05-11 23:57 KST
- depends_on: ASC-0014, ASC-0015, ASC-0016
- brief: |
    Add a long-running observer sidecar to `scripts/aios_monitor.py` with
    foreground bounded runs, background start, stop, status, PID file, latest
    snapshot, and event log. Keep it observer-only.
- result: implemented and verified; see Receipts.
