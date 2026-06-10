---
contract_id: ASC-0034
slug: governance-action-policy-engine
status: closed
goal: Add a machine-checkable AIOS action policy engine that gates proposed actions by authority, risk, privacy, resource use, and checkpoint requirements.
created: 2026-05-12 14:40 KST
accepted: 2026-05-12 14:40 KST
closed: 2026-05-12 14:42 KST
---

# ASC-0034 Governance Action Policy Engine

## Why Now

ASC-0033 defined post-L6 governance readiness. The next step is enforceable
policy: before AIOS executes or dispatches high-impact work, the control plane
should be able to classify the proposed action as `allow`, `hold`, `deny`, or
`escalate`.

This does not execute actions. It evaluates whether an action is authorized
enough to proceed.

## Scope

repos:

- `myworld`

allowed_files:

- `docs/AIOS_ACTION_POLICY.md`
- `scripts/aios_action_policy.py`
- `tests/test_aios_action_policy.py`
- `docs/contracts/ASC-0034-governance-action-policy-engine.md`
- `docs/contracts/README.md`
- `docs/goals/AIOS-GOAL-0001-make-something-great.md`
- `docs/goals/AIOS-GOAL-0001-evolution.md`
- `docs/AIOS_AGENT_LEDGER.md`

forbidden_files:

- `hivemind/**`
- `memoryOS/**`
- `CapabilityOS/**`
- `uri/**`
- `.aios/logs/**`
- `.env`
- raw export paths

## Responsibilities

### myworld.must_produce

- A policy document describing action classes and decisions.
- A JSON CLI evaluator for proposed AIOS actions.
- Tests covering allow, hold, deny, and escalate.
- Contract closeout and ledger entry.

### child repos

- No source changes. Future contracts may require child watchers or dispatch to
  call this policy before execution.

## Verification Gate

```bash
python -m unittest tests/test_aios_action_policy.py
python scripts/aios_action_policy.py evaluate --example low_risk_local --json
python scripts/aios_action_policy.py evaluate --example public_authority --json
python -m unittest tests/test_aios_instruction_index.py tests/test_aios_loop_policy.py tests/test_aios_doc_scout.py tests/test_aios_readiness.py tests/test_aios_dispatch.py tests/test_aios_loop.py tests/test_aios_monitor.py tests/test_aios_goal_evolution.py tests/test_aios_child_watcher.py tests/test_aios_round_controller.py tests/test_aios_web_research_receipt.py tests/test_aios_institution_readiness.py tests/test_aios_action_policy.py
python scripts/aios_monitor.py assess --json
```

Pass criteria:

- Low-risk local contracted action is allowed.
- Missing evidence/contract causes hold.
- Forbidden action types are denied.
- Public authority, legal/safety, paid, credentialed, or irreversible actions
  without human approval escalate.
- Full myworld tests pass and monitor remains clear.

## Stop Conditions

- `policy_allows_forbidden_action`
- `policy_skips_human_checkpoint`
- `policy_blocks_all_low_risk_work`
- `policy_executes_action`
- `child_repo_scope_leak`

## Receipts

- Implementation: `docs/AIOS_ACTION_POLICY.md`,
  `scripts/aios_action_policy.py`, and `tests/test_aios_action_policy.py`.
- Dispatch: `.aios/inbox/myworld/asc-0034.myworld.json`.
- Result packet: `.aios/outbox/myworld/asc-0034.myworld.result.json`.
- Release: `python scripts/aios_dispatch.py release --dispatch-id asc-0034
  --reason asc_0034_governance_action_policy_engine_verified`.
- Verification:
  - `python -m unittest tests/test_aios_action_policy.py` passed 6/6.
  - `python scripts/aios_action_policy.py evaluate --example low_risk_local
    --json` returned `decision=allow`.
  - `python scripts/aios_action_policy.py evaluate --example
    public_authority --json` returned `decision=escalate`.
  - Full myworld suite passed 56/56.
  - Final `python scripts/aios_monitor.py assess --json` returned
    `health=clear`.

## Work Packets

### WP-0034-A — Codex@myworld implements action policy engine

- target_agent: codex
- target_repo: myworld
- status: accepted
- issued: 2026-05-12
- accepted: 2026-05-12
- closed: 2026-05-12
- depends_on: ASC-0033
- brief: |
    Implement a recommendation-only action policy evaluator. It should return
    allow, hold, deny, or escalate with reason codes. It must not execute
    actions or edit child repos.
- result: `.aios/outbox/myworld/asc-0034.myworld.result.json`
