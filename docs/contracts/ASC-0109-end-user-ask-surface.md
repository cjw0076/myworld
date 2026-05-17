---
contract_id: ASC-0109
slug: end-user-ask-surface
status: closed
goal: Raise the AIOS control app from operator dashboard to end-user intake by letting a local user submit one goal and receive ask artifacts plus a proposed contract seed.
created: 2026-05-13 KST
accepted: 2026-05-13 KST by Codex under founder continuation
closed: 2026-05-13 KST
praxis_required: true
praxis_ref: docs/praxis/ASC-0109-end-user-ask-surface.json
origin: founder request to raise the interface layer for end users
---

# ASC-0109 End User Ask Surface

## Why Now

ASC-0103 and ASC-0104 made `bin/aios ask` useful from CLI. The founder now
needs the same loop to appear in the local control app, so a non-operator can
state intent without knowing contracts, dispatch IDs, or shell commands.

## Scope

repos:

- `myworld`

allowed_files:

- `docs/contracts/ASC-0109-end-user-ask-surface.md`
- `docs/praxis/ASC-0109-end-user-ask-surface.json`
- `docs/AIOS_MONITOR_RECONCILIATIONS.json`
- `docs/AIOS_CONTROL_APP.md`
- `docs/AGENT_WORKLOG.md`
- `scripts/aios_local_app.py`
- `apps/control/index.html`
- `apps/control/app.js`
- `apps/control/styles.css`
- `tests/test_aios_local_app.py`

forbidden_files:

- `.env`
- raw exports
- private provider auth files
- child repo implementation files
- `hivemind/**`
- `memoryOS/**`
- `CapabilityOS/**`
- `GenesisOS/**`

## Responsibilities

### myworld

must_produce:

- Local-only HTTP API on the existing control app server for end-user asks.
- Browser form that posts one natural-language goal and requests
  `--draft-contract` by default.
- API response that returns ask receipt fields and artifact paths without
  executing child repo work.
- Validation that rejects empty or oversized ask text.
- Documentation showing the control app as an intake surface.

### memoryos

must_produce:

- No direct repo work in this contract.
- Context is represented through the ask/invocation artifacts emitted by the
  existing `scripts/aios_ask.py` route.

### capabilityos

must_produce:

- No direct repo work in this contract.
- Capability routing remains inside the existing ask/invocation plan-only
  artifacts.

### hive_mind

must_produce:

- No direct child repo execution.
- Verification is owned by `myworld` tests and local smoke commands.

### operator

must_produce:

- Review generated ask artifacts or contract seeds before any accepted dispatch.

## Verification Gate

```bash
cd .
python -m unittest tests/test_aios_local_app.py tests/test_aios_ask.py
python scripts/aios_work_praxis.py validate docs/praxis/ASC-0109-end-user-ask-surface.json --json
python scripts/aios_local_app.py refresh --json
python scripts/aios_control_snapshot.py --check-app-js apps/control/app.js --json
```

## Stop Conditions

- `ask_api_executes_child_repo_work`
- `ask_api_bypasses_contract_acceptance`
- `ask_api_accepts_empty_goal`
- `ask_api_writes_outside_aios_asks`
- `private_provider_auth_exposed`
- `control_app_static_mode_crashes`
- `contract_id_collision_unreconciled`

## Receipts

- Implemented a local-only control app API:
  - `GET /api/health`
  - `POST /api/ask`
- `POST /api/ask` validates goal text, enforces `MAX_ASK_CHARS`, and calls
  `scripts/aios_ask.py --draft-contract --json` in plan-only mode.
- Updated `python scripts/aios_local_app.py start/up` so the control app uses
  the AIOS-aware local server instead of plain `python -m http.server`.
- Added the browser `Ask AIOS` form in `apps/control/index.html`, with
  JavaScript submission and artifact-path rendering in `apps/control/app.js`.
- Added responsive styling in `apps/control/styles.css`.
- Documented the end-user intake path in `docs/AIOS_CONTROL_APP.md`.
- Reconciled the transient `asc-0105` dispatch ID-collision artifact after
  ASC-0105 was already assigned to the DNA canonical spec and this work moved
  to ASC-0109.
- Verification passed:
  - `python -m unittest tests/test_aios_local_app.py tests/test_aios_ask.py`
  - `python scripts/aios_work_praxis.py validate docs/praxis/ASC-0109-end-user-ask-surface.json --json`
  - `python scripts/aios_local_app.py refresh --json`
  - `python scripts/aios_control_snapshot.py --check-app-js apps/control/app.js --json`
  - `python scripts/aios_dispatch.py watch --repo myworld --dispatch-id asc-0109 --once`
  - `python scripts/aios_dispatch.py collect --repo myworld`
  - `python scripts/aios_monitor.py assess --write --json`
- Dispatch result:
  - `.aios/outbox/myworld/asc-0109.myworld.result.json` passed.
- Live API smoke:
  - `POST http://127.0.0.1:8765/api/ask`
  - ask `ask-5d5f30ff692a-20260513T164357`
  - contract seed `.aios/asks/ask-5d5f30ff692a-20260513T164357/contract_seed.md`
- Final monitor health:
  - `clear`
- Release writeback:
  - MemoryOS draft `mem_25eb447f7bb8257a`
