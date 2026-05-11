---
contract_id: ASC-0001
slug: memoryos-hivemind-loop
status: accepted
goal: Codify the existing MemoryOS <-> Hive Mind memory loop as a reviewable,
  gated, stop-conditioned cross-OS contract.
created: 2026-05-11 21:32 KST
accepted: 2026-05-11 KST
closed:
supersedes:
---

# ASC-0001 MemoryOS <-> Hive Mind Loop

## Control Plane Position

`myworld` is the AIOS control plane for this contract. It issues the contract,
records operator decisions, and hands bounded work packets to the child repo
agents. It is not the worker that directly edits `hivemind` or `memoryOS`
source code.

Any implementation after this proposal is accepted must happen inside the
owning child repo by that repo's agent:

- Hive Mind agent owns `hivemind/` implementation and verification.
- MemoryOS agent owns `memoryOS/` implementation and review/provenance
  behavior.
- `myworld/` owns this contract file and contract lifecycle only.

## Goal

Lock down the existing loop:

```text
Hive run produces memory_drafts.json
  -> MemoryOS import-run imports drafts as draft MemoryObjects
  -> operator/agent review accepts selected drafts
  -> memoryos context build --for hive emits context JSON and RetrievalTrace
  -> Hive writes .runs/<run_id>/context_pack.md and run_state accepted_memories_used
  -> next Hive run can use accepted MemoryOS context
```

This is ASC-0001, rather than a CapabilityOS bootstrap, because this loop is
already substantively built: MemoryOS K57 covers the fixture/proof path and
Hive Mind has a gated memory-loop demo. ASC-0001 codifies current behavior so
future contracts, including ASC-0002 for CapabilityOS, can copy a concrete
surface instead of a speculative one.

## Design Answers

Q1: Is this contract codifying what currently works or forward-looking to K44?

Answer: ASC-0001 codifies what currently works. It intentionally excludes the
future K44 selected-memory snapshot behavior. If K44 changes the selected
memory snapshot or context provenance shape, that should be a new contract or
an explicit ASC-0001 revision after operator approval.

Q2: Where does the verification gate live?

Answer: The gate uses existing test surfaces, not a new `myworld` harness. Hive
Mind owns the end-to-end execution demo, so the primary gate is the existing
Hive `demo memory-loop` surface. MemoryOS owns provenance and review lifecycle,
so the same gate also cites the existing MemoryOS K57 fixture/proof surface for
accepted-memory provenance. `myworld` only records the commands and outcome.

Q3: How does the operator approve in practice?

Answer: Approval is a frontmatter status change from `proposed` to `accepted`
in this file, committed in git with an operator-approved message. Do not append
to `docs/AIOS_AGENT_LEDGER.md` at proposal time. A single ledger entry should
be written only when ASC-0001 is locked or closed, covering the accepted
contract snapshot and closeout evidence.

Counter-proposal note: CapabilityOS first executable surface remains important
for ASC-0002, but it should not precede ASC-0001. Codifying the existing
Hive-Memory loop first gives CapabilityOS a concrete route target and avoids
making the first contract depend on an unproven capability execution surface.

## Scope

repos:

- `hivemind`
- `memoryOS`

allowed_files:

- `hivemind/hivemind/memory_bridge.py`
- `hivemind/hivemind/harness.py`
- `hivemind/hivemind/quickstart.py`
- `hivemind/hivemind/hive.py`
- `hivemind/hivemind/run_validation.py`
- `hivemind/tests/test_quickstart.py`
- `hivemind/tests/test_production_hardening.py`
- `hivemind/tests/test_run_validation.py`
- `memoryOS/docs/HIVE_INTEGRATION.md`
- `memoryOS/docs/JSON_SCHEMAS.md`
- `memoryOS/memoryos/cli.py`
- `memoryOS/memoryos/schema.py`
- `memoryOS/memoryos/store.py`
- `memoryOS/tests/test_import_run.py`
- `memoryOS/tests/test_sprint4.py`
- `memoryOS/tests/fixtures/hive_runs/k57_loop/run_state.json`
- `memoryOS/tests/fixtures/hive_runs/k57_loop/memory_drafts.json`
- `memoryOS/tests/fixtures/hive_runs/k57_loop/transcript.md`

The listed files are the contract surface for child repo agents. `myworld` must
not directly patch those files under this contract; it may only issue a work
packet naming them.

forbidden_files:

