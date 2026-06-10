---
contract_id: ASC-0006
slug: aios-l6-repeatable-proof
status: closed
goal: Add a machine-readable AIOS readiness gate that proves or blocks L6 repeatable completion.
created: 2026-05-11 22:18 KST
accepted: 2026-05-11 22:18 KST by codex acting operator
closed: 2026-05-11 22:20 KST
supersedes: none
---

# ASC-0006 AIOS L6 Repeatable Proof

## Control Plane Position

`myworld` owns this contract. It does not change child repo implementation.
It turns `docs/AIOS_DEFINITION.md` into an executable readiness gate so the
Codex/Claude operator loop cannot declare AIOS complete by intuition.

## Goal

Create a local readiness command that grades AIOS against L0-L6:

```bash
python scripts/aios_readiness.py --json
```

The command must return the current level, evidence, gaps, and the next
contract/action needed to advance. It is a gate, not a marketing summary.

## Scope

repos:

- `myworld`

allowed_files:

- `scripts/aios_readiness.py`
- `tests/test_aios_readiness.py`
- `docs/AIOS_DEFINITION.md`
- `docs/AIOS_WORK_DISPATCH.md`
- `docs/contracts/ASC-0006-aios-l6-repeatable-proof.md`
- `docs/contracts/README.md`
- `docs/AIOS_AGENT_LEDGER.md`

forbidden_files:

- `hivemind/**`
- `memoryOS/**`
- `CapabilityOS/**`
- `.runs/**`
- `raw_exports/**`
- `weights/**`
- `.env`
- `.env.*`

## Per-OS Responsibility

- **myworld.must_produce**: readiness script, regression test, contract closeout,
  and ledger record.
- **hive_mind.must_produce**: no source change; readiness may inspect dispatch
  and result evidence already returned by Hive.
- **memoryos.must_produce**: no source change; readiness may inspect dispatch
  and result evidence already returned by MemoryOS.
- **capabilityos.must_produce**: no source change; readiness may inspect closed
  CapabilityOS contracts and result evidence.
- **operator.must_produce**: release only if the script reaches L6; otherwise
  keep loop running and follow the emitted next action.

## Verification Gate

```bash
cd /home/user/workspaces/jaewon/myworld
python -m unittest tests/test_aios_readiness.py
python scripts/aios_readiness.py --json
```

Expected evidence:

- unit test passes;
- readiness output includes `level`, `level_name`, `evidence`, `gaps`, and
  `next_action`;
- if level is below L6, output names the missing invariant instead of claiming
  completion.

## Stop Conditions

- `overclaiming_aios_complete`: readiness says L6 while any necessary condition
  from `AIOS_DEFINITION.md` is missing.
- `child_repo_source_edit`: this contract modifies child repo source.
- `private_data_leak`: readiness output includes raw prompts, logs, exports, or
  secrets.
- `chat_context_dependency`: readiness can only be interpreted with chat
  history.

## Receipts

Closed 2026-05-11 22:20 KST by `codex@myworld` acting operator.

- Implemented `scripts/aios_readiness.py`.
- Added `tests/test_aios_readiness.py`.
- Verification:
  - `python -m py_compile scripts/aios_readiness.py scripts/aios_dispatch.py scripts/aios_loop.py scripts/aios_monitor.py` passed.
  - `python -m unittest tests/test_aios_readiness.py tests/test_aios_dispatch.py tests/test_aios_loop.py tests/test_aios_monitor.py` -> 14 tests OK.
  - First `python scripts/aios_readiness.py --json` correctly stopped at
    L5 because ASC-0006 was not yet closed.
- Stop conditions triggered: none.

## Work Packets

### WP-0006-A — Codex implements readiness gate

- target_agent: codex
- target_repo: myworld
- status: done
- issued: 2026-05-11
- accepted: 2026-05-11 22:18 KST
- closed: 2026-05-11 22:20 KST
- depends_on: ASC-0001..ASC-0005 closed
- brief: |
    Implement `scripts/aios_readiness.py` and `tests/test_aios_readiness.py`.
    The script must inspect local docs/contracts/dispatch state and map the
    current system to AIOS_DEFINITION.md L0-L6. It must not edit child repos or
    read private raw data. If AIOS is not L6, emit the next missing action.
- result: implemented and verified; see Receipts.
