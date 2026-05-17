---
contract_id: ASC-0151
slug: promotion-review-queue
status: closed
goal: Show reviewed session promotions and generated contract seeds in the Control Center so users do not have to search `.aios/promotions`.
created: 2026-05-14 KST
accepted: 2026-05-14 11:24 KST
closed: 2026-05-14 11:30 KST
origin: ASC-0145 can generate promotion receipts and contract seeds, but those artifacts remain hidden from the end-user interface after creation.
---

# ASC-0151 Promotion Review Queue

DNA references: Invariant 1 (decide before acting), Invariant 4 (named exit),
Invariant 5 (provenance chain), Invariant 6 (operator override remains
possible).

## Scope

repos:

- `myworld`

allowed_files:

- `scripts/aios_control_snapshot.py`
- `apps/control/index.html`
- `apps/control/app.js`
- `apps/control/styles.css`
- `tests/test_aios_control_snapshot.py`
- `tests/test_aios_local_app.py`
- `docs/AIOS_CONTROL_APP.md`
- `docs/contracts/ASC-0151-promotion-review-queue.md`
- `docs/contracts/README.md`
- `docs/AGENT_WORKLOG.md`
- `docs/AIOS_AGENT_LEDGER.md`

forbidden_files:

- `hivemind/**`
- `memoryOS/**`
- `CapabilityOS/**`
- `GenesisOS/**`
- `.env`
- raw export paths
- provider auth files

## myworld.must_produce

- Snapshot section listing recent `.aios/promotions/*/promotion.json`
  receipts.
- Control Center queue showing promotion status, envelope ref, contract seed
  path, and next action.
- No accept/dispatch button unless a later contract binds authority and
  close-condition checks.

## Verification Gate

```bash
cd /home/user/workspaces/jaewon/myworld
python -m py_compile scripts/aios_control_snapshot.py
python scripts/aios_control_snapshot.py --check-app-js apps/control/app.js --json
python -m unittest tests/test_aios_control_snapshot.py tests/test_aios_local_app.py
python scripts/aios_local_app.py refresh --json
python -m unittest discover -s tests -p 'test_aios_*.py'
```

Pass criteria:

- Snapshot includes recent promotion receipts.
- Browser UI exposes the promotion queue without reading raw private paths
  outside `.aios/promotions`.
- Queue preserves `session_envelope.ref`, `contract_seed`, and `next_action`.
- Full MyWorld AIOS tests pass.

## Stop Conditions

- `promotion_queue_reads_outside_promotions`
- `promotion_queue_auto_accepts_contract`
- `promotion_queue_auto_dispatches`
- `session_envelope_ref_missing`
- `verification_gate_failed`

## Receipts

- watcher result: `.aios/outbox/myworld/asc-0151.myworld.result.json`
- screenshot: `.aios/screenshots/aios-control-promotion-queue.png`

## Work Packets

### WP-0151-A — codex@myworld exposes promotion queue

- target_agent: codex
- target_repo: myworld
- status: done
- issued: 2026-05-14
- accepted: 2026-05-14
- closed: 2026-05-14
- depends_on: ASC-0145
- brief: |
    Add a Control Center promotion queue backed only by
    `.aios/promotions/*/promotion.json`. Show status, goal, session envelope
    ref, contract seed, dispatch preview, and next action. Do not add accept or
    dispatch execution controls.
- result: `.aios/outbox/myworld/asc-0151.myworld.result.json`
