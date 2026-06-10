---
contract_id: ASC-0015
slug: child-repo-dirty-triage
status: closed
goal: Resolve the remaining memoryOS and hivemind dirty files left after ASC-0012 and ASC-0014.
created: 2026-05-11 23:46 KST
accepted: 2026-05-11 23:46 KST by codex acting operator
closed: 2026-05-11 23:48 KST
supersedes: none
---

# ASC-0015 Child Repo Dirty Triage

## Goal

Turn the remaining child repo dirty state into explicit repo-local commits or
documented holds so the control-plane monitor reports only actionable drift.

ASC-0014 removed false monitor alerts. This contract handles the remaining real
dirty files:

- `memoryOS/docs/AGENT_WORKLOG.md`
- `memoryOS/data/README.md`
- `hivemind/.ai-runs/shared/comms_log.md`
- `hivemind/hivemind/harness.py`

## Scope

repos:

- `memoryOS`
- `hivemind`
- `myworld`

allowed_files:

- `memoryOS/docs/AGENT_WORKLOG.md`
- `memoryOS/data/README.md`
- `hivemind/.ai-runs/shared/comms_log.md`
- `hivemind/hivemind/harness.py`
- `docs/contracts/ASC-0015-child-repo-dirty-triage.md`
- `docs/contracts/README.md`
- `docs/AIOS_AGENT_LEDGER.md`

forbidden_files:

- `memoryOS/data/*` except `memoryOS/data/README.md`
- `memoryOS/memory/**`
- `memoryOS/ontology/**`
- `hivemind/.runs/**`
- `hivemind/.ai-runs/**` except `hivemind/.ai-runs/shared/comms_log.md`
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

- **memoryos.must_produce**: a scoped commit for the worklog and tracked
  `data/README.md` policy file, or a hold reason if either contains private
  material. Raw export files under `data/` must remain uncommitted.
- **hive_mind.must_produce**: a scoped commit for the ASC-0005 harness
  integration and repo-required shared comms log, or a hold reason if the
  harness diff is unrelated or tests fail.
- **capabilityos.must_produce**: no role in this contract.
- **operator.must_produce**: verify child repo statuses after commits, update
  myworld gitlinks, and close only when dirty state is reduced to ignored raw
  local data or zero alerts.

## Triage Decisions

- `memoryOS/docs/AGENT_WORKLOG.md`: commit. It is a repo-local worklog entry
  documenting ASC-0001 child watcher verification and contains no raw export
  body.
- `memoryOS/data/README.md`: commit. `memoryOS/.gitignore` explicitly ignores
  `data/*` while allowing only `!data/README.md`; this README is a policy file,
  not raw data.
- `hivemind/.ai-runs/shared/comms_log.md`: commit as a narrow exception. The
  file is already tracked, `hivemind/AGENTS.md` requires meaningful decisions
  there, and ASC-0005 previously allowed this exact shared log while keeping all
  other `.ai-runs/**` paths forbidden.
- `hivemind/hivemind/harness.py`: commit. The diff wires the existing
  `capability_bridge.py` into Hive route/external-agent prompt flow, which is
  required to make ASC-0005's stated receipts match durable code.

## Verification Gate

```bash
cd /home/user/workspaces/jaewon/myworld/memoryOS
git diff --check

cd /home/user/workspaces/jaewon/myworld/hivemind
python -m pytest tests/test_capability_bridge.py tests/test_quickstart.py -v

cd /home/user/workspaces/jaewon/myworld
python scripts/aios_monitor.py snapshot --json
python -m unittest tests/test_aios_monitor.py tests/test_aios_dispatch.py
```

Expected evidence:

- memoryOS commit includes only `docs/AGENT_WORKLOG.md` and `data/README.md`.
- memoryOS raw files under `data/` remain ignored/uncommitted.
- hivemind commit includes only `.ai-runs/shared/comms_log.md` and
  `hivemind/harness.py`.
- Hive capability bridge and quickstart tests pass.
- monitor child dirty alerts are cleared or reduced to ignored local raw data.

## Stop Conditions

- `private_data_in_commit`: raw export text, provider archives, secrets, or
  generated memory stores would be staged.
- `runtime_scope_creep`: any `.ai-runs/**` path other than the tracked shared
  comms log would be staged.
- `harness_test_failed`: ASC-0005 harness integration breaks quickstart or
  capability bridge tests.
- `unrelated_diff_detected`: a target file contains unrelated changes that
  cannot be separated by staging only intended paths.
- `capabilityos_reopened`: cleanup requires editing `CapabilityOS/**`.

## Receipts

Closed 2026-05-11 23:48 KST by `codex@myworld` acting operator.

- `memoryOS`: committed `f227454` (`Record child watcher verification docs`)
  with only `docs/AGENT_WORKLOG.md` and `data/README.md`. Raw exports under
  `data/*` remain ignored and uncommitted.
- `hivemind`: committed `101d769` (`Wire CapabilityOS bridge into harness`)
  with only `.ai-runs/shared/comms_log.md` and `hivemind/harness.py`.
- Verification:
  - `cd memoryOS && git diff --check` passed.
  - `cd hivemind && python -m pytest tests/test_capability_bridge.py tests/test_quickstart.py -v`
    passed 8/8.
  - `python scripts/aios_monitor.py snapshot --json` reports no child repo
    dirty alerts; only the pre-existing legacy ASC-0001 proposed-to-closed
    dispatch status alert remains.
- Stop conditions triggered: none.

## Work Packets

### WP-0015-A — Codex@memoryOS commits local dirty documentation

- target_agent: codex
- target_repo: memoryOS
- status: done
- issued: 2026-05-11
- accepted: 2026-05-11 23:46 KST
- closed: 2026-05-11 23:48 KST
- depends_on: ASC-0012
- brief: |
    Commit only `docs/AGENT_WORKLOG.md` and `data/README.md` after verifying
    no raw export body is included. Leave all other `data/*` files ignored and
    uncommitted.
- result: committed `f227454`; raw `data/*` files remain ignored.

### WP-0015-B — Codex@hivemind commits ASC-0005 residual dirty files

- target_agent: codex
- target_repo: hivemind
- status: done
- issued: 2026-05-11
- accepted: 2026-05-11 23:46 KST
- closed: 2026-05-11 23:48 KST
- depends_on: ASC-0005, ASC-0012
- brief: |
    Commit only `.ai-runs/shared/comms_log.md` and `hivemind/harness.py` after
    verifying the capability bridge and quickstart tests. Do not stage any
    other `.ai-runs/**` runtime files.
- result: committed `101d769`; Hive capability bridge tests passed.

### WP-0015-C — Codex@myworld closes monitor hygiene follow-up

- target_agent: codex
- target_repo: myworld
- status: done
- issued: 2026-05-11
- accepted: 2026-05-11 23:46 KST
- closed: 2026-05-11 23:48 KST
- depends_on: WP-0015-A, WP-0015-B
- brief: |
    Update the contract, contract README, ledger, and child repo gitlinks after
    child commits pass verification. Rerun monitor and myworld regression
    tests before closeout.
- result: child repos clean; myworld gitlinks and ledger updated.
