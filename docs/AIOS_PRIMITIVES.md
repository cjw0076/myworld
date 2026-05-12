# AIOS Primitives — substrate-independent operator surface

`scripts/aios_primitives/` exposes the same primitives `claude@myworld`
used during the 2026-05-12 session (Monitor, ScheduleWakeup,
TaskCreate/Update, Skill, AskUserQuestion, ToolSearch, WebFetch/Search) as
**callable code** so codex and local LLM workers get the same operator
vocabulary.

State lives under `.aios/primitives/`:

```
.aios/primitives/
├── events.jsonl                 # shared append-only event log
├── monitors/<name>.json         # running watchers
├── schedules/<name>.json        # scheduled fires
├── tasks/<id>.json              # task records
├── questions/<id>.json          # operator questions + answers
└── tools/registry.json          # local tool/skill registry
```

Companion doctrine:
- `docs/AIOS_AGENT_SELF_LOOP.md` — claude vs codex persistence patterns
- `docs/AIOS_OPERATOR_PLAYBOOK.md` — operator workflow modes + recipes
- `docs/discoveries/2026-05-12-claude-cli-primitives-reverse-engineering.md`
  — the reverse-engineering analysis that produced this surface
- `docs/contracts/ASC-0050-aios-primitive-surface.md` — the implementing contract

## How to call

### From a shell (any agent)

```bash
# Monitor — start/list/stop a named persistent watcher
python scripts/aios_primitives.py monitor start \
  --name my-watch \
  --command 'while true; do echo $(git rev-parse HEAD); sleep 30; done'
python scripts/aios_primitives.py monitor list
python scripts/aios_primitives.py monitor stop --name my-watch

# Task — create/update/list
python scripts/aios_primitives.py task create \
  --subject "verify ASC-0050" --description "..." --owner claude --json
python scripts/aios_primitives.py task update --id t-xxxx --status completed
python scripts/aios_primitives.py task list --status pending

# Schedule — one-shot or repeat
python scripts/aios_primitives.py schedule once \
  --delay-seconds 60 --dispatch /path/to/packet.json --json
python scripts/aios_primitives.py schedule repeat \
  --name heartbeat --interval-seconds 300 --dispatch /path/to/heartbeat.json
python scripts/aios_primitives.py schedule list

# Ask — operator question channel
python scripts/aios_primitives.py ask create \
  --question "OK to release ASC-0XXX?" --options "yes,hold,escalate" \
  --to operator --from-agent codex@myworld
python scripts/aios_primitives.py ask wait --id q-xxxx --timeout-seconds 600
python scripts/aios_primitives.py ask answer --id q-xxxx --answer yes \
  --answered-by claude@myworld

# Tools — capability/skill discovery
python scripts/aios_primitives.py tools discover --query "web research"
python scripts/aios_primitives.py tools register \
  --id tool.demo --name "Demo Tool" --tags demo,example

# Web — cited evidence receipts
python scripts/aios_primitives.py web fetch \
  --url https://example.com/docs \
  --claim "API supports streaming" \
  --claim "rate limit is 60/min" \
  --publisher "Example" \
  --record docs/evidence/example.json

# Events — read the shared log
python scripts/aios_primitives.py events --event-kind monitor.event --limit 20
python scripts/aios_primitives.py events --name my-watch --limit 5
python scripts/aios_primitives.py stop --name my-watch --json
```

### From Python (local LLM workers)

```python
from aios_primitives import monitor, task, schedule, ask, tools, web, events

# Same semantics:
m = monitor.start("my-watch", "tail -F /var/log/app.log | grep ERROR")
t = task.create("review PR #42")
task.update(t["id"], status="in_progress")
q = ask.create("Approve schema change?", options=["yes", "no"], to="operator")
state = ask.wait(q["id"], timeout_seconds=300)
recs = events.read_events(name="my-watch", kind="monitor.event")
```

When running from the source tree without installation, `scripts/aios_primitives.py`
adds `scripts/` to `sys.path` for the shim. Long-lived workers should run from
the myworld root or install this package path in their environment instead of
patching `sys.path` at each callsite.

### Schema (every event)

```json
{
  "schema_version": "aios.primitive_event.v1",
  "kind": "monitor.event | task.created | task.status | schedule.fired | ask.answered | ...",
  "name": "<primitive-instance-id>",
  "ts_iso": "2026-05-12T23:04:09+09:00",
  "ts_monotonic_ns": 1234567890,
  "payload": { ... kind-specific fields ... }
}
```

## Invariants (enforced)

These are stop conditions on ASC-0050 — violations terminate the loop:

- `primitive_executes_child_repo_edit`: no primitive writes to child repo source.
- `primitive_accepts_memory`: no primitive flips MemoryOS draft → accepted.
- `primitive_binds_capability`: no primitive installs / binds a tool.
- `monitor_orphan`: every `monitor start` either returns alive PID or fails.
- `ask_silent_drop`: every `ask create` lands a question record on disk.
- `event_log_corrupt`: `events.jsonl` stays line-parseable.
- `web_fetch_uncited`: web records reject empty `claims`.

