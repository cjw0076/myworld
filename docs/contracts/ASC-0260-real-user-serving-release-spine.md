---
contract_id: ASC-0260
slug: real-user-serving-release-spine
status: closed
goal: Reframe AIOS serving work as a real end-user served product, not a local demo or operator UI, and split the missing production slices into owner-bound work packets.
created: 2026-06-13T19:40:00+09:00
accepted: 2026-06-13T19:40:00+09:00
closed: 2026-06-13T20:07:00+09:00
human_approved: true
human_approved_note: The operator explicitly clarified that the serving target is for real end users. This contract produces only deliberation artifacts and follow-on contract scope; it does not deploy, does not create deployment manifests, does not call remote APIs, does not access provider auth files, and includes no deployment code.
origin: The operator clarified that the AIOS serving path is "아예 User들이 사용할 때 진짜 서빙용" — for real users using an actually served product.
depends_on:
  - ASC-0251
  - ASC-0252
  - ASC-0253
  - ASC-0258
  - ASC-0259
---

# ASC-0260 Real User Serving Release Spine

## Decision

AIOS end-user serving means a real user-facing served product. This contract
produces only deliberation artifacts and follow-on contract scope. It does not
deploy and includes no deployment code. It is not:

- the local operator Control Center with sections hidden;
- a static mock that claims production readiness;
- a single-user localhost demo;
- a direct child-repo implementation from `myworld` without owner contracts.

The serving product must let real users submit work, resume jobs, approve
sensitive actions, review memory drafts, receive artifacts, and exercise data
controls through a private account/session boundary.

## Current Gate State

The Product Design gate is now recorded at:

- `.aios/serving/design_gate.json`

Current gate meaning:

- `product_goal`: real end-user AIOS served product;
- `visual_target_type`: `needs_ideation`;
- `next_product_design_step`: `ideate`;
- `build_allowed`: `false`.

Therefore, ASC-0253 may proceed only to Product Design ideation until a
concrete visual target is accepted. It must not build `apps/serving/**` yet.

## Scope

repos:

- `myworld`

allowed_files:

- `docs/contracts/ASC-0260-real-user-serving-release-spine.md`
- `docs/contracts/ASC-0253-end-user-serving-prototype-scope.md`
- `docs/AGENT_WORKLOG.md`
- `docs/AIOS_AGENT_LEDGER.md`

forbidden_files:

- `.env`
- `.env.*`
- provider auth files
- private vault contents
- raw provider logs
- private history stores
- `apps/control/**`
- `apps/serving/**`
- child repo implementation files
- `uri/**`
- `CapabilityOS/**`
- `hivemind/**`
- `memoryOS/**`
- `GenesisOS/**`
- `artifacts/**`
- `gemini/**`
- `gemini-cli/**`
- `1.md`

## Production Serving Slices

| Slice | Owner | Output | Acceptance Evidence |
| --- | --- | --- | --- |
| Product direction and visual target | Product Design + myworld | 3-5 serving interface directions, then one accepted target for ASC-0253 | `.aios/serving/design_gate.json` updated to a concrete `url`, `image`, `figma`, `screenshot`, or `design_system`; `build_allowed=true` |
| End-user web surface | myworld UI contract | Separate `apps/serving/**` route set for tasks, job timeline, approvals, memory, artifacts, settings | Browser proof at 375px and 1280px for new task, approval, memory draft review, artifact download |
| Runtime profile | myworld + hivemind | `end_user_serving` runtime policy with user/session scoped authority | tests prove build-control/operator state is not exposed and child execution is scoped to a user workspace |
| Hosted worker execution | hivemind | queue/resume worker for user tasks with provider receipts | two interrupted jobs resume from receipts without duplicate sensitive actions |
| Memory boundary | memoryOS | per-user namespace, draft-first lifecycle, export/delete request receipts | tests prove user A cannot retrieve user B memory; accepted memory requires user review |
| Capability and provider-access boundary | CapabilityOS | per-user connector access-grant scopes and rate/cost/risk route policy | denial receipts for missing consent; budget/rate limit refusal before dispatch |
| Observability and support | myworld + memoryOS | redacted job timeline and incident support view | support/admin views show stage/error metadata but not raw user content or provider logs |
| Release readiness gate | myworld | production-serving readiness CLI/checklist distinct from local completion | world readiness remains false until all required serving evidence markers exist |
| Adversarial closeout | GenesisOS | privacy, abuse, frozen-knowledge, and assumption-negation review before launch | launch candidate cannot close with unresolved cross-user data, authority, or support-risk findings |

## Required Near-Term Work

