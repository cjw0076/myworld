---
contract_id: ASC-0252
slug: serving-readiness-gate-correction
status: accepted
goal: Correct the world-deployment readiness gate so AIOS cannot claim world-ready service readiness while the end-user serving runtime/interface is only a spec.
created: 2026-06-13T15:47:00+09:00
accepted: 2026-06-13T15:47:00+09:00
human_approved: true
origin: `scripts/aios_world_readiness.py --json` currently reports `ready_for_world_deployment=true`, but ASC-0251 explicitly says the end-user serving interface is design/spec only and `apps/serving/` plus `end_user_serving` runtime are not implemented.
---

# ASC-0252 Serving Readiness Gate Correction

## Why Now

The current world readiness CLI now returns:

```text
ready_for_world_deployment=true
met_count=7
partial_count=0
missing_count=0
```

That result is too broad for the founder's current goal. AIOS has local
control-plane readiness, runtime isolation, MemoryOS lineage, credential
brokerage, SkillOS routing, and Genesis entropy markers. It does not yet have
a real product serving surface for users.

ASC-0251 closed only a design/spec packet:

- `docs/product/AIOS_END_USER_SERVING_INTERFACE_SPEC.md`
- `docs/product/AIOS_SERVING_INTERFACE_ROUTE_MAP.md`

ASC-0251 also records the remaining gaps:

- `end_user_serving` runtime profile is not added to `RUNTIME_PROFILES`;
- `apps/serving/` is not created;
- serving API/auth/transport decisions are still open;
- no browser-visible user workflow has passed.

Therefore, `ready_for_world_deployment=true` is currently an overclaim for
service deployment. This contract corrects the gate before any product claims
or hosting work are made from false evidence.

## Scope

repos:

- `myworld`

allowed_files:

- `scripts/aios_world_readiness.py`
- `tests/test_aios_world_readiness.py`
- `docs/contracts/ASC-0252-serving-readiness-gate-correction.md`
- `docs/AIOS_AGENT_LEDGER.md`
- `docs/AGENT_WORKLOG.md`

forbidden_files:

- `.env`
- `.env.*`
- provider auth files
- private vault contents
- raw provider logs
- private history stores
- child repo implementation files
- `apps/control/**`
- `apps/serving/**`
- `scripts/aios_dispatch.py`
- `tests/test_aios_dispatch.py`
- `uri/**`
- `CapabilityOS/**`
- `artifacts/**`
- `gemini/**`
- `gemini-cli/**`
- `1.md`

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
  - `dispatch_result_packet`

## Required Work For Claude

Correct the readiness CLI and its tests without implementing the serving UI.

Minimum requirements:

1. Add an explicit world-readiness axis or equivalent gate for end-user serving
   readiness.
2. The new gate must remain `partial` or `missing` until evidence proves all of
   the following:
   - separate end-user serving surface exists outside `apps/control/`;
   - `end_user_serving` runtime profile or equivalent user-delegated runtime
     boundary is implemented;
   - first workflow proof has browser-test evidence for new task, approval,
     memory review, and artifact download flows;
   - user/session/workspace isolation is represented in the evidence, not just
     in prose.
3. Current repository behavior must become:
   - `ready_for_world_deployment=false`;
   - prior seven infrastructure axes may remain `met`;
   - serving readiness is not `met`;
   - `next_action` points to `ASC-0252` or a follow-on serving prototype
     contract.
4. Update tests so the previous overclaim is impossible:
   - all old dedicated infrastructure markers alone do not reach world-ready;
   - adding only ASC-0251 docs still does not reach world-ready;
   - only adding explicit serving implementation/proof markers can reach
     world-ready in a synthetic fixture.
5. Keep the local-completion boundary intact:
   - `scripts/aios_completion.py` remains local self-maintenance only;
   - `scripts/aios_world_readiness.py` remains the hosted/service readiness
     gate.
6. Write a result packet for ASC-0252 with status, changed files, tests, and
   any remaining gaps.
7. Update the ledger/worklog with a short closeout entry.

Do not create `apps/serving/` in this contract. That belongs to a follow-on
prototype/build contract after a visual target or Product Design brief is
accepted.

## AIOS Role Evidence

### MemoryOS

- context_pack: existing ASC-0234, ASC-0235, ASC-0251 contracts and product
  docs.
- retrieval_trace: local repo inspection in this Codex turn.
- accepted_memory_ids: pending_or_not_required.
- draft_memory_policy: no memory acceptance in this contract.

### CapabilityOS

- route: myworld primitive gate correction.
- recommended_tools: Python unittest, `aios_world_readiness.py --json`,
  `git diff --check`.
- fallback_plan: if Claude cannot run, Codex may verify the failed/degraded
  result and dispatch a narrower follow-on.
- authority: execute_with_receipt inside allowed files only.

### GenesisOS

- branch_set: "world-ready means infra markers" versus "world-ready means real
  user serving proof".
- assumption_mutations: reject the narrower infra-only claim for this founder
  goal.
- semantic_alignment_notes: "세상에 배포할 준비" includes users actually using
  an isolated, observable, resumable service surface.
- authority: advisory framing only.

### Hive Mind

- execution_plan: Claude edits bounded myworld CLI/test/docs slice.
- provider_route: `claude@myworld` via AIOS child watcher or manual provider
  execution under explicit runtime policy.
- verification_receipt: focused tests, py_compile, readiness JSON, diff check.
- degraded_or_fallback_receipt: required if provider access, timeout, or
  build/runtime isolation prevents execution.

## Plain-Language Framing

The old gate says "the factory has tools, power, safety rules, and inspectors,
so the product is ready for customers." That is not enough. Customers still
need a front door, a counter, receipts, private lockers, and a working first
service flow. ASC-0252 makes the readiness gate stop confusing factory
readiness with service readiness.

## Counter Branch

Counter-default option: keep `ready_for_world_deployment=true` because the
seven original infrastructure axes are met.

Rejected. The founder's current objective is not "local AIOS has mature
internals"; it is "users can use AIOS as a real served agent company." Without
serving proof, the readiness claim is too strong.

## Verification Gate

```bash
python3 -m unittest tests.test_aios_world_readiness -v
python3 -m py_compile scripts/aios_world_readiness.py
python3 scripts/aios_world_readiness.py --json
git diff --check
```

Expected current-repo result after this contract:

```text
ready_for_world_deployment=false
serving_readiness.status != met
```

## Work Packets

### WP-0252-A — Claude serving readiness gate correction

- target_repo: `myworld`
- target_agent: `claude`
- status: issued
- instruction: Correct `scripts/aios_world_readiness.py` and
  `tests/test_aios_world_readiness.py` so the world readiness gate cannot
  report service deployment readiness until the end-user serving interface and
  runtime proof exist. Do not create UI code or touch forbidden paths.
- result: pending

## Stop Conditions

- `world_readiness_claim_without_serving_surface`
- `serving_docs_counted_as_serving_implementation`
- `apps_control_reused_as_user_serving_proof`
- `ui_implementation_before_visual_target`
- `credential_value_in_prompt_or_doc`
- `raw_provider_history_leak`
- `child_repo_implementation_without_dispatch`
- `scope_violation`
