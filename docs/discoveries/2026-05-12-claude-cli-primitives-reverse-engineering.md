# Claude CLI Primitives — Reverse-Engineering for AIOS

Source: live observation of `claude@myworld` operator session 2026-05-12 (this
session). The goal is to extract every primitive the Claude CLI provided to
the operator and translate it into an AIOS-native primitive surface that
`codex@*` and local LLM workers can call with the same semantics.

Companion files:
- `docs/AIOS_AGENT_SELF_LOOP.md` — claude vs codex persistence patterns
- `docs/AIOS_OPERATOR_PLAYBOOK.md` — claude operator workflow spec
- `docs/operator_sessions/2026-05-12-claude-myworld.md` — concrete mode log

## 1. Primitives observed in this session

### 1a. Monitor — persistent background watcher

What it did:
- A bash polling loop ran in a background task (`bjrb5nkn2`, later `bko5zbir2`).
- Each `echo` line on stdout became an event delivered to the operator's chat.
- The loop watched: git HEAD, contract count, open-contract count, inbox/outbox
  sizes, failed result count, and (in v2) monitor health.

Recipe used:
```bash
# v1 (noisy): emits every cycle if failed > 0
while true; do
  sleep 45
  ... compute current state ...
  if [ "$cur_failed" -gt 0 ]; then
    echo "[$ts] FAILED_OR_TIMEOUT_RESULTS=$cur_failed"
  fi
done

# v2 (delta-only): emits only when value changes
if [ "$cur_failed" != "$prev_failed" ]; then
  echo "[$ts] FAILED_DELTA was=$prev_failed now=$cur_failed"
  prev_failed=$cur_failed
fi
```

Failure mode encountered:
- v1 emitted `FAILED_OR_TIMEOUT_RESULTS=3` every 45 s even when nothing
  changed → cache burn + chat noise. Fixed by switching to delta-only.

AIOS equivalent today:
- `aios_round_controller.py run` is a watcher BUT it controls dispatch, not
  observation. There is no general "named watcher with event log" surface.

Gap:
- No CLI to start/stop named watchers and stream their events to a shared
  `.aios/events.jsonl`.

### 1b. ScheduleWakeup — timed self-fire

What it offers:
- `ScheduleWakeup(delaySeconds=N, prompt=...)` resumes claude with the supplied
  prompt after N seconds. Clamped 60..3600.
- The point of the 5-min cache TTL: <270 s keeps cache warm; >300 s pays one
  miss but amortizes longer sleep. Don't sleep 300 s exactly.

Not used in this session — claude stayed interactive — but documented.

AIOS equivalent today:
- `cron` for repeating, `aios_dispatch.py` for explicit packets. No one-shot
  timer that fires a packet after delay N.

Gap:
- No `aios_schedule once|repeat` for time-driven packet emission.

### 1c. TaskCreate/Update/List/Get — task tracking

What it did:
- Tracked 7 tasks across the session: monitor armed, watch ASC-0036,
  uncommitted-artifacts watch, escalation watch, etc.
- Status: `pending → in_progress → completed | deleted`.
- Reminders fired when tasks went stale.

AIOS equivalent today:
- No persistent task list outside ledger entries and the playbook's session
  log.

Gap:
- No `aios_task create|update|list|get` storing tasks per session in
  `.aios/tasks/`.

### 1d. Agent(subagent_type, prompt) — subagent spawn

What it offers:
- Spawns a fresh, context-isolated agent of a chosen type (Explore,
  general-purpose, code-reviewer, Plan, etc.) with a self-contained prompt.
- Result returns to the parent agent as a single tool result.

Not used in this session — operator stayed solo — but documented.

AIOS equivalent today:
- `aios_dispatch.py send` + `aios_child_watcher.sh` is async: packet → outbox.
- For sync subagent spawn (claude needs the result before continuing), there
  is no equivalent.

Gap:
- No synchronous `aios agent run --type <slug> --prompt <text>` that blocks
  until result is ready.

### 1e. Skill(name, args) — skill invocation

What it offers:
- Loads a skill by name (e.g. `init`, `review`, `loop`, `schedule`) and runs
  it inline in the current session.
- Skills bring their own instructions + tool access.

AIOS equivalent today:
- `capabilityos recommend` ranks tool/skill candidates BUT does not invoke.
  `capability_observation_feedback` records outcomes but is read-only.

Gap:
- No `aios skill run <name>` that actually executes a skill against operator
  state.

### 1f. AskUserQuestion — operator escalation surface

What it offers:
- Structured questions (1-4) with multi-select / single-select / preview-mode
  options.
- Used when the chat needs explicit operator input rather than guessed
  defaults.

Not used in this session — operator volunteered judgment — but documented.