1. Product Design ideation must happen before UI implementation.
2. Claude should turn this release spine into concrete implementation contracts
   for each owner repo, preserving the table above as acceptance evidence.
3. Hivemind should not run live hosted child execution until the runtime
   profile, session boundary, provider-access boundary, and memory boundary
   contracts
   exist.
4. MyWorld should keep `scripts/aios_world_readiness.py` conservative:
   infrastructure markers alone are not world readiness.

## AIOS Role Evidence

### MemoryOS

- retrieved context: `rtrace_68986cdf59c789fe`
- relevant memory: production praxis and "AIOS remains after provider CLIs"
  framing.
- required future output: per-user memory namespace and draft-review proof.

### CapabilityOS

- route recommendation: AIOS Readiness Scorer, CapabilityOS recommendation,
  child watcher orchestration.
- required future output: real serving risk/cost/provider-access/consent route
  policy, not only a UI spec.

### GenesisOS

- challenge outcome: prose-only framing is insufficient; use a table/schema,
  named assumptions, and short/medium/long horizon checks.
- assumptions to negate:
  1. A good prototype proves production readiness.
  2. Single-user local state is enough for real users.
  3. Operator audit access can include raw user content by default.

### Hive Mind

- required future output: queue/resume execution proof, per-user sandbox
  receipts, and no duplicate sensitive action on retry/resume.

### 5-Persona Use

- Hive / Wrapper: owns hosted worker execution and resume proof.
- MemoryOS / Retriever: owns user-scoped memory lifecycle and retrieval traces.
- CapabilityOS / Router: owns connector access-grant, cost, and consent routing.
- GenesisOS / Philosophy: owns pre-launch assumption and privacy challenge.
- MyWorld / Sovereign: owns contracts, readiness gates, operator override, and
  product release decision.

## Time Horizons

| Horizon | Meaning | Exit |
| --- | --- | --- |
| 1 hour | Stop accidental local-demo overclaim. | This contract accepted; design gate written as `needs_ideation`; ASC-0253 remains build-blocked. |
| 1 week | Reach a browser-visible prototype with fake data and real isolation fixtures. | Accepted visual target, `apps/serving/**` prototype, browser proof, no world-ready claim. |
| 1 year | Multi-user service with durable jobs, memory controls, connectors, incidents, commercial controls, and audited launch process. | Production serving readiness gate passes with live or staging receipts. |

## Work Packets

### WP-0260-A — Claude production-serving implementation contract pack

- target_agent: claude
- target_repo: myworld
- status: issued
- issued: 2026-06-13
- accepted: pending
- closed: pending
- depends_on: none
- brief: |
    Read `docs/contracts/ASC-0260-real-user-serving-release-spine.md`,
    `docs/contracts/ASC-0253-end-user-serving-prototype-scope.md`,
    `docs/product/AIOS_END_USER_SERVING_INTERFACE_SPEC.md`, and
    `docs/product/AIOS_SERVING_INTERFACE_ROUTE_MAP.md`.

    Produce an implementation contract pack for real end-user AIOS serving.
    Do not build UI code and do not touch `apps/serving/**`.

    The pack must split the work into owner-bound follow-on contracts for:
    Product Design ideation, serving UI prototype, `end_user_serving` runtime
    profile, Hivemind hosted worker queue/resume, MemoryOS per-user memory
    lifecycle, CapabilityOS provider-access/rate/consent routing,
    observability and support redaction, release readiness gate, and GenesisOS
    pre-launch challenge.

    Each follow-on contract must include allowed/forbidden files, acceptance
    evidence markers, tests or browser proof, stop conditions, and dispatch
    owner. Preserve the rule that `needs_ideation` permits ideation only and
    `build_allowed=false`.
- result: pending

## Verification Gate

```bash
python3 scripts/aios_serving_design_gate.py assess --root . --json
python3 scripts/aios_world_readiness.py --json
python3 scripts/aios_monitor.py assess --json
```

Expected current state:

- serving design gate exists and routes to Product Design ideation;
- world readiness remains `false`;
- no `apps/serving/**` implementation exists from this contract.

## Stop Conditions

- `local_demo_claimed_as_real_serving`
- `prototype_claimed_as_world_ready`
- `ui_implementation_before_visual_target`
- `serving_ui_reuses_operator_control_center`
- `single_user_state_used_for_multi_user_claim`
- `cross_user_memory_or_artifact_visibility`
- `operator_or_support_raw_user_content_leak`
- `provider_access_value_in_doc_prompt_or_log`
- `child_repo_implementation_without_owner_contract`
- `world_readiness_claim_without_release_proof`
