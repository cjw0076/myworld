---
contract_id: ASC-0238
slug: skillos-recommendation-registry
status: closed
goal: Add a recommendation-only SkillOS registry so AIOS can map skills, tools, provider surfaces, owner repos, risk, evidence, and fallbacks without granting execution authority.
created: 2026-06-13T00:20:00+09:00
closed: 2026-06-13T00:26:00+09:00
origin: ASC-0234 and ASC-0235 world-readiness gap: CapabilityOS / SkillOS neuromuscular routing is partial.
---

# ASC-0238 SkillOS Recommendation Registry

## Why Now

AIOS needs a neuromuscular layer: a map of what skills/tools/provider surfaces
exist, who owns them, what they can do, what risk they carry, and what fallback
path exists. This should improve routing without letting SkillOS or
CapabilityOS execute tools directly.

## Scope

repos:

- `myworld`

allowed_files:

- `scripts/aios_skillos_registry.py`
- `tests/test_aios_skillos_registry.py`
- `docs/contracts/ASC-0238-skillos-recommendation-registry.md`
- `docs/AIOS_AGENT_LEDGER.md`

forbidden_files:

- `.env`
- `.env.*`
- provider credentials
- raw provider logs
- child repo implementation files

## Substrate / Surface / Knowledge Gate

- schema_version: `aios.boundary_classifier.v1`
- layer: `capability_plugin_route`
- owner_repo: `CapabilityOS`
- substrate_level: `none`
- surface_type: `plugin`
- knowledge_scope: `local_only`
- authority: `recommendation_only`
- required_receipts:
  - `skillos_registry_json`
  - `focused_test_report`

## Result

Implemented `scripts/aios_skillos_registry.py` with schema
`aios.skillos_registry.v1`.

The registry:

- emits SkillOS cards with owner repo, risk, domains, actions, evidence refs,
  and fallback ids;
- returns `recommendation_only=true`;
- returns `execution_enabled=false`;
- provides `list` and `recommend` commands;
- never executes provider/tool/script actions.

## Verification Gate

```bash
python3 -m unittest tests.test_aios_skillos_registry -v
python3 -m py_compile scripts/aios_skillos_registry.py
python3 scripts/aios_skillos_registry.py --json list
python3 scripts/aios_world_readiness.py --json
git diff --check
```

## Stop Conditions

- `skillos_executes_tool`
- `capabilityos_executes_tool`
- `provider_truth_without_verifier`
- `child_repo_implementation_without_dispatch`

## Next

CapabilityOS should eventually own the deeper dynamic registry and observation
feedback loop. For world readiness, the remaining MyWorld-reported partial axes
are MemoryOS Akashic lineage, Hive hosted isolation, Akashic trace graph, and
Genesis SECI entropy.
