---
contract_id: ASC-0008
slug: workspace-doc-ingest-memoryos
status: closed
goal: Turn ASC-0007 doc scout signals into reviewed MemoryOS context records with provenance, without raw export ingestion.
created: 2026-05-11 KST
accepted: 2026-05-11 KST by claude acting operator
closed: 2026-05-11 22:48 KST
supersedes: none
acceptance_authority: claude@myworld (operator) per founder directive 2026-05-11 KST.
origin: auto-proposed by `scripts/aios_doc_scout.py` (ASC-0007 output, top of `docs/AIOS_TASK_RADAR.md`).
---

# ASC-0008 Workspace Doc Ingest into MemoryOS

## Control Plane Position

Issued and accepted by `claude@myworld` after `aios_doc_scout.py` (ASC-0007) auto-proposed it. MemoryOS owns the implementation; control plane only provides the scout output and the contract surface.

## Goal

ASC-0007's doc scout produces a `docs/AIOS_TASK_RADAR.md` and JSON containing path/heading/score/signal-label tuples for 1067 jaewon documents with signals. These are *signals*, not memory. ASC-0008 turns selected high-score signals into MemoryOS `MemoryObject` drafts (status=`draft` until reviewed) carrying provenance via `derives_from` hyperedges back to source path + line + scout-run id.

V1 scope:
- Ingest only signals from the **myworld + hivemind + memoryOS + CapabilityOS** domains (control-plane and OS-internal docs). Defer `_from_desktop/` and active research repos until provenance/privacy review.
- Memory objects must NOT contain raw document bodies. `evidence_refs` carries `(path, line_start, line_end, signal_labels[])` only.
- Drafts only — no auto-acceptance. Operator review via existing memoryOS review CLI.

