---
contract_id: ASC-0048
slug: goal-evolution-semantic-verifier-refinement
status: closed
goal: Refine the recurring Hive radar-gap recommendation to the concrete semantic-verifier TODO instead of returning a broad RADAR_GAP_TRIAGE source.
created: 2026-05-12 21:07 KST
accepted: 2026-05-12 21:07 KST by codex acting operator
closed: 2026-05-12 21:09 KST
supersedes: ASC-0046
---

# ASC-0048 Goal Evolution Semantic Verifier Refinement

## Why Now

After ASC-0047 closed the `hive evaluate` TODO, the round controller returned
`myworld/hivemind/docs/RADAR_GAP_TRIAGE.md` as the next executable candidate.
The intended next concrete Hive-owned candidate is the existing unchecked
`semantic verifier LLM review for high-risk runs` TODO. The refinement exists
in code but misses hyphenated phrase matches such as `high-risk`.

## AIOS Inputs

- MemoryOS context: `rtrace_5ccc398180c7cebb`
- Accepted memory used: `mem_90b5cfe6570e6ee2`
- CapabilityOS top route: `cap_hivemind_execution_harness`
- Supporting routes: `cap_web_research_route`, `cap_memoryos_import_run`,
  `cap_memoryos_context_build`, `cap_capabilityos_recommendation`
- Hive dry-run: `run_20260512_210606_fda8f5`

## Scope

repos:

- `myworld`

allowed_files:

- `scripts/aios_goal_evolution.py`
- `tests/test_aios_goal_evolution.py`
- `docs/contracts/ASC-0048-goal-evolution-semantic-verifier-refinement.md`
- `docs/contracts/README.md`
- `docs/goals/AIOS-GOAL-0001-evolution.md`
- `docs/AIOS_AGENT_LEDGER.md`

forbidden_files:

- `hivemind/**`
- `memoryOS/**`
- `CapabilityOS/**`
- `.aios/logs/**`
- `.aios/state/**`
- `.runs/**`
- raw export paths

## Responsibilities

### myworld.must_produce

- Normalize pattern phrases and TODO item text consistently when refining the
  Hive radar-gap source.
- Tests proving the semantic-verifier TODO is selected after the evaluate TODO
  is already checked.
- Refreshed goal-evolution markdown showing the concrete semantic-verifier TODO
  anchor.

### hive_mind.must_produce

- No source change. Hive provides the TODO evidence only.

### memoryos.must_produce

- No source change.

### capabilityos.must_produce

- No source change.

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

- Recommendation path is `myworld/hivemind/docs/TODO.md#semantic-verifier`
  when `hive evaluate` is checked and the semantic-verifier TODO remains open.
- Stop conditions remain empty with monitor clear.
- No child repo source changes occur.

## Stop Conditions

- `child_repo_edit`: implementation edits lower repo files under this
  myworld-only contract.
- `semantic_todo_not_found`: planner cannot resolve the remaining concrete
  Hive TODO.
- `broad_radar_repeated`: planner keeps recommending only
  `myworld/hivemind/docs/RADAR_GAP_TRIAGE.md`.
- `verification_gate_failed`
- `monitor_not_clear`

## Receipts

Closed 2026-05-12 21:09 KST by `codex@myworld` acting operator.

- Dispatch:
  - `.aios/inbox/myworld/asc-0048.myworld.json`
  - `.aios/outbox/myworld/asc-0048.myworld.result.json`
- Verification:
  - `python -m py_compile scripts/aios_goal_evolution.py` passed.
  - `python -m unittest tests/test_aios_goal_evolution.py` passed 5/5.
  - `python scripts/aios_goal_evolution.py plan --goal
    docs/goals/AIOS-GOAL-0001-make-something-great.md --write
    docs/goals/AIOS-GOAL-0001-evolution.md` wrote
    `myworld/hivemind/docs/TODO.md#semantic-verifier`.
  - `python scripts/aios_goal_evolution.py plan --goal
    docs/goals/AIOS-GOAL-0001-make-something-great.md --json` returned the
    semantic-verifier recommendation with `source_path` set to the Hive radar
    source.
  - `python -m unittest discover -s tests -p 'test_aios_*.py'` passed 92/92.
  - `git diff --check` passed.
- Stop conditions triggered: none after result collection/release.

## Work Packets

### WP-0048-A — Codex@myworld normalizes Hive radar TODO refinement

- target_agent: codex
- target_repo: myworld
- status: done
- issued: 2026-05-12
- accepted: 2026-05-12 21:07 KST
- closed: 2026-05-12 21:09 KST
- depends_on: ASC-0047
- brief: |
    Fix `scripts/aios_goal_evolution.py` so Hive radar-gap refinement compares
    normalized TODO items against normalized pattern phrases. Add tests proving
    `semantic-verifier` is selected after `hive evaluate` is closed. Do not
    edit child repos.
- result: `.aios/outbox/myworld/asc-0048.myworld.result.json`
