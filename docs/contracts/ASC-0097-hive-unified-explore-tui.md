---
contract_id: ASC-0097
slug: hive-unified-explore-tui
status: accepted
goal: Improve `hive tui` so the 5 separate Hive exploration commands (agents status / runs / inspect / live / events) are reachable from one screen with shared context, eliminating CLI hop overhead for operators exploring Hive state.
created: 2026-05-13 KST
accepted: 2026-05-13 KST by claude acting operator (founder explicit GO "A,D 진행하고 B도 병렬 처리.")
acceptance_authority: claude@myworld (operator) per founder explicit GO 2026-05-13 KST.
origin: founder verified 5-CLI burden to explore Hive state. ASC-0097 unifies into one TUI surface without inventing new commands — just compose existing ones.
---

# ASC-0097 Hive Unified Explore TUI

## Why Now

`python -m hivemind.hive tui` exists. It's currently focused on board
view. But operator exploration of Hive state requires hopping across
`agents status`, `runs`, `inspect`, `live`, `events`. Each switch loses
context (current run id, selected agent, etc.).

ASC-0097 makes `hive tui` a single screen with tabs/panes:

- **Agents** (left pane): provider registry from `agents status`
- **Runs** (middle pane): run list from `runs`, click to select
- **Inspect** (right pane): receipts/ledger/results for selected run
- **Events** (bottom pane): live event stream from current run
- **Ask** (top input): one-line `ask` invocation, result drops into Inspect

No new commands invented. Just composes 5 existing CLI outputs into one
window with shared state (selected run id, selected agent).

## Required Reading

- `hivemind/hivemind/hive.py` (CLI argparse setup)
- existing `hive tui` implementation (likely in `hive.py` or
  `hivemind/hivemind/tui_*.py`)
- `hivemind/hivemind/local_workers.py` (WorkerSpec format)
- `docs/AIOS_HIVE_GATE.md` if exists

## Scope

repos: `hivemind`

allowed_files:

- `hivemind/hivemind/tui*.py` (only tui-related modules)
- `hivemind/hivemind/hive.py` (only `tui` subcommand wiring)
- `hivemind/tests/test_tui*.py`
- `hivemind/docs/HIVE_TUI.md`

forbidden_files:

- `hivemind/hivemind/local_workers.py`
- `hivemind/hivemind/provider_loop.py`
- `hivemind/hivemind/capability_bridge.py`
- `hivemind/hivemind/memory_bridge.py`
- `myworld/**`, `memoryOS/**`, `CapabilityOS/**`, `GenesisOS/**`, `uri/**`
- `_from_desktop/**`, `dain/**`, `minyoung/**`
- `.env`

## Per-OS Responsibility

### hivemind.must_produce

- `hive tui` (or `hive tui --explore`) opens a single screen with:
  - tabs or panes covering: Agents / Runs / Inspect / Events / Ask
  - keyboard navigation (arrow keys + tab)
  - shared state: selected run_id, selected agent_id propagate across panes
  - Ask submit → uses existing `hive ask`, result appears in Inspect pane
- TUI library: prefer existing dependency (curses or whatever board view uses)
  to avoid new pip install
- Tests: render each pane against synthetic state, exit cleanly,
  navigation works

### child repos

- No source change.

## Verification Gate

```bash
cd hivemind
python -m py_compile hivemind/hive.py hivemind/tui*.py
python -m pytest tests/test_tui*.py -v
python -m hivemind.hive tui --help   # confirms subcommand
# manual: open hive tui, navigate panes, ask one prompt, verify result
cd ..
python -m unittest discover -s tests -p 'test_aios_*.py'
```

Pass criteria:

- All 5 panes render without crash
- Navigation across panes preserves selected_run_id + selected_agent_id
- Ask result appears in Inspect pane within 5 s
- No new dependencies added

## Stop Conditions

- `tui_invents_new_command`: must compose existing commands, not invent
- `tui_adds_pip_dependency`: V1 stays within current deps
- `tui_silent_crash`: any pane fails — explicit error message in pane
- `tui_state_leak`: pane state shouldn't bleed across runs
- `child_repo_scope_leak`
- `verification_gate_failed`

## Receipts

Pending.

## Work Packets

### WP-0097-A — codex@hivemind unifies hive tui

- target_agent: codex
- target_repo: hivemind
- status: accepted
- brief: extend hive tui into 5-pane explore screen using existing
  Hive subcommand outputs as data sources. No new CLI commands. Tests
  cover render + navigation. Dogfood: launch tui, navigate, ask one
  prompt, verify Inspect updates.