The surface is **coordination only**. Execution lives in Hive Mind via
dispatch packets. Memory acceptance lives in MemoryOS review. Capability
binding lives in CapabilityOS contracts.

## Persistence semantics

- **Monitors**: spawned with `start_new_session=True` so the watcher survives
  the caller exiting. PID stored in state file. `monitor list` re-checks
  liveness on every call.
- **Schedules**: each spawn its own background Python loop. On fire, emits
  `schedule.fired` event and updates state file. Caller no longer needs to
  poll — the next agent reading the event log sees the fire.
- **Tasks / questions / tools**: pure file state. Multiple writers safe via
  `O_APPEND` for events; per-file writes are last-writer-wins (acceptable
  for low-contention metadata).

## ASC-0050 Design Answers

- **Q1 subprocess survival**: use Python `subprocess.Popen(...,
  start_new_session=True)`, which calls `setsid()` in the child and preserves
  the watcher after the operator process exits. `monitor list` re-checks PID
  liveness instead of trusting stale state.
- **Q2 event ordering**: every event records both `ts_iso` for humans and
  `ts_monotonic_ns` for ordering ties.
- **Q3 schema**: every event uses `schema_version=aios.primitive_event.v1`,
  `kind`, `name`, `ts_iso`, `ts_monotonic_ns`, and `payload`.
- **Q4 concurrency**: event writes use POSIX `O_APPEND`; readers ignore a
  partial trailing line.
- **Q5 Python import**: source-tree callers import `aios_primitives` from the
  `scripts/` package path. The shim supports CLI use without callsite hacks;
  a later packaging contract can make it installable across child repos.
- **Q6 ask blocking**: `ask wait` polls every 2 seconds by default, up to 600
  seconds, marks timeout state, emits `ask.timeout`, and exits with code 124.

## Gap Translation Table

| Claude primitive | AIOS primitive | Notes |
|---|---|---|
| Monitor | `monitor start/list/stop` | Named persistent watcher with shared event log. |
| ScheduleWakeup | `schedule once/repeat/stop` | Emits scheduled fire events for dispatch packets. |
| TaskCreate/Update/List/Get | `task create/update/list/get` | File-backed task records. |
| Agent(subagent_type, prompt) | existing `aios_dispatch.py` + future sync wrapper | Async dispatch already exists; sync blocking agent run is deferred to a follow-up contract. |
| Skill(name, args) | `tools discover/register` | Discovery parity exists; skill execution remains policy-gated future work. |
| AskUserQuestion | `ask create/wait/answer/list/get` | Structured question channel with timeout semantics. |
| Bash background | `monitor start` | Background process plus event emission. |
| ToolSearch | `tools discover` | CapabilityOS recommendation plus local registry fallback. |
| WebFetch/WebSearch | `web fetch/search` | Cited receipt artifacts, no raw page body storage. |
| TaskStop | `stop --name`, plus kind-specific stops | Generic stop attempts monitor and schedule stop. |

## Comparison to existing AIOS infrastructure

| Concern | Existing AIOS | aios_primitives | When to use which |
|---|---|---|---|
| Long-running watcher | `aios_round_controller.py run` | `monitor start` | Round controller for the *AIOS control loop*; aios_primitives for any operator-defined watcher (build status, log tail, custom dashboards) |
| Async agent spawn | `aios_dispatch.py send` | (use dispatch) | aios_primitives does NOT replace dispatch — it complements it |
| Operator question | `aios_dispatch.py escalate` | `ask create/wait` | escalate is fire-and-forget; `ask` blocks on the answer |
| Web evidence | ASC-0030 `web-route` plan | `web fetch/search` | Route is the *plan*; `web fetch/search` records the *receipt* |
| Tool discovery | `capabilityos recommend` | `tools discover` | `tools discover` calls capabilityos AND a local registry; use it for cross-source discovery |

## Failure recovery

If a monitor or schedule's state file becomes inconsistent (e.g. PID dead
but file says alive), `monitor list` / `schedule list` corrects the
`alive` flag on read; the underlying state files can be removed manually
under `.aios/primitives/<kind>/` without harm.

The events log (`events.jsonl`) is append-only and never overwritten — if
it grows large, rotate via standard tools (`logrotate`, `mv events.jsonl
events.YYYY-MM-DD.jsonl`).

## Why this matters

Today only `claude@myworld` (via Claude Code) had rich primitives. Codex
and local LLM workers lacked them. After ASC-0050, the operator-loop
vocabulary is substrate-independent:

- `codex@myworld` can arm its own watcher without claude.
- Local LLM workers (memoryOS `local_workers.py`, hivemind workers) can
  record tasks, raise questions, emit events that surface in the same
  dashboard.
- The control plane no longer requires Claude Code to be alive for
  monitoring or task tracking to function.

The CLI assistant is now optional infrastructure rather than mandatory
runtime.
