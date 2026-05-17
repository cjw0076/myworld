---
contract_id: ASC-0064
slug: live-dashboard-websocket
status: closed
goal: Replace ASC-0039's static snapshot with a live web dashboard that tails `.aios/primitives/events.jsonl` over WebSocket and updates the DOM in real time, while supporting both an "operator mode" (full state) and a "simple mode" (status + headline events) so the same surface scales from technical operators to non-technical viewers.
created: 2026-05-13 KST
accepted: 2026-05-13 KST by claude acting operator (founder role delegated)
closed: 2026-05-13 KST by codex@myworld
acceptance_authority: claude@myworld (operator) per founder approval of UI sequence and directive "최종적으로 레이어가 다른 사람들을 전부 아우를 수 있어야하니까".
origin: claude UI proposal 2026-05-13 KST. ASC-0039 dashboard is currently static — must reload to see new state. Live event stream is the foundation for every later UI ASC.
---

# ASC-0064 Live Dashboard via WebSocket

## Why Now

ASC-0039 created a static snapshot dashboard at `apps/control/`. ASC-0040
wrapped it in a local server. The dashboard data is REGENERATED only when
`aios_control_snapshot.py` runs — there is no live update. To watch the
loop in real time, the operator must hit refresh. This blocks every
later UI ASC (decision inbox, goal bar, pulse heartbeat) which need
streaming state.

Founder approved the UI sequence with explicit guidance that every UI
layer must scale from technical operators to non-technical viewers. ASC-0064
implements that scale by adding both an **operator mode** (full state, raw
event lines, debug detail) and a **simple mode** (status indicator,
plain-language headline events, friendly counts) that share the same data
stream and toggle without page reload.

## Scope

repos:

- `myworld`

allowed_files:

- `apps/control/index.html`
- `apps/control/app.js`
- `apps/control/styles.css`
- `apps/control/live.js`
- `scripts/aios_local_app.py`
- `scripts/aios_dashboard_ws.py`
- `tests/test_aios_dashboard_ws.py`
- `docs/AIOS_CONTROL_APP.md`
- `docs/contracts/ASC-0064-live-dashboard-websocket.md`
- `docs/contracts/README.md`
- `docs/AIOS_AGENT_LEDGER.md`

forbidden_files:

- `hivemind/**`, `memoryOS/**`, `CapabilityOS/**`, `uri/**`
- `.env`, `.env.*`
- `.aios/logs/**`

## Per-OS Responsibility

### myworld.must_produce

- `scripts/aios_dashboard_ws.py` — WebSocket server (Python stdlib only or
  `websockets` if already vendored — operator picks). Tails
  `.aios/primitives/events.jsonl` and pushes one frame per new line.
  Also pushes a heartbeat every 30 s with current `aios_monitor.py assess`
  health and pulse list. Stops cleanly on SIGTERM.
- `scripts/aios_local_app.py up` extended: now also starts the WebSocket
  server on a sibling port (e.g. http :8088, ws :8089). `status` reports
  both PIDs.
- `apps/control/live.js` — small client that opens the WebSocket, listens
  for frames, and updates DOM via the existing app.js render functions.
  No bundler; vanilla JS only.
- `apps/control/index.html` — adds a **mode toggle** at top-right:
  - `operator` — full panes (current ASC-0039 layout) + raw event line tail
  - `simple` — only status bar + 3-pane summary (Health, Last Activity,
    Decisions Waiting). No ASC IDs, no contract numbers, no JSON. Plain
    sentences ("All systems healthy. 3 jobs running. 34 things waiting
    for your review.")
  - Toggle persists in localStorage.
- `apps/control/styles.css` — simple mode uses larger fonts, fewer
  colors, no scrolling.
- `tests/test_aios_dashboard_ws.py` — unit tests for: WS server starts,
  events.jsonl line → frame, heartbeat structure, both modes render
  without error against a sample data set.

### child repos

- No source change.

## Verification Gate

```bash
python -m py_compile scripts/aios_dashboard_ws.py scripts/aios_local_app.py
python -m unittest tests/test_aios_dashboard_ws.py
python scripts/aios_local_app.py up --json
sleep 2
# touch a new event to test live push
python scripts/aios_primitives.py task create --subject "ASC-0064 live test" --description x --json
sleep 2
python scripts/aios_local_app.py status --json --assert-live
python scripts/aios_local_app.py stop
python -m unittest discover -s tests -p 'test_aios_*.py'
python scripts/aios_monitor.py assess --json
```

Pass criteria:

- `up` starts both http and ws servers; `status` reports both running.
- A new event line is pushed to connected clients within 1 s.
- Heartbeat frame includes monitor health + pulse list.
- Mode toggle (operator ↔ simple) works without reload; selection
  persists across page refresh via localStorage.
- Simple mode renders ZERO ASC IDs, contract numbers, or raw JSON
  — only plain sentences.
- Full test suite green.

## Stop Conditions

- `single_audience_lock`: dashboard works only in operator mode (no simple
  mode) — fails the multi-audience directive.
- `progressive_disclosure_failure`: simple mode shows technical IDs or
  raw JSON.
- `events_path_traversal`: WebSocket exposes file paths outside
  `.aios/primitives/`.
- `heartbeat_silence`: heartbeat frame missing or > 60 s gap.
- `child_repo_scope_leak`
- `verification_gate_failed`

## Receipts

- implementation: `scripts/aios_dashboard_ws.py`, `scripts/aios_local_app.py`,
  `apps/control/live.js`, `apps/control/index.html`, `apps/control/app.js`,
  `apps/control/styles.css`, `tests/test_aios_dashboard_ws.py`
- local verification:
  - `python -m py_compile scripts/aios_dashboard_ws.py scripts/aios_local_app.py`
  - `python -m unittest tests/test_aios_dashboard_ws.py tests/test_aios_local_app.py`
  - `python scripts/aios_local_app.py up --port 9875 --ws-port 9876 --json`
  - `python scripts/aios_primitives.py task create --subject "ASC-0064 live test" --description x --json`
  - `python scripts/aios_local_app.py status --json --assert-live`
  - `python scripts/aios_local_app.py stop --json`
- dispatch receipt: `.aios/outbox/myworld/asc-0064.myworld.result.json`
  with `status=passed`.

## Work Packets

### WP-0064-A — codex@myworld implements live dashboard

- target_agent: codex
- target_repo: myworld
- status: done
- closed: 2026-05-13 KST
- brief: |
    Add WebSocket server, integrate with aios_local_app.py up/status/stop,
    write live.js client, add mode toggle (operator ↔ simple) to index.html
    with persisted localStorage selection. Both modes share the same
    data stream. Stop conditions specifically forbid single-audience or
    technical-only renders.

    After verification, dogfood: run `up`, open browser, toggle modes,
    fire a `task create` event, confirm both modes update within 1 s.
- result: `.aios/outbox/myworld/asc-0064.myworld.result.json`
