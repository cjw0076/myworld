---
contract_id: ASC-0060
slug: action-policy-scope-aware
status: accepted
goal: Stop the action policy gate (ASC-0034) from false-escalating myworld-only operator-script changes as `private_remote_data` so the dispatch flow does not require manual operator override for legitimate myworld-scope work.
created: 2026-05-13 KST
accepted: 2026-05-13 KST by claude acting operator
closed:
acceptance_authority: claude@myworld (operator) per founder directive.
origin: ASC-0037 dispatch escalation incident (2026-05-12 15:47) where myworld-only locale-fix contract was escalated as `human_checkpoint_required:private_remote_data` despite touching no remote data — required manual claude release.
---

# ASC-0060 Action Policy Scope-Aware Classification

## Why Now

ASC-0034 created the action policy engine with `allow|hold|deny|escalate`
classifications. ASC-0035 wired it into dispatch send. The gate works,
but its scope-classification heuristic produces false positives:

- ASC-0037 (myworld-only operator script change) was classified as
  `human_checkpoint_required:private_remote_data`. ASC-0037 touched
  zero remote data.
- The same false positive blocked ASC-0037 retry attempts.

Fix: the policy classifier needs scope-aware reasoning. A contract
that lists only `myworld` in `repos[]` and only `scripts/` or `docs/`
in `allowed_files` and has zero `private_remote_data`-related fields
should classify `allow` directly without escalation.

## Scope

repos:

- `myworld`

allowed_files:

- `scripts/aios_action_policy.py`
- `tests/test_aios_action_policy.py`
- `docs/AIOS_ACTION_POLICY.md`
- `docs/contracts/ASC-0060-action-policy-scope-aware.md`
- `docs/contracts/README.md`
- `docs/AIOS_AGENT_LEDGER.md`

forbidden_files:

- `hivemind/**`, `memoryOS/**`, `CapabilityOS/**`, `uri/**`
- `.env`

## Per-OS Responsibility

### myworld.must_produce

- `aios_action_policy.py` updated with scope-aware classifier:
  - `myworld_only` = `repos == ["myworld"]` and `allowed_files` are all
    under `scripts/`, `tests/`, `docs/`, or `.aios/primitives/` and no
    forbidden_file pattern includes external-data paths.
  - Such contracts: `allow` immediately, reason
    `myworld_local_operator_scope`.
- New regression test cases: ASC-0037-shaped contract → `allow`,
  ASC-0036-shaped contract (multi-repo) → existing classification,
  contract that touches `_from_desktop/` → still escalates.
- Documentation: extend `AIOS_ACTION_POLICY.md` with the scope rule
  and the false-positive history.

### child repos

- No source change.

## Verification Gate

```bash
python -m py_compile scripts/aios_action_policy.py
python -m unittest tests/test_aios_action_policy.py
python scripts/aios_action_policy.py evaluate --example low_risk_local --json
python scripts/aios_action_policy.py evaluate --example public_authority --json
python -m unittest discover -s tests -p 'test_aios_*.py'
python scripts/aios_monitor.py assess --json
```

Pass criteria:

- ASC-0037-shape contract returns `allow` not `escalate`.
- ASC-0036-shape contract still escalates (multi-repo cross-OS).
- Founder-gated paths still escalate.
- Full test suite green.

## Stop Conditions

- `policy_allows_forbidden_action`
- `policy_skips_human_checkpoint`: scope rule must NOT bypass real
  high-authority actions.
- `policy_blocks_all_local_dispatch`: must still allow legitimate
  myworld-only work.
- `child_repo_scope_leak`
- `verification_gate_failed`

## Receipts

Pending.

## Work Packets

### WP-0060-A — codex@myworld adds scope-aware classification

- target_agent: codex
- target_repo: myworld
- status: accepted
- brief: |
    Implement the scope-aware classifier. Cases must include both the
    false-positive (myworld-only allow) and the true-positive (founder
    paths still escalate). Document the change.
- result: pending
