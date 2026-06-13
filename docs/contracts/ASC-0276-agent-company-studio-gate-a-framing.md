---
contract_id: ASC-0276
slug: agent-company-studio-gate-a-framing
status: accepted
accepted: 2026-06-14T03:10:00+09:00
goal: Preserve the Agent Company Studio product framing as a Gate A docs-only artifact without creating serving UI before visual target selection.
created: 2026-06-14T03:20:00+09:00
human_approved: true
parent: ASC-0271
depends_on:
  - ASC-0268
  - ASC-0269
  - ASC-0270
  - ASC-0271
external_baseline:
  - docs/research/AIOS_AGENT_SERVICE_INFRA_DELTA_2026-06-14.md
---

# ASC-0276 Agent Company Studio Gate A Framing

## Decision

AIOS should become an agent company operating system, but product language must
not outrun evidence. Before UI code, MyWorld may preserve a docs-only product
framing that maps the company metaphor to real OS state: contracts, workers,
memory drafts, capability recommendations, approvals, artifacts, and receipts.

## Scope

repos:

- `myworld`

allowed_files:

- `docs/product/AIOS_AGENT_COMPANY_STUDIO_BRIEF.md`
- `docs/product/AIOS_SERVING_DESIGN_BRIEF.md`
- `docs/contracts/ASC-0276-agent-company-studio-gate-a-framing.md`
- `docs/AGENT_WORKLOG.md`
- `docs/AIOS_AGENT_LEDGER.md`

forbidden_files:

- `.env`
- `.env.*`
- provider auth files
- credential vault contents
- raw provider logs
- raw user data
- private history stores
- `apps/**`
- `hivemind/**`
- `memoryOS/**`
- `CapabilityOS/**`
- `GenesisOS/**`
- `uri/**`
- unrelated child repo source files

## Substrate / Surface / Knowledge Gate

- schema_version: `aios.boundary_classifier.v1`
- owner_repo: `myworld`
- substrate_level: `none`
- surface_type: `contract`
- knowledge_scope: `web_primary_sources`
- authority: `draft_only`
- required_receipts:
  - `aios.product_framing.v1`
  - `design_gate_build_allowed_false`
  - `no_apps_serving_diff`

## Required Work

Create a product brief that:

- explains AIOS as a company the user can hire;
- maps each OS to user-visible service concepts without exposing raw logs;
- keeps MemoryOS drafts, CapabilityOS recommendations, Genesis findings, and
  Hivemind receipts visually distinct;
- defines how approvals and credential grants should feel to the user;
- states that `apps/**` work remains blocked until the design gate has a
  concrete visual target and browser verification contract.

## Verification Gate

```bash
python3 scripts/aios_world_readiness.py --json
python3 scripts/aios_serving_design_gate.py assess --root . --json
python3 scripts/aios_serving_release_gate.py assess --root . --json
git diff --check
```

Expected:

- `build_allowed=false`;
- `ready_for_production_serving=false`;
- no `apps/**` diff.

## Stop Conditions

- `ui_before_visual_target`
- `company_framing_replaces_individual_user_product`
- `raw_logs_become_primary_user_surface`
- `world_ready_claim_without_release_proof`

## Dispatch Packet

- target_repo: `myworld`
- target_agent: `codex`
- status: not_sent
- reason: proposed Gate A docs-only product framing awaits operator/delegated release.
