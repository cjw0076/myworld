---
contract_id: ASC-0046
slug: goal-evolution-concrete-hive-todo
status: closed
goal: Make goal evolution refine the recurring Hive radar-gap recommendation into a concrete unchecked Hive TODO so the loop does not repeat closed subitems.
created: 2026-05-12 20:34 KST
accepted: 2026-05-12 20:34 KST by codex acting operator
closed: 2026-05-12 20:40 KST
supersedes: none
---

# ASC-0046 Goal Evolution Concrete Hive TODO

## Why Now

After ASC-0045 closed, `aios_round_controller.py once --json` still
recommended `myworld/hivemind/docs/RADAR_GAP_TRIAGE.md`. That file is a valid
radar source, but its earlier concrete subitems (`arrival-pack`,
`source-read`, and `HANDOFF.json` import) are now closed. If the control plane
continues to recommend only the radar document, the autonomous loop can repeat
instead of selecting the next implementable Hive slice.

This contract teaches goal evolution to refine that known Hive radar source
into a concrete unchecked Hive TODO, currently the first-class
`hive evaluate` / `hive subagents review` command.

## Scope

repos:

- `myworld`

allowed_files:

- `scripts/aios_goal_evolution.py`
- `tests/test_aios_goal_evolution.py`
- `docs/contracts/ASC-0046-goal-evolution-concrete-hive-todo.md`
- `docs/contracts/README.md`
- `docs/goals/AIOS-GOAL-0001-evolution.md`
- `docs/goals/AIOS-GOAL-0001-make-something-great.md`
- `docs/AIOS_AGENT_LEDGER.md`

forbidden_files:

- `hivemind/**`
- `memoryOS/**`
- `CapabilityOS/**`
- `uri/**`
- `.aios/logs/**`
- `.aios/state/**`
- `.aios/inbox/**`
- `.aios/outbox/**`
- `.env`
- raw export paths

## Responsibilities

### myworld.must_produce

- Goal-evolution logic that recognizes the recurring
  `hivemind/docs/RADAR_GAP_TRIAGE.md` recommendation and refines it to a
  concrete unchecked Hive TODO when the matching child TODO is still open.
- Tests proving closed/stale radar subitems do not keep being selected and the
  concrete `hive evaluate` TODO is recommended.
- Updated goal evolution markdown showing the concrete path/task.

### hive_mind.must_produce

- No source change. Hive provides the TODO source only.

### memoryos.must_produce

- No source change.

### capabilityos.must_produce

- No source change.

### operator.must_produce

- Release only if the planner no longer returns the generic radar-gap
  recommendation when a concrete unchecked Hive TODO can be named.

## Verification Gate

```bash
python -m py_compile scripts/aios_goal_evolution.py
python -m unittest tests/test_aios_goal_evolution.py
python scripts/aios_goal_evolution.py plan --goal docs/goals/AIOS-GOAL-0001-make-something-great.md --write docs/goals/AIOS-GOAL-0001-evolution.md
python scripts/aios_goal_evolution.py plan --goal docs/goals/AIOS-GOAL-0001-make-something-great.md --json
python -m unittest discover -s tests -p 'test_aios_*.py'
python scripts/aios_monitor.py assess --json
```

Pass criteria:

- Recommendation path is concrete, not only
  `myworld/hivemind/docs/RADAR_GAP_TRIAGE.md`, when the Hive TODO can be
  refined.
- Recommended task mentions `hive evaluate` or `hive subagents review`.
- Existing history/index/closed/private blocking behavior remains intact.
- Monitor remains clear.

## Stop Conditions

- `todo_parse_ambiguous`: planner cannot identify an unchecked Hive TODO
  without guessing.
- `closed_item_recommended`: planner recommends arrival-pack, source-read, or
  HANDOFF import after those contracts are closed.
- `child_repo_edit`: implementation edits Hive source or docs under this
  myworld-only contract.
- `verification_gate_failed`
- `monitor_not_clear`

## Receipts

Closed 2026-05-12 20:40 KST by `codex@myworld` acting operator.

- Dispatch:
  - `.aios/inbox/myworld/asc-0046.myworld.json`
  - `.aios/outbox/myworld/asc-0046.myworld.result.json`
- Verification:
  - `python -m py_compile scripts/aios_goal_evolution.py` passed.
  - `python -m unittest tests/test_aios_goal_evolution.py` passed 4/4.
  - `python scripts/aios_goal_evolution.py plan --goal
    docs/goals/AIOS-GOAL-0001-make-something-great.md --write
    docs/goals/AIOS-GOAL-0001-evolution.md` wrote the concrete Hive TODO
    recommendation.
  - `python scripts/aios_goal_evolution.py plan --goal
    docs/goals/AIOS-GOAL-0001-make-something-great.md --json` recommended
    `myworld/hivemind/docs/TODO.md#hive-evaluate` with task
    `Add first-class hive evaluate or hive subagents review...`.
  - `python -m unittest discover -s tests -p 'test_aios_*.py'` passed 91/91.
  - `git diff --check` passed.
- Stop conditions triggered: none after result collection/release.

## Work Packets

### WP-0046-A — Codex@myworld implements concrete Hive TODO refinement

- target_agent: codex
- target_repo: myworld
- status: done
- issued: 2026-05-12
- accepted: 2026-05-12 20:34 KST
- closed: 2026-05-12 20:40 KST
- depends_on: ASC-0045
- brief: |
    Update `scripts/aios_goal_evolution.py` so the recurrent
    `hivemind/docs/RADAR_GAP_TRIAGE.md` recommendation can resolve to the next
    concrete unchecked Hive TODO instead of repeating stale closed subitems.
    Keep this recommendation-only; do not edit child repos.
- result: concrete Hive TODO refinement implemented and verified; see
  Receipts.
