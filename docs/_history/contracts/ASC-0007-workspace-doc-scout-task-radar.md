---
contract_id: ASC-0007
slug: workspace-doc-scout-task-radar
status: closed
goal: Add a control-plane doc scout that searches jaewon workspace docs and turns signals into an AIOS task radar and next contract candidates.
created: 2026-05-11 22:28 KST
accepted: 2026-05-11 22:28 KST by codex acting operator
closed: 2026-05-11 22:34 KST
supersedes: none
---

# ASC-0007 Workspace Doc Scout Task Radar

## Control Plane Position

`myworld` owns this contract. It scans documentation surfaces to propose work;
it does not edit child repo implementation files and does not ingest raw
private exports into shared docs.

This is the first post-L6 continuation contract. ASC-0006 proved one repeatable
AIOS loop. ASC-0007 keeps the loop alive by finding the next contractable work
from the workspace itself.

## Goal

Create a local scout command:

```bash
cd /home/user/workspaces/jaewon/myworld
python scripts/aios_doc_scout.py --root /home/user/workspaces/jaewon --write docs/AIOS_TASK_RADAR.md --json
```

The command must:

- scan workspace documentation files;
- exclude runtime, dependency, raw-data, and secret-bearing paths;
- emit a machine-readable report with task signals and proposed next contracts;
- write a human-readable `docs/AIOS_TASK_RADAR.md`;
- store paths, headings, line numbers, and signal labels only, not raw document
  bodies.

## Scope

repos:

- `myworld`

allowed_files:

- `scripts/aios_doc_scout.py`
- `tests/test_aios_doc_scout.py`
- `docs/AIOS_TASK_RADAR.md`
- `docs/AIOS_WORK_DISPATCH.md`
- `docs/contracts/ASC-0007-workspace-doc-scout-task-radar.md`
- `docs/contracts/README.md`
- `docs/AIOS_AGENT_LEDGER.md`
- `scripts/aios_pingpong.sh`

forbidden_files:

- `hivemind/**`
- `memoryOS/**`
- `CapabilityOS/**`
- `.aios/**`
- `.runs/**`
- `.agent/**`
- `.claude/**`
- `data/**`
- `raw_exports/**`
- `exports/**`
- `node_modules/**`
- `.conda/**`
- `site-packages/**`
- `.ai-runs/**`
- `runs/**`
- `logs/**`
- `outputs/**`
- `results/**`
- `checkpoints/**`
- `weights/**`
- `**/*secret*`
- `**/*credential*`
- `.env`
- `.env.*`

## Per-OS Responsibility

- **myworld.must_produce**: doc scout CLI, regression test, task radar markdown,
  ASC-0007 closeout, and ledger entry.
- **hive_mind.must_produce**: no source change; future contract candidates may
  route executable work to Hive after this scout identifies it.
- **memoryos.must_produce**: no source change; ASC-0008 should decide how task
  radar entries become reviewed context with provenance.
- **capabilityos.must_produce**: no source change; ASC-0009 should decide how
  task radar and dispatch results become capability observations.
- **operator.must_produce**: release the scout only if it is privacy-bounded
  and produces concrete next contracts instead of vague summaries.

## Design Answers

Q1. Scope is "what currently works plus post-L6 continuation", not a full
semantic planner. The scout should produce contract candidates from docs; it
must not claim it has selected or executed the work.

Q2. The verification gate lives in existing myworld unittest and CLI surfaces.
This is control-plane behavior, so no new harness is introduced and child repo
tests are not required.

Q3. Acting-operator approval follows the contract README convention:
frontmatter `status: accepted` plus git commit. Ledger is written only at
closeout.

## Verification Gate

```bash
cd /home/user/workspaces/jaewon/myworld
bash -n scripts/aios_pingpong.sh
bash -n scripts/aios_child_watcher.sh
python -m py_compile scripts/aios_doc_scout.py scripts/aios_readiness.py scripts/aios_dispatch.py scripts/aios_loop.py scripts/aios_monitor.py
python -m unittest tests/test_aios_doc_scout.py tests/test_aios_readiness.py tests/test_aios_dispatch.py tests/test_aios_loop.py tests/test_aios_monitor.py
python scripts/aios_doc_scout.py --root /home/user/workspaces/jaewon --limit 40 --write docs/AIOS_TASK_RADAR.md --json
```

Expected evidence:

- unit tests pass;
- JSON output has `schema_version: aios.doc_scout.v1`, counts, top task
  signals, and proposed next contracts;
- `docs/AIOS_TASK_RADAR.md` exists and contains proposed ASC-0008..ASC-0010
  candidates, plus follow-up candidates when enough signals exist;
- generated `docs/AIOS_TASK_RADAR.md` is excluded from future scout input so
  the loop does not amplify its own summary;
- output excludes raw-data and dependency paths and does not paste document
  bodies.

## Stop Conditions

- `privacy_violation`: scout output includes secrets, raw exports, full private
  message bodies, or `.env` values.
- `scope_violation`: this contract edits child repo source instead of only
  scanning docs and writing myworld control-plane artifacts.
- `dependency_noise`: dependency/cache documentation dominates the radar.
- `raw_data_scan`: paths under `data`, `raw_exports`, or similar private stores
  are scanned.
- `contract_candidate_absent`: scout produces a summary but no concrete next
  contract candidates.
- `chat_context_dependency`: the output requires chat history to interpret.

## Receipts

Closed 2026-05-11 22:34 KST by `codex@myworld` acting operator.

- Implemented `scripts/aios_doc_scout.py`.
- Added `tests/test_aios_doc_scout.py`.
- Generated `docs/AIOS_TASK_RADAR.md`.
- Updated `scripts/aios_pingpong.sh` so post-L6 continuation is explicit via
  `AIOS_CONTINUE_AFTER_READY=1`.
- Verification:
  - `bash -n scripts/aios_pingpong.sh` passed.
  - `bash -n scripts/aios_child_watcher.sh` passed.
  - `python -m py_compile scripts/aios_doc_scout.py scripts/aios_readiness.py scripts/aios_dispatch.py scripts/aios_loop.py scripts/aios_monitor.py` passed.
  - `python -m unittest tests/test_aios_doc_scout.py tests/test_aios_readiness.py tests/test_aios_dispatch.py tests/test_aios_loop.py tests/test_aios_monitor.py` -> 16 tests OK.
  - `python scripts/aios_doc_scout.py --root /home/user/workspaces/jaewon --limit 40 --write docs/AIOS_TASK_RADAR.md --json` produced `schema_version=aios.doc_scout.v1`, scanned 1679 docs, found 1067 docs with signals, and proposed ASC-0008..ASC-0012.
- Stop conditions triggered: none.

## Work Packets

### WP-0007-A — Codex implements doc scout

- target_agent: codex
- target_repo: myworld
- status: done
- issued: 2026-05-11
- accepted: 2026-05-11 22:28 KST
- closed: 2026-05-11 22:34 KST
- depends_on: ASC-0006
- brief: |
    Implement `scripts/aios_doc_scout.py`, `tests/test_aios_doc_scout.py`, and
    generate `docs/AIOS_TASK_RADAR.md`. The scout must search documentation
    under `/home/user/workspaces/jaewon` while excluding runtime, dependency,
    raw-data, and secret-bearing paths. It must produce concrete next contract
    candidates and preserve the myworld control-plane boundary.
- result: implemented and verified; see Receipts.
