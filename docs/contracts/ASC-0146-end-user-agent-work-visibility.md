---
contract_id: ASC-0146
slug: end-user-agent-work-visibility
status: closed
goal: Make the end-user control app show how AIOS agents performed work and what artifacts they produced, not just that a session envelope exists.
created: 2026-05-14 KST
accepted: 2026-05-14 KST by founder directive "눈으로 보고 디자인 해"
closed: 2026-05-14 KST
acceptance_authority: founder
origin: ASC-0144 created session intake, but visual inspection showed the first screen still hid agent work and result artifacts behind file paths.
---

# ASC-0146 End-User Agent Work Visibility

DNA references: Invariant 1 (decide before acting), Invariant 5 (provenance
chain), Invariant 8 (classify before committing).

## Scope

repos:

- `myworld`

allowed_files:

- `scripts/aios_control_snapshot.py`
- `apps/control/index.html`
- `apps/control/app.js`
- `apps/control/styles.css`
- `tests/test_aios_control_snapshot.py`
- `docs/AIOS_CONTROL_APP.md`
- `docs/contracts/ASC-0146-end-user-agent-work-visibility.md`
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

- Snapshot support for recent `.aios/invocations/*/receipt.json` and
  `session_envelope.json`.
- Safe artifact previews for files under `.aios/invocations` only.
- A first-screen `Agent Work` surface showing:
  - GenesisOS, MemoryOS, CapabilityOS, Hive role status.
  - executor assignment.
  - artifact paths and previews.
  - recent dispatch timeline.
- Browser screenshot evidence after visual inspection.

## Verification Gate

```bash
cd /home/user/workspaces/jaewon/myworld
python -m py_compile scripts/aios_control_snapshot.py
python -m unittest tests/test_aios_control_snapshot.py tests/test_aios_local_app.py tests/test_aios_invoke.py
python scripts/aios_control_snapshot.py --check-app-js apps/control/app.js --json
python scripts/aios_local_app.py refresh --json
python -m unittest discover -s tests -p 'test_aios_*.py'
```

Pass criteria:

- Snapshot includes `invocations.latest`.
- Latest invocation includes role statuses, executor assignment, artifact refs,
  and safe artifact previews.
- Browser first screen renders `Agent Work`, role cards, artifact previews, and
  recent dispatch timeline.
- Full MyWorld AIOS tests pass.

## Stop Conditions

- `artifact_preview_reads_outside_invocations`
- `raw_export_previewed`
- `agent_work_surface_missing`
- `result_artifact_preview_missing`
- `verification_gate_failed`

## Receipts

- 2026-05-14 KST: `scripts/aios_control_snapshot.py` now emits
  `invocations.latest` from `.aios/invocations/*/receipt.json` and
  `session_envelope.json`.
- Artifact previews are constrained to files under `.aios/invocations`.
- `apps/control/index.html`, `apps/control/app.js`, and
  `apps/control/styles.css` now render `Agent Work`, role cards, executor
  assignment, artifact previews, and recent dispatch timeline on the first
  screen.
- Visual baseline: `.aios/screenshots/aios-control-before.png`.
- Visual verification:
  `.aios/screenshots/aios-control-after-agent-work.png` and
  `.aios/screenshots/aios-control-after-previews.png`.
- Focused tests passed 18/18.
- Full MyWorld AIOS test suite passed 311/311.
- Watcher result:
  `.aios/outbox/myworld/asc-0146.myworld.result.json` passed.
- MemoryOS draft writeback: `mem_eb56be3ecc0ae906`.
