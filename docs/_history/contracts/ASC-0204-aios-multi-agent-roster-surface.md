---
contract_id: ASC-0204
slug: aios-multi-agent-roster-surface
status: closed
closed: 2026-05-18 KST
closeout_authority: claude@myworld operator — both work packets done (data projection + UI render); Named Exit met, 13 control-snapshot tests pass.
goal: Give apps/control a multi-agent roster surface — one card per repo-agent with a one-line status digest, a contract-lifecycle kanban, an out-of-band done/blocked/needs-input channel, and diff-first review — so the AIOS interface reads as a multi-agent control plane, not a single hidden chat thread.
created: 2026-05-18 KST
proposed_by: claude@myworld
accepted: 2026-05-18 KST
acceptance_authority: claude@myworld operator — ASC-0192 follow-on; UI is a read-only projection of existing state, no new invariant, routine acceptance.
origin: ASC-0192 follow-on item 3 ("multi-agent surface"). ASC-0192 diagnosed apps/control/chat.html as a single thread with hidden substrate routing — "not multi-agent". Research: docs/research/AGENT_MULTIPLEXER_LANDSCAPE.md (Claude Squad list-pane + detail-tabs; cmux one-line status digest + out-of-band event channel; Conductor diff-first review; vibe-kanban lifecycle columns).
---

# ASC-0204 AIOS — Multi-Agent Roster Surface

DNA references: Invariant 3 (append-only audit — the kanban is a *read*
projection of the contract ledger, it does not become a second source of
truth), Invariant 6 (operator override — the roster shows state, the operator
still drives), Invariant 8 (the roster reflects verified state, not claims).

## Diagnosis (from ASC-0192)

`apps/control/` already has a dashboard (ASC-0064+) and a chat thread, but no
surface where the operator *sees the agents*. AIOS runs six repo-agents —
`claude@myworld`, `codex@myworld`, `codex@hivemind`, `codex@memoryOS`,
`codex@CapabilityOS`, `codex@GenesisOS` — and their state is scattered across
`.aios/inbox/`, `.aios/outbox/`, contract frontmatter, `child_watcher` state,
and per-repo git status. The operator has to reconstruct "who is doing what"
by hand.

## What to borrow (AGENT_MULTIPLEXER_LANDSCAPE.md)

- **Claude Squad** — a list-pane of agents + per-agent detail tabs.
- **cmux** — a *one-line status digest* per agent (so the roster scans in
  one glance) and an *out-of-band event channel* (done / blocked /
  needs-input surface, not buried in a log).
- **Conductor** — *diff-first review*: a closed contract surfaces its
  changed files as the default review artifact.
- **vibe-kanban** — columns mapped to a lifecycle. AIOS's lifecycle is the
  **contract** lifecycle: proposed → accepted → dispatched → collected →
  closed.

The roster is a **projection**, never a new store — every cell traces to a
contract, a dispatch packet, or a ledger entry.

## Required outcome — first buildable slice

1. **Roster projection (data).** `aios_control_snapshot.py` emits a `roster`
   block: one entry per repo-agent with `agent`, `repo`, `health`, a
   `status_digest` one-liner (current contract + dispatch in/out + last
   activity), and an `event` field (`idle` / `working` / `done` / `blocked`
   / `needs_input`) derived from inbox/outbox/contract state — no new file,
   composed from existing loaders (`load_contracts`, `load_dispatches`,
   `load_repos`, `child_watcher` state).
2. **Kanban projection (data).** The snapshot emits a `contract_board`:
   contracts bucketed into the five lifecycle columns, each card carrying
   `contract_id`, title, repos, and (for `closed`) the `changed`/evidence
   refs already in the ledger — the diff-first hook.
3. **Roster surface (UI).** `apps/control/` renders the roster as agent
   cards with the one-line digest and an event badge, and the kanban as
   five columns. Clicking a card opens detail tabs (contract text · dispatch
   packet · changed files). Pure read view; the operator's existing controls
   are unchanged.
4. The out-of-band channel: `blocked` / `needs_input` agents surface at the
   top of the roster regardless of sort — the operator never has to scroll
   to find a stuck agent.

## Named Exit

Closed when: the snapshot emits `roster` + `contract_board`; a test asserts
both project correctly from a fixture `.aios/` tree (six agents bucketed,
lifecycle columns correct, a blocked agent surfaces); `apps/control/` renders
the roster + kanban from the snapshot; `python -m unittest
tests.test_aios_control_snapshot` passes.

## Verification Gate

```bash
python -m py_compile scripts/aios_control_snapshot.py scripts/aios_local_app.py
python scripts/aios_control_snapshot.py --check-app-js apps/control/app.js --json
python -m unittest tests.test_aios_control_snapshot -v
python scripts/aios_local_app.py refresh --json
python scripts/aios_monitor.py assess --json
```

## Stop Conditions

- If a roster cell cannot be traced to a contract / packet / ledger entry,
  render it as `unknown`, never invent state (Invariant 8).
- The kanban must not become writable — a card move is not a state change;
  only the contract lifecycle is. If the UI ever needs drag-to-advance, that
  is a separate contract.

## Scope

repos: `myworld` — `scripts/aios_control_snapshot.py` (projection + tests),
`apps/control/` (render). Owner: codex@myworld; UI render may be handed to
the codex UI agent (docs/agents/CODEX_UI_AGENT.md).

## Work Packets

### codex@myworld — data

Add the `roster` and `contract_board` projections to
`aios_control_snapshot.py`, composed from existing loaders. Add
`tests/test_aios_control_snapshot.py` cases for both.

### codex@myworld (UI agent) — render

Render the roster cards + lifecycle kanban + detail tabs in `apps/control/`
from the snapshot's new blocks. Diff-first: a closed card shows changed
files. Read-only.

## Implementation Receipts

Both work packets executed by claude@myworld operator (UI packet in
deadlock recovery — no codex@myworld process running, and the pending
`asc-0204` packet was holding the L6 "repeatable" readiness gap open).

### Packet 1 — data projection (committed `3aec50a`)

`aios_control_snapshot.py` emits `roster` (six repo-agents, one-line
status digest, out-of-band event with blocked/needs_input floated to the
top) and `contract_board` (all contracts in the five lifecycle columns).
4 tests in `tests/test_aios_control_snapshot.py`.

### Packet 2 — UI render

- `apps/control/index.html` — new `#roster` section: a roster grid +
  a contract-board grid, placed directly under the Agent Work band.
- `apps/control/app.js` — `renderRoster` and `renderContractBoard` added
  (following the existing `renderRepos`/`renderDispatches` pattern) and
  wired into the main render pass. Roster cards carry an event-coloured
  left border; the board renders five lifecycle columns.
- `apps/control/styles.css` — ~70 lines for `.roster-band` / `.roster-card`
  / `.contract-board` / `.board-column`, themed via the existing CSS vars
  so it follows light/dark.
- `aios_control_snapshot.check_app_js` now also requires the `renderRoster`
  and `renderContractBoard` markers.

### Verification

- `python -m unittest tests.test_aios_control_snapshot` → 13 passed.
- `node --check apps/control/app.js` → ok.
- `aios_control_snapshot --check-app-js apps/control/app.js` → `ok: true`.
- regenerated snapshot carries `roster` (6 agents) and `contract_board`
  (proposed 29 / accepted 0 / dispatched 1 / collected 1 / closed 175).
- dispatch result: `.aios/outbox/myworld/asc-0204.myworld.result.json`
  passed 2026-05-20T16:22:56+09:00 after adding the dispatch-safe
  `Verification Gate` block above.

Named Exit met. ASC-0192's last follow-on is closed.
