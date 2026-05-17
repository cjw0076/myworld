---
contract_id: ASC-0119
slug: os-activity-evidence
status: closed
goal: Stop self-check from flagging an OS as ghosted when it has recent role artifacts through AIOS invocation receipts, not just inbox packets.
created: 2026-05-13 KST
accepted: 2026-05-13 KST by codex acting founder-delegated operator
closed: 2026-05-13 KST by codex@myworld after dispatch gate passed
acceptance_authority: codex@myworld per founder directive to keep AIOS maturing through its own loop.
origin: After ASC-0118 restored readiness L6, self-check still flagged `CROSS_OS_GHOST repos= GenesisOS` even though `scripts/aios_invoke.py` had just produced `role_statuses.genesis=passed` and `.aios/invocations/.../genesis/branches.json`.
---

# ASC-0119 OS Activity Evidence

DNA references: Invariant 5 (provenance), Invariant 8 (classify before
committing).

## Scope

repos: `myworld`

allowed_files:

- `scripts/aios_os_activity.py`
- `scripts/aios_self_check.sh`
- `tests/test_aios_os_activity.py`
- `docs/contracts/ASC-0119-os-activity-evidence.md`
- `docs/contracts/README.md`
- `docs/AGENT_WORKLOG.md`
- `docs/AIOS_AGENT_LEDGER.md`

forbidden_files:

- `.aios/invocations/**` (read-only evidence)
- `.aios/inbox/**` (read-only evidence)
- `hivemind/**`, `memoryOS/**`, `CapabilityOS/**`, `GenesisOS/**`, `uri/**`
- `.env`

## Per-OS Responsibility

### myworld.must_produce

`scripts/aios_os_activity.py`:

- maps OS repo names to invocation roles:
  - `GenesisOS -> genesis`
  - `memoryOS -> memory`
  - `CapabilityOS -> capability`
  - `hivemind -> hive`
- reports recent activity from either:
  - `.aios/inbox/<repo>/*.json` modified within the window
  - `.aios/invocations/*/receipt.json` where `role_statuses.<role>` is
    `passed` or `degraded` within the window
- returns JSON with per-OS evidence and `ghost_repos`

`scripts/aios_self_check.sh`:

- replaces the hardcoded inbox-only CROSS_OS_GHOST check with
  `aios_os_activity.py`

## Verification Gate

```bash
python -m py_compile scripts/aios_os_activity.py
python -m unittest tests/test_aios_os_activity.py
bash -n scripts/aios_self_check.sh
python scripts/aios_os_activity.py --json
bash scripts/aios_self_check.sh
python -m unittest discover -s tests -p 'test_aios_*.py'
python scripts/aios_monitor.py assess --json
```

Pass criteria:

- recent GenesisOS invocation role evidence prevents `CROSS_OS_GHOST GenesisOS`
- inbox-only activity still counts for child repos
- no child repo files are modified

## Stop Conditions

- `activity_false_clear`: failed invocation role must not count as active
- `activity_ignores_inbox`: ordinary inbox packets must still count
- `child_repo_scope_leak`
- `verification_gate_failed`

## Receipts

- Dispatch result: `.aios/outbox/myworld/asc-0119.myworld.result.json`
  status `passed`.
- Verification passed:
  - `python -m py_compile scripts/aios_os_activity.py`
  - `python -m unittest tests/test_aios_os_activity.py` (`4` tests)
  - `bash -n scripts/aios_self_check.sh`
  - `python scripts/aios_os_activity.py --json` reported `ghost_repos=[]`
    and GenesisOS active from recent invocation receipts
  - `bash scripts/aios_self_check.sh` emitted no `CROSS_OS_GHOST`
  - `python -m unittest discover -s tests -p 'test_aios_*.py'` (`241` tests)
  - post-collect `python scripts/aios_monitor.py assess --write --json`
    reported `health=clear`
- Release: `python scripts/aios_dispatch.py release --dispatch-id asc-0119
  --reason "ASC-0119 OS activity evidence verified; GenesisOS invocation
  artifacts now count"` returned `status=released`.
- MemoryOS closeout writeback: draft `mem_561d7633490e0f56`.

## Work Packets

### WP-0119-A — codex@myworld fixes OS activity evidence

- target_agent: codex
- target_repo: myworld
- status: done
- depends_on: ASC-0103, ASC-0118
- brief: Add a small OS activity helper and wire self-check CROSS_OS_GHOST to
  it so GenesisOS invocation artifacts count as real OS participation.
- result: `.aios/outbox/myworld/asc-0119.myworld.result.json`
