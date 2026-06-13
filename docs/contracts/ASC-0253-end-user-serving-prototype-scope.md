---
contract_id: ASC-0253
slug: end-user-serving-prototype-scope
status: proposed
goal: Define and then build the first runnable end-user AIOS serving prototype once Product Design brief/visual target and runtime scope are accepted.
created: 2026-06-13T15:38:00+09:00
origin: ASC-0252 corrected the readiness gate and now points to this follow-on because the current repo has only ASC-0251 serving specs, not a runnable user service surface.
---

# ASC-0253 End-User Serving Prototype Scope

## Why Now

AIOS can no longer honestly report world deployment readiness until users have
a real serving surface and proof flow. ASC-0251 defined the product boundary.
ASC-0252 made that boundary part of the readiness gate. The next step is a
prototype/build contract, but it must not start by reusing the operator Control
Center or inventing visuals without a Product Design brief.

ASC-0260 further narrows the meaning of "serving": the target is a real
end-user served product, not a local demo. This contract remains the first
visual/prototype slice only. Production readiness requires the ASC-0260
release spine: account/session boundary, per-user runtime authority, worker
queue/resume, memory lifecycle, credential/rate/consent routing, redacted
observability, incident/support flow, and release proof.

## Proposed Scope

repos:

- `myworld`

candidate_allowed_files:

- `apps/serving/**`
- `tests/test_aios_serving_*.py`
- `scripts/aios_serving_session.py`
- `scripts/aios_world_readiness.py`
- `tests/test_aios_world_readiness.py`
- `docs/contracts/ASC-0253-end-user-serving-prototype-scope.md`
- `docs/AIOS_AGENT_LEDGER.md`
- `docs/AGENT_WORKLOG.md`

forbidden_files:

- `.env`
- `.env.*`
- provider auth files
- private vault contents
- raw provider logs
- private history stores
- `apps/control/**` except read-only reference
- child repo implementation files unless a separate owner contract names them
- `uri/**`
- `CapabilityOS/**`
- `artifacts/**`
- `gemini/**`
- `gemini-cli/**`
- `1.md`

## Acceptance Prerequisites

Before this contract is accepted, confirm:

1. Product Design brief and visual target for the end-user serving surface.
2. Whether the first prototype is static/mock-only or includes a local serving
   session API.
3. Whether `end_user_serving` runtime profile is implemented in this slice or
   split into a separate myworld runtime contract.
4. Browser verification target viewports and required first workflow path.

Current Product Design gate state:

- `.aios/serving/design_gate.json` exists;
- `visual_target_type=needs_ideation`;
- `next_product_design_step=ideate`;
- `build_allowed=false`.

Therefore this contract cannot move to UI implementation until Product Design
ideation produces a concrete visual target and the gate is updated.

## Minimum Future Build Gates

The accepted implementation contract should prove:

1. Separate `apps/serving/` surface exists and does not reuse operator Control
   Center as the user product.
2. First workflow works in browser-visible form:
   - new task;
   - job progress timeline;
   - approval gate;
   - memory draft review;
   - artifact review/download.
3. User/session/workspace isolation is represented in fixtures or local API
   state, not only in prose.
4. `scripts/aios_world_readiness.py --json` still reports not ready unless the
   prototype proof markers are present.
5. Accessibility and responsive checks cover 375px and 1280px widths.

## Stop Conditions

- `ui_implementation_before_visual_target`
- `serving_ui_reuses_operator_control_center`
- `user_memory_not_visible`
- `session_boundary_ambiguous`
- `approval_path_missing`
- `privacy_boundary_ambiguous`
- `world_readiness_claim_without_browser_proof`
- `prototype_claimed_as_world_ready`
- `local_demo_claimed_as_real_serving`
