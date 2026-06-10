---
contract_id: ASC-0018
slug: loop-policy-source-hygiene
status: closed
goal: Prevent loop policy from accepting already-closed contract documents as new executable work.
created: 2026-05-11 23:58 KST
accepted: 2026-05-11 23:58 KST by codex acting operator
closed: 2026-05-11 23:58 KST
supersedes: none
---

# ASC-0018 Loop Policy Source Hygiene

## Goal

Make the next-work selector distinguish closed evidence documents from live
work candidates.

After ASC-0017, monitor is clean and loop policy is the next control-plane
source of work. It currently may mark already-closed `docs/contracts/ASC-*.md`
sources as `accept_now` because those files contain dense AIOS keywords. That
can waste child-agent capacity by reissuing work that is already closed.

## Scope

repos:

- `myworld`

allowed_files:

- `scripts/aios_loop_policy.py`
- `tests/test_aios_loop_policy.py`
- `docs/AIOS_LOOP_POLICY.md`
- `docs/contracts/ASC-0018-loop-policy-source-hygiene.md`
- `docs/contracts/README.md`
- `docs/AIOS_AGENT_LEDGER.md`

forbidden_files:

- `.aios/**`
- `hivemind/**`
- `memoryOS/**`
- `CapabilityOS/**`
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

- **myworld.must_produce**: loop-policy closed-contract source detection,
  tests, regenerated policy snapshot, and closeout record.
- **hive_mind.must_produce**: no source change.
- **memoryos.must_produce**: no source change.
- **capabilityos.must_produce**: no source change.
- **operator.must_produce**: release only if closed contract sources cannot be
  `accept_now` while ordinary executable candidates still can.

## Verification Gate

```bash
cd /home/user/workspaces/jaewon/myworld
python -m unittest tests/test_aios_loop_policy.py
python scripts/aios_loop_policy.py --write docs/AIOS_LOOP_POLICY.md --json
python scripts/aios_monitor.py snapshot --json --fail-on-alert
```

Expected evidence:

- a radar row pointing at a closed `docs/contracts/ASC-*.md` source becomes
  `reject_closed_contract_reference`;
- a non-contract executable myworld source can still become `accept_now`;
- monitor remains zero-alert.

## Stop Conditions

- `closed_contract_accepted`: a closed contract source still returns
  `accept_now`.
- `all_myworld_blocked`: ordinary myworld executable sources are rejected just
  because closed contracts are filtered.
- `child_repo_edit`: child repo files are modified.
- `runtime_state_edit`: `.aios/**` files are committed or edited as part of the
  policy change.

## Receipts

Closed 2026-05-11 23:58 KST by `codex@myworld` acting operator.

- Updated `scripts/aios_loop_policy.py` so radar rows pointing at closed or
  superseded `docs/contracts/ASC-*.md` sources return
  `reject_closed_contract_reference`.
- Added regression coverage in `tests/test_aios_loop_policy.py`.
- Regenerated `docs/AIOS_LOOP_POLICY.md`.
- Verification:
  - `python -m unittest tests/test_aios_loop_policy.py` passed 2/2.
  - `python scripts/aios_loop_policy.py --write docs/AIOS_LOOP_POLICY.md --json`
    showed closed contract sources rejected while ordinary executable sources
    can still be `accept_now`.
  - `python scripts/aios_monitor.py snapshot --json --fail-on-alert` exited
    zero.
- Stop conditions triggered: none.

## Work Packets

### WP-0018-A — Codex@myworld tightens loop policy source filtering

- target_agent: codex
- target_repo: myworld
- status: done
- issued: 2026-05-11
- accepted: 2026-05-11 23:58 KST
- closed: 2026-05-11 23:58 KST
- depends_on: ASC-0017
- brief: |
    Update `scripts/aios_loop_policy.py` so closed contract source documents
    are never returned as `accept_now`. Add tests and regenerate
    `docs/AIOS_LOOP_POLICY.md`.
- result: implemented and verified; see Receipts.
