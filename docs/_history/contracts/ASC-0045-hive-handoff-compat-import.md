---
contract_id: ASC-0045
slug: hive-handoff-compat-import
status: closed
goal: Add a Hive HANDOFF.json/shared-folder compatibility import so old MemoryOS pingpong loops can replay into Hive run artifacts.
created: 2026-05-12 20:18 KST
accepted: 2026-05-12 20:18 KST by codex acting operator
closed: 2026-05-12 20:31 KST
supersedes: none
---

# ASC-0045 Hive Handoff Compat Import

## Why Now

Goal evolution selected `hivemind/docs/RADAR_GAP_TRIAGE.md` as the next
unblocked Hive-owned candidate. The stale selected item in that file
(`arrival-pack`) is already closed by ASC-0021, and the source-read registry is
closed by ASC-0023. The next concrete remaining Hive-owned packet is
`HANDOFF.json`/shared-folder compatibility import so old MemoryOS pingpong loops
can be replayed into Hive run artifacts.

This improves AIOS repeatability: work that previously lived as a shared-folder
handoff can enter the same Hive run/inspect/verify surface as new runs.

## AIOS Inputs Used

- MemoryOS context build:
  `trace_id=rtrace_574a26fbfc3f431c`, selected accepted memory
  `mem_90b5cfe6570e6ee2`.
- CapabilityOS route:
  `cap_memoryos_import_run`, `cap_hivemind_execution_harness`,
  `cap_memoryos_context_build`, `cap_capabilityos_recommendation`, and
  `cap_web_research_route`. The web route is not needed for execution.
- Hive Mind dry-run:
  `run_20260512_201717_8efb3e`, prepared under
  `/tmp/asc-0045-hive-dry-run` for planning evidence only.

## Semantic Handshake

```text
semantic_handshake:
  contract_id: ASC-0045
  target_repo: hivemind
  terms_confirmed:
    - AIOS smart contract
    - dispatch packet
    - memory draft
    - capability route
    - hive execution
    - stop condition
  ambiguous_terms: []
```

## Scope

repos:

- `hivemind`
- `myworld`

allowed_files:

- `hivemind/hivemind/handoff_import.py`
- `hivemind/hivemind/hive.py`
- `hivemind/hivemind/run_validation.py`
- `hivemind/tests/test_handoff_import.py`
- `hivemind/docs/TODO.md`
- `hivemind/docs/AGENT_WORKLOG.md`
- `hivemind/.ai-runs/shared/comms_log.md`
- `docs/contracts/ASC-0045-hive-handoff-compat-import.md`
- `docs/contracts/README.md`
- `docs/goals/AIOS-GOAL-0001-make-something-great.md`
- `docs/AIOS_AGENT_LEDGER.md`

forbidden_files:

- `hivemind/.runs/**`
- `hivemind/data/**`
- `hivemind/raw_exports/**`
- `hivemind/exports/**`
- `hivemind/logs/**`
- `hivemind/weights/**`
- `hivemind/.env`
- `hivemind/.env.*`
- `memoryOS/**`
- `CapabilityOS/**`
- `uri/**`
- `.aios/logs/**`
- `.aios/state/**`
- `.aios/inbox/**`
- `.aios/outbox/**`
- `.env`
- raw export paths

## Responsibilities

### hive_mind.must_produce

- A compatibility importer that reads a `HANDOFF.json` file or a shared-folder
  handoff directory and writes privacy-safe Hive run artifacts.
- A CLI surface, preferably
  `python -m hivemind.hive handoff import <path> --root <root> --json`.
- Imported artifacts that make old pingpong state inspectable without requiring
  MemoryOS or CapabilityOS to be installed.
- Path/ref-based summaries only; do not ingest raw provider logs, private
  exports, or arbitrary shared-folder bodies.
- Tests with synthetic temporary roots and redacted fixture content.

### memoryos.must_produce

- No source change. MemoryOS provides context evidence only. The importer may
  preserve MemoryOS pingpong vocabulary as Hive artifact fields, but it must not
  accept memory or mutate MemoryOS stores.

### capabilityos.must_produce

- No source change. CapabilityOS provided a recommendation-only route. The
  selected execution route is local Hive implementation plus MemoryOS import
  compatibility awareness.

### myworld.must_produce

- This accepted contract.
- A Hive dispatch packet or equivalent child-repo work record.
- Collection/release evidence, final receipts, contract closeout, README index,
  and ledger entry after verification.

### operator.must_produce

- Release only if the CLI imports a synthetic handoff into a Hive run directory,
  tests pass, no raw private shared-folder data is committed, and monitor is
  clear.

