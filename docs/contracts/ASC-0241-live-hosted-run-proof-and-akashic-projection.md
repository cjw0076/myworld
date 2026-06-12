---
contract_id: ASC-0241
slug: live-hosted-run-proof-and-akashic-projection
status: closed
goal: Prove AIOS world-readiness beyond marker evidence by running a real provider/local worker through Hive runtime isolation receipts and projecting the result into MemoryOS Akashic lineage.
created: 2026-06-12T23:55:00+09:00
closed: 2026-06-12T23:59:00+09:00
origin: ASC-0240 closed marker/schema-level hosted runtime isolation; live hosted-run proof remains unproven.
---

# ASC-0241 Live Hosted-Run Proof And Akashic Projection

## Why Now

`scripts/aios_world_readiness.py --json` now reports all seven readiness axes
as met. That is useful, but it is still marker-level readiness: the system has
the schemas, contracts, and verification surfaces. The next proof must show a
real Hive execution path writing runtime isolation receipts and MemoryOS
lineage references without relying on chat context.

## Scope

repos:

- `hivemind`
- `memoryOS`
- `myworld`

allowed_files:

- `hivemind/hivemind/**`
- `hivemind/tests/**`
- `hivemind/docs/**`
- `memoryOS/memoryos/**`
- `memoryOS/tests/**`
- `memoryOS/docs/**`
- `memoryOS/memory/akashic_work_index.jsonl`
- `docs/contracts/ASC-0241-live-hosted-run-proof-and-akashic-projection.md`
- `docs/AIOS_AGENT_LEDGER.md`
- `.aios/outbox/**`

forbidden_files:

- `.env`
- `.env.*`
- provider auth files
- credential vault contents
- raw provider logs
- private history stores
- unrelated child repo source files

## Substrate / Surface / Knowledge Gate

- schema_version: `aios.boundary_classifier.v1`
- layer: `execution_substrate + memory_lineage`
- owner_repo: `hivemind`
- supporting_repos: `memoryOS`, `myworld`
- substrate_level: `runtime`
- surface_type: `direct_hive_execution`
- knowledge_scope: `local_only`
- authority: `execute_with_receipt`
- required_receipts:
  - `runtime_scope_receipt`
  - `provider_or_local_worker_terminal_receipt`
  - `akashic_work_index_receipt`
  - `world_readiness_recheck`

## Required Work

Hive should wire one real provider/local worker path so it writes
`aios.hive_runtime_isolation_receipt.v1` automatically during execution or
prepare-only proof. The run should then be represented by a MemoryOS
`aios.akashic_work_index.v1` reference row.

The proof may use a deterministic local worker or dry-run provider path. It
must not require raw provider credentials and must not store raw stdout/stderr
or prompt bodies in shared docs.

## Acceptance Tests

1. A live or deterministic Hive run writes a runtime isolation receipt.
2. The receipt references credential refs only and contains no credential
   values.
3. The same work is represented by a MemoryOS Akashic work index row.
4. MyWorld can collect the result packet and rerun
   `scripts/aios_world_readiness.py --json`.
5. The final report distinguishes marker-level readiness from live deployment
   proof.

## Result

Hive provider passthrough now writes a runtime isolation receipt automatically
for native provider prepare/execute/policy-blocked paths. MyWorld now has
`scripts/aios_live_hosted_proof.py`, a replayable ASC-0241 proof that:

1. creates a deterministic Hive provider passthrough prepare run;
2. verifies the generated `aios.hive_runtime_isolation_receipt.v1`;
3. projects safe refs into MemoryOS `aios.akashic_work_index.v1`;
4. emits a compact proof payload without raw provider bodies or credential
   values.

Workspace proof:

- run id: `run_20260612_235914_2fd12a`
- runtime receipt:
  `hivemind/.runs/run_20260612_235914_2fd12a/runtime_isolation/provider_codex_native_01.json`
- provider result:
  `hivemind/.runs/run_20260612_235914_2fd12a/agents/codex/native/passthrough_01_result.yaml`
- Akashic index: `memoryOS/memory/akashic_work_index.jsonl`
- Akashic index id: `akashic_c12ae7508fd4cb1b`

Evidence:

- `python3 scripts/aios_live_hosted_proof.py --write-memory --json` passed and
  wrote the Akashic row.
- `python3 -m unittest tests.test_aios_live_hosted_proof -v` passed.
- `python -m pytest tests/test_provider_passthrough.py tests/test_cloud_isolation.py -q`
  passed 19/19 in `hivemind`.
- `memoryOS` reconstruction for `ASC-0241` reports `resumable=true`,
  one session, and `raw_bodies_stored=false`.

This closes live hosted-run proof for the deterministic prepare path. It does
not claim production hosting is complete; the next proof must cover packaging,
fresh-checkout install smoke, provider credential broker adoption, and hosted
worker backend selection.

## Stop Conditions

- `credential_value_in_runtime_receipt`
- `raw_provider_history_leak`
- `hosted_run_claim_without_runtime_receipt`
- `akashic_projection_missing`
- `child_repo_scope_violation`

## Return Packet

Write:

```text
.aios/outbox/hivemind/asc-0241.hivemind.result.json
```

with `status`, `changed_files`, `evidence`, `privacy_receipt`,
`runtime_receipt_ref`, `akashic_index_ref`, `world_readiness_recheck`, and
`next`.

## Next

Move to packaging/deployment evidence: clean commit scope, install script smoke
from a fresh checkout, provider credential broker adoption, and hosted worker
backend selection.
