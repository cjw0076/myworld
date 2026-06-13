---
contract_id: ASC-0267
slug: serving-support-redaction
status: closed
goal: Implement redacted serving support and incident timeline projections so real-user AIOS serving can be debugged without exposing raw user content, memory bodies, provider logs, or credential material.
created: 2026-06-14T01:27:00+09:00
accepted: 2026-06-14T01:27:00+09:00
closed: 2026-06-14T01:33:00+09:00
human_approved: true
origin: ASC-0260/ASC-0261 release gate marks observability/support redaction as partial and owner-bound to myworld with MemoryOS privacy constraints.
depends_on:
  - ASC-0237
  - ASC-0255
  - ASC-0260
  - ASC-0261
  - ASC-0264
---

# ASC-0267 Serving Support Redaction

## Decision

MyWorld owns the serving support projection because support and incident views
are release-control surfaces. MemoryOS owns the privacy rule: raw user memory
and private content must not be exposed through support/admin summaries.

This contract turns ASC-0260 Slice 7 into an executable owner-bound packet for
`myworld`.

## Plain Language

In plain language: build the support view that lets an operator understand
which stage failed, when it failed, and what kind of error happened, without
showing the user's private message, memory text, raw tool output, provider log,
or secret.

## Counter-Default Branch

The common default is "debugging needs the full logs." That is not acceptable
for real users. The counter-default branch is to treat full logs as private by
default and expose only structured, redacted incident metadata unless a later
explicit privacy contract authorizes more.

## Cross-Domain Frame

Helpdesk ticket routing is the useful analogy: the support desk needs status,
severity, owning team, and escalation path; it does not need the full private
conversation. Serving support should expose the minimum useful operational
signal.

## Scope

repos:

- `myworld`

allowed_files:

- `scripts/aios_serving_support.py`
- `tests/test_aios_serving_support.py`
- `docs/contracts/ASC-0267-serving-support-redaction.md`
- `docs/AGENT_WORKLOG.md`
- `docs/AIOS_AGENT_LEDGER.md`

forbidden_files:

- `.env`
- `.env.*`
- provider auth files
- credential vault contents
- raw provider logs
- private history stores
- raw user exports
- `apps/**`
- `hivemind/**`
- `memoryOS/**`
- `CapabilityOS/**`
- `GenesisOS/**`
- `uri/**`
- `artifacts/**`
- `gemini/**`
- `gemini-cli/**`
- `1.md`

## Substrate / Surface / Knowledge Gate

- schema_version: `aios.boundary_classifier.v1`
- layer: `serving_observability_projection`
- owner_repo: `myworld`
- substrate_level: `runtime`
- surface_type: `dispatch`
- knowledge_scope: `memoryos_context`
- authority: `execute_with_receipt`
- required_receipts:
  - `aios.serving_support_projection.v1`
  - `aios.serving_incident_timeline.v1`
  - `raw_content_redaction_test`
  - `cross_user_incident_denial_test`

## Required Work

Implement a deterministic support projection primitive that:

- accepts serving job/session/incident events as structured dictionaries;
- emits user-scoped incident timelines with stage name, status, timestamp,
  error type, severity, retryability, and opaque refs;
- redacts raw fields such as user message body, memory body, provider output,
  raw tool output, prompt text, credential value, token, and private export;
- denies support projection access when requested `user_id` does not match the
  incident owner;
- emits admin summaries that expose counts and status/error metadata only;
- has no live provider, network, or app-server dependency.

## Per-OS Responsibility

### MyWorld

must_produce:

- `scripts/aios_serving_support.py`
- `tests/test_aios_serving_support.py`
- focused test evidence for redaction, cross-user denial, incident timeline,
  admin summary, and deterministic JSON output

### MemoryOS

must_produce:

- no implementation in this contract; privacy rule is consumed from the
  MemoryOS serving-memory boundary

### Hive Mind

must_produce:

- no implementation in this contract; worker receipts can later feed support
  projections

### CapabilityOS

must_produce:

- no implementation in this contract; access decisions can later feed support
  metadata

### GenesisOS

must_produce:

- no implementation in this contract; future launch challenge consumes support
  redaction evidence

## Acceptance Evidence

- `scripts/aios_serving_support.py` exists and emits
  `aios.serving_support_projection.v1`.
- `tests/test_aios_serving_support.py` proves raw message, memory body, raw
  provider output, tool output, prompt text, and credential-looking values are
  absent from support/admin projections.
- Tests prove cross-user incident projection is denied.
- Tests prove admin/support summaries keep stage/error/status metadata.
- `python3 scripts/aios_serving_release_gate.py assess --root . --json`
  reports `observability_support_redaction` as `met`.

## Verification Gate

```bash
python3 -m unittest tests.test_aios_serving_support -v
python3 -m py_compile scripts/aios_serving_support.py tests/test_aios_serving_support.py
python3 scripts/aios_serving_release_gate.py assess --root . --json
python3 scripts/aios_world_readiness.py --json
git diff --check
```

## Stop Conditions

- `raw_user_content_in_support_view`
- `cross_user_incident_access`
- `operator_audit_exposes_user_memory_body`
- `provider_log_body_in_projection`
- `credential_value_in_support_projection`
- `serving_support_claim_without_tests`

## Return Packet

Write `.aios/outbox/myworld/asc-0267.myworld.result.json` with:

- changed files;
- test commands and outcomes;
- remaining gaps;
- stop conditions triggered, if any.

## Result

The first `asc-0267` watcher attempt held on `pending_concurrent_work` because
the dispatch-policy preparation files were still dirty. Codex committed that
preparation as `e167ddc Prepare serving support redaction dispatch`, then
reissued the packet as `asc-0267-r2`.

Claude executed `asc-0267-r2` through `scripts/aios_child_watcher.sh` as
`claude@myworld`.

Evidence:

- dispatch result: `.aios/outbox/myworld/asc-0267-r2.myworld.result.json`
- changed files:
  - `scripts/aios_serving_support.py`
  - `tests/test_aios_serving_support.py`
  - `docs/AGENT_WORKLOG.md`
- verification:
  - `python3 -m unittest tests.test_aios_serving_support -v` passed 36/36
  - `python3 -m py_compile scripts/aios_serving_support.py tests/test_aios_serving_support.py` passed
  - `python3 scripts/aios_serving_release_gate.py assess --root . --json` reports `observability_support_redaction` as `met`
  - `python3 scripts/aios_world_readiness.py --json` remains `ready_for_world_deployment=false`
  - `git diff --check` passed

Release gate delta:

- `observability_support_redaction`: `partial` -> `met`
- release gate totals: `ready_for_production_serving=false`, `met=6`,
  `partial=3`, `missing=0`

Remaining serving blockers:

- Product Design visual target and design brief
- end-user serving UI/browser proof
- runtime Genesis launch-candidate proof