AIOS equivalent today:
- `aios_dispatch.py escalate --reason <slug>` records the need. There is no
  channel that surfaces the question + collects the answer + resumes the
  blocked work.

Gap:
- No `aios ask --to operator --question ... --options ...` UI/channel.

### 1g. Bash with run_in_background — async subprocess

What it offers:
- A background bash job (with notifications on completion) that doesn't block
  the chat.

Not directly used (Monitor played a similar role).

Gap:
- AIOS workers can `subprocess.Popen` but there is no shared event log and no
  named-job lifecycle.

### 1h. ToolSearch — deferred tool discovery

What it did:
- Used 4× in this session. Each time a non-base tool was needed (TaskStop,
  Monitor, TaskCreate, etc.), `ToolSearch(select:<name>)` fetched the schema
  before invocation.
- Keeps the base prompt small until a tool is actually needed.

AIOS equivalent today:
- All workers see fixed capabilities at start. There is no lazy-load mechanism
  for capability/skill schemas.

Gap:
- No `aios tools discover --query <terms>` that returns just-in-time schema
  for selected capabilities.

### 1i. WebFetch / WebSearch — broad internet

What it offers:
- `WebFetch(url)` and `WebSearch(query)` provide cited, fetched content.

AIOS today:
- `cap_web_research_route` (ASC-0030) routes the *plan*; execution happens
  outside AIOS (codex's own web tool). ASC-0031 produced one validated
  receipt manually.

Gap:
- No `aios web fetch <url> --record` and `aios web search <q> --record` that
  produce cited evidence receipts identical to ASC-0031's shape.

### 1j. TaskStop — kill a running primitive

What it did:
- One call when the noisy v1 Monitor needed to be replaced with the
  delta-only v2.

AIOS today:
- `aios_round_controller.py stop` for that specific daemon. No generic stop.

Gap:
- No `aios primitives stop --name <id>` covering all primitive types.

## 2. Translation principles

For each primitive that lacks an AIOS equivalent:

1. **One subcommand under `scripts/aios_primitives.py`** so the surface is
   discoverable: `monitor`, `schedule`, `task`, `ask`, `tools`, `web`, `stop`.
2. **State on disk under `.aios/primitives/<kind>/<name>.json`** — append-only
   for events, mutable only for status fields, so workers can co-exist.
3. **Events go to a shared `.aios/primitives/events.jsonl`** so the existing
   `aios_monitor.py assess` can surface them.
4. **No primitive may execute a child repo source edit, accept a memory, or
   bind a capability**. They are coordination primitives, not execution.
5. **Same semantics across callers**: claude (via tool calls), codex (via
   `python scripts/aios_primitives.py <subcommand>`), local LLM workers (via
   `from aios_primitives import <subcommand>` Python import).

## 3. Why this matters

Today only `claude@myworld` (this CLI session) can use the rich primitive
set. `codex@*` falls back to bash + ledger + dispatch packets. Local LLM
workers (memoryOS local_workers.py, hivemind intent_router) have no primitive
surface beyond their narrow callsite.

If we make the primitive surface uniform:

- `codex@myworld` can arm its own monitor instead of needing claude to watch.
- `codex@hivemind` (and other child agents) can spawn synchronous subagents
  for review without going through full dispatch.
- Local LLM workers can record tasks, raise operator questions, and emit
  events that show up in the same monitor dashboard.

The system becomes **substrate-independent**. Whether the operator is
claude-via-Claude-Code, codex-via-OpenAI-CLI, or a local 7B running in
memoryos, the same operating-loop vocabulary applies.

## 4. Open questions for the implementation contract

- Q1 — Subprocess management: how does `monitor start` keep its watcher
  alive across the operator's session boundary? Suggestion: write a PID file
  + use `nohup`/`setsid` so the watcher survives the operator agent's exit
  and resurrects on next `monitor list`.
- Q2 — Event ordering: monotonic timestamps from `time.monotonic_ns()` vs
  wallclock ISO. Suggestion: wallclock for human readability + monotonic
  for ordering ties.
- Q3 — Schema: a single `aios.primitive_event.v1` schema covering all
  kinds, with a `kind` field (`monitor.event`, `task.update`, etc.).
- Q4 — Concurrency: lock file vs. `O_APPEND` on JSONL. Suggestion: pure
  `O_APPEND` writes; readers must tolerate partial last line.
- Q5 — Local LLM access: Python import path. Suggestion: install
  `aios_primitives` as a thin package under `scripts/` so
  `sys.path` insertion in workers is unnecessary.

## 5. Sequencing recommendation

This is a meta-contract: implementing it gives every future contract a
better operating surface. So **prioritize before more application contracts**
(ASC-0050 should come before further visualization or web research work).

Proposed contract ID: **ASC-0050 — AIOS Primitive Surface**.