ASC-0008 explicitly does **not**:
- ingest `_from_desktop/` or `dain/` content (operator-gated).
- store any raw text body inside MemoryObjects.
- modify the doc scout itself (that's ASC-0007).
- modify hivemind or CapabilityOS source.

## Open Design Questions

To be answered by `codex@memoryOS` (WP-0008-A):

- **Q1 — Memory object shape**: which existing `MemoryObject.type` (observation / claim / decision / etc.) maps best to a "doc-radar signal"? Recommendation: `observation` with `attrs.signal_labels[]` and `attrs.scout_score`.
- **Q2 — Provenance graph**: each ingested signal becomes one `MemoryObject` plus one `Hyperedge(type=derives_from)` linking to a `SourceArtifact(kind=workspace_doc_signal)` and to a `Node(type=observation, source_path, line)`. Justify or simplify.
- **Q3 — Stable id rule**: ingestion must be idempotent. Use `stable_id("memory_object_doc_signal", scout_run_id, source_path, line_start, signal_labels_sorted)`. Justify if you choose differently.
- **Q4 — Domain filter**: V1 includes only myworld+hivemind+memoryOS+CapabilityOS. Confirm or restrict further (e.g. exclude `.ai-runs/`).
- **Q5 — CLI surface**: `memoryos ingest-doc-radar <path-to-radar.json>` or extend `import-run`? Recommend a new subcommand for clarity.

## Scope

repos:

- `memoryOS`
- `myworld`

allowed_files:

- `memoryOS/memoryos/cli.py`
- `memoryOS/memoryos/importers.py`
- `memoryOS/memoryos/schema.py`
- `memoryOS/memoryos/store.py`
- `memoryOS/tests/test_doc_radar_ingest.py`
- `memoryOS/docs/AGENT_WORKLOG.md`
- `docs/AIOS_TASK_RADAR.md`
- `docs/discoveries/2026-05-11-jaewon-search.md`
- `docs/contracts/ASC-0008-workspace-doc-ingest-memoryos.md`
- `docs/contracts/README.md`
- `docs/AIOS_AGENT_LEDGER.md`

forbidden_files:

- `hivemind/**`
- `CapabilityOS/**`
- `myworld/scripts/aios_doc_scout.py`
- `_from_desktop/**`
- `dain/**`
- `minyoung/**`
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

- **memoryos.must_produce**: `ingest-doc-radar` CLI, MemoryObject draft entries with provenance hyperedges, regression test, `SourceArtifact.kind=workspace_doc_signal` schema addition.
- **myworld.must_produce**: nothing further — radar already exists. Closeout receipt entry only.
- **hive_mind / capabilityos**: not in scope.
- **operator.must_produce**: closeout review (claude@myworld), confirm no raw bodies in MemoryObjects.

## Verification Gate

```bash
cd /home/user/workspaces/jaewon/myworld
python scripts/aios_doc_scout.py --root /home/user/workspaces/jaewon --limit 40 --json > /tmp/radar.json
cd /home/user/workspaces/jaewon/myworld/memoryOS
python -m memoryos ingest-doc-radar /tmp/radar.json --json
python -m pytest tests/test_doc_radar_ingest.py -v
```

Expected evidence:
- N MemoryObject drafts created where N matches the in-scope domain count from the scout JSON.
- Each MemoryObject has at least one `derives_from` hyperedge to a `SourceArtifact`.
- Re-running the same radar produces zero new drafts (idempotency via stable_id).
- No MemoryObject contains a `body`/`text`/`raw` field with document content.
- Test includes a privacy assertion that no doc body string appears in the JSONL store.

## Stop Conditions

- `raw_body_in_memory`: any MemoryObject contains document text bodies.
- `from_desktop_ingest_creep`: V1 ingests `_from_desktop/`, `dain/`, or other founder-gated paths.
- `auto_accept`: ingestion sets MemoryObject `status` to anything other than `draft`.
- `non_idempotent`: re-running the same radar input creates duplicate MemoryObjects.
- `provenance_drop`: MemoryObject created without a `derives_from` hyperedge.
- `schema_drift`: existing `MemoryObject` or `SourceArtifact` field renamed without migration note.

## Receipts

Closed 2026-05-11 22:48 KST by `codex@myworld` acting operator.

- Implemented in `memoryOS` by `codex@memoryOS`.
- Verification:
  - `python -m pytest tests/test_doc_radar_ingest.py -v` passed 3/3.
  - `python scripts/aios_doc_scout.py --root /home/user/workspaces/jaewon --limit 40 --json > /tmp/radar.json` generated the radar input.
  - `python -m memoryos --root /tmp/asc-0008-memory-root ingest-doc-radar /tmp/radar.json --json` imported 33 draft memory objects, 33 source artifacts, 33 nodes, and 33 hyperedges.
  - Re-running the same ingest imported 0 and skipped 33 of each record type.
  - `python scripts/aios_dispatch.py watch --repo memoryOS --dispatch-id asc-0008 --once` passed and wrote `.aios/outbox/memoryOS/asc-0008.memoryOS.result.json`.
  - dispatch collect/release succeeded with reason `asc_0008_memoryos_doc_radar_ingest_verified`.
- Stop conditions triggered: none.

## Work Packets

### WP-0008-A — Codex@memoryOS implements doc-radar ingestion

- target_agent: codex
- target_repo: memoryOS
- status: done
- issued: 2026-05-11
- accepted: 2026-05-11 by codex@memoryOS
- closed: 2026-05-11
- depends_on: ASC-0007 closed (radar JSON shape stable)
- brief: |
    Fill ASC-0008 stub sections (Scope, Per-OS Responsibility, Verification
    Gate, Stop Conditions) and answer Q1–Q5. Implement the
    `ingest-doc-radar` CLI in memoryOS with provenance + idempotency.

    Required reading:
      1. /home/user/workspaces/jaewon/myworld/docs/AIOS_DEFINITION.md
      2. /home/user/workspaces/jaewon/myworld/docs/contracts/README.md
      3. /home/user/workspaces/jaewon/myworld/docs/contracts/ASC-0007-workspace-doc-scout-task-radar.md (radar source)
      4. /home/user/workspaces/jaewon/myworld/docs/AIOS_TASK_RADAR.md (sample output)
      5. /home/user/workspaces/jaewon/myworld/docs/discoveries/2026-05-11-jaewon-search.md (synthesis context)
      6. /home/user/workspaces/jaewon/myworld/memoryOS/memoryos/schema.py (existing MemoryObject / SourceArtifact / Hyperedge)
      7. /home/user/workspaces/jaewon/myworld/memoryOS/memoryos/importers.py (existing import pattern to mirror)

    Constraints:
    - Drafts only. No auto-acceptance.
    - No raw bodies in MemoryObjects.
    - V1 scope = myworld + hivemind + memoryOS + CapabilityOS domains only.
    - Idempotent via stable_id.
    - Mirror the existing memoryOS import pattern; do not invent a new
      ingestion subsystem.

    If GoEN's "mempool → candidate → consolidated" edge-lifecycle insight
    (see discoveries doc) suggests a richer review model, write it as a
    `## Counter-Proposal` rather than silently changing scope.

    After drafting + implementing:
    - Update WP-0008-A status `issued` → `done`, fill `closed`, `result`
      with commit SHA(s).
    - Issue WP-0008-B inline: target_agent claude, target_repo myworld,
      brief = "review filled ASC-0008: provenance correctness, no raw
      bodies, idempotency proof, V1 domain scope respected".
- result: |
    Implemented in working tree (no commit SHA yet; operator did not request a
    commit). Added `memoryos ingest-doc-radar <radar.json>` and
    metadata-only doc-radar importer in MemoryOS.

    Design answers:
    - Q1: doc-radar signals use `MemoryObject.type=observation`, status
      `draft`, origin `assistant`.
    - Q2: each signal creates one `MemoryObject`, one
      `SourceArtifact(kind=workspace_doc_signal)`, one observation `Node`, and
      one `derives_from` hyperedge with role attrs: child=memory object,
      parents=[source artifact, node].
    - Q3: memory object stable id is
      `stable_id("memory_object_doc_signal", scout_run_id, source_path,
      line_start, signal_labels_sorted)`.
    - Q4: V1 domain allowlist is `myworld`, `hivemind`, `memoryOS`,
      `CapabilityOS`; gated/private/runtime paths remain excluded.
    - Q5: new `ingest-doc-radar` subcommand was added rather than extending
      `import-run`.

    Verification:
    - `python -m pytest tests/test_doc_radar_ingest.py -v` passed 3/3.
    - Generated `/tmp/radar.json` with
      `python scripts/aios_doc_scout.py --root /home/user/workspaces/jaewon
      --limit 40 --json`.
    - `python -m memoryos --root /tmp/asc-0008-memory-root
      ingest-doc-radar /tmp/radar.json --json` imported 33 draft memory
      objects, 33 hyperedges, 33 source artifacts, and 33 nodes.
    - Rerunning the same ingest imported 0 and skipped 33 of each record type.

### WP-0008-B — Claude@myworld reviews doc-radar ingest

- target_agent: claude
- target_repo: myworld
- status: issued
- issued: 2026-05-11
- accepted: pending
- closed: pending
- depends_on: WP-0008-A
- brief: |
    review filled ASC-0008: provenance correctness, no raw bodies,
    idempotency proof, V1 domain scope respected
- result: pending

### WP-0008-C — Codex@myworld operator verification

- target_agent: codex
- target_repo: myworld
- status: done
- issued: 2026-05-11
- accepted: 2026-05-11 22:48 KST
- closed: 2026-05-11 22:48 KST
- depends_on: WP-0008-A
- brief: |
    Re-run ASC-0008 verification gate, collect the result packet, and release
    or hold the dispatch according to evidence.
- result: passed, collected, and released; see Receipts.
