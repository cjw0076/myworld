---
contract_id: ASC-0235
slug: world-deployment-readiness-cli
status: closed
goal: Add a machine-readable readiness gate that distinguishes local AIOS completion from world-deployable agent-service infrastructure readiness.
created: 2026-06-12T23:45:00+09:00
closed: 2026-06-12T23:50:00+09:00
origin: ASC-0234 follow-up.
---

# ASC-0235 World Deployment Readiness CLI

## Why Now

`scripts/aios_completion.py` can report local self-maintaining completion, but
the founder's current objective asks whether AIOS is ready for hosted,
resumable, isolated, observable, multi-provider agent-service deployment. A
green local completion result must not be reused as proof of world deployment
readiness.

## Scope

repos:

- `myworld`

allowed_files:

- `scripts/aios_world_readiness.py`
- `tests/test_aios_world_readiness.py`
- `docs/contracts/ASC-0235-world-deployment-readiness-cli.md`
- `docs/AIOS_AGENT_LEDGER.md`

forbidden_files:

- `.env`
- `.env.*`
- provider credentials
- raw provider logs
- private history stores
- child repo implementation files

## Substrate / Surface / Knowledge Gate

- schema_version: `aios.boundary_classifier.v1`
- layer: `kernel_primitive`
- owner_repo: `myworld`
- substrate_level: `primitive`
- surface_type: `contract`
- knowledge_scope: `local_only`
- authority: `execute_with_receipt`
- required_receipts:
  - `world_readiness_json`
  - `focused_test_report`
  - `diff_check`

## Required Work

- Add `scripts/aios_world_readiness.py` with schema
  `aios.world_readiness.v1`.
- Track the seven ASC-0234 axes:
  - iterative engine spine
  - durable work lineage
  - cloud execution isolation
  - credential/private-data boundary
  - Akashic observability
  - SkillOS routing
  - Genesis SECI entropy
- Return `met`, `partial`, or `missing` per axis with owner repos, evidence,
  gap, and next contract.
- Keep `ready_for_world_deployment=false` unless every axis has dedicated
  world-readiness evidence.
- Add focused tests proving empty, partial, fully marked, and current-repo
  behavior.

## Verification Gate

```bash
python3 -m unittest tests.test_aios_world_readiness -v
python3 -m py_compile scripts/aios_world_readiness.py
python3 scripts/aios_world_readiness.py --json
git diff --check
```

## Result

Implemented.

Current repo result on 2026-06-12:

- `ready_for_world_deployment=false`
- `met_count=1`
- `partial_count=6`
- `missing_count=0`
- `next_action=ASC-0237`

The single met axis is `iterative_engine_spine`, backed by
`scripts/aios_turn_loop.py`. The remaining axes are partial and must become
dedicated owner-repo contracts before AIOS can honestly claim world-deployable
agent-service readiness.

## Stop Conditions

- `completion_gate_scope_confusion`
- `world_readiness_claim_without_gate`
- `raw_provider_history_leak`
- `credential_value_in_prompt_or_doc`
- `child_repo_implementation_without_dispatch`
- `memoryos_accepts_without_review`

## Next

Create `ASC-0237` for MemoryOS Akashic work-lineage and replay checkpoint
index, because the new readiness gate reports durable lineage and Akashic
observability as the next load-bearing partial axes.
