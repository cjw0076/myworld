---
contract_id: ASC-0016
slug: monitor-reconciliation-registry
status: closed
goal: Add an audited monitor reconciliation registry for known legacy dispatch-history drift.
created: 2026-05-11 23:51 KST
accepted: 2026-05-11 23:51 KST by codex acting operator
closed: 2026-05-11 23:52 KST
supersedes: none
---

# ASC-0016 Monitor Reconciliation Registry

## Goal

Clear the final known monitor alert without mutating append-only runtime
dispatch history or hiding future drift.

After ASC-0014 and ASC-0015, `python scripts/aios_monitor.py snapshot --json`
has one remaining alert:

```json
{
  "code": "dispatch_contract_status_stale",
  "dispatch_id": "asc-0001",
  "recorded": "proposed",
  "current": "closed",
  "contract_path": "docs/contracts/ASC-0001-memoryos-hivemind-loop.md"
}
```

This is a legacy bootstrap artifact: ASC-0001 was dispatched while still
`proposed`, then accepted and closed through later evidence. The closeout is
valid, but the historical `created` event remains append-only local runtime
state.

## Scope

repos:

- `myworld`

allowed_files:

- `scripts/aios_monitor.py`
- `tests/test_aios_monitor.py`
- `docs/AIOS_MONITOR_RECONCILIATIONS.json`
- `docs/contracts/ASC-0016-monitor-reconciliation-registry.md`
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

- **myworld.must_produce**: a committed reconciliation registry, monitor
  support for exact alert fingerprint reconciliation, regression tests, and
  closeout evidence.
- **hive_mind.must_produce**: no source change.
- **memoryos.must_produce**: no source change.
- **capabilityos.must_produce**: no source change.
- **operator.must_produce**: approve only exact-match reconciliation for the
  ASC-0001 legacy bootstrap drift.

## Design Decision

Do not edit `.aios/state/dispatches.jsonl`. It is local append-only evidence.
Instead, add `docs/AIOS_MONITOR_RECONCILIATIONS.json`, a committed audit file
whose entries contain:

- an exact `match` object for alert fields;
- reason and operator metadata;
- optional notes linking the contract that authorized reconciliation.

The monitor may suppress only alerts whose fields match the registry exactly.
It must report applied reconciliations in the snapshot payload so the zero-alert
state remains auditable.

## Verification Gate

```bash
cd /home/user/workspaces/jaewon/myworld
python -m py_compile scripts/aios_monitor.py
python -m unittest tests/test_aios_monitor.py
python scripts/aios_monitor.py snapshot --json --fail-on-alert
```

Expected evidence:

- stale drift still alerts when there is no reconciliation registry;
- exact ASC-0001 legacy drift is removed when the registry matches;
- non-matching drift is not hidden;
- snapshot includes `reconciliations_applied`;
- current workspace monitor exits zero with `--fail-on-alert`.

## Stop Conditions

- `runtime_history_mutation`: implementation edits `.aios/state/dispatches.jsonl`.
- `broad_suppression`: reconciliation hides alerts by code only, wildcard, or
  partial dispatch id.
- `future_drift_hidden`: proposed-to-closed drift for a different dispatch is
  hidden without an exact registry entry.
- `child_repo_edit`: any child repo source change is required.

## Receipts

Closed 2026-05-11 23:52 KST by `codex@myworld` acting operator.

- Added `docs/AIOS_MONITOR_RECONCILIATIONS.json` with one exact-match entry
  for the ASC-0001 bootstrap `proposed -> closed` dispatch drift.
- Updated `scripts/aios_monitor.py` to load the committed registry, suppress
  only exact alert fingerprints, and report applied entries under
  `reconciliations_applied`.
- Added regression tests proving:
  - stale drift still alerts without a registry;
  - exact registry matches are applied;
  - partial or different dispatch matches do not hide drift.
- Verification:
  - `python -m py_compile scripts/aios_monitor.py` passed.
  - `python -m unittest tests/test_aios_monitor.py` passed as part of the
    monitor suite; reconciliation-specific tests cover exact and non-matching
    registry behavior.
  - `python -m json.tool docs/AIOS_MONITOR_RECONCILIATIONS.json >/dev/null`
    passed.
  - `python scripts/aios_monitor.py snapshot --json --fail-on-alert` exited
    zero with `alerts=[]` and one `reconciliations_applied` entry.
- Stop conditions triggered: none.

## Work Packets

### WP-0016-A — Codex@myworld adds audited monitor reconciliation

- target_agent: codex
- target_repo: myworld
- status: done
- issued: 2026-05-11
- accepted: 2026-05-11 23:51 KST
- closed: 2026-05-11 23:52 KST
- depends_on: ASC-0014, ASC-0015
- brief: |
    Add exact-match monitor reconciliation for the single known ASC-0001
    bootstrap stale dispatch alert. Do not edit `.aios/state`. Add tests that
    prove unmatched stale alerts still fire.
- result: implemented and verified; see Receipts.
