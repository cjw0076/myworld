---
contract_id: ASC-0021
slug: hive-arrival-pack
status: closed
goal: Add a Hive arrival-pack surface that gives incoming agents a compact, privacy-safe run brief from live run state.
created: 2026-05-12 00:14 KST
accepted: 2026-05-12 00:14 KST by codex acting operator
closed: 2026-05-12 00:21 KST
supersedes: none
---

# ASC-0021 Hive Arrival Pack

## Goal

Hive Mind still has a live coordination gap: a new agent can arrive without a
compact brief of objective, current authority state, blocked work, accepted
facts, contested claims, scope hints, latest artifacts, and next commands.

This contract adds a repo-local `hive arrival-pack` surface that builds that
incoming-agent brief from current run state. It should reuse existing run
inspection/live data instead of inventing a second state model.

## Design Answers

- Q1: Scope is "what currently works", not the future K44/selected-memory
  snapshot. The selected-memory snapshot can improve pack richness later, but
  this packet must close against existing Hive artifacts today.
- Q2: The verification gate lives in existing `hivemind` tests and CLI smoke
  surfaces. A new myworld fixture would hide whether the child repo can operate
  independently.
- Q3: Operator approval is frontmatter status plus git commit. Result release
  is recorded through dispatch collect/release and final receipts, consistent
  with `docs/contracts/README.md`.

## Scope

repos:

- `hivemind`
- `myworld`

allowed_files:

- `hivemind/hivemind/arrival_pack.py`
- `hivemind/hivemind/hive.py`
- `hivemind/tests/test_arrival_pack.py`
- `hivemind/docs/TODO.md`
- `hivemind/docs/AGENT_WORKLOG.md`
- `hivemind/.ai-runs/shared/comms_log.md`
- `docs/contracts/ASC-0021-hive-arrival-pack.md`
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
  - `hivemind/arrival_pack.py` with a JSON-safe arrival pack builder.
  - CLI command `python -m hivemind.hive arrival-pack --run <run_id> --json`.
  - Pack fields for objective, run id, owners/agents, blocked items, accepted
    claims, contested claims, scope hints, latest artifacts, suggested
    commands, and privacy posture.
  - Graceful degrade when MemoryOS or CapabilityOS artifacts are missing.
  - No raw provider stdout/stderr bodies in arrival-pack output.
- **memoryos.must_produce**: no source change. Existing memory context, when
  attached to a Hive run, may be summarized by id/count/trace only.
- **capabilityos.must_produce**: no source change and no role in this contract.
  Capability route enrichment remains a future contract.
- **myworld.must_produce**: contract, dispatch packet, collect/release
  decision, ledger closeout, and monitor/readiness verification.
- **operator.must_produce**: release only if the pack is generated from current
  run artifacts, remains privacy-safe by default, and passes the Hive test/CLI
  gate.

## Verification Gate

```bash
cd /home/user/workspaces/jaewon/myworld/hivemind
python -m pytest tests/test_arrival_pack.py -v
```

Operational smoke equivalent:

```bash
cd /home/user/workspaces/jaewon/myworld/hivemind
python -m hivemind.hive --root /tmp/hive-arrival-pack-smoke run "arrival pack smoke" --json
python -m hivemind.hive --root /tmp/hive-arrival-pack-smoke arrival-pack --run RUN_ID_FROM_PREVIOUS_COMMAND --json
```

Expected evidence:

- JSON output has `kind=hive_arrival_pack` and a stable schema version.
- `objective`, `run_id`, `owners`, `blocked_items`, `accepted_claims`,
  `contested_claims`, `scope_hints`, `latest_artifacts`, and
  `suggested_commands` are present.
- Paths are hidden by default and shown only with an explicit debug option.
- Raw provider stdout/stderr bodies are not included.
- Missing MemoryOS/CapabilityOS artifacts do not fail pack generation.

## Stop Conditions

- `raw_provider_body_leak`: arrival pack includes raw stdout/stderr bodies or
  prompt text from provider artifacts.
- `requires_sibling_os`: pack generation fails when MemoryOS or CapabilityOS is
  absent.
- `run_fixture_mutation`: implementation mutates committed `.runs/**` fixtures
  instead of using synthetic test roots.
- `inspect_duplicate`: command only reprints `hive inspect` without
  incoming-agent fields.
- `scope_violation`: files outside `allowed_files` require edits.
- `schema_drift`: pack shape conflicts with existing `hive inspect`/`live`
  data in a way tests do not cover.
- `private_runtime_commit`: raw exports, generated runs, logs, secrets, or
  `.aios/**` runtime state would be staged.

## Receipts

Closed 2026-05-12 00:21 KST by `codex@myworld` acting operator.

- Dispatch:
  - `.aios/inbox/hivemind/asc-0021.hivemind.json`
  - `.aios/outbox/hivemind/asc-0021.hivemind.result.json`
- `hivemind`: committed `63ae099` (`Add arrival pack command`) with:
  - `hivemind/arrival_pack.py`
  - `hivemind/hive.py`
  - `tests/test_arrival_pack.py`
  - `docs/TODO.md`
  - `docs/AGENT_WORKLOG.md`
  - `.ai-runs/shared/comms_log.md`
- Verification:
  - `cd hivemind && python -m pytest tests/test_arrival_pack.py -v` passed
    5/5.
  - `cd hivemind && python -m pytest tests/test_arrival_pack.py
    tests/test_inspect.py -v` passed 16/16.
  - Operational CLI smoke created `/tmp/hive-arrival-pack-smoke` and
    `arrival-pack --json` returned `kind=hive_arrival_pack`,
    `paths_hidden=true`, and `blocked_items=0`.
  - `git diff --check` passed in `hivemind`.
  - `python scripts/aios_dispatch.py collect --repo hivemind` collected the
    result packet as `passed`.
  - `python scripts/aios_dispatch.py release --dispatch-id asc-0021 --reason
    asc_0021_hive_arrival_pack_verified` succeeded.
- Stop conditions triggered: none.

## Work Packets

### WP-0021-A — Codex@hivemind implements arrival pack

- target_agent: codex
- target_repo: hivemind
- status: done
- issued: 2026-05-12
- accepted: 2026-05-12 00:16 KST
- closed: 2026-05-12 00:20 KST
- depends_on: ASC-0020
- brief: |
    Read `docs/RADAR_GAP_TRIAGE.md`, `docs/HIVE_MIND_GAPS.md`,
    `docs/TODO.md`, `hivemind/inspect_run.py`, and `hivemind/hive.py`.
    Implement `hive arrival-pack` as a compact incoming-agent brief generated
    from current run state. Reuse existing live/inspect summaries where
    possible. Keep output privacy-safe by default, avoid raw provider bodies,
    and add focused tests under `tests/test_arrival_pack.py`.
- result: committed `63ae099`; `tests/test_arrival_pack.py` passed 5/5.

### WP-0021-B — Codex@myworld collects and releases arrival-pack result

- target_agent: codex
- target_repo: myworld
- status: done
- issued: 2026-05-12
- accepted: 2026-05-12 00:20 KST
- closed: 2026-05-12 00:21 KST
- depends_on: WP-0021-A
- brief: |
    Collect the Hive result packet, run the contract verification gate,
    update contract receipts and index, append the ecosystem ledger closeout,
    and release or hold ASC-0021.
- result: dispatch collected and released; see Receipts.
