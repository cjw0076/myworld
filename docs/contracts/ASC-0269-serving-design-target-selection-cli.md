---
contract_id: ASC-0269
slug: serving-design-target-selection-cli
status: closed
goal: Add a safe Product Design target-selection command so an operator choice can promote one generated serving option into a concrete visual target without hand-editing the gate.
created: 2026-06-14T02:20:00+09:00
accepted: 2026-06-14T02:20:00+09:00
closed: 2026-06-14T02:20:00+09:00
human_approved: true
origin: ASC-0268 generated three serving UI options and left the release gate at `needs_selection`. The next step needs a replayable, receipt-friendly way to bind an operator-selected option before `apps/serving/**` implementation begins.
---

# ASC-0269 Serving Design Target Selection CLI

## Decision

`scripts/aios_serving_design_gate.py` now supports the full Product Design gate
sequence:

```text
needs_ideation -> needs_selection -> concrete image target -> prototype
```

The new command is:

```bash
python3 scripts/aios_serving_design_gate.py select \
  --root . \
  --option-id option_1_task_cabin \
  --confirmed-by-user \
  --write \
  --json
```

The command refuses to select an option unless:

- the current gate is `visual_target_type=needs_selection`;
- `--confirmed-by-user` is present;
- the option id exists in `ideation_options`;
- the referenced option image exists on disk;
- the resulting concrete gate validates.

It does not build UI code and does not touch `apps/serving/**`.

## Scope

repos:

- `myworld`

allowed_files:

- `scripts/aios_serving_design_gate.py`
- `tests/test_aios_serving_design_gate.py`
- `docs/contracts/ASC-0269-serving-design-target-selection-cli.md`
- `docs/product/AIOS_SERVING_DESIGN_BRIEF.md`
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

## Verification

```bash
python3 -m unittest tests.test_aios_serving_design_gate -v
python3 -m py_compile scripts/aios_serving_design_gate.py
python3 scripts/aios_serving_design_gate.py assess --root . --json
python3 scripts/aios_serving_release_gate.py assess --root . --json
python3 scripts/aios_world_readiness.py --json
git diff --check
```

Expected state before operator selection:

- design gate assessment is valid with
  `next_action=product_design_select_visual_target`;
- release gate remains not production-ready;
- world readiness remains false.

Expected state after operator selection:

- `.aios/serving/design_gate.json` becomes a concrete `image` target;
- release gate can advance the Product Design slice;
- ASC-0253 may then build `apps/serving/**` under its own implementation
  contract and browser proof requirements.

## Stop Conditions

- `select_without_operator_confirmation`
- `unknown_option_id`
- `selected_visual_target_missing`
- `ui_implementation_before_visual_target`
- `world_readiness_claim_without_browser_proof`
