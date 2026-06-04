---
contract_id: ASC-0201
slug: aios-anticipatory-surface
status: closed
goal: Add a first-screen anticipatory surface so AIOS shows what it would do next if the operator does nothing.
created: 2026-05-18T04:31:00+09:00
accepted: 2026-05-18T04:31:00+09:00
closed: 2026-05-18T04:33:00+09:00
origin: ASC-0200 GenesisOS strongest discomfort `reactive_passivity`
accepted_by: codex_delegated_operator
---

# ASC-0201 AIOS Anticipatory Surface

## Why Now

ASC-0200 closed with a GenesisOS finding: the Control Center is becoming a
better evidence dashboard, but AIOS still feels reactive. It shows what already
happened, not what the operating loop would do next if left alone.

This contract implements the smallest visible step toward an anticipatory
interaction grammar without hiding audit evidence.

## Scope

repos:

- `myworld`

allowed_files:

- `docs/contracts/ASC-0201-aios-anticipatory-surface.md`
- `docs/AGENT_WORKLOG.md`
- `docs/AIOS_CONTROL_APP.md`
- `apps/control/index.html`
- `apps/control/app.js`
- `apps/control/styles.css`
- `tests/test_aios_local_app.py`

forbidden_files:

- `.env`
- raw exports
- private provider auth files
- child repo implementation files
- `memoryOS/`
- `CapabilityOS/`
- `GenesisOS/genesisos/`
- `hivemind/`

## Requirements

must_produce:

- A first-screen `Next If Idle` surface in the Control Center conversation area.
- The surface must show:
  - predicted next owner,
  - predicted next action,
  - why AIOS thinks that action matters,
  - current stop/health state,
  - at least one action button that routes through existing AIOS ask/session
    machinery instead of executing hidden work.
- The surface must be data-driven from existing snapshot state. Do not add a
  new backend daemon.
- The surface must not claim autonomous execution. It is a recommendation layer,
  not an executor.

must_not:

- Hide existing Evidence Desk receipts.
- Add another generic log panel.
- Execute child repo work directly from the browser.
- Remove auditability or artifact controls.

## Verification Gate

```bash
python -m py_compile scripts/aios_control_snapshot.py scripts/aios_local_app.py scripts/aios_visual_verify.py
python scripts/aios_control_snapshot.py --check-app-js apps/control/app.js --json
python -m unittest tests.test_aios_local_app.AiosLocalAppTest.test_control_app_contains_end_user_ask_surface -v
python -m unittest tests.test_aios_local_app tests.test_aios_control_snapshot tests.test_aios_visual_verify -v
python scripts/aios_local_app.py refresh --json
python scripts/aios_visual_verify.py 'http://127.0.0.1:8765/?mode=simple' --screenshot .aios/screenshots/aios-control-v4-anticipatory-surface.png --allow-degraded --json
python scripts/aios_monitor.py assess --json
```

## Stop Conditions

- `anticipatory_surface_missing`
- `surface_claims_hidden_execution`
- `surface_not_first_screen`
- `surface_breaks_chat_input`
- `visual_verification_failed`
- `existing_control_app_tests_regress`
- `audit_receipts_hidden`

## Receipts

- implementation: `apps/control/index.html`, `apps/control/app.js`,
  `apps/control/styles.css`
- docs: `docs/AIOS_CONTROL_APP.md`, `docs/AGENT_WORKLOG.md`
- tests: `tests/test_aios_local_app.py`
- visual_receipt: `.aios/visual_verification/vis-3942e6665663/receipt.json`
- dispatch_result: `.aios/outbox/myworld/asc-0201.myworld.result.json`
- dispatch_status: `asc-0201` sent to `myworld`, watcher passed, collected
  2026-05-20T16:20:48+09:00.
- visual_receipt_after_dispatch:
  `.aios/visual_verification/vis-cbaa55c028a4/receipt.json`
- screenshot: `.aios/screenshots/aios-control-v4-anticipatory-surface.png`

Outcome:

- The first-screen conversation surface now shows `Next If Idle`.
- `Explain` routes through chat prompt preparation.
- `Govern` routes through governed ask creation.
- No hidden child-repo execution is triggered from the browser.
