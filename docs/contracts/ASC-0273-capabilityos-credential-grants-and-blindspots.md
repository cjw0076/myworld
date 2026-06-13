---
contract_id: ASC-0273
slug: capabilityos-credential-grants-and-blindspots
status: closed
accepted: 2026-06-14T03:10:00+09:00
closed: 2026-06-14T04:05:00+09:00
goal: Build CapabilityOS Gate A schemas for credential grants, provider blindspot harvesting, fallback risk, and recommendation-only route observations.
created: 2026-06-14T03:20:00+09:00
human_approved: true
parent: ASC-0271
depends_on:
  - ASC-0265
  - ASC-0270
  - ASC-0271
external_baseline:
  - docs/research/AIOS_AGENT_SERVICE_INFRA_DELTA_2026-06-14.md
---

# ASC-0273 CapabilityOS Credential Grants And Blindspots

## Decision

CapabilityOS should treat providers, MCP servers, A2A agents, local models,
plugins, and tools as vendors. It recommends routes and records risk; it does
not execute or install anything under this contract.

This contract proposes a Gate A CapabilityOS slice: define credential-grant
references and provider-blindspot observations before any serving UI or live
provider dispatch depends on them.

## Scope

repos:

- `CapabilityOS`

allowed_files:

- `CapabilityOS/capabilityos/credential_grant.py`
- `CapabilityOS/capabilityos/provider_blindspot.py`
- `CapabilityOS/tests/test_credential_grant.py`
- `CapabilityOS/tests/test_provider_blindspot.py`
- `CapabilityOS/docs/**`

forbidden_files:

- `.env`
- `.env.*`
- provider auth files
- credential vault contents
- raw provider logs
- raw connector exports
- private history stores
- `hivemind/**`
- `memoryOS/**`
- `GenesisOS/**`
- `apps/**`
- `uri/**`
- unrelated child repo source files

## Substrate / Surface / Knowledge Gate

- schema_version: `aios.boundary_classifier.v1`
- owner_repo: `CapabilityOS`
- substrate_level: `runtime`
- surface_type: `dispatch`
- knowledge_scope: `web_primary_sources`
- authority: `recommendation_only`
- required_receipts:
  - `aios.credential_grant_schema.v1`
  - `aios.provider_blindspot_observation.v1`
  - `aios.route_fallback_risk.v1`
  - `raw_credential_rejection_test`

## Required Work

Implement recommendation-only primitives that:

- represent credentials as opaque grant refs with provider/tool id, scopes,
  expiry, injection target, revocation state, and receipt refs;
- reject raw-looking credential values in grants and route observations;
- classify provider friction as refusal, timeout, hallucination, credential
  friction, convergence, sandbox mismatch, or unavailable fallback;
- mark single-provider routes as `single_provider_risk` unless a fallback is
  present or a `no_fallback_reason` is explicit;
- produce recommendations only and never execute tools, MCP calls, provider
  calls, installs, or credential injection.

## Verification Gate

```bash
cd CapabilityOS
python3 -m unittest tests.test_credential_grant tests.test_provider_blindspot -v
python3 -m py_compile capabilityos/credential_grant.py capabilityos/provider_blindspot.py
git diff --check
```

## Stop Conditions

- `credential_raw_value_transits`
- `capabilityos_executes_tool`
- `provider_lock_in_without_fallback`
- `revocation_not_modeled`
- `route_observation_contains_raw_private_output`

## Dispatch Packet

- target_repo: `CapabilityOS`
- target_agent: `claude`
- status: not_sent
- reason: proposed Gate A contract awaits operator/delegated release.
