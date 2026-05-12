---
contract_id: ASC-0050
slug: aios-primitive-surface
status: accepted
goal: Reverse-engineer the Claude CLI primitive set used by claude@myworld this session and provide an AIOS-native primitive surface that codex and local LLM workers can call with identical semantics.
created: 2026-05-12 23:00 KST
accepted: 2026-05-12 23:00 KST by claude acting operator (founder directive)
closed:
acceptance_authority: claude@myworld (operator) per founder request "Claude의 CLI 기능들을 탑재할거야. 세션 로그나 대화 내용들을 토대로 역설계해서 시스템을 구축하는건 어때? codex와 local LLM도 사용할 수 있게".
origin: founder directive 2026-05-12 evening + reverse-engineering analysis in `docs/discoveries/2026-05-12-claude-cli-primitives-reverse-engineering.md`.
---

# ASC-0050 AIOS Primitive Surface

## Why Now

Today only `claude@myworld` (via Claude Code) has rich primitives: persistent
monitor, scheduled wakeup, task tracking, sync subagent spawn, skill
invocation, structured operator-question, deferred tool discovery, cited web
fetch, named-task stop. `codex@*` and local LLM workers fall back to bash +
dispatch packets. This asymmetry forces the operator pair to do work that
should be available to every AIOS agent.

The founder asked for the Claude CLI feature set to be **mounted** into
AIOS, reverse-engineered from this session's logs and chat so the system
itself owns the primitives. After this contract, the operator-loop
vocabulary is substrate-independent: same semantics whether the caller is
claude, codex, or a local LLM.

## Required Reading

- `docs/discoveries/2026-05-12-claude-cli-primitives-reverse-engineering.md`
  (the analysis this contract executes against)
- `docs/AIOS_AGENT_SELF_LOOP.md`
- `docs/AIOS_OPERATOR_PLAYBOOK.md`
- `docs/operator_sessions/2026-05-12-claude-myworld.md`
- `scripts/aios_round_controller.py` (existing watcher daemon)
- `scripts/aios_dispatch.py` (existing async agent spawn)
- `scripts/aios_monitor.py` (existing health assessment)

## Scope

repos:

- `myworld`

allowed_files:

- `scripts/aios_primitives.py`
- `scripts/aios_primitives/__init__.py`
- `scripts/aios_primitives/monitor.py`
- `scripts/aios_primitives/schedule.py`
- `scripts/aios_primitives/task.py`
- `scripts/aios_primitives/ask.py`
- `scripts/aios_primitives/tools.py`
- `scripts/aios_primitives/web.py`
- `scripts/aios_primitives/events.py`
- `tests/test_aios_primitives.py`
- `tests/test_aios_primitives_monitor.py`
- `tests/test_aios_primitives_schedule.py`
- `tests/test_aios_primitives_task.py`
- `docs/AIOS_PRIMITIVES.md`
- `docs/AIOS_WORK_DISPATCH.md`
- `docs/discoveries/2026-05-12-claude-cli-primitives-reverse-engineering.md`
- `docs/contracts/ASC-0050-aios-primitive-surface.md`
- `docs/contracts/README.md`
- `docs/goals/AIOS-GOAL-0001-make-something-great.md`
- `docs/goals/AIOS-GOAL-0001-evolution.md`
- `docs/AIOS_AGENT_LEDGER.md`

forbidden_files:

- `hivemind/**`
- `memoryOS/**`
- `CapabilityOS/**`
- `uri/**`
- `.aios/logs/**`
- `.aios/state/**`
- `.env`
- raw export paths

## Per-OS Responsibility

### myworld.must_produce

- `scripts/aios_primitives.py` (or package under `scripts/aios_primitives/`)
  exposing these subcommands, each with `--json`:
  - `monitor start --name <id> --command <bash>` — launch named persistent
    watcher; writes events to `.aios/primitives/events.jsonl`.
  - `monitor stop --name <id>` — halt a named watcher.
  - `monitor list` — show running watchers and their last event.
  - `schedule once --delay-seconds N --dispatch <packet.json>` — fire a
    packet after N seconds.
  - `schedule repeat --interval-seconds N --dispatch <packet.json>` — fire
    repeatedly (with cap, e.g. max 100 fires) until stopped.
  - `schedule stop --name <id>` — halt a scheduled fire.
  - `task create --subject <text> --description <text>` — create a task
    record in `.aios/primitives/tasks/<id>.json`.
  - `task update --id <id> --status <pending|in_progress|completed>` —
    transition a task.
  - `task list` — list tasks with status.
  - `task get --id <id>` — fetch full record.
  - `ask --to <agent> --question <text> --options <comma-separated>` —
    create an operator-question record in `.aios/primitives/questions/<id>.json`;
    blocks (or polls) until an answer is written.
  - `tools discover --query <terms>` — return AIOS capability/skill schemas
    matching the query (mirrors Claude `ToolSearch`).
  - `web fetch --url <u> --record <path>` — fetch URL through the
    CapabilityOS `web-route`, write an `aios.web_research_receipt.v1`-shaped
    artifact.
  - `web search --query <q> --record <path>` — same but for search.
  - `stop --name <id>` — generic halt for any named primitive.
