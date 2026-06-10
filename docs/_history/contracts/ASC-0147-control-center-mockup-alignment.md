---
contract_id: ASC-0147
slug: control-center-mockup-alignment
status: closed
goal: Align the AIOS end-user control application with the generated final interface mockup: sidebar, system status row, compact command input, agent work cards, artifact lane, and timeline.
created: 2026-05-14 KST
accepted: 2026-05-14 KST by founder directive "해당 이미지대로 디자인 해"
closed: 2026-05-14 KST
acceptance_authority: founder
origin: Generated image `/home/user/.codex/generated_images/019e16ee-7c0f-79a0-b3d4-9b52fa2ab268/ig_03c0e549c66efb13016a04b222cbb4819195020bfdb2c9ae1d.png`.
---

# ASC-0147 Control Center Mockup Alignment

DNA references: Invariant 1 (decide before acting), Invariant 5 (provenance
chain), Invariant 8 (classify before committing).

## Scope

repos:

- `myworld`

allowed_files:

- `apps/control/index.html`
- `apps/control/app.js`
- `apps/control/styles.css`
- `docs/contracts/ASC-0147-control-center-mockup-alignment.md`
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

- A sidebar-first layout matching the mockup's Control Center frame.
- Compact system status top row.
- Compact command input surface.
- Agent Work cards with artifact preview content inside each role card.
- Artifact lane and recent timeline visible in the first screen.
- Screenshot verification against the mockup direction.

## Verification Gate

```bash
cd /home/user/workspaces/jaewon/myworld
python scripts/aios_control_snapshot.py --check-app-js apps/control/app.js --json
python -m unittest tests/test_aios_control_snapshot.py tests/test_aios_local_app.py
python scripts/aios_local_app.py refresh --json
python -m unittest discover -s tests -p 'test_aios_*.py'
```

Pass criteria:

- Browser screenshot shows sidebar, status chips, command input, Agent Work
  cards, artifact lane, and timeline.
- Agent cards include artifact preview snippets.
- Full MyWorld AIOS tests pass.

## Stop Conditions

- `mockup_alignment_missing_sidebar`
- `agent_card_preview_missing`
- `command_input_overdominates_first_screen`
- `artifact_lane_not_visible`
- `verification_gate_failed`

## Receipts

- Implemented sidebar shell in `apps/control/index.html`.
- Updated `apps/control/styles.css` to match the generated mockup's visual
  structure: left rail, compact status row, command panel, five role cards,
  artifact lane, and timeline.
- Updated `apps/control/app.js` so Agent cards render artifact previews.
- Visual verification:
  `.aios/screenshots/aios-control-mockup-aligned.png` and
  `.aios/screenshots/aios-control-mockup-aligned-v2.png`.
- Focused verification passed:
  `tests/test_aios_control_snapshot.py tests/test_aios_local_app.py` 11/11.
- Full MyWorld AIOS test suite passed 311/311.
- Manual JS syntax check passed: `node --check apps/control/app.js`.
- Watcher result:
  `.aios/outbox/myworld/asc-0147.myworld.result.json` passed.
- MemoryOS draft writeback: `mem_6c40f955eced0362`.