## Verification Gate

```bash
cd /home/user/workspaces/jaewon/myworld/hivemind
python -m pytest tests/test_handoff_import.py -v
python -m hivemind.hive --root /tmp/asc-0045-handoff-smoke handoff import /tmp/asc-0045-handoff-fixture/HANDOFF.json --json
python -m hivemind.hive --root /tmp/asc-0045-handoff-smoke inspect RUN_ID_FROM_IMPORT --json
```

Pass criteria:

- Import output includes a Hive `run_id`, imported source metadata, and an
  artifact path/ref list without raw shared-folder bodies.
- The imported run is inspectable through the existing Hive inspect surface.
- The importer degrades cleanly on missing optional fields and fails clearly on
  malformed JSON.
- Tests use synthetic fixtures and do not mutate committed `.runs/**`.

## Stop Conditions

- `raw_shared_folder_body_leak`: importer stores raw provider logs, prompts,
  stdout/stderr bodies, or private export bodies.
- `memoryos_mutation`: importer writes to MemoryOS stores or accepts memory.
- `capability_binding_without_review`: importer binds or executes external
  tools based on CapabilityOS recommendations.
- `run_fixture_mutation`: implementation mutates committed `.runs/**` fixtures.
- `scope_violation`: implementation needs files outside `allowed_files`.
- `inspect_not_supported`: imported output cannot be inspected through Hive.
- `verification_gate_failed`: focused tests or smoke check fail.
- `monitor_not_clear`: myworld monitor reports active alerts at closeout.

## Receipts

Closed 2026-05-12 20:31 KST by `codex@myworld` acting operator.

- Dispatch:
  - `.aios/inbox/hivemind/asc-0045.hivemind.json`
  - `.aios/outbox/hivemind/asc-0045.hivemind.result.json`
- `hivemind`: committed `26a2209` (`Add HANDOFF compatibility import`) with:
  - `hivemind/handoff_import.py`
  - `hivemind/hive.py`
  - `hivemind/run_validation.py`
  - `tests/test_handoff_import.py`
  - `docs/TODO.md`
  - `docs/AGENT_WORKLOG.md`
  - `.ai-runs/shared/comms_log.md`
- Verification:
  - `cd hivemind && python -m pytest tests/test_handoff_import.py -v`
    passed 4/4.
  - `cd hivemind && python -m pytest tests/test_handoff_import.py
    tests/test_inspect.py -v` passed 15/15.
  - `cd hivemind && python -m hivemind.hive --root
    /tmp/asc-0045-handoff-smoke handoff import docs/HANDOFF.json --json`
    imported `run_20260512_202643_5921bf` with
    `schema_version=hive.handoff_import.v1`.
  - `cd hivemind && python -m hivemind.hive --root
    /tmp/asc-0045-handoff-smoke inspect run_20260512_202643_5921bf --json`
    returned `status=imported`, `validation_verdict=pass`, and
    `verdict=clean`.
  - `cd hivemind && python -m pytest` passed 310/310.
  - `cd hivemind && git diff --check` passed.
- Stop conditions triggered: none.

## Work Packets

### WP-0045-A — Codex@hivemind implements HANDOFF compatibility import

- target_agent: codex
- target_repo: hivemind
- status: done
- issued: 2026-05-12
- accepted: 2026-05-12 20:19 KST
- closed: 2026-05-12 20:28 KST
- depends_on: ASC-0021, ASC-0023
- brief: |
    Read `AGENTS.md`, `docs/TODO.md`, `docs/HANDOFF.json`,
    `docs/RADAR_GAP_TRIAGE.md`, `hivemind/hive.py`, and the existing
    inspect/run artifact helpers. Implement a local Hive import surface for
    old MemoryOS-style `HANDOFF.json` or shared-folder handoff directories.
    The importer must write a Hive run that can be inspected, must use
    synthetic tests, and must not store raw provider/private bodies.
- result: committed `26a2209`; focused tests passed 4/4 and full Hive pytest
  passed 310/310.

### WP-0045-B — Codex@myworld collects and releases HANDOFF import result

- target_agent: codex
- target_repo: myworld
- status: done
- issued: 2026-05-12
- accepted: 2026-05-12 20:28 KST
- closed: 2026-05-12 20:31 KST
- depends_on: WP-0045-A
- brief: |
    Verify the Hive result, collect or write the result packet, update receipts
    and the contract index, append the ledger closeout, and release or hold the
    contract based on monitor evidence.
- result: dispatch result written, receipts linked, monitor checked, and
  contract released; see Receipts.
