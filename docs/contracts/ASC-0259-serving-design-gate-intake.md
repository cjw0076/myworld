---
contract_id: ASC-0259
slug: serving-design-gate-intake
status: closed
goal: Add a serving design-gate intake workflow that asks the required Product Design questions and prevents `needs_ideation` from being treated as build permission.
created: 2026-06-13T19:27:00+09:00
accepted: 2026-06-13T19:27:00+09:00
closed: 2026-06-13T19:31:00+09:00
human_approved: true
origin: ASC-0258 made the serving design gate machine-checkable, but the gate still needs a deterministic intake path and sharper separation between ideation readiness and implementation readiness.
---

# ASC-0259 Serving Design Gate Intake

## Why Now

ASC-0258 correctly blocks `apps/serving/` while the design gate artifact is
missing. It also exposed a subtle policy issue: a confirmed brief with
`visual_target_type=needs_ideation` must permit ideation, not implementation.

This contract adds an intake primitive:

```text
questions -> draft artifact -> assess -> ASC-0253 ideate/prototype
```

No UI is built here.

## Scope

repos:

- `myworld`

allowed_files:

- `scripts/aios_serving_design_gate.py`
- `tests/test_aios_serving_design_gate.py`
- `docs/contracts/ASC-0259-serving-design-gate-intake.md`
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
- `artifacts/**`
- `gemini/**`
- `gemini-cli/**`
- `1.md`

## Required Work

1. Add `questions --json` to output the exact fields needed from the operator.
2. Add `draft --json` to produce a candidate `aios.serving_design_gate.v1`
   artifact from supplied answers, with optional `--write`.
3. Require `next_product_design_step`.
4. Enforce:
   - `visual_target_type=needs_ideation` -> `next_product_design_step=ideate`
     and `build_allowed=false`.
   - concrete visual target -> `next_product_design_step=prototype` and
     `build_allowed=true`.
5. Keep JSON assessment inspection non-throwing for automation.
6. Add focused tests.

## Verification Gate

```bash
python3 -m unittest tests.test_aios_serving_design_gate -v
python3 -m py_compile scripts/aios_serving_design_gate.py
python3 scripts/aios_serving_design_gate.py questions --json
python3 scripts/aios_serving_design_gate.py draft --root . --product-goal "..." --visual-target-type needs_ideation --interactivity-level full --confirmed-by-user --json
git diff --check
```

## Stop Conditions

- `apps_serving_modified`
- `needs_ideation_allows_build`
- `draft_writes_without_explicit_write_flag`
- `private_design_reference_logged`

next: ask the operator the generated questions and write
`.aios/serving/design_gate.json` only after the brief is confirmed.

## Result Packet

schema_version: `aios.result_packet.v1`
contract_id: `ASC-0259`
dispatch_id: `asc-0259`
repo: `myworld`
agent: `codex@myworld`
status: `passed`

changed:

- `scripts/aios_serving_design_gate.py`
- `tests/test_aios_serving_design_gate.py`
- `docs/contracts/ASC-0259-serving-design-gate-intake.md`
- `docs/AGENT_WORKLOG.md`
- `docs/AIOS_AGENT_LEDGER.md`

evidence:

- `python3 -m unittest tests.test_aios_serving_design_gate -v` passed 10/10.
- `python3 -m py_compile scripts/aios_serving_design_gate.py` passed.
- `python3 scripts/aios_serving_design_gate.py questions --json` returns the
  required Product Design intake fields and routing rules.
- `python3 scripts/aios_serving_design_gate.py draft --root . --product-goal
  'End user creates and tracks an AIOS task.' --visual-target-type
  needs_ideation --interactivity-level full --confirmed-by-user --json`
  returns `ready=true`, `next_product_design_step=ideate`, and
  `build_allowed=false`, without writing the artifact.

implemented:

- `questions --json`
- `draft --json`
- `draft --write`
- `next_product_design_step`
- `needs_ideation` no longer grants build permission.

remaining_gaps:

- The real serving design gate artifact is still not written because the
  operator has not answered/confirmed the Product Design brief.
- `apps/serving/` remains intentionally unimplemented.
