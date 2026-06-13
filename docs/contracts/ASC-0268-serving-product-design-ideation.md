---
contract_id: ASC-0268
slug: serving-product-design-ideation
status: closed
goal: Generate and preserve three Product Design visual directions for the real end-user AIOS serving product without starting UI implementation.
created: 2026-06-14T02:05:00+09:00
accepted: 2026-06-14T02:05:00+09:00
closed: 2026-06-14T02:05:00+09:00
human_approved: true
origin: The operator resumed the real-user serving preparation path. ASC-0260 and ASC-0262 made Product Design ideation the first release blocker before any `apps/serving/**` build work.
---

# ASC-0268 Serving Product Design Ideation

## Decision

Product Design Slice 1 has generated three visual directions for AIOS
end-user serving:

1. Task Cabin
2. Mission Control For One Job
3. Memory-First Service Desk

The options and brief are preserved in:

- `docs/product/AIOS_SERVING_DESIGN_BRIEF.md`
- `docs/product/assets/aios-serving-option-01-task-cabin.png`
- `docs/product/assets/aios-serving-option-02-mission-control.png`
- `docs/product/assets/aios-serving-option-03-memory-first-service-desk.png`

This closes ideation only. It does not select a visual target and does not
authorize UI implementation.

## Scope

repos:

- `myworld`

allowed_files:

- `docs/product/AIOS_SERVING_DESIGN_BRIEF.md`
- `docs/product/assets/aios-serving-option-*.png`
- `.aios/serving/design_gate.json`
- `scripts/aios_serving_release_gate.py`
- `tests/test_aios_serving_release_gate.py`
- `docs/contracts/ASC-0268-serving-product-design-ideation.md`
- `docs/AGENT_WORKLOG.md`
- `docs/AIOS_AGENT_LEDGER.md`

forbidden_files:

- `.env`
- `.env.*`
- provider auth files
- private vault contents
- raw provider logs
- private history stores
- `apps/serving/**`
- `apps/control/**`
- child repo implementation files
- `CapabilityOS/**`
- `hivemind/**`
- `memoryOS/**`
- `GenesisOS/**`
- `uri/**`
- `artifacts/**`
- `gemini/**`
- `gemini-cli/**`
- `1.md`

## Product Design Evidence

- Product Design `user-context` preflight reported no saved context.
- Local visual context was inspected from existing AIOS Control Center
  screenshots, design docs, and CSS.
- The three generated directions use the end-user serving routes and privacy
  boundaries from ASC-0251, ASC-0260, and ASC-0262.
- The Image Gen tool could not receive local screenshot attachments in this
  tool surface; local screenshots were inspected directly and summarized into
  the prompts instead.

## Gate State

The serving design gate now means:

- `visual_target_type=needs_selection`
- `next_product_design_step=select_visual_target`
- `build_allowed=false`

Therefore ASC-0253 remains blocked from UI implementation until one option is
selected or a revised option becomes the concrete visual target.

## Verification

```bash
python3 -m unittest tests.test_aios_serving_release_gate -v
python3 scripts/aios_serving_release_gate.py assess --root . --json
python3 scripts/aios_world_readiness.py --json
git diff --check
```

Expected state:

- serving release remains not ready;
- world readiness remains false;
- product design slice remains partial until a concrete option is selected;
- no `apps/serving/**` files exist from this contract.

## Stop Conditions

- `ui_implementation_before_visual_target`
- `serving_ui_reuses_operator_control_center`
- `selected_option_missing`
- `visual_target_claim_without_image`
- `world_readiness_claim_without_browser_proof`
