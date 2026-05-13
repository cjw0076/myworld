---
contract_id: ASC-0109
slug: end-user-ask-surface
status: accepted
goal: Raise the AIOS control app from operator dashboard to end-user intake by letting a local user submit one goal and receive ask artifacts plus a proposed contract seed.
created: 2026-05-13 KST
accepted: 2026-05-13 KST by Codex under founder continuation
closed:
praxis_required: true
praxis_ref: docs/praxis/ASC-0105-end-user-ask-surface.json
origin: founder request to raise the interface layer for end users
---

# ASC-0105 End User Ask Surface

## Why Now

ASC-0103 and ASC-0104 made `bin/aios ask` useful from CLI. The founder now
needs the same loop to appear in the local control app, so a non-operator can
state intent without knowing contracts, dispatch IDs, or shell commands.

## Scope

repos:

- `myworld`

allowed_files:

- `docs/contracts/ASC-0105-end-user-ask-surface.md`
- `docs/praxis/ASC-0105-end-user-ask-surface.json`
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
python scripts/aios_work_praxis.py validate docs/praxis/ASC-0105-end-user-ask-surface.json --json
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

## Receipts

Pending.