- Each subcommand returns `aios.primitive_event.v1` JSON: a uniform schema
  with `kind`, `name`, `ts_iso`, `ts_monotonic_ns`, `payload`.
- All state under `.aios/primitives/`:
  - `events.jsonl` — append-only event log (shared).
  - `monitors/<name>.json` — pid, command, started_at, last_event_at.
  - `schedules/<name>.json` — fire schedule, next_fire_at, fires_remaining.
  - `tasks/<id>.json` — task record.
  - `questions/<id>.json` — question record + (when answered) answer field.
- Python import surface: `from aios_primitives import monitor, task, ask, ...`
  with the same semantics as the CLI. Local LLM workers (memoryOS
  `local_workers.py`, hivemind `intent_router`) can call these without going
  through subprocess.
- Tests covering: monitor lifecycle (start/stop/respawn-after-operator-exit),
  schedule once vs repeat, task transitions, ask blocking + answer write,
  tools discover schema return, web fetch evidence shape, stop reaching all
  primitive kinds.
- Documentation in `docs/AIOS_PRIMITIVES.md` showing the same recipe used by
  claude this session (`Monitor` arm pattern) plus the codex/local invocation
  forms.

### child repos

- No source role in this contract. They consume the primitives once they
  exist, via separate future contracts.

### operator

- Close only after the discovery doc's translation table is fully covered
  (every "Gap" row has a corresponding subcommand) and tests prove parity.

## Open Design Questions

To be answered by `codex@myworld` (WP-0050-A) before implementation:

- **Q1 — Subprocess survival**: `monitor start` must keep the watcher alive
  across the operator's session boundary. Recommend `setsid` + PID file +
  resurrect on `monitor list`. Justify if you choose differently.
- **Q2 — Event ordering**: wallclock ISO for humans + monotonic_ns for
  ordering ties. Confirm or simplify.
- **Q3 — Schema**: single `aios.primitive_event.v1` with `kind` field
  enumerating all event types. Confirm field set.
- **Q4 — Concurrency**: pure `O_APPEND` JSONL writes; readers tolerate
  partial last line. Confirm or propose a lighter alternative.
- **Q5 — Local LLM Python import**: install path so workers do not need
  `sys.path` hacks. Recommend a thin `pyproject.toml`-installable package
  layout under `scripts/aios_primitives/`. Justify if different.
- **Q6 — Ask blocking**: should `ask` poll for answer or signal? Recommend
  polling every 2 s up to a configurable timeout; default 600 s; falls back
  to writing an `escalate` event and exiting with code 124 on timeout.

## Verification Gate

```bash
python -m py_compile scripts/aios_primitives.py
python -m unittest tests/test_aios_primitives.py tests/test_aios_primitives_monitor.py tests/test_aios_primitives_schedule.py tests/test_aios_primitives_task.py
python scripts/aios_primitives.py monitor start --name verify-watch --command "echo verify-event" --json
python scripts/aios_primitives.py monitor list --json
python scripts/aios_primitives.py monitor stop --name verify-watch --json
python scripts/aios_primitives.py task create --subject "verify ASC-0050" --description "smoke task" --json
python scripts/aios_primitives.py task list --json
python -m unittest discover -s tests -p 'test_aios_*.py'
python scripts/aios_monitor.py assess --json
```

Pass criteria:

- Every "Gap" row in the discovery doc has a working subcommand.
- Tests prove parity between CLI subcommand and Python import surface.
- `.aios/primitives/events.jsonl` accumulates correctly across kinds.
- Existing `aios_monitor.py assess` surfaces primitive findings (orphan
  monitors, overdue schedules, blocked questions) without modification —
  by reading the events log.
- Full myworld test suite passes.
- Monitor remains clear.

## Stop Conditions

- `primitive_executes_child_repo_edit`: any primitive writes to child repo
  source.
- `primitive_accepts_memory`: any primitive flips a MemoryOS draft to
  accepted.
- `primitive_binds_capability`: any primitive installs or binds an external
  tool/MCP/provider.
- `monitor_orphan`: `monitor start` returns success but no PID survives to
  `monitor list`.
- `ask_silent_drop`: `ask` exits 0 without writing the question record.
- `event_log_corrupt`: `events.jsonl` cannot be parsed line-by-line.
- `web_fetch_uncited`: `web fetch` writes an artifact missing source/url
  fields.
- `child_repo_scope_leak`
- `verification_gate_failed`

## Receipts

Pending until verification.

## Work Packets

### WP-0050-A — Codex@myworld builds the AIOS primitive surface

- target_agent: codex
- target_repo: myworld
- status: accepted
- issued: 2026-05-12
- accepted: 2026-05-12
- closed: pending
- depends_on: ASC-0043 (autodraft) — useful for prompt scaffolding but not
  hard-blocking.
- brief: |
    Implement the unified primitive surface in `scripts/aios_primitives/`
    (or a single `aios_primitives.py` if simpler), answer Q1-Q6, write the
    tests, write `docs/AIOS_PRIMITIVES.md`, and dogfood by arming one
    `monitor start --name asc-0050-dogfood` watcher during verification.

    After closeout, surface a follow-up note: once these primitives exist,
    propose ASC-0051 — adapter for child repos so codex@hivemind /
    codex@memoryOS / codex@CapabilityOS can call them through `../scripts/`.
- result: pending