- `CapabilityOS/README.md`
- `CapabilityOS/docs`
- `CapabilityOS/.gitignore`
- `hivemind/.runs`
- `hivemind/.ai-runs`
- `hivemind/.hivemind`
- `hivemind/.local`
- `hivemind/data`
- `memoryOS/.runs`
- `memoryOS/data`
- `memoryOS/raw_exports`
- `memoryOS/tests/fixtures/exports`
- `.env`
- `.env.*`
- `*.pt`
- `*.pth`
- `*.ckpt`
- `*.safetensors`

Runtime verification may create temporary run directories under system temp
locations or a command-specific `--root`. It must not commit `.runs/<other_runs>`
or raw exports.

## Responsibilities

### Hive Mind

responsibility: `plan_execute_verify`

must_produce:

- `.runs/<run_id>/memory_drafts.json` with a top-level `memory_drafts` array.
- Each memory draft should use the current Hive/MemoryOS draft shape:
  `type`, `content`, `origin`, `project`, `confidence`, `status`, `raw_refs`.
- `run_state.json` must preserve the MemoryOS context use fields written by
  the bridge:
  - `accepted_memories_used`
  - `memoryos_context.trace_id`
  - `memoryos_context.accepted_memory_ids`
  - `memoryos_context.context_items`
- `.runs/<run_id>/context_pack.md` when MemoryOS context is available. The
  pack must include `trace_id` and `accepted_memory_ids` from MemoryOS context
  output.
- Graceful degrade when MemoryOS is absent or disabled:
  - bridge status is `unavailable` or `failed`
  - `accepted_memory_ids` is an empty array
  - Hive execution remains nonblocking
  - `context_pack.md` records the reason without inventing memory

### MemoryOS

responsibility: `retrieve_remember_review`

must_produce:

- `memoryos import-run <run_ref> --json` K43.2 response with the stable nested
  field set:
  - `command`
  - `schema_version`
  - `timestamp`
  - `dry_run`
  - `status`
  - `run_refs.source_run_id`
  - `run_refs.import_run_id`
  - `run_refs.source_artifact_ids`
  - `run_refs.raw_ref_count`
  - `run_refs.raw_refs_included`
  - `counts.planned.source_artifacts`
  - `counts.planned.nodes`
  - `counts.planned.edges`
  - `counts.planned.memory_objects`
  - `counts.planned.hyperedges`
  - `counts.imported.source_artifacts`
  - `counts.imported.nodes`
  - `counts.imported.edges`
  - `counts.imported.memory_objects`
  - `counts.imported.hyperedges`
  - `counts.skipped.source_artifacts`
  - `counts.skipped.nodes`
  - `counts.skipped.edges`
  - `counts.skipped.memory_objects`
  - `counts.skipped.hyperedges`
  - `imported_ids.source_artifacts`
  - `imported_ids.nodes`
  - `imported_ids.edges`
  - `imported_ids.memory_objects`
  - `imported_ids.hyperedges`
  - `skipped_ids.source_artifacts`
  - `skipped_ids.nodes`
  - `skipped_ids.edges`
  - `skipped_ids.memory_objects`
  - `skipped_ids.hyperedges`
  - `warnings[].code`
  - `warnings[].message`
  - `warnings[].count`
- Imported Hive drafts become `MemoryObject` rows with `status="draft"` until
  reviewed. MemoryOS must not silently accept them.
- `memoryos context build --for hive --json` output with:
  - `trace_id`
  - `decisions`
  - `constraints`
  - `open_questions`
  - `recent_actions`
  - `other`
  - `raw_refs`
  - `total_accepted`
  - `total_available`
  - `excluded_items`
  - `context_items`
  - `token_estimate`
  - `signal_coverage`
  - `deduped_count`
- Append-only `RetrievalTrace` with:
  - `id`
  - `query`
  - `task`
  - `role`
  - `candidate_generators`
  - `selected`
  - `excluded`
  - `budget`
  - `privacy_filter`
  - `project`
  - `token_estimate`
  - `signal_coverage`
  - `deduped_count`
  - `attrs`
  - `schema_version`
  - `created_at`
- Selected accepted memory ids must resolve back to `MemoryObject` rows with
  source provenance through `source_run_id`, raw refs retained internally, and
  `derives_from` hyperedges or equivalent store provenance.

### CapabilityOS

responsibility: none for ASC-0001

must_produce:

- no capability plan
- no fallback plan
- no binding proposal
- no code, docs, catalog, MCP, API, or skill changes

CapabilityOS is explicitly out of scope. ASC-0002 should cover the first
CapabilityOS executable surface.

### Operator

responsibility: `release_revise_cancel`

