---
contract_id: ASC-0059
slug: watcher-race-resolution
status: closed
goal: Eliminate the watcher race between aios_child_watcher.sh's codex exec and any concurrently-running interactive codex sessions, so partial work in child repos doesn't leave orphan dirty state.
created: 2026-05-13 KST
accepted: 2026-05-13 KST by claude acting operator
closed: 2026-05-13 KST by codex@myworld
acceptance_authority: claude@myworld (operator) per founder directive.
origin: ASC-0036 deadlock incident (2026-05-12 15:43) where watcher's codex exec auth-failed in Korean while interactive codex sessions completed the work but left it uncommitted, causing repo_dirty deadlock.
---

# ASC-0059 Watcher Race Resolution

## Why Now

During ASC-0036, three child fan-out dispatches failed at the watcher
level (Korean codex CLI auth denial, fixed in ASC-0037). But the
interactive codex sessions in other ptys completed the actual work
in working trees — without committing — leaving repo_dirty findings
that deadlocked the round controller until claude operator manually
committed each child.

Two fixes needed:

1. Watcher must detect existing dirty work before spawning a new
   agent (avoid duplicate work).
2. After agent attempt (success or fail), watcher must check if the
   work was actually completed in working tree and either commit it
   or surface as an explicit `pending_commit` finding.

## Scope

repos:

- `myworld`

allowed_files:

- `scripts/aios_child_watcher.sh`
- `scripts/aios_monitor.py`
- `tests/test_aios_child_watcher.py`
- `tests/test_aios_monitor.py`
- `docs/AIOS_WORK_DISPATCH.md`
- `docs/contracts/ASC-0059-watcher-race-resolution.md`
- `docs/contracts/README.md`
- `docs/AIOS_AGENT_LEDGER.md`

forbidden_files:

- `hivemind/**`, `memoryOS/**`, `CapabilityOS/**`, `uri/**`
- `.env`

## Per-OS Responsibility

### myworld.must_produce

- `aios_child_watcher.sh` adds:
  - **pre-spawn check**: if target repo has uncommitted changes that
    look like related work-in-progress (matching packet's allowed_files),
    log `pending_concurrent_work` event and skip spawn.
  - **post-attempt check**: after agent exits (success or fail), check
    if working tree changed. If yes AND result packet is `failed` →
    add `orphan_work_detected` to result with file list. Operator can
    then commit-as-codex (per ASC-0036 resolution pattern).
- `aios_monitor.py` adds new finding `orphan_dirty_post_failure`:
  fires when result packet shows `orphan_work_detected: true` and
  child repo is still dirty. Severity: high. Action:
  `commit_orphan_work_or_reset`.
- Tests: simulate the race, assert detection + finding.

### child repos

- No source change. Better detection of their state, no modification.

## Verification Gate

```bash
python -m unittest tests/test_aios_child_watcher.py tests/test_aios_monitor.py
python scripts/aios_monitor.py assess --json
python -m unittest discover -s tests -p 'test_aios_*.py'
```

Pass criteria:

- Synthetic race test passes both detection paths.
- Monitor finding present and routes to operator.
- No regression on existing watcher tests.

## Stop Conditions

- `watcher_auto_commits_child`: watcher must NOT auto-commit child repo
  source — only flag for operator.
- `watcher_resets_child_work`: watcher must not destroy in-progress work.
- `false_positive_pending_concurrent_work`: blocks legitimate work too aggressively.
- `child_repo_scope_leak`
- `verification_gate_failed`

## Receipts

- 2026-05-13 KST codex@myworld added pre-spawn dirty work detection,
  post-failure orphan work detection, and monitor surfacing.
- Verification passed:
  - `bash -n scripts/aios_child_watcher.sh`
  - `python -m py_compile scripts/aios_monitor.py`
  - `python -m unittest tests/test_aios_child_watcher.py tests/test_aios_monitor.py -v`
  - `python scripts/aios_dispatch.py release --dispatch-id asc-0059 --reason asc_0059_watcher_race_detection_verified`
  - `python scripts/aios_dispatch.py watch --repo myworld --dispatch-id asc-0059 --once`
  - `python scripts/aios_monitor.py assess --json`
- Evidence artifacts:
  - `.aios/inbox/myworld/asc-0059.myworld.json`
  - `.aios/outbox/myworld/asc-0059.myworld.result.json`

## Work Packets

### WP-0059-A — codex@myworld adds race detection to watcher

- target_agent: codex
- target_repo: myworld
- status: done
- brief: |
    Add pre-spawn dirty check + post-attempt orphan detection to
    aios_child_watcher.sh. Add monitor finding. Tests for both paths.
- result: watcher now holds related pre-existing dirty work and flags
  orphan work left after failed agent attempts; monitor raises
  `orphan_dirty_post_failure`.
