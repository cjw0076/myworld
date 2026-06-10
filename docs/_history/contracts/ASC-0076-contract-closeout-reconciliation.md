---
contract_id: ASC-0076
slug: contract-closeout-reconciliation
status: closed
goal: Reconcile accepted-but-unclosed contracts from ASC-0056 through ASC-0068 into an explicit execution queue before additional AIOS runtime work proceeds.
created: 2026-05-13 KST
accepted: 2026-05-13 KST by founder directive to order the remaining contracts and proceed.
closed: 2026-05-13 KST by codex@myworld
acceptance_authority: founder/operator approval in chat
origin: founder asked why earlier contracts were not all complete before ASC-0067/0068 execution.
---

# ASC-0076 Contract Closeout Reconciliation

## Why Now

AIOS cannot claim autonomous execution if accepted contracts remain open
without a visible order. A clean monitor is not enough: contract frontmatter,
dispatch state, receipts, tests, and ledger entries must agree.

ASC-0076 freezes new feature expansion long enough to classify the open
contracts and identify the next executable closeout.

## Scope

repos:

- `myworld`

allowed_files:

- `docs/AIOS_CONTRACT_EXECUTION_ORDER.md`
- `docs/AIOS_CONTRACT_RECONCILIATION.md`
- `scripts/aios_contract_reconcile.py`
- `tests/test_aios_contract_reconcile.py`
- `docs/contracts/ASC-0076-contract-closeout-reconciliation.md`
- `docs/contracts/README.md`
- `docs/AIOS_AGENT_LEDGER.md`

read_only_files:

- `docs/contracts/ASC-0056-memoryos-draft-pipeline-closure.md`
- `docs/contracts/ASC-0057-pulse-heartbeat-persistence.md`
- `docs/contracts/ASC-0058-goal-inbox-processor.md`
- `docs/contracts/ASC-0059-watcher-race-resolution.md`
- `docs/contracts/ASC-0060-action-policy-scope-aware.md`
- `docs/contracts/ASC-0061-dispatch-escalate-recovery.md`
- `docs/contracts/ASC-0062-peer-share-privacy-projection.md`
- `docs/contracts/ASC-0063-uri-content-relevance-filter.md`
- `docs/contracts/ASC-0064-live-dashboard-websocket.md`
- `docs/contracts/ASC-0065-genesisos-bootstrap.md`
- `docs/contracts/ASC-0066-provider-backpressure-role-distillation.md`
- `docs/contracts/ASC-0067-unified-os-invocation-pipeline.md`
- `docs/contracts/ASC-0068-global-project-agent-discovery.md`
- `.aios/state/dispatches.jsonl`

forbidden_files:

- child repo source edits
- `_from_desktop/**`
- `dain/**`
- `minyoung/**`
- `.env`
- `.env.*`
- raw exports
- provider execution
- contract closeout without verification evidence

## Required Classification

Each target contract must be classified as one of:

- `closed_verified`: frontmatter closed and evidence exists.
- `close_now`: implementation/evidence exists but frontmatter/ledger needs
  closeout.
- `retry_now`: blocked previously, but a later contract removed the blocker.
- `continue_implementation`: accepted and still needs implementation.
- `hold`: cannot proceed without operator or provider condition.
- `supersede`: replace with a newer contract instead of finishing as written.

The first required matrix covers:

```text
ASC-0056, ASC-0057, ASC-0058, ASC-0059, ASC-0060, ASC-0061,
ASC-0062, ASC-0063, ASC-0064, ASC-0065, ASC-0066, ASC-0067, ASC-0068
```

## Verification Gate

```bash
python -m py_compile scripts/aios_contract_reconcile.py
python -m unittest tests/test_aios_contract_reconcile.py
python scripts/aios_contract_reconcile.py --from 56 --to 68 --write docs/AIOS_CONTRACT_RECONCILIATION.md --json
python scripts/aios_contract_reconcile.py --from 56 --to 68 --json
python -m unittest discover -s tests -p 'test_aios_*.py'
python scripts/aios_monitor.py assess --json
```

Pass criteria:

- Every ASC in the target range appears exactly once.
- Any contract with `status=accepted` and no `closed` value is not reported as
  complete.
- Any held dispatch is surfaced as `hold` or `retry_now`, not ignored.
- `ASC-0066` is classified as `close_now` only if Hive test evidence is
  present.
- `ASC-0067` and `ASC-0068` stay `continue_implementation` until their own
  verification gates pass.
- The generated order matches `docs/AIOS_CONTRACT_EXECUTION_ORDER.md`.
- The script performs no provider execution and no child repo writes.

## Stop Conditions

- `contract_missing_from_matrix`
- `accepted_contract_marked_complete_without_closed`
- `held_dispatch_ignored`
- `closeout_without_evidence`
- `child_repo_scope_leak`
- `provider_execution_attempted`
- `verification_gate_failed`

## Work Packets

### WP-0076-A — codex@myworld implements reconciliation matrix

- target_agent: codex
- target_repo: myworld
- status: accepted
- depends_on: none
- brief: |
    Implement the contract reconciliation script, tests, and generated
    reconciliation report. Do not close feature contracts yet. The first
    output is an auditable order and classification matrix.
- return_to: `.aios/outbox/myworld/asc-0076.myworld.result.json`
- result: pending

### WP-0076-B — claude@myworld reviews lifecycle semantics

- target_agent: claude
- target_repo: myworld
- status: proposed
- depends_on: WP-0076-A
- brief: |
    Review whether each classification is semantically correct: close, hold,
    retry, continue, or supersede. Pay special attention to ASC-0056 held
    status and ASC-0066 closeout evidence.
- return_to: `.aios/outbox/myworld/asc-0076.claude-review.result.json`
- result: pending