acceptance criteria:

- status remains `proposed` until the operator accepts it.
- approval is a frontmatter status change to `accepted` plus a git commit.
- no ledger entry is written until the accepted snapshot or closeout is ready.
- any request to include CapabilityOS, K44 selected-memory snapshots, raw
  exports, or broad wildcard file scope requires a new operator checkpoint.

checkpoint conditions:

- scope expands beyond the listed files
- the verification gate needs a new harness instead of existing Hive/MemoryOS
  test surfaces
- MemoryOS import JSON or context JSON shape changes
- Hive run state stops recording `accepted_memories_used`
- accepted context references cannot be traced back to MemoryObjects and
  provenance

## Verification Gate

Single gate name: `ASC-0001 closed-loop proof`.

The gate uses existing surfaces only. It passes when the Hive demo closes the
loop and the MemoryOS K57 proof confirms accepted selected context has review
and provenance evidence.

Commands:

```bash
cd /home/user/workspaces/jaewon/myworld/hivemind
python -m pytest tests/test_quickstart.py::QuickstartDemoTest::test_memory_loop_demo_closes_isolated_feedback_loop

cd /home/user/workspaces/jaewon/myworld/memoryOS
python -m pytest tests/test_import_run.py::ImportRunTest::test_k57_hive_loop_reviewed_drafts_enter_hive_context tests/test_import_run.py::ImportRunTest::test_k57_hive_loop_proof_cli_json_suppresses_private_refs
```

Operational smoke equivalent:

```bash
cd /home/user/workspaces/jaewon/myworld/hivemind
python -m hivemind.hive --root /tmp/asc-0001-hive demo memory-loop --json

cd /home/user/workspaces/jaewon/myworld/memoryOS
python -m memoryos.cli harness hive-loop-proof --fixture tests/fixtures/hive_runs/k57_loop --json
```

Expected evidence:

- Hive report status is `closed_loop`.
- Hive second run context has non-empty `accepted_memory_ids`.
- Hive run state contains `accepted_memories_used` equal to selected MemoryOS
  ids.
- Hive writes `context_pack.md` with the MemoryOS trace id and accepted memory
  ids.
- MemoryOS proof status is `ok`.
- MemoryOS selected context ids include accepted imported memory ids.
- MemoryOS selected rows include review record provenance.
- Raw refs, transcript text, stdout/stderr, absolute local paths, and private
  exports are not emitted in operator JSON.

## Stop Conditions

Stop for operator checkpoint if any of these occurs:

- `privacy_violation`: raw private exports, secrets, transcript bodies,
  provider stdout/stderr, absolute local paths, or local-only data would enter
  shared docs or committed artifacts.
- `missing_import_run_json`: `memoryos import-run --json` is missing,
  malformed, non-K43.2, or lacks the stable fields listed above.
- `schema_drift`: Hive `memory_drafts.json` no longer matches MemoryOS importer
  expectations.
- `missing_provenance`: accepted memory is referenced in Hive context without
  resolving back to a MemoryObject and source provenance.
- `silent_acceptance`: MemoryOS imports Hive drafts as accepted memory without
  an explicit review record.
- `capabilityos_scope_creep`: any CapabilityOS file, binding, tool catalog, MCP
  surface, API route, or skill enters this contract.
- `wildcard_scope_creep`: implementation asks for broad `docs/**`, `src/**`,
  package-wide, or repo-wide edit scope.
- `new_harness_request`: closure requires a new `myworld` test harness instead
  of existing Hive/MemoryOS test surfaces.
- `dirty_target_conflict`: existing uncommitted child-repo edits touch target
  files and ownership is ambiguous.

## Work Packets After Acceptance

If accepted, `myworld` should issue two child-repo work packets instead of
editing child code directly:

Hive Mind work packet:

- target repo: `hivemind`
- owner: Hive Mind agent
- task: run the Hive side of `ASC-0001 closed-loop proof`, confirm graceful
  degrade and `accepted_memories_used`, and record results in repo-local
  worklog.

MemoryOS work packet:

- target repo: `memoryOS`
- owner: MemoryOS agent
- task: run the K57 import/review/context proof, confirm K43.2 JSON and
  RetrievalTrace provenance, and record results in repo-local worklog.

## Receipts

No receipts yet. This contract is `proposed`.

When accepted and executed, link evidence here instead of pasting raw logs:

- Hive Mind work packet:
- Hive Mind verification result:
- MemoryOS work packet:
- MemoryOS verification result:
- Accepted contract commit:
- Ledger closeout entry:
