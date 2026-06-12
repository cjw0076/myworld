---
contract_id: ASC-0240
slug: hive-hosted-runtime-isolation-receipts
status: closed
goal: Define Hive-owned hosted runtime isolation receipts for filesystem, process, network, package, timeout, and degraded execution boundaries.
created: 2026-06-13T00:42:00+09:00
closed: 2026-06-13T00:50:00+09:00
origin: aios.world_readiness.v1 reports cloud_execution_isolation as partial after ASC-0239.
---

# ASC-0240 Hive Hosted Runtime Isolation Receipts

## Why Now

AIOS has local sandbox pieces such as `scripts/aios_sandbox.py`, but
world-deployable agent service readiness needs hosted execution receipts. A
provider/tool run must declare its filesystem, process, network, package, and
timeout boundaries before execution and emit a degraded or success receipt
afterward.

## Scope

repos:

- `hivemind`
- `myworld`

allowed_files:

- `hivemind/docs/**`
- `hivemind/tests/**`
- `hivemind/hivemind/**`
- `docs/contracts/ASC-0240-hive-hosted-runtime-isolation-receipts.md`
- `docs/AIOS_AGENT_LEDGER.md`

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
- layer: `execution_substrate`
- owner_repo: `hivemind`
- substrate_level: `runtime`
- surface_type: `direct_hive_execution`
- knowledge_scope: `local_only`
- authority: `execute_with_receipt`
- required_receipts:
  - `runtime_scope_receipt`
  - `sandbox_policy_receipt`
  - `network_policy_receipt`
  - `package_manifest_receipt`
  - `degraded_or_success_receipt`

## Required Work

Hive should define a receipt schema for hosted runtime execution that includes:

- `run_id`
- `work_id`
- `provider`
- `model_or_worker`
- `filesystem_scope`
- `process_scope`
- `network_policy`
- `package_manifest`
- `timeout_s`
- `credential_refs`
- `sandbox_backend`
- `started_at`
- `ended_at`
- `status`
- `degraded_reason`
- `verification_refs`

The receipt should use credential references only. It must not contain raw
secret values or raw provider transcripts.

## Acceptance Tests

Hive should prove:

1. A local sandboxed run emits a runtime scope receipt.
2. A network-denied run records `network_policy=denied` or equivalent.
3. A missing sandbox backend degrades fail-closed unless explicitly overridden.
4. Credential refs are allowed, credential values are rejected.
5. MyWorld `scripts/aios_world_readiness.py --json` can see dedicated hosted
   isolation evidence or receives a concrete blocker.

## MyWorld Verification Gate

```bash
python3 scripts/aios_world_readiness.py --json
python3 -m unittest tests.test_aios_world_readiness -v
git diff --check
```

## Result

Hive now owns `hivemind/hivemind/cloud_isolation.py`, which defines
`aios.hive_runtime_isolation_receipt.v1` for hosted execution boundaries.
The receipt records filesystem scope, process scope, network policy, package
manifest, timeout, credential references, sandbox backend, status,
degraded reason, and verification refs without storing raw provider bodies.

Policy behavior:

- missing `sandbox_backend` fails closed with `status=blocked`
- missing sandbox can only degrade with an explicit override reason
- `network_policy=denied` is first-class
- unrestricted network requires an override reason
- credential references such as `vault://...` and `env://...` are allowed
- credential-looking values and raw provider body fields are rejected

Evidence:

- `python -m pytest tests/test_cloud_isolation.py -q` passed 6/6 in
  `hivemind`
- `python -m pytest tests/test_run_validation.py tests/test_provider_passthrough.py -q`
  passed 23/23 in `hivemind`
- `python -m py_compile hivemind/cloud_isolation.py tests/test_cloud_isolation.py`
  passed
- `git diff --check` passed in `hivemind`

World readiness delta:

- `cloud_execution_isolation`: `partial` -> `met`
- `scripts/aios_world_readiness.py --json` can now report all seven
  readiness axes as met, subject to the script's evidence-marker scope.

## Stop Conditions

- `unsandboxed_execution_without_override`
- `credential_value_in_runtime_receipt`
- `raw_provider_history_leak`
- `network_policy_missing`
- `package_manifest_missing`
- `child_repo_implementation_without_owner_scope`

## Return Packet

Hive should write:

```text
.aios/outbox/hivemind/asc-0240.hivemind.result.json
```

with `status`, `changed_files`, `evidence`, `privacy_receipt`,
`world_readiness_delta`, and `next`.

## Next

After this closes, world-readiness work should move from marker-level
readiness to live hosted-run proof: execute a real provider/local worker through
the receipt path, project it into MemoryOS Akashic lineage, and keep credential
values outside the sandbox through vault references only.
