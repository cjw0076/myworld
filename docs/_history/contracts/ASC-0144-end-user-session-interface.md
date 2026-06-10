---
contract_id: ASC-0144
slug: end-user-session-interface
status: closed
goal: Make the local AIOS control app start from an end-user goal and create a plan-only AIOS session envelope before any executor work.
created: 2026-05-14 KST
accepted: 2026-05-14 KST by founder GO "end user interface로 만들어볼 수 있나 ?"
closed: 2026-05-14 KST
acceptance_authority: founder
origin: ASC-0143 created the session envelope runtime binding; the browser control app still exposed ask/contract tools before the end-user AIOS entrypoint.
---

# ASC-0144 End-User Session Interface

DNA references: Invariant 1 (decide before acting), Invariant 4 (named exit),
Invariant 5 (provenance chain), Invariant 8 (classify before committing).

## Scope

repos:

- `myworld`

allowed_files:

- `scripts/aios_local_app.py`
- `apps/control/index.html`
- `apps/control/app.js`
- `apps/control/styles.css`
- `tests/test_aios_local_app.py`
- `docs/AIOS_CONTROL_APP.md`
- `docs/contracts/ASC-0144-end-user-session-interface.md`
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

- A local app endpoint that accepts one end-user goal and calls
  `scripts/aios_invoke.py` in plan-only mode.
- A generated `.aios/invocations/end-user-*/session_envelope.json`.
- Browser UI that shows role statuses for GenesisOS, MemoryOS, CapabilityOS,
  and Hive before executor work.
- Browser UI that shows executor assignment as an AIOS output, not as direct
  provider selection by the user.
- Tests proving the endpoint rejects empty goals and returns a session envelope.

## capabilityos

No direct tool execution is granted by this contract. CapabilityOS may appear
only through the recommendation artifact produced by `aios_invoke.py`.

## memoryos

MemoryOS remains draft/context only. This contract must not auto-accept any
memory.

## hive_mind

Hive remains the execution owner in the session envelope. This contract does
not dispatch executable Hive work.

## Verification Gate

```bash
cd /home/user/workspaces/jaewon/myworld
python -m py_compile scripts/aios_local_app.py
python -m unittest tests/test_aios_local_app.py
python scripts/aios_control_snapshot.py --check-app-js apps/control/app.js --json
python scripts/aios_invoke.py --goal "ASC-0144 end user session smoke" --write .aios/invocations/asc-0144-smoke --plan-only --json
python -m unittest discover -s tests -p 'test_aios_*.py'
```

Pass criteria:

- `POST /api/session` rejects missing goals.
- `POST /api/session` returns a receipt and loaded
  `aios.session_envelope.v1`.
- The browser has a first-screen `session-form` with role status rendering.
- Focused local app tests pass.
- Full MyWorld AIOS tests pass.

Manual JS syntax evidence may additionally use `node --check apps/control/app.js`,
but the contract gate must remain executable by the AIOS dispatch watcher
allowlist.

## Stop Conditions

- `session_endpoint_missing`
- `session_envelope_missing`
- `ui_bypasses_aios_invoke`
- `executor_runs_from_ui_without_dispatch`
- `memory_auto_accept_from_ui`
- `capability_tool_executes_from_ui`
- `verification_gate_failed`

## Receipts

- 2026-05-14 KST: `scripts/aios_local_app.py` added `POST /api/session`,
  which calls `scripts/aios_invoke.py --plan-only --json`, writes under
  `.aios/invocations/end-user-*`, and returns the loaded
  `aios.session_envelope.v1`.
- `apps/control/index.html`, `apps/control/app.js`, and
  `apps/control/styles.css` added the first-screen end-user session form and
  role status rendering for GenesisOS, MemoryOS, CapabilityOS, and Hive.
- Smoke invocation:
  `.aios/invocations/asc-0144-smoke/session_envelope.json`.
- Dispatch packet:
  `.aios/inbox/myworld/asc-0144.myworld.json` includes
  `session_envelope.ref`.
- Watcher result:
  `.aios/outbox/myworld/asc-0144.myworld.result.json` passed and echoes role
  statuses plus executor assignment from the same envelope.
- Live endpoint smoke after server restart returned `ok=true`,
  `envelope_schema=aios.session_envelope.v1`, and all four role statuses
  `passed`; generated
  `.aios/invocations/end-user-7c408aa140-20260514T020126/session_envelope.json`.
- Focused tests passed 15/15 for `tests/test_aios_invoke.py` and
  `tests/test_aios_local_app.py`.
- Full MyWorld AIOS test suite passed 311/311.
- Manual JS syntax check passed: `node --check apps/control/app.js`.
- MemoryOS draft writeback: `mem_70907d5d8614f66e`.
