---
contract_id: ASC-0022
slug: aios-goal-evolution-loop
status: closed
goal: Add a goal-level AIOS evolution loop that turns one active north-star goal into the next best contract candidate with evidence.
created: 2026-05-12 01:24 KST
accepted: 2026-05-12 01:24 KST by codex acting operator
closed: 2026-05-12 01:31 KST
supersedes: none
---

# ASC-0022 AIOS Goal Evolution Loop

## Goal

AIOS has a working task loop, but the operator now wants a higher-level loop:
one goal should steer repeated search, contract selection, verification, and
learning until the system materially improves.

This contract adds the first goal-level control-plane surface. It does not
auto-edit child repos. It produces a checkable recommendation for the next
contract and explains why that work improves the active goal.

## Scope

repos:

- `myworld`

allowed_files:

- `scripts/aios_goal_evolution.py`
- `tests/test_aios_goal_evolution.py`
- `docs/goals/AIOS-GOAL-0001-make-something-great.md`
- `docs/AIOS_BUILD_METHOD.md`
- `docs/contracts/ASC-0022-aios-goal-evolution-loop.md`
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
  - active goal file under `docs/goals/`;
  - `scripts/aios_goal_evolution.py`;
  - tests proving JSON/Markdown output, closed-contract rejection, and private
    path hold behavior.
- **hive_mind.must_produce**: no source change. Future goal plans may issue
  Hive packets after a contract is opened.
- **memoryos.must_produce**: no source change. Future goal plans may request
  accepted context or memory observations.
- **capabilityos.must_produce**: no source change. Future goal plans may ask
  for capability routing when policy marks a candidate `hold_for_capability`.
- **operator.must_produce**: accept/hold/revise the recommended next contract
  candidate. The script may recommend; it may not silently open child-repo
  implementation contracts.

## Verification Gate

```bash
cd /home/user/workspaces/jaewon/myworld
python -m unittest tests/test_aios_goal_evolution.py
python scripts/aios_goal_evolution.py plan --goal docs/goals/AIOS-GOAL-0001-make-something-great.md --json
python scripts/aios_goal_evolution.py plan --goal docs/goals/AIOS-GOAL-0001-make-something-great.md --write docs/goals/AIOS-GOAL-0001-evolution.md
```

Expected evidence:

- JSON output has `schema_version=aios.goal_evolution.v1`.
- The active goal includes a quality function and anti-cheat checks.
- The plan cites monitor health, readiness level, loop policy decisions, and a
  recommended next contract candidate or hold reason.
- Closed contract documents are never selected as the next action.
- Operator-gated/private paths remain held, not accepted.

## Stop Conditions

- `self_evolution_without_goal`: script runs without an explicit goal file or
  active goal id.
- `closed_contract_reopened`: recommendation selects a closed contract document
  as new work.
- `private_path_auto_accept`: `_from_desktop`, `dain`, `minyoung`, raw export,
  logs, or secret paths are recommended for automatic acceptance.
- `child_repo_edit`: implementation touches child repo files.
- `no_quality_function`: goal lacks measurable quality criteria.
- `no_verification_evidence`: recommendation lacks monitor/readiness/policy
  evidence.

## Receipts

Closed 2026-05-12 01:31 KST by `codex@myworld` acting operator.

- Dispatch:
  - `.aios/inbox/myworld/asc-0022.myworld.json`
  - `.aios/outbox/myworld/asc-0022.myworld.result.json`
- Implementation:
  - `scripts/aios_goal_evolution.py`
  - `tests/test_aios_goal_evolution.py`
  - `docs/goals/AIOS-GOAL-0001-make-something-great.md`
  - `docs/goals/AIOS-GOAL-0001-evolution.md`
  - `docs/AIOS_BUILD_METHOD.md`
- Verification:
  - `python -m unittest tests/test_aios_goal_evolution.py` passed 4/4.
  - `python scripts/aios_goal_evolution.py plan --goal
    docs/goals/AIOS-GOAL-0001-make-something-great.md --json` returned
    `schema_version=aios.goal_evolution.v1` and recommended
    `myworld/hivemind/docs/RADAR_GAP_TRIAGE.md` with `blocked=false`.
  - `python scripts/aios_goal_evolution.py plan --goal
    docs/goals/AIOS-GOAL-0001-make-something-great.md --write
    docs/goals/AIOS-GOAL-0001-evolution.md` wrote the markdown plan.
  - `python -m py_compile scripts/aios_goal_evolution.py` passed.
  - `python scripts/aios_dispatch.py collect --repo myworld` collected the
    result packet as `passed`.
  - `python scripts/aios_dispatch.py release --dispatch-id asc-0022 --reason
    asc_0022_goal_evolution_loop_verified` succeeded.
  - `python scripts/aios_monitor.py assess --json` returned `health=clear`.
- Selected next candidate: Hive-owned source-read registry from
  `hivemind/docs/RADAR_GAP_TRIAGE.md`.
- Stop conditions triggered: none.

## Work Packets

### WP-0022-A — Codex@myworld implements goal evolution planner

- target_agent: codex
- target_repo: myworld
- status: done
- issued: 2026-05-12
- accepted: 2026-05-12 01:24 KST
- closed: 2026-05-12 01:31 KST
- depends_on: ASC-0021
- brief: |
    Implement a goal-level control-plane planner. It should read one goal file,
    current readiness/monitor/policy signals, and task radar candidates, then
    emit a JSON/Markdown recommendation for the next best contract candidate.
    Keep it recommendation-only and do not edit child repo source.
- result: dispatch collected and released; see Receipts.
