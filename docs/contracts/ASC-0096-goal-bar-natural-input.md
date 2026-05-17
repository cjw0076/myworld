---
contract_id: ASC-0096
slug: goal-bar-natural-input
status: closed
goal: Add a natural-language Goal Bar input box to apps/control/ that classifies the user's text and routes to the right AIOS CLI (hive ask, agents status, dispatch status, primitive query, etc.) — running locally only, no external LLM, surfacing the result inline in the dashboard.
created: 2026-05-13 KST
accepted: 2026-05-13 KST by claude acting operator (founder explicit GO "A,D 진행하고 B도 병렬 처리.")
closed: 2026-05-13 21:17 KST by codex acting founder-delegated operator
acceptance_authority: claude@myworld (operator) per founder explicit GO 2026-05-13 KST.
origin: founder turn diagnosing 5-CLI burden to ask "어떤 Agent가 있지?". Goal Bar removes the CLI memorization barrier.
---

# ASC-0096 Goal Bar — Natural Input

## Why Now

Verified 2026-05-13: to answer "어떤 Agent가 있지?" the founder had to
know `hive agents status` + `hive ask` + `hive runs` + `hive inspect` +
`hive live`. 5 commands for one question. Even claude operator had to
look up correct syntax mid-turn.

ASC-0064 (live dashboard) closed — the surface exists. ASC-0096 adds
the input bar that converts natural language → right CLI invocation,
keeping discovery cost zero.

## Required Reading

- `apps/control/index.html`, `app.js`, `live.js` (existing dashboard)
- `scripts/aios_local_app.py` (HTTP + WS surface)
- `scripts/aios_primitives/tools.py` (discover existing AIOS commands)
- `hivemind/hivemind/hive.py` (hive ask intent classifier)

## Scope

repos:

- `myworld`

allowed_files:

- `apps/control/index.html`
- `apps/control/app.js`
- `apps/control/styles.css`
- `apps/control/goal_bar.js`
- `scripts/aios_goal_bar.py`
- `scripts/aios_local_app.py`
- `scripts/aios_dashboard_ws.py`
- `tests/test_aios_goal_bar.py`
- `tests/test_aios_local_app.py`
- `docs/AIOS_GOAL_BAR.md`
- `docs/contracts/ASC-0096-goal-bar-natural-input.md`
- `docs/contracts/README.md`
- `docs/AIOS_AGENT_LEDGER.md`
- `docs/AGENT_WORKLOG.md`

scope_notes:

- `scripts/aios_local_app.py` owns HTTP POST `/api/goal_bar`.
- `scripts/aios_dashboard_ws.py` is a read-only live-status dependency and
  remains WebSocket-only.

forbidden_files:

- `hivemind/**`
- `memoryOS/**`
- `CapabilityOS/**`
- `GenesisOS/**`
- `uri/**`
- `_from_desktop/**`
- `dain/**`
- `minyoung/**`
- `.env`

## Per-OS Responsibility

### myworld.must_produce

- `scripts/aios_goal_bar.py` — classifier:
  - input: natural language string (Korean or English)
  - intent classification (deterministic V1 — keywords + pattern):
    - "어떤/what/list" + "agent/provider" → `hive agents status`
    - "어떤/what/list" + "contract" → `aios_dispatch.py status`
    - "어떤/what/list" + "monitor/watch" → `aios_primitives monitor list`
    - "ask/물어봐" → `hive ask "<text>"`
    - "memory/기억" → `memoryos drafts list` or `memoryos context build`
    - "capability/도구" → `capabilityos recommend --task "<text>"`
    - "invoke/실행" → `aios_invoke.py --goal "<text>" --plan-only`
    - default → `hive ask "<text>"`
  - returns JSON: `{intent, classified_command, will_execute: bool, reason}`
  - `--execute` flag: actually runs the command and returns combined result
  - V2 may use Ollama Qwen for fuzzy classification — out of scope here
- `apps/control/goal_bar.js` — DOM:
  - input box at top of dashboard
  - submit button + Enter key
  - shows classified command before executing (allow operator cancel)
  - displays result inline (next to input, expand on click)
- `aios_local_app.py` POST `/api/goal_bar` endpoint that runs
  `aios_goal_bar.py` in classify mode first and `--execute` only after a
  confirmed request. `aios_dashboard_ws.py` remains WebSocket-only.
- Tests cover: each intent class, default fallback, dangerous-command
  rejection (e.g. `rm -rf` in input), result rendering

### child repos

- No source change. Goal bar reads existing CLI surfaces only.

## Verification Gate

```bash
python -m py_compile scripts/aios_goal_bar.py
python -m py_compile scripts/aios_local_app.py
python -m unittest tests/test_aios_goal_bar.py tests/test_aios_local_app.py
python scripts/aios_goal_bar.py "어떤 Agent가 있지?" --json
python scripts/aios_goal_bar.py "어떤 contract가 열려있나" --json
python scripts/aios_local_app.py status --assert-live --json
python -m unittest discover -s tests -p 'test_aios_*.py'
```

Pass criteria:

- 5 intent classes resolve to right command in tests.
- Submit -> classified command shown first; execution requires confirmed
  execute request and returns result inline.
- Dangerous patterns (rm/dd/sudo) reject before execution.
- Running control app serves the Goal Bar endpoint and WebSocket health remains
  live.
- Full test suite green.

## Stop Conditions

- `goal_bar_executes_dangerous_command`: rm/dd/sudo/etc. patterns must reject
- `goal_bar_uses_external_llm_v1`: must be deterministic local
- `goal_bar_silent_skip`: never execute without showing classification first
- `child_repo_scope_leak`
- `verification_gate_failed`

## Receipts

- dispatch: `.aios/inbox/myworld/asc-0096-goalbar.myworld.json`
- result: `.aios/outbox/myworld/asc-0096-goalbar.myworld.result.json`
- log: `.aios/logs/asc-0096-goalbar.myworld.log`
- control_app: `http://127.0.0.1:9885/` restarted on 2026-05-13 21:14 KST
  with Goal Bar endpoint loaded.
- live_api_smoke: `POST /api/goal_bar` classified "어떤 Agent가 있지?",
  rejected execution without `confirm`, and executed successfully with
  `{execute:true, confirm:true}`.
- close_condition: recommended `closed_goal_met`, unmet=0, manual=5.
- memory_writeback: release wrote MemoryOS draft `mem_a1b127491f1482d1`.

## Work Packets

### WP-0096-A — codex@myworld implements goal bar

- target_agent: codex
- target_repo: myworld
- status: done
- depends_on: ASC-0064 (live dashboard) closed ✓
- brief: implement classifier + DOM input + WS endpoint + tests + docs.
  Dogfood: open dashboard, type "어떤 Agent가 있지?", verify result is
  the same as `hive agents status` direct output.
- result: `.aios/outbox/myworld/asc-0096-goalbar.myworld.result.json`
