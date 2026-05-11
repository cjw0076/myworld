---
contract_id: ASC-0019
slug: monitor-assessment-brain
status: closed
goal: Give the control-plane monitor an assessment layer that maps alerts to owner, severity, and next action.
created: 2026-05-11 23:59 KST
accepted: 2026-05-11 23:59 KST by codex acting operator
closed: 2026-05-11 23:59 KST
supersedes: none
---

# ASC-0019 Monitor Assessment Brain

## Goal

Upgrade the observer from passive signal collection to actionable
control-plane triage.

The monitor should still avoid execution authority, but it should have enough
control-plane ability to interpret what it sees: classify health, severity,
owner, and next action for alerts so the operator loop can decide whether to
release, hold, retry, or escalate.

## Scope

repos:

- `myworld`

allowed_files:

- `scripts/aios_monitor.py`
- `tests/test_aios_monitor.py`
- `docs/AIOS_BUILD_METHOD.md`
- `docs/contracts/ASC-0019-monitor-assessment-brain.md`
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

- **myworld.must_produce**: monitor assessment command, sidecar assessment
  persistence, tests, docs, and closeout evidence.
- **hive_mind.must_produce**: no source change.
- **memoryos.must_produce**: no source change.
- **capabilityos.must_produce**: no source change.
- **operator.must_produce**: keep the assessment layer recommendation-only.

## Design Decision

Add `python scripts/aios_monitor.py assess --json`.

Assessments use a machine-readable schema:

- `health`: `clear`, `watch`, `attention`, or `blocked`;
- `findings[]`: one per monitor alert with `code`, `severity`, `owner`,
  `action`, `reason`, and the original alert;
- `next_actions[]`: deduplicated owner/action recommendations.

The sidecar writes assessments alongside snapshots:

- `.aios/state/monitor_assessments.jsonl`
- `.aios/state/monitor_assessment.latest.json`

## Verification Gate

```bash
cd /home/user/workspaces/jaewon/myworld
python -m py_compile scripts/aios_monitor.py
python -m unittest tests.test_aios_monitor
python scripts/aios_monitor.py assess --json
python scripts/aios_monitor.py run --iterations 1 --interval 1 --quiet
python scripts/aios_monitor.py status --json
```

Expected evidence:

- pending dispatch alerts classify as `blocked` with owner/action;
- clear snapshots classify as `clear` with `continue_observing`;
- sidecar writes assessment latest/log files;
- status exposes latest assessment health.

## Stop Conditions

- `execution_authority_leak`: assessment starts tools, agents, watchers, or
  child repo execution.
- `opaque_recommendation`: assessment omits owner, severity, or action.
- `runtime_state_committed`: `.aios/**` artifacts are added to committed scope.
- `child_repo_edit`: any child repo source is modified.

## Receipts

Closed 2026-05-11 23:59 KST by `codex@myworld` acting operator.

- Added alert assessment rules to `scripts/aios_monitor.py`.
- Added `python scripts/aios_monitor.py assess --json`.
- Sidecar now writes assessment state alongside snapshots:
  - `.aios/state/monitor_assessments.jsonl`
  - `.aios/state/monitor_assessment.latest.json`
- `status --json` exposes latest assessment path, health, and next-action
  count.
- Updated `docs/AIOS_BUILD_METHOD.md` with assessment usage.
- Added tests for pending-dispatch `blocked` assessment, sidecar assessment
  persistence, and status reporting.
- Verification:
  - `python -m py_compile scripts/aios_monitor.py` passed.
  - `python -m unittest tests/test_aios_monitor.py` passed 9/9.
  - `python scripts/aios_monitor.py assess --json` returned `health=clear`
    and `continue_observing`.
  - `python scripts/aios_monitor.py snapshot --json --fail-on-alert` exited
    zero.
- Stop conditions triggered: none.

## Work Packets

### WP-0019-A — Codex@myworld adds monitor assessment layer

- target_agent: codex
- target_repo: myworld
- status: done
- issued: 2026-05-11
- accepted: 2026-05-11 23:59 KST
- closed: 2026-05-11 23:59 KST
- depends_on: ASC-0017
- brief: |
    Add a recommendation-only assessment layer to `scripts/aios_monitor.py`.
    It should classify monitor alerts into health, severity, owner, and next
    action; persist assessments during sidecar runs; and expose latest health
    through `status --json`.
- result: implemented and verified; see Receipts.
