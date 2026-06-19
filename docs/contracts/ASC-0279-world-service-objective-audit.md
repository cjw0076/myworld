---
contract_id: ASC-0279
slug: world-service-objective-audit
status: closed
created: 2026-06-19T15:35:00+09:00
closed: 2026-06-19T15:45:00+09:00
goal: Add a read-only machine-readable audit for the full AIOS world-service objective so green readiness gates cannot overclaim completion of hosting, memory, isolation, credentials, entropy, SkillOS, Hivemind, and provider-state absorption.
owner_repo: myworld
parent: ASC-0235
depends_on:
  - ASC-0270
  - ASC-0271
  - ASC-0235
  - ASC-0261
  - ASC-0277
  - ASC-0278
---

# ASC-0279 World-Service Objective Audit

## Decision

`scripts/aios_world_readiness.py` and `scripts/aios_serving_release_gate.py`
are release-readiness gates. They are necessary, but the active founder
objective is broader: AIOS must be credible as an agent company operating
system with hosting, session lineage, isolation, credentials, MemoryOS,
CapabilityOS/SkillOS, Hivemind, Genesis entropy, and provider-state absorption.

ASC-0270 opened the aggressive AIOS dream-expansion lane, and ASC-0271 made
Claude's hardening lane explicit. This contract does not replace that split and
does not authorize child-repo hardening from `myworld`.

It adds a read-only audit that maps those objective requirements to concrete
evidence and marks each row as `proven`, `partial`, `weak`, or `missing`. It
consumes existing gates instead of becoming a new release gate, and it is
intentionally allowed to say the full objective is not yet complete even when
release-readiness scripts are green.

## Scope

repos:

- `myworld`

allowed_files:

- `scripts/aios_world_service_audit.py`
- `tests/test_aios_world_service_audit.py`
- `docs/contracts/ASC-0279-world-service-objective-audit.md`
- `docs/AGENT_WORKLOG.md`
- `docs/AIOS_AGENT_LEDGER.md`

forbidden_files:

- `.env`
- `.env.*`
- provider auth files
- credential vault contents
- raw provider logs
- raw trace bodies
- raw user data
- `hivemind/**`
- `memoryOS/**`
- `CapabilityOS/**`
- `GenesisOS/**`
- `uri/**`
- `apps/**`
- unrelated generated snapshots

## Substrate / Surface / Knowledge Gate

- schema_version: `aios.boundary_classifier.v1`
- owner_repo: `myworld`
- substrate_level: `primitive`
- surface_type: `contract`
- knowledge_scope: `local_only`
- authority: `execute_with_receipt`
- required_receipts:
  - `aios.world_service_objective_audit.v1`
  - `focused_test_report`
  - `diff_check`

## Required Work

- Add `scripts/aios_world_service_audit.py`.
- Emit schema `aios.world_service_objective_audit.v1`.
- Consume existing `aios_serving_design_gate.py`,
  `aios_serving_release_gate.py`, and `aios_world_readiness.py` outputs as
  source evidence.
- Cover at least these requirement groups:
  - serving product surface
  - hosting/deployment preparation
  - live public hosting proof
  - session/resume lineage
  - filesystem/execution isolation
  - credential vault boundary
  - user-private memory boundary
  - Akashic/web absorption
  - CLI log asset pool
  - SECI/token/context automation
  - Genesis entropy/frozen-knowledge pressure
  - CapabilityOS/SkillOS routing
  - Hivemind parallel execution
  - provider-managed state absorption
- Keep `ready_for_goal_completion=false` unless every requirement is `proven`
  and no contract-hygiene caveat remains.
- Add focused tests for empty, weak, partial, proven, text-mode, and current
  repo honesty.

## Verification Gate

```bash
python3 -m unittest tests.test_aios_world_service_audit -v
python3 -m py_compile scripts/aios_world_service_audit.py
python3 scripts/aios_world_service_audit.py --json
git diff --check
```

## Result

Implemented. The audit is expected to remain stricter than the release gates
without replacing them: ASC-0277 and ASC-0278 are still proposed/weak until
owner-specific results are collected, CapabilityOS SkillOS ownership still has
a migration gap, and live public hosting proof still needs an
operator-authorized external deployment target.

This preserves the ASC-0270/ASC-0271 boundary: Codex can keep expanding the
product and service objective surface, while Claude owns hardening result
packets and owner-specific implementation.

## Stop Conditions

- `world_readiness_gate_overclaims_objective_completion`
- `weak_contract_marker_treated_as_proof`
- `raw_private_evidence_leak`
- `child_repo_implementation_from_myworld`
- `provider_state_auto_promoted_to_memory`

## Next

Use this audit before any future claim that the full active AIOS objective is
complete. First gaps should flow to ASC-0277, ASC-0278, and a hosted-scale proof
contract only when the operator grants external deployment authority.
