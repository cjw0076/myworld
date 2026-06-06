---
contract_id: ASC-0230
slug: myworld-hivemind-docs-hive-product-evaluation-md-next-product-p0-3
status: closed
goal: Reconcile `hive flow` and `plan_dag.json` into one scheduler surface
created: 2026-06-06 20:16 KST
accepted: 2026-06-06 20:36 KST
closed: 2026-06-06 20:58 KST
---

# ASC-0230 Myworld Hivemind Docs Hive Product Evaluation Md Next Product P0 3

## Why Now

Goal evolution selected this unblocked recommendation:

- path: `myworld/hivemind/docs/HIVE_PRODUCT_EVALUATION.md#next-product-p0-3`
- domain: `hivemind`
- policy_decision: `unknown`
- reason: refined from Hive product evaluation to first concrete P0

This contract is closed. The accepted implementation narrowed
`workflow_state.json` into a `plan_dag.json` read model instead of a competing
scheduler list.

## Scope

repos:

- `hivemind`

allowed_files:

- `hivemind/hivemind/flow_runtime.py`
- `hivemind/hivemind/workflow_projection.py`
- `hivemind/tests/test_workflow_scheduler_surface.py`
- `hivemind/tests/test_production_hardening.py`
- `hivemind/docs/AGENT_WORKLOG.md`
- `hivemind/docs/HIVE_PRODUCT_EVALUATION.md`
- `hivemind/docs/TODO.md`

forbidden_files:

- `.aios/logs/**`
- `.aios/state/**`
- `.aios/inbox/**`
- `.aios/outbox/**`
- `.env`
- raw export paths

## Responsibilities

### myworld.must_produce

- A narrowed implementation plan for: Reconcile `hive flow` and `plan_dag.json` into one scheduler surface.
- Exact allowed files before acceptance if the defaults above are too broad.
- Verification commands that prove the contract closed.
- Dispatch, result packet, release, and ledger evidence after acceptance.

### child repos

- Hive Mind owns implementation.

## Substrate / Surface / Knowledge Gate

- schema_version: `aios.boundary_classifier.v1`
- layer: `execution_substrate`
- owner_repo: `hivemind`
- substrate_level: `runtime`
- surface_type: `direct_hive_execution`
- knowledge_scope: `local_only`
- authority: `execute_with_receipt`
- next_contract_kind: `hive_execution_contract`

required_receipts:

- `run_receipt`
- `verification_receipt`
- `stop_or_degraded_receipt`

boundary_stop_conditions:

- `provider_truth_without_verifier`
- `fallback_executes_without_contract`


## AIOS Role Evidence

### MemoryOS

- context_pack: `not_required`
- retrieval_trace: `not_required`
- accepted_memory_ids: `not_required`
- draft_memory_policy: `draft_first_no_auto_accept`

### CapabilityOS

- route: `cap_skill_registry_route`, `cap_aios_route_planner`
- recommended_tools: local repo search, Hive tests, release gate
- fallback_plan: provider/model advisory attempted; no execution authority moved
- authority: `recommendation_only`

### GenesisOS

- branch_set: `not_required_for_this_runtime_slice`
- assumption_mutations: `not_required_for_this_runtime_slice`
- semantic_alignment_notes: `plan_dag authority, workflow_state read model`
- authority: `advisory_only`

### Hive Mind

- execution_plan: create focused regression tests, extract DAG read-model projection, wire `flow_runtime`, update Hive P0 docs
- provider_route: local Codex implementation; Claude attempt timed out; Gemini attempt hit quota retry then timed out; Ollama unavailable
- verification_receipt: Hive commit `9c1f689` pushed to `origin/main`
- degraded_or_fallback_receipt: local model unavailable (`ollama` missing); provider advisory degraded but implementation verified locally

## Implementation Result

Hive commit:

- `9c1f689` — `Reconcile flow scheduler surface`

Changed behavior:

- `plan_dag.json` is the scheduler authority for `hive flow`.
- `artifacts/workflow_state.json` declares:
  - `scheduler_authority=plan_dag.json`
  - `surface_role=read_model`
  - `read_model_of=<plan_dag_path>`
- `workflow_state.json` now exposes one `steps` projection derived from
  `plan_dag.json`.
- Competing `legacy_steps` and `dag_steps` scheduler lists are removed from
  DAG-backed workflow state.

Next:

- Product P0 #4: Add bounded parallel fan-out plus barrier join for safe
  internal/local steps first, provider execution later.


## Verification Gate

```bash
python -m unittest discover -s tests -p 'test_workflow_scheduler_surface.py'
python -m unittest discover -s tests -p 'test_production_hardening.py'
python -m unittest discover -s tests -p 'test_plan_dag.py'
python -m unittest discover -s tests -p 'test_workloop_ledger.py'
python -m unittest discover -s tests -p 'test_provider_passthrough.py'
python -m unittest discover -s tests -p 'test_step_result_hardening.py'
python -m py_compile hivemind/workflow_projection.py hivemind/flow_runtime.py
git diff --check
bash scripts/public-release-check.sh
python scripts/aios_monitor.py assess --json
```

Pass criteria:

- Focused scheduler regression passes.
- Existing flow/DAG/result/ledger/provider tests pass.
- Public release gate remains green.
- Monitor remains clear or only watch-level advisory.

## Stop Conditions

- `operator_acceptance_missing` — cleared by accepted execution in this turn.
- `scope_ambiguous` — cleared by exact allowed file list.
- `allowed_files_too_broad` — cleared by exact allowed file list.
- `child_repo_source_edit` — cleared by Hive-owned implementation.
- `verification_gate_failed` — cleared.
- `monitor_not_clear` — cleared; MyWorld monitor health is `watch` with only
  info-level `persona_axis_advisory`.

## Source Plan Evidence

- generated_at: `2026-06-06T20:16:17+09:00`
- monitor_health: `watch`
- readiness: `L6 repeatable`
- alignment_reasons: `verification_signal, concrete_product_eval_p0`
- blocked_reasons: ``
