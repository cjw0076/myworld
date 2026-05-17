---
contract_id: ASC-0145
slug: reviewed-envelope-to-dispatch-promotion
status: closed
goal: Let the end-user AIOS session UI promote a reviewed session envelope into a governed contract seed or dispatch packet without falling back to chat-only operator prompts.
created: 2026-05-14 KST
accepted: 2026-05-14 KST by founder GO "진행"
closed: 2026-05-14 KST
acceptance_authority: founder
origin: ASC-0144 made the browser create plan-only session envelopes, but the next step still requires manual operator translation from envelope to contract or dispatch.
---

# ASC-0145 Reviewed Envelope To Dispatch Promotion

DNA references: Invariant 1 (decide before acting), Invariant 4 (named exit),
Invariant 5 (provenance chain), Invariant 6 (operator override remains
possible), Invariant 8 (classify before committing).

## Scope

repos:

- `myworld`

allowed_files:

- `scripts/aios_local_app.py`
- `scripts/aios_ask.py`
- `scripts/aios_dispatch.py`
- `apps/control/index.html`
- `apps/control/app.js`
- `apps/control/styles.css`
- `tests/test_aios_local_app.py`
- `tests/test_aios_ask.py`
- `tests/test_aios_dispatch.py`
- `docs/AIOS_CONTROL_APP.md`
- `docs/AIOS_INVOCATION_PIPELINE.md`
- `docs/contracts/ASC-0145-reviewed-envelope-to-dispatch-promotion.md`
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

- A reviewed-envelope promotion endpoint that accepts a
  `.aios/invocations/*/session_envelope.json` ref and returns one of:
  - proposed contract seed,
  - dispatch-ready packet preview,
  - blocked receipt with explicit stop condition.
- UI action on the session result that runs promotion only after the user
  confirms the reviewed envelope.
- Promotion must preserve the original `session_envelope.ref` in the generated
  contract seed or dispatch preview.
- No executor work starts from this UI action unless an accepted contract and
  dispatch packet already exist.

## Verification Gate

```bash
cd /home/user/workspaces/jaewon/myworld
python -m py_compile scripts/aios_local_app.py scripts/aios_ask.py scripts/aios_dispatch.py
python -m unittest tests/test_aios_local_app.py tests/test_aios_ask.py tests/test_aios_dispatch.py
python scripts/aios_invoke.py --goal "ASC-0145 promotion smoke" --write .aios/invocations/asc-0145-smoke --plan-only --json
python -m unittest discover -s tests -p 'test_aios_*.py'
```

Pass criteria:

- Promotion rejects envelope refs outside `.aios/invocations`.
- Promotion rejects missing or invalid `aios.session_envelope.v1`.
- Promotion output cites the same envelope ref.
- UI confirmation is required before promotion.
- Full MyWorld AIOS tests pass.

## Stop Conditions

- `session_envelope_missing`
- `session_envelope_ref_outside_invocations`
- `promotion_without_confirmation`
- `executor_runs_from_promotion`
- `dispatch_packet_missing_envelope_ref`
- `verification_gate_failed`

## Receipts

- `scripts/aios_local_app.py` now exposes `POST /api/promote_session`, which
  requires explicit confirmation, validates that the envelope ref stays under
  `.aios/invocations/*/session_envelope.json`, rejects invalid
  `aios.session_envelope.v1`, and writes a non-executing promotion receipt plus
  contract seed under `.aios/promotions/`.
- `apps/control/app.js` renders a `Promote reviewed session` action on session
  results and blocks promotion until the user checks review confirmation.
- `apps/control/styles.css` adds the promotion receipt panel layout.
- `docs/AIOS_CONTROL_APP.md` documents that promotion does not start executor
  work.
- Focused tests passed 36/36.
- Invocation smoke:
  `.aios/invocations/asc-0145-smoke/session_envelope.json`.
- HTTP promotion smoke wrote:
  `.aios/promotions/promotion-0990071087b3-20260514T031028/promotion.json`.
- Full MyWorld AIOS test suite passed 316/316.
- Watcher result:
  `.aios/outbox/myworld/asc-0145.myworld.result.json` passed.
- MemoryOS draft writeback: `mem_4b70ac85e4e6e6d6`.
