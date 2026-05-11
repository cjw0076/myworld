---
contract_id: ASC-0025
slug: child-watcher-provider-fallback
status: closed
goal: Make child watcher implementation runs recover once from provider access-denied by trying an allowed alternate agent and recording structured fallback evidence.
created: 2026-05-12 02:26 KST
accepted: 2026-05-12 02:26 KST by codex acting operator
closed: 2026-05-12 02:29 KST
supersedes: none
---

# ASC-0025 Child Watcher Provider Fallback

## Goal

ASC-0020 and later ledger entries show that child watcher implementation runs
can fail at the provider CLI boundary with access denied, forcing manual
repo-local fallback work. That keeps AIOS at a fragile L6: the loop is
repeatable only when a human/operator notices the provider failure and reroutes
the work.

This contract adds one bounded automatic fallback inside the myworld child
watcher: if the assigned provider fails with an access/auth/permission-denied
class error, the watcher may try an allowed alternate agent once and record the
attempt chain in the result packet.

## Scope

repos:

- `myworld`

allowed_files:

- `scripts/aios_child_watcher.sh`
- `tests/test_aios_child_watcher.py`
- `docs/contracts/ASC-0025-child-watcher-provider-fallback.md`
- `docs/contracts/README.md`
- `docs/AIOS_AGENT_LEDGER.md`
- `docs/AIOS_WORK_DISPATCH.md`

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

## Design Decision

The fallback belongs in `scripts/aios_child_watcher.sh`, not in child repos.
The failure happens before repo-local code can act: the provider CLI does not
complete the bounded agent turn. A child repo should not be required to know how
to recover from a control-plane provider invocation failure.

Fallback is intentionally narrow:

- only one alternate provider attempt per packet;
- only for access/auth/permission-denied style failures;
- no fallback after timeout, unsupported agent, command missing, or ordinary
  child-agent failure;
- no raw stdout/stderr copied into durable result packets;
- full logs remain local under `.aios/logs/`.

## Per-OS Responsibility

- **myworld.must_produce**:
  - child watcher provider-failure classification;
  - one-shot alternate-agent retry for provider access-denied failures;
  - result packet fields that show attempted agents, final agent, fallback
    usage, and failure category;
  - tests using fake provider CLIs, not real Codex/Claude calls.
- **hive_mind.must_produce**: no source change.
- **memoryos.must_produce**: no source change.
- **capabilityos.must_produce**: no source change.
- **operator.must_produce**: release only if fallback behavior is proven by a
  local fake-provider test and monitor stays clear.

## Verification Gate

```bash
cd /home/user/workspaces/jaewon/myworld
python -m unittest tests/test_aios_child_watcher.py
python -m unittest tests/test_aios_instruction_index.py tests/test_aios_loop_policy.py tests/test_aios_doc_scout.py tests/test_aios_readiness.py tests/test_aios_dispatch.py tests/test_aios_loop.py tests/test_aios_monitor.py tests/test_aios_goal_evolution.py tests/test_aios_child_watcher.py
python scripts/aios_monitor.py assess --json
```

Additional operator syntax/status checks:

- `bash -n scripts/aios_child_watcher.sh`
- `scripts/aios_child_watcher.sh status`

Expected evidence:

- a fake assigned `codex` exits with an access-denied message;
- watcher tries fake `claude` once and writes a passed result packet;
- result JSON records `fallback_used=true`, attempted agents, final agent, and
  `failure_category=provider_access_denied` for the failed first attempt;
- non-access failures do not trigger fallback;
- no child repo source files are modified.

## Stop Conditions

- `child_repo_edit`: implementation touches `hivemind/`, `memoryOS/`, or
  `CapabilityOS/` source.
- `unbounded_retry`: watcher can loop across agents indefinitely.
- `fallback_on_timeout`: timeout triggers alternate provider execution.
- `fallback_on_unknown_failure`: ordinary child-agent failure triggers fallback.
- `raw_log_leak`: result packet includes raw stdout/stderr or full provider log.
- `monitor_blocked`: myworld monitor reports blocked after verification.

## Work Packets

### WP-0025-A — Codex@myworld adds child watcher provider fallback

- target_agent: codex
- target_repo: myworld
- status: done
- issued: 2026-05-12
- accepted: 2026-05-12 02:26 KST
- closed: 2026-05-12 02:29 KST
- depends_on: ASC-0024
- brief: |
    Add a bounded provider access-denied fallback to
    `scripts/aios_child_watcher.sh`, prove it with fake provider CLIs, and
    record the resulting behavior in myworld docs.
- result: dispatch collected and released; see Receipts.

## Receipts

Closed 2026-05-12 02:29 KST by `codex@myworld` acting operator.

- Dispatch:
  - `.aios/inbox/myworld/asc-0025.myworld.json`
  - `.aios/outbox/myworld/asc-0025.myworld.result.json`
- Implementation:
  - `scripts/aios_child_watcher.sh`
  - `tests/test_aios_child_watcher.py`
  - `docs/AIOS_WORK_DISPATCH.md`
- Verification:
  - `python -m unittest tests/test_aios_child_watcher.py` passed 2/2.
  - `python -m unittest tests/test_aios_instruction_index.py
    tests/test_aios_loop_policy.py tests/test_aios_doc_scout.py
    tests/test_aios_readiness.py tests/test_aios_dispatch.py
    tests/test_aios_loop.py tests/test_aios_monitor.py
    tests/test_aios_goal_evolution.py tests/test_aios_child_watcher.py`
    passed 37/37.
  - `bash -n scripts/aios_child_watcher.sh` passed.
  - `scripts/aios_child_watcher.sh status` returned all child repos
    `pending=0`.
  - `python scripts/aios_dispatch.py watch --repo myworld --dispatch-id
    asc-0025 --once` wrote a passed result packet.
  - `python scripts/aios_dispatch.py collect --repo myworld` collected the
    result packet.
  - `python scripts/aios_dispatch.py release --dispatch-id asc-0025 --reason
    asc_0025_child_watcher_provider_fallback_verified` succeeded.
  - `python scripts/aios_monitor.py assess --json` returned `health=clear`
    after release.
- Stop conditions triggered: none.
