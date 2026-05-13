---
contract_id: ASC-0096
slug: goal-bar-natural-input
status: accepted
goal: Add a natural-language Goal Bar input box to apps/control/ that classifies the user's text and routes to the right AIOS CLI (hive ask, agents status, dispatch status, primitive query, etc.) — running locally only, no external LLM, surfacing the result inline in the dashboard.
created: 2026-05-13 KST
accepted: 2026-05-13 KST by claude acting operator (founder explicit GO "A,D 진행하고 B도 병렬 처리.")
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

repos: `myworld`

allowed_files:

- `apps/control/index.html`
- `apps/control/app.js`
- `apps/control/styles.css`
- `apps/control/goal_bar.js`
- `scripts/aios_goal_bar.py`
- `scripts/aios_dashboard_ws.py` (POST endpoint for goal bar submissions)
- `tests/test_aios_goal_bar.py`
- `docs/AIOS_GOAL_BAR.md`
- `docs/contracts/ASC-0096-goal-bar-natural-input.md`
- `docs/contracts/README.md`
- `docs/AIOS_AGENT_LEDGER.md`

forbidden_files:

- `hivemind/**`, `memoryOS/**`, `CapabilityOS/**`, `GenesisOS/**`, `uri/**`
- `_from_desktop/**`, `dain/**`, `minyoung/**`
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
- `aios_dashboard_ws.py` POST `/goal_bar` endpoint that runs
  `aios_goal_bar.py --execute` and streams result
- Tests cover: each intent class, default fallback, dangerous-command
  rejection (e.g. `rm -rf` in input), result rendering

### child repos

- No source change. Goal bar reads existing CLI surfaces only.

## Verification Gate

```bash
python -m py_compile scripts/aios_goal_bar.py
python -m unittest tests/test_aios_goal_bar.py
python scripts/aios_goal_bar.py "어떤 Agent가 있지?" --json
# expect: classified_command="hive agents status", will_execute=true
python scripts/aios_goal_bar.py "어떤 contract가 열려있나" --json
# expect: classified_command containing "aios_dispatch.py status"
python scripts/aios_local_app.py up --port 9877 --ws-port 9878 --json
# manual: open http://localhost:9877, type query in goal bar, see result
python scripts/aios_local_app.py stop
python -m unittest discover -s tests -p 'test_aios_*.py'
```

Pass criteria:

- 5 intent classes resolve to right command in tests
- Submit → classified_command shown → on confirm, runs + result inline
- Dangerous patterns (rm/dd/sudo) rejected
- Full test suite green

## Stop Conditions

- `goal_bar_executes_dangerous_command`: rm/dd/sudo/etc. patterns must reject
- `goal_bar_uses_external_llm_v1`: must be deterministic local
- `goal_bar_silent_skip`: never execute without showing classification first
- `child_repo_scope_leak`
- `verification_gate_failed`

## Receipts

Pending.

## Work Packets

### WP-0096-A — codex@myworld implements goal bar

- target_agent: codex
- target_repo: myworld
- status: accepted
- depends_on: ASC-0064 (live dashboard) closed ✓
- brief: implement classifier + DOM input + WS endpoint + tests + docs.
  Dogfood: open dashboard, type "어떤 Agent가 있지?", verify result is
  the same as `hive agents status` direct output.
