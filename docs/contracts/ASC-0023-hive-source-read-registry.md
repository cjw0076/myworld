---
contract_id: ASC-0023
slug: hive-source-read-registry
status: closed
goal: Add a Hive source-read registry so runs can record which agents read which source artifacts and surface divergent interpretations.
created: 2026-05-12 02:06 KST
accepted: 2026-05-12 02:06 KST by codex acting operator
closed: 2026-05-12 02:11 KST
supersedes: none
---

# ASC-0023 Hive Source-Read Registry

## Goal

ASC-0022 selected `hivemind/docs/RADAR_GAP_TRIAGE.md` as the next
goal-aligned Hive packet. The remaining Hive-owned candidate is a source-read
registry: record which source artifacts each agent processed during a run and
surface shared-source divergent interpretations before they become implicit
operator memory.

## Scope

repos:

- `hivemind`
- `myworld`

allowed_files:

- `hivemind/hivemind/source_reads.py`
- `hivemind/hivemind/hive.py`
- `hivemind/hivemind/arrival_pack.py`
- `hivemind/tests/test_source_reads.py`
- `hivemind/docs/TODO.md`
- `hivemind/docs/AGENT_WORKLOG.md`
- `hivemind/.ai-runs/shared/comms_log.md`
- `docs/contracts/ASC-0023-hive-source-read-registry.md`
- `docs/contracts/README.md`
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

- **hive_mind.must_produce**:
  - source-read registry module and CLI;
  - per-run `artifacts/source_reads.json` schema;
  - summary that groups reads by source, agents, and interpretation hash;
  - divergence hints when multiple agents read one source and record distinct
    interpretations;
  - arrival-pack integration that surfaces source-read summary and
    reconciliation hints.
- **memoryos.must_produce**: no source change. Future contracts may import
  `SourceArtifact` records into MemoryOS.
- **capabilityos.must_produce**: no source change.
- **myworld.must_produce**: contract, dispatch packet, collect/release
  decision, ledger closeout, and monitor/readiness verification.
- **operator.must_produce**: release only if source-read records avoid raw
  source bodies and stay path/ref based.

## Verification Gate

```bash
cd /home/user/workspaces/jaewon/myworld/hivemind
python -m pytest tests/test_source_reads.py -v
python -m pytest tests/test_source_reads.py tests/test_arrival_pack.py -v
```

Operational smoke equivalent:

```bash
cd /home/user/workspaces/jaewon/myworld/hivemind
python -m hivemind.hive --root /tmp/hive-source-read-smoke run "source read smoke" --json
python -m hivemind.hive --root /tmp/hive-source-read-smoke source-read record --run RUN_ID --agent codex --source docs/example.md --interpretation implementation_view --json
python -m hivemind.hive --root /tmp/hive-source-read-smoke source-read summary --run RUN_ID --json
```

Expected evidence:

- registry JSON uses `schema_version=hive.source_reads.v1`.
- source records include source ref/id, agent, role, interpretation hash,
  verification state, and timestamp without raw source body.
- summary identifies shared sources and divergent interpretation candidates.
- arrival pack includes `source_reads` and blocks/recommends reconciliation
  when divergence exists.

## Stop Conditions

- `raw_source_body_leak`: registry stores full source document bodies.
- `private_path_commit`: raw exports, generated runs, logs, secrets, or local
  runtime state would be staged.
- `requires_memoryos`: source-read registry cannot function without MemoryOS.
- `run_fixture_mutation`: implementation mutates committed `.runs/**` fixtures
  instead of synthetic test roots.
- `scope_violation`: files outside `allowed_files` require edits.
- `no_arrival_pack_integration`: source-read data exists but incoming agents
  cannot see it in the arrival pack.

## Receipts

Closed 2026-05-12 02:11 KST by `codex@myworld` acting operator.

- Dispatch:
  - `.aios/inbox/hivemind/asc-0023.hivemind.json`
  - `.aios/outbox/hivemind/asc-0023.hivemind.result.json`
- `hivemind`: committed `f96fd57` (`Add source-read registry`) with:
  - `hivemind/source_reads.py`
  - `hivemind/hive.py`
  - `hivemind/arrival_pack.py`
  - `tests/test_source_reads.py`
  - `docs/TODO.md`
  - `docs/AGENT_WORKLOG.md`
  - `.ai-runs/shared/comms_log.md`
- Verification:
  - `cd hivemind && python -m pytest tests/test_source_reads.py -v` passed
    4/4.
  - `cd hivemind && python -m pytest tests/test_source_reads.py
    tests/test_arrival_pack.py -v` passed 9/9.
  - Operational CLI smoke under `/tmp/hive-source-read-smoke` recorded one
    source read and summarized `schema_version=hive.source_reads.v1` with
    `record_count=1`.
  - `git diff --check` passed in `hivemind`.
  - `python scripts/aios_dispatch.py collect --repo hivemind` collected the
    result packet as `passed`.
  - `python scripts/aios_dispatch.py release --dispatch-id asc-0023 --reason
    asc_0023_hive_source_read_registry_verified` succeeded.
  - `python scripts/aios_monitor.py assess --json` returned `health=clear`.
- Stop conditions triggered: none.

## Work Packets

### WP-0023-A — Codex@hivemind implements source-read registry

- target_agent: codex
- target_repo: hivemind
- status: done
- issued: 2026-05-12
- accepted: 2026-05-12 02:07 KST
- closed: 2026-05-12 02:10 KST
- depends_on: ASC-0021, ASC-0022
- brief: |
    Implement Hive source-read registry and CLI, then surface its summary in
    arrival packs. Keep the registry path/ref based, do not store raw source
    bodies, and use synthetic test roots.
- result: committed `f96fd57`; source-read tests passed 4/4 and
  source-read+arrival-pack tests passed 9/9.

### WP-0023-B — Codex@myworld collects and releases source-read result

- target_agent: codex
- target_repo: myworld
- status: done
- issued: 2026-05-12
- accepted: 2026-05-12 02:10 KST
- closed: 2026-05-12 02:11 KST
- depends_on: WP-0023-A
- brief: |
    Collect the Hive result packet, run monitor/readiness checks, update
    contract receipts and ledger, then release or hold ASC-0023.
- result: dispatch collected and released; see Receipts.
