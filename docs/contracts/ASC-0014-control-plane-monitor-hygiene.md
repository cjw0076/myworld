---
contract_id: ASC-0014
slug: control-plane-monitor-hygiene
status: closed
goal: Remove monitor false positives for normal contract closeout and repo-suffixed legacy result dispatch ids.
created: 2026-05-11 23:42 KST
accepted: 2026-05-11 23:42 KST by codex acting operator
closed: 2026-05-11 23:42 KST
supersedes: none
---

# ASC-0014 Control Plane Monitor Hygiene

## Goal

Make `scripts/aios_monitor.py snapshot` distinguish real drift from normal
control-plane lifecycle events.

## Scope

repos:

- `myworld`

allowed_files:

- `scripts/aios_monitor.py`
- `tests/test_aios_monitor.py`
- `docs/contracts/ASC-0014-control-plane-monitor-hygiene.md`
- `docs/contracts/README.md`
- `docs/AIOS_AGENT_LEDGER.md`

forbidden_files:

- `hivemind/**`
- `memoryOS/**`
- `CapabilityOS/**`
- `.aios/**`
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

- **myworld.must_produce**: monitor normalization, regression tests, contract
  closeout, and ledger entry.
- **hive_mind.must_produce**: no source change.
- **memoryos.must_produce**: no source change.
- **capabilityos.must_produce**: no source change.
- **operator.must_produce**: release only if accepted-to-closed contract
  progression and repo-suffixed result ids no longer produce false alerts.

## Verification Gate

```bash
cd /home/user/workspaces/jaewon/myworld
python -m py_compile scripts/aios_monitor.py
python -m unittest tests/test_aios_monitor.py
python scripts/aios_monitor.py snapshot --json
```

Expected evidence:

- unittest includes accepted-to-closed progression and repo-suffixed result id
  regressions;
- `accepted -> closed` does not emit `dispatch_contract_status_stale`;
- `asc-0012.CapabilityOS` is normalized into `asc-0012` for monitor summary;
- `asc-0012` no longer reports `dispatch_results_pending` for CapabilityOS.

## Stop Conditions

- `real_drift_hidden`: proposed-to-closed or regressive status drift is hidden.
- `pending_result_hidden`: a genuinely missing repo result is suppressed.
- `runtime_state_edit_required`: fix depends on editing `.aios/state` history.
- `child_repo_source_edit`: contract edits child repo implementation.

## Receipts

Closed 2026-05-11 23:42 KST by `codex@myworld` acting operator.

- Implemented dispatch id normalization in `scripts/aios_monitor.py`.
- Excluded expected `accepted -> closed` progression from stale status alerts.
- Added tests:
  - accepted-to-closed progression is not stale;
  - repo-suffixed collected dispatch ids normalize to the base dispatch id.
- Verification:
  - `python -m py_compile scripts/aios_monitor.py` passed.
  - `python -m unittest tests/test_aios_monitor.py` passed 4/4.
  - `python scripts/aios_monitor.py snapshot --json` now reports 3 alerts:
    one legacy `ASC-0001 proposed -> closed` stale alert and the two real child
    repo dirty alerts.
- Stop conditions triggered: none.

## Work Packets

### WP-0014-A — Codex@myworld fixes monitor false positives

- target_agent: codex
- target_repo: myworld
- status: done
- issued: 2026-05-11
- accepted: 2026-05-11 23:42 KST
- closed: 2026-05-11 23:42 KST
- depends_on: ASC-0012
- brief: |
    Fix monitor false positives: normalize `asc-0012.CapabilityOS` to
    `asc-0012`, and do not flag normal `accepted -> closed` progression as
    stale.
- result: implemented and verified; see Receipts.
