---
contract_id: ASC-0013
slug: workspace-instruction-index
status: closed
goal: Index AGENTS, CLAUDE, CODEX, CURRENT, and repo ownership rules into a control-plane instruction map.
created: 2026-05-11 23:00 KST
accepted: 2026-05-11 23:00 KST by codex acting operator
closed: 2026-05-11 23:02 KST
supersedes: none
---

# ASC-0013 Workspace Instruction Index

## Goal

Build a metadata-only instruction index so future agents can find repo-local
rules without chat context.

## Scope

repos:

- `myworld`

allowed_files:

- `scripts/aios_instruction_index.py`
- `tests/test_aios_instruction_index.py`
- `docs/AIOS_INSTRUCTION_INDEX.md`
- `docs/contracts/ASC-0013-workspace-instruction-index.md`
- `docs/contracts/README.md`
- `docs/AIOS_AGENT_LEDGER.md`

forbidden_files:

- `hivemind/**`
- `memoryOS/**`
- `CapabilityOS/**`
- `.aios/**`
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

- **myworld.must_produce**: instruction-index CLI, tests, markdown index,
  contract closeout, and ledger entry.
- **hive_mind.must_produce**: no source change.
- **memoryos.must_produce**: no source change.
- **capabilityos.must_produce**: no source change.
- **operator.must_produce**: release only if output is metadata-only and
  excludes runtime/raw/private paths.

## Verification Gate

```bash
cd /home/user/workspaces/jaewon/myworld
python -m unittest tests/test_aios_instruction_index.py
python scripts/aios_instruction_index.py --root /home/user/workspaces/jaewon/myworld --write docs/AIOS_INSTRUCTION_INDEX.md --json
```

Expected evidence:

- unittest passes;
- JSON output has `schema_version=aios.instruction_index.v1`;
- markdown output exists;
- output includes repo instruction surfaces and excludes runtime/raw/private
  paths.

## Stop Conditions

- `private_content_leak`: output includes raw private content, secrets, or full
  instruction bodies.
- `runtime_path_indexed`: `.aios`, `.ai-runs`, `.runs`, `data`, exports, logs,
  or weights appear in output.
- `child_repo_source_edit`: contract edits child repo implementation files.
- `chat_context_dependency`: future agents need chat history to interpret the
  index.

## Receipts

Closed 2026-05-11 23:02 KST by `codex@myworld` acting operator.

- Implemented `scripts/aios_instruction_index.py`.
- Added `tests/test_aios_instruction_index.py`.
- Generated `docs/AIOS_INSTRUCTION_INDEX.md`.
- Verification:
  - `python -m py_compile scripts/aios_instruction_index.py` passed.
  - `python -m unittest tests/test_aios_instruction_index.py` passed 2/2.
  - `python scripts/aios_instruction_index.py --root /home/user/workspaces/jaewon/myworld --write docs/AIOS_INSTRUCTION_INDEX.md --json` produced `schema_version=aios.instruction_index.v1`, 12 instruction files, and by-domain counts for myworld, hivemind, memoryOS, and CapabilityOS.
  - Full myworld unittest suite passed 23 tests.
  - `python scripts/aios_dispatch.py watch --repo myworld --dispatch-id asc-0013 --once` passed; collect/release succeeded with reason `asc_0013_instruction_index_verified`.
- Stop conditions triggered: none.

## Work Packets

### WP-0013-A — Codex@myworld implements instruction index

- target_agent: codex
- target_repo: myworld
- status: done
- issued: 2026-05-11
- accepted: 2026-05-11 23:00 KST
- closed: 2026-05-11 23:02 KST
- depends_on: ASC-0007, ASC-0012
- brief: |
    Implement metadata-only instruction index over workspace instruction files.
    Do not read or emit raw private/runtime content.
- result: implemented, verified, collected, and released; see Receipts.
