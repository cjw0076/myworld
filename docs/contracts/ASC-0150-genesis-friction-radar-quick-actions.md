---
contract_id: ASC-0150
slug: genesis-friction-radar-quick-actions
status: closed
goal: Use GenesisOS critique to expose Control Center discomfort as quick actions and a Friction Radar so end users can reach AIOS capabilities without knowing internal commands.
created: 2026-05-14 KST
accepted: 2026-05-14 KST by founder GO "AIOS 사용해서 개발"
closed: 2026-05-14 KST
acceptance_authority: founder
origin: The Control Center could talk to AIOS, show worldlines, and expose artifacts, but the first conversation panel still left users unsure what to do next.
---

# ASC-0150 Genesis Friction Radar Quick Actions

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
- `tests/test_aios_local_app.py`
- `docs/contracts/ASC-0150-genesis-friction-radar-quick-actions.md`
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

## AIOS Inputs Used

- GenesisOS divergence:
  `.aios/invocations/inv-b317cdfcdde3-20260514T025155/genesis/branches.json`
- GenesisOS critique of the UI discomfort:
  `needs_human_or_genesis_review`
- MyWorld monitor next-actions:
  `.aios/state/monitor_assessment.latest.json`

## myworld.must_produce

- A snapshot-level `friction_radar` section derived from monitor next-actions
  with a fallback item when the monitor is quiet.
- Control Center quick-action buttons that seed useful AIOS prompts into the
  inline conversation surface.
- A visible Friction Radar band that shows owner, severity, need, source, and
  reason without forcing users to inspect JSON artifacts.
- Tests proving the snapshot and browser surface contain the new UI entry
  points.

## genesisos.must_produce

- A critique signal identifying the empty/hidden-action conversation panel as a
  product discomfort before implementation.
- A non-binding worldline lens remains visible beside the new radar; GenesisOS
  proposes and challenges, but MyWorld selects the implementation.

## memoryos.must_produce

- No direct memory acceptance in this contract.
- MemoryOS receives the closeout as a draft writeback through the existing
  release path after verification.

## capabilityos.must_produce

- No new external capability execution in this contract.
- Existing chat and HTTP fallback routes remain the access path; future tool
  recommendations stay under CapabilityOS-owned contracts.

## hive_mind.must_produce

- No child-repo execution in this contract.
- MyWorld watcher verification is sufficient because this is a control-app
  visibility and snapshot slice.

## Operator Criteria

- End users can see suggested AIOS actions before typing a custom prompt.
- Current AIOS friction is visible as product needs, not only as monitor JSON.
- The implementation stays within the MyWorld control app and does not mutate
  child OS repos.

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

- Snapshot includes `friction_radar.items`.
- Browser HTML includes quick actions and the Friction Radar grid.
- Browser JS renders both Genesis Lens and Friction Radar.
- The visual app refresh reports a valid control snapshot.
- Full MyWorld AIOS tests pass.

## Stop Conditions

- `quick_actions_bypass_aios_chat_router`
- `friction_radar_uses_private_or_raw_paths`
- `genesis_lens_replaces_operator_decision`
- `child_repo_scope_violation`
- `verification_gate_failed`

## Receipts

- `scripts/aios_control_snapshot.py` now emits `friction_radar` from monitor
  next-actions with a safe fallback item.
- `apps/control/index.html` adds Quick Actions and a `Friction Radar` band.
- `apps/control/app.js` seeds quick-action prompts into `Talk to AIOS` and
  renders Friction Radar cards.
- `apps/control/styles.css` adds responsive provider-grade treatment for quick
  actions, Friction Radar, and Genesis Lens.
- Manual JS syntax check with `node --check apps/control/app.js` passed; the
  watcher-safe gate uses `scripts/aios_control_snapshot.py --check-app-js`.
- Focused tests passed 12/12.
- Full MyWorld AIOS test suite passed 313/313.
- Watcher result:
  `.aios/outbox/myworld/asc-0150.myworld.result.json` passed.
- MemoryOS draft writeback: `mem_fac482c25fb70df1`.
- Visual screenshot:
  `.aios/screenshots/aios-control-friction-radar.png`
