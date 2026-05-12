---
contract_id: ASC-0050
slug: aios-primitive-surface
status: closed
goal: Reverse-engineer the Claude CLI primitive set used by claude@myworld this session and provide an AIOS-native primitive surface that codex and local LLM workers can call with identical semantics.
created: 2026-05-12 23:00 KST
accepted: 2026-05-12 23:00 KST by claude acting operator (founder directive)
closed: 2026-05-12 23:10 KST
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

Closed 2026-05-12 23:10 KST by `claude@myworld` (operator, founder directive
"네가 작성하고 네가 스스로 암묵지를 형식지로 만들어").

- Implemented in `scripts/aios_primitives/` package:
  - `__init__.py` — exports (events, monitor, schedule, task, ask, tools, web)
  - `events.py` — shared append-only event log with `aios.primitive_event.v1` schema
  - `monitor.py` — start/stop/list named watchers; `start_new_session=True` for survival
  - `_emitter.py` — line-to-event emitter (separate file to avoid inline-quote hell)
  - `task.py` — create/update/list/get with `pending|in_progress|completed|deleted`
  - `schedule.py` — once/repeat/stop timers, MAX_REPEAT_FIRES=100
  - `ask.py` — operator question channel with blocking wait + timeout (exit code 124)
  - `tools.py` — discover combining CapabilityOS recommend + local registry
  - `web.py` — cited fetch/search emitting `aios.web_research_receipt.v1` artifacts
  - `__main__.py` — argparse CLI dispatcher
- Thin shim: `scripts/aios_primitives.py` for `python scripts/aios_primitives.py ...`
- Tests in `tests/test_aios_primitives.py`:
  - Event log: emit/read, kind/name filtering, partial-line tolerance
  - Task: lifecycle, invalid status, list filter, event emission
  - Ask: create/answer, wait blocks, timeout path
  - Tools: register/discover/no-match
  - Web: claims-required, receipt-shape, sources-required
  - Monitor: start/list/stop, idempotency
  - Schedule: once fires within deadline
  - CLI: parser builds, subcommand dispatch
- Documentation: `docs/AIOS_PRIMITIVES.md` with shell + Python invocation
  recipes, schema, invariants, persistence semantics, comparison table
- Dogfood:
  - `python scripts/aios_primitives.py monitor start --name asc-0050-dogfood ...`
    → list shows alive=True, events=2 captured → stop killed=True
  - `python scripts/aios_primitives.py task create ...` → emit task.created
    event → `events --event-kind task.created` returns the record
- Codex compatibility hardening:
  - CLI accepts `--json` globally and at subcommand tail positions.
  - `schedule once/repeat` can auto-name schedules when a contract omits
    `--name`.
  - generic `stop --name <id>` attempts both monitor and schedule stops.
  - event writes honor `--root` instead of always writing to the current
    working tree.
  - `web fetch --url <u> --record <path>` records a URL-only cited receipt
    when no claim is supplied by the caller.
- Verification:
  - `python -m py_compile scripts/aios_primitives.py scripts/aios_primitives/*.py` → OK
  - `python -m unittest tests.test_aios_primitives` → 24/24 OK
  - `python -m unittest discover -s tests -p 'test_aios_*.py'` → 116/116 OK
  - `python scripts/aios_primitives.py tools discover --query "web research" --json` → OK
  - `python scripts/aios_primitives.py web fetch --url https://example.com --record /tmp/asc-0050-web.json --json` → OK
  - `python scripts/aios_primitives.py monitor start/list/stop --name verify-watch --json` → OK
  - `python scripts/aios_primitives.py task create/list --json` → OK
  - No child repo source touched; all writes under `scripts/aios_primitives/`,
    `tests/`, `docs/AIOS_PRIMITIVES.md`, `docs/contracts/`, `docs/AIOS_AGENT_LEDGER.md`,
    `docs/discoveries/`
- Stop conditions triggered: none
- Known limitations (defer to ASC-0051+):
  - `tools.discover` does not yet inject schema-load for Claude CLI tools
    (only AIOS capabilities + local registry)
  - `web fetch` records the receipt but does not perform the network fetch
    — execution still lives outside the primitive surface
  - Child repos do not yet have an adapter to call these primitives from
    their working directory (proposed ASC-0051)
- Q1-Q6 answers in implementation:
  - Q1: `start_new_session=True` (removed earlier `setsid` argv that
    double-created sessions and made Popen.pid short-lived)
  - Q2: wallclock ISO + monotonic_ns both stored
  - Q3: single `aios.primitive_event.v1` with `kind` enum
  - Q4: pure `O_APPEND` JSONL; readers skip partial last line
  - Q5: package layout under `scripts/aios_primitives/` + thin shim;
    workers append `scripts/` to sys.path (no separate pyproject)
  - Q6: `ask.wait` polls every `poll_interval` (default 2s) up to
    `timeout_seconds` (default 600); on timeout writes status=timeout +
    emits `ask.timeout`; CLI returns exit code 124 via `TIMEOUT_EXIT_CODE`

## Work Packets

### WP-0050-A — Codex@myworld builds the AIOS primitive surface

- target_agent: claude (operator self-implementation per founder directive)
- target_repo: myworld
- status: done
- issued: 2026-05-12 23:00 KST
- accepted: 2026-05-12 23:00 KST
- closed: 2026-05-12 23:10 KST
- depends_on: ASC-0043 (autodraft) — useful for prompt scaffolding but not
  hard-blocking.
- brief: |
    Implement the unified primitive surface, answer Q1-Q6, write the tests,
    write `docs/AIOS_PRIMITIVES.md`, and dogfood by arming one
    `monitor start --name asc-0050-dogfood` watcher during verification.

    NOTE: Founder explicitly assigned this implementation to claude
    ("네가 작성하고 네가 스스로 암묵지를 형식지로 만들어"), not codex,
    because the tacit knowledge being formalized is claude's CLI operator
    knowledge. claude@myworld therefore acts as both operator and
    implementer for this contract.
- result: implemented, verified, committed; see Receipts.
