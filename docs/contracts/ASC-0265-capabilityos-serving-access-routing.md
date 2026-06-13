---
contract_id: ASC-0265
slug: capabilityos-serving-access-routing
status: closed
goal: Implement CapabilityOS per-user provider-access, consent, rate, and budget routing for real end-user AIOS serving before any provider dispatch.
created: 2026-06-13T20:00:00+09:00
accepted: 2026-06-13T20:00:00+09:00
closed: 2026-06-13T20:13:00+09:00
human_approved: true
origin: ASC-0260/ASC-0261 release gate marks CapabilityOS provider-access/rate/consent routing as missing and owner-bound to CapabilityOS.
depends_on:
  - ASC-0238
  - ASC-0260
  - ASC-0261
  - ASC-0262
---

# ASC-0265 CapabilityOS Serving Access Routing

## Decision

CapabilityOS owns recommendation and routing policy for provider/tool access.
For real serving, a user task cannot dispatch to a provider or connector until
consent, scope, rate, cost, and revocation state are checked.

This contract turns ASC-0260 Slice 6 into an executable owner-bound packet for
`CapabilityOS`.

## Plain Language

In plain language: build the gate that decides whether a user task is allowed
to use a provider, connector, or tool before the call happens. If consent,
budget, rate, or scope is missing, the answer must be "no" with a receipt.

## Counter-Default Branch

The common default is "route to the best tool." That is not enough for serving
users. The counter-default branch is to prefer refusal over usefulness whenever
the user's permission, cost limit, or connector scope is not proven.

## Cross-Domain Frame

Airport boarding control is the useful analogy: a passenger with a valid ticket
for one flight cannot board every flight, and a revoked boarding pass must stop
movement before the gate opens. Provider access should behave the same way.

## Scope

repos:

- `CapabilityOS`

allowed_files:

- `CapabilityOS/capabilityos/serving_access.py`
- `CapabilityOS/tests/test_serving_access.py`
- `CapabilityOS/docs/**`

forbidden_files:

- `.env`
- `.env.*`
- provider auth files
- credential vault contents
- raw provider logs
- private history stores
- raw user connector exports
- `hivemind/**`
- `memoryOS/**`
- `GenesisOS/**`
- `apps/**`
- `uri/**`
- unrelated child repo source files

## Substrate / Surface / Knowledge Gate

- schema_version: `aios.boundary_classifier.v1`
- layer: `capability_plugin_route`
- owner_repo: `CapabilityOS`
- substrate_level: `runtime`
- surface_type: `dispatch`
- knowledge_scope: `memoryos_context`
- authority: `recommendation_only`
- required_receipts:
  - `aios.serving_access_decision.v1`
  - `missing_consent_denial_receipt`
  - `budget_or_rate_refusal_receipt`
  - `revocation_propagation_test`

## Required Work

Implement a serving-access routing primitive that:

- takes `user_id`, `session_id`, provider/tool id, requested scopes, estimated
  cost, and rate bucket;
- returns `allow`, `deny`, or `degrade` as a structured recommendation before
  any provider dispatch;
- denies missing consent before provider execution;
- refuses budget/rate violations before dispatch;
- models connector revocation and makes active sessions see the revocation
  within one round;
- stores credential references and access grants only as references or opaque
  ids, never raw credential values;
- remains recommendation-only and does not execute tools.

## Per-OS Responsibility

### CapabilityOS

must_produce:

- `CapabilityOS/capabilityos/serving_access.py`
- `CapabilityOS/tests/test_serving_access.py`
- focused test evidence for consent denial, rate/budget refusal, revocation, cross-user isolation, and recommendation-only behavior

### Hive Mind

must_produce:

- no implementation in this contract; future workers consume access decisions

### MemoryOS

must_produce:

- no implementation in this contract; user consent records may later become reviewed memory/context

### GenesisOS

must_produce:

- no implementation in this contract; future challenge checks consent assumptions

## Acceptance Evidence

- Missing consent produces a denial receipt before any provider call.
- Budget/rate limit produces a refusal receipt before dispatch.
- User revocation propagates to an active session within one round.
- `user_id=A` access grants cannot authorize `user_id=B`.
- Tests prove the module returns recommendations and never executes a provider,
  connector, shell command, or network call.

## Verification Gate

```bash
cd CapabilityOS
python -m pytest tests/test_serving_access.py -q
python -m py_compile capabilityos/serving_access.py tests/test_serving_access.py
git diff --check
```

## Stop Conditions

- `provider_call_without_consent_check`
- `budget_exceeded_without_refusal_receipt`
- `access_grant_leaked_across_users`
- `credential_value_in_access_receipt`
- `capabilityos_executes_provider`
- `child_repo_implementation_without_owner_contract`

## Return Packet

Write `.aios/outbox/CapabilityOS/asc-0265.CapabilityOS.result.json` with:

- changed files;
- test commands and outcomes;
- remaining gaps;
- stop conditions triggered, if any.

## Result

Claude executed the owner-bound packet through `scripts/aios_child_watcher.sh`
as `claude@CapabilityOS`.

Evidence:

- dispatch result: `.aios/outbox/CapabilityOS/asc-0265.CapabilityOS.result.json`
- child commit: `CapabilityOS` `12e7b38 ASC-0265: implement per-user serving access routing`
- changed child files:
  - `CapabilityOS/capabilityos/serving_access.py`
  - `CapabilityOS/tests/test_serving_access.py`
  - `CapabilityOS/AGENTS.md`
- verification:
  - `python -m pytest tests/test_serving_access.py -q` passed 26/26 in `CapabilityOS`
  - `python -m py_compile capabilityos/serving_access.py tests/test_serving_access.py` passed
  - `git diff --check` passed in `CapabilityOS`

Release gate delta:

- `capabilityos_access_routing`: `missing` -> `met`
