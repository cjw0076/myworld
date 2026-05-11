---
contract_id: ASC-0024
slug: goal-planner-source-hygiene
status: closed
goal: Keep the goal evolution planner from selecting broad history/index documents as direct implementation candidates and advance completed preferred-next items.
created: 2026-05-12 02:20 KST
accepted: 2026-05-12 02:20 KST by codex acting operator
closed: 2026-05-12 02:23 KST
supersedes: none
---

# ASC-0024 Goal Planner Source Hygiene

## Goal

After ASC-0023 closed, `aios_goal_evolution.py` still recommended
`hivemind/docs/AGENT_WORKLOG.md` because it contained recent source-read
signals. That is the wrong surface: worklogs, ecosystem ledgers, and contract
indexes are evidence, not direct implementation packets.

This contract tightens the goal planner so broad history/index documents are
held for triage and completed preferred-next items no longer steer the next
recommendation.

## Scope

repos:

- `myworld`

allowed_files:

- `scripts/aios_goal_evolution.py`
- `tests/test_aios_goal_evolution.py`
- `docs/goals/AIOS-GOAL-0001-make-something-great.md`
- `docs/goals/AIOS-GOAL-0001-evolution.md`
- `docs/contracts/ASC-0024-goal-planner-source-hygiene.md`
- `docs/contracts/README.md`
- `docs/AIOS_AGENT_LEDGER.md`

forbidden_files:

- `hivemind/**`
- `memoryOS/**`
- `CapabilityOS/**`
- `.aios/**`
- `.runs/**`
- `raw_exports/**`
- `exports/**`
- `logs/**`
- `weights/**`
- `**/*secret*`
- `**/*credential*`
- `.env`
- `.env.*`

## Per-OS Responsibility

- **myworld.must_produce**:
  - planner hygiene rules for broad history/index sources;
  - tests proving high-score worklogs/ledgers are held, not recommended;
  - active goal update moving `source_read_registry` into completed progress
    and leaving the next preferred item executable.
- **hive_mind.must_produce**: no source change.
- **memoryos.must_produce**: no source change.
- **capabilityos.must_produce**: no source change.
- **operator.must_produce**: release only if the goal planner's next
  recommendation is not a broad history or closed/index document.

## Verification Gate

```bash
cd /home/user/workspaces/jaewon/myworld
python -m unittest tests/test_aios_goal_evolution.py
python scripts/aios_goal_evolution.py plan --goal docs/goals/AIOS-GOAL-0001-make-something-great.md --json
python scripts/aios_goal_evolution.py plan --goal docs/goals/AIOS-GOAL-0001-make-something-great.md --write docs/goals/AIOS-GOAL-0001-evolution.md
```

Expected evidence:

- `AGENT_WORKLOG.md`, `AIOS_AGENT_LEDGER.md`, and `docs/contracts/README.md`
  candidates are blocked with a specific history/index reason.
- The active goal records `source_read_registry` as completed.
- The next recommendation is either `goal:watcher_execution_reliability` or a
  narrower non-history source aligned with that preferred item.
- Closed contract documents remain rejected.

## Stop Conditions

- `history_doc_selected`: planner recommends a worklog, ledger, comms log, or
  contract index as direct implementation.
- `completed_item_recommended`: planner keeps selecting
  `source_read_registry` after ASC-0023 closure.
- `private_path_auto_accept`: private/archive paths are recommended for
  automatic acceptance.
- `child_repo_edit`: implementation touches child repo files.
- `no_verification_evidence`: planner output lacks monitor/readiness/policy
  evidence.

## Receipts

Closed 2026-05-12 02:23 KST by `codex@myworld` acting operator.

- Dispatch:
  - `.aios/inbox/myworld/asc-0024.myworld.json`
  - `.aios/outbox/myworld/asc-0024.myworld.result.json`
- Implementation:
  - `scripts/aios_goal_evolution.py`
  - `tests/test_aios_goal_evolution.py`
  - `docs/goals/AIOS-GOAL-0001-make-something-great.md`
  - `docs/goals/AIOS-GOAL-0001-evolution.md`
- Verification:
  - `python -m unittest tests/test_aios_goal_evolution.py` passed 4/4.
  - `python scripts/aios_goal_evolution.py plan --goal
    docs/goals/AIOS-GOAL-0001-make-something-great.md --json` recommended
    `goal:watcher_execution_reliability`.
  - `python scripts/aios_goal_evolution.py plan --goal
    docs/goals/AIOS-GOAL-0001-make-something-great.md --write
    docs/goals/AIOS-GOAL-0001-evolution.md` wrote a monitor-clear markdown
    plan.
  - `python -m py_compile scripts/aios_goal_evolution.py` passed.
  - `python scripts/aios_dispatch.py collect --repo myworld` collected the
    result packet as `passed`.
  - `python scripts/aios_dispatch.py release --dispatch-id asc-0024 --reason
    asc_0024_goal_planner_source_hygiene_verified` succeeded.
  - `python scripts/aios_monitor.py assess --json` returned `health=clear`.
- Stop conditions triggered: none.

## Work Packets

### WP-0024-A — Codex@myworld tightens goal planner source hygiene

- target_agent: codex
- target_repo: myworld
- status: done
- issued: 2026-05-12
- accepted: 2026-05-12 02:20 KST
- closed: 2026-05-12 02:23 KST
- depends_on: ASC-0022, ASC-0023
- brief: |
    Update the goal evolution planner so broad history/index docs are held for
    triage instead of recommended as direct work. Move source_read_registry to
    completed goal progress and verify the next recommendation advances the
    remaining preferred goal.
- result: dispatch collected and released; see Receipts.
