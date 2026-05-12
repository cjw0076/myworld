---
contract_id: ASC-0043
slug: contract-autodraft-from-goal-plan
status: closed
goal: turn an unblocked goal evolution recommendation into a proposed smart contract draft without relying on chat memory.
created: 2026-05-12 19:11 KST
accepted: 2026-05-12 19:12 KST by codex acting operator
closed: 2026-05-12 19:17 KST
---

# ASC-0043 Contract Autodraft From Goal Plan

## Why Now

Goal evolution selected this unblocked recommendation:

- path: `goal:contract_autodraft_from_goal_plan`
- domain: `myworld`
- policy_decision: `goal_preferred`
- reason: listed in active goal Preferred Next Improvements

This draft is proposed only. Operator acceptance must flip frontmatter status
before dispatch.

## Scope

repos:

- `myworld`

allowed_files:

- `scripts/aios_contract_autodraft.py`
- `tests/test_aios_contract_autodraft.py`
- `docs/contracts/ASC-0043-contract-autodraft-from-goal-plan.md`
- `docs/contracts/README.md`
- `docs/AIOS_WORK_DISPATCH.md`
- `docs/goals/AIOS-GOAL-0001-make-something-great.md`
- `docs/goals/AIOS-GOAL-0001-evolution.md`
- `docs/AIOS_AGENT_LEDGER.md`

forbidden_files:

- `.aios/logs/**`
- `.aios/state/**`
- `.aios/inbox/**`
- `.aios/outbox/**`
- `.env`
- raw export paths

## Responsibilities

### myworld.must_produce

- `scripts/aios_contract_autodraft.py` with a `draft` command that reads the
  active goal evolution plan and renders a proposed smart contract.
- Refusal behavior when the goal plan has stop conditions or the selected
  recommendation is blocked.
- Tests proving the generated contract remains `status: proposed` and
  `auto_accept=false`.
- Dogfood evidence: this ASC-0043 file starts from the generated draft and is
  manually accepted/closed only after verification.

### child repos

- No source role unless the accepted contract explicitly assigns one.

## Verification Gate

```bash
python -m py_compile scripts/aios_contract_autodraft.py scripts/aios_goal_evolution.py
python -m unittest tests/test_aios_contract_autodraft.py
python -m unittest discover -s tests -p 'test_aios_*.py'
python scripts/aios_monitor.py assess --json
```

Pass criteria:

- Contract remains `proposed` until operator acceptance.
- CLI can write a proposed contract draft to a requested output directory.
- Blocked recommendations are refused.
- Scope names exact repos and avoids child-repo source edits unless assigned.
- Verification evidence is linked before closeout.
- Monitor remains clear.

## Stop Conditions

- `operator_acceptance_missing`
- `scope_ambiguous`
- `allowed_files_too_broad`
- `child_repo_source_edit`
- `verification_gate_failed`
- `monitor_not_clear`

## Source Plan Evidence

- generated_at: `2026-05-12T19:11:50+09:00`
- monitor_health: `clear`
- readiness: `L6 repeatable`
- alignment_reasons: `goal_preferred_next`
- blocked_reasons: ``

## Receipts

- implementation:
  - `scripts/aios_contract_autodraft.py` adds
    `draft --goal ... --write --json`.
  - `tests/test_aios_contract_autodraft.py` covers proposed-only output,
    blocked-plan refusal, and CLI write behavior.
  - This contract was generated first by:
    `python scripts/aios_contract_autodraft.py --root . draft --contract-id ASC-0043 --output-dir docs/contracts --write --json`.
- dispatch evidence:
  - `asc-0043` sent to `myworld`, watched, collected, and released with reason
    `asc_0043_contract_autodraft_verified`.
  - result packet:
    `.aios/outbox/myworld/asc-0043.myworld.result.json`.
- verification:
  - focused ASC-0043 tests passed 3/3.
  - full myworld suite passed 86/86.
  - final `python scripts/aios_monitor.py assess --write --json` returned
    `health=clear`.
