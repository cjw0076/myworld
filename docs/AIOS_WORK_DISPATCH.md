# AIOS Work Dispatch

`myworld/` is the control tower and control plane. It should not become the
fourth implementation repo. It assigns work to the repo that owns the behavior.

In airport terms:

```text
myworld        = control tower
hivemind       = aircraft operations / execution fleet
memoryOS       = flight history, maps, black boxes, and reviewed knowledge
CapabilityOS   = runway/tool availability, routing options, and fallback plans
operator       = air traffic controller with release/hold authority
```

The tower does not fly every aircraft. It decides which runway is clear, which
route is allowed, what information is needed, and when to hold.

## Dispatch Model

```text
myworld/
  -> defines goal, contract, scope, stop conditions, and handoff

hivemind/
  -> executes work, schedules agents, wraps provider CLIs, verifies outputs

memoryOS/
  -> retrieves context, records provenance, imports run artifacts, manages
     memory drafts/review

CapabilityOS/
  -> recommends tools, MCPs, APIs, skills, provider routes, and fallbacks
```

## Correct Flow

1. The operator writes or approves a goal in `myworld`.
2. `myworld` creates an AIOS smart contract for the task.
3. The contract names the owner repo for each responsibility.
4. Agents are started inside the owning repo, not from `myworld` as a generic
   worker.
5. Each repo writes local implementation logs and returns a summary to
   `myworld/docs/AIOS_AGENT_LEDGER.md`.
6. Codex and Claude can act as delegated operators when the human operator
   assigns them that role. They may release, hold, retry, escalate, or revise
   work, but every decision must be visible in contract/status/result
   artifacts.

## What MyWorld Should Produce

For each meaningful task, `myworld` should produce:

- contract id
- user goal
- owning repo per work slice
- allowed and forbidden paths
- required outputs
- test or verification gates
- privacy constraints
- stop conditions
- next repo/agent handoff

## What MyWorld Should Not Do

- Do not directly edit implementation files across repos as the default mode.
- Do not bypass repo-local `AGENTS.md`, tests, worklogs, or ownership rules.
- Do not let one repo silently decide another repo's lifecycle policy.
- Do not execute external tools directly; route execution through Hive Mind.
- Do not store private raw data in shared control-plane docs.

## Dispatch Packet Template

```md
# ASC-0000 <short goal>

- goal:
- owner repo:
- primary agent:
- supporting repos:
- required MemoryOS context:
- required CapabilityOS recommendation:
- allowed files:
- forbidden files:
- required outputs:
- verification gate:
- stop conditions:
- return summary to:
```

## Repo Ownership Defaults

| Work Type | Owner Repo |
| --- | --- |
| Provider CLI wrapping, scheduler, verifier, receipts | `hivemind/` |
| Memory import, context build, review lifecycle, provenance | `memoryOS/` |
| Tool/MCP/API/skill discovery, scoring, binding plans | `CapabilityOS/` |
| Cross-repo contract, north star, ecosystem ledger | `myworld/` |

If ownership is unclear, stop and create an operator checkpoint.

## Automation Skeleton

The first automation layer is file-based. `myworld` writes packets and state;
repo-local agents or watchers consume packets and execute inside their own
repos.

```text
myworld/
  .aios/inbox/myworld/*.json
  .aios/inbox/hivemind/*.json
  .aios/inbox/memoryOS/*.json
  .aios/inbox/CapabilityOS/*.json
  .aios/outbox/myworld/*.json
  .aios/outbox/hivemind/*.json
  .aios/outbox/memoryOS/*.json
  .aios/outbox/CapabilityOS/*.json
  .aios/state/dispatches.jsonl
```

The runtime `.aios/` directory is local state and should not be committed.

CLI entry point:

```bash
python scripts/aios_dispatch.py create docs/contracts/ASC-0001-memoryos-hivemind-loop.md
python scripts/aios_dispatch.py send --repo memoryOS --agent codex
python scripts/aios_dispatch.py send --repo hivemind --agent codex
python scripts/aios_dispatch.py watch --repo memoryOS --once
python scripts/aios_dispatch.py watch --repo hivemind --once
python scripts/aios_dispatch.py status
python scripts/aios_dispatch.py collect
python scripts/aios_dispatch.py release --reason verified
python scripts/aios_dispatch.py hold --reason needs_review
python scripts/aios_dispatch.py retry --reason transient_failure
python scripts/aios_dispatch.py escalate --reason scope_conflict
python scripts/aios_dispatch.py stop --reason operator_checkpoint
```

Child repo agent watcher entry point:

```bash
# Run one pending packet inside a child repo.
scripts/aios_child_watcher.sh once --repo memoryOS
scripts/aios_child_watcher.sh once --repo hivemind
scripts/aios_child_watcher.sh once --repo CapabilityOS

# Start background watchers for all child repos.
scripts/aios_child_watcher.sh start --repo all

# Inspect and stop.
scripts/aios_child_watcher.sh status
scripts/aios_child_watcher.sh stop --repo all
```

The child watcher reads `.aios/inbox/<repo>/*.json`, builds a bounded prompt,
runs the packet's assigned agent from inside the target repo, and writes
`.aios/outbox/<repo>/*.result.json`. It is the execution bridge from the
control tower to repo-local agents.

To start the myworld Codex/Claude pingpong loop and child watchers together:

```bash
AIOS_START_CHILD_WATCHERS=1 scripts/aios_pingpong.sh start
```

After the L6 readiness marker exists, the pingpong loop normally stops. To keep
the control-plane loop producing follow-up contracts after readiness, opt in
explicitly:

```bash
AIOS_CONTINUE_AFTER_READY=1 AIOS_START_CHILD_WATCHERS=1 scripts/aios_pingpong.sh start
```

The follow-up loop should generate contracts and dispatch packets. It should
not treat `myworld` as a broad worker that edits child repo source directly.
See `docs/AIOS_OPERATING_LOOP.md` for the standard operator call sequence:
MemoryOS context, CapabilityOS route, Hive dry-run or verification, contract,
dispatch, watcher, collect, verify, learn.

Workspace task radar:

```bash
python scripts/aios_doc_scout.py --root /home/user/workspaces/jaewon --write docs/AIOS_TASK_RADAR.md --json
```

The scout scans documentation surfaces, excludes runtime/dependency/raw-data
paths, and writes `docs/AIOS_TASK_RADAR.md` so the next contracts can be chosen
from durable evidence instead of chat memory.

Loop selection policy:

```bash
python scripts/aios_loop_policy.py --json
python scripts/aios_loop_policy.py --write docs/AIOS_LOOP_POLICY.md
```

The policy is advisory. It ranks radar candidates as `accept_now`,
`hold_for_capacity`, `hold_for_capability`, `hold_for_operator`, or
`reject_out_of_scope`; it never flips contract status or sends packets.

Persistent control-plane rounds:

```bash
python scripts/aios_round_controller.py once --json
python scripts/aios_round_controller.py start --interval 30
python scripts/aios_round_controller.py status
python scripts/aios_round_controller.py stop
```

This is the provider-independent way to keep the control tower awake after a
chat turn ends. Each round assesses monitor health, refreshes the active goal
plan, applies the dispatch loop, checks child watcher status, and writes a
receipt to `.aios/state/round_controller.jsonl`. It recommends the next action
instead of silently accepting, closing, or drafting contracts.

Child execution remains opt-in:

```bash
python scripts/aios_round_controller.py once --execute-children --json
```

Use that only when pending child packets are already scoped by an accepted
contract.

Repo-originated goal intake:

```bash
python scripts/aios_repo_goal.py submit --repo hivemind --kind friction --goal "..." --json
python scripts/aios_repo_goal.py route --repo hivemind --json
python scripts/aios_repo_goal.py status --repo all --json
```

This is the self-resonant repo loop entry point. A lower repo reports a goal,
blocker, friction, or improvement candidate; myworld writes a route packet with
MemoryOS, CapabilityOS, and Hive responsibilities; the acting operator turns
that route into a smart contract or a hold. The route packet is
recommendation-only and must not execute child work directly.

Local control application:

```bash
python scripts/aios_local_app.py up --json
python scripts/aios_local_app.py status --json
python scripts/aios_local_app.py stop --json
```

`up` refreshes monitor state and the control snapshot, then serves
`apps/control/` on localhost. It is a local operator surface, not a child-repo
implementation worker.

Native desktop control application:

```bash
python scripts/aios_desktop_app.py status --json
python scripts/aios_desktop_app.py snapshot --json
python scripts/aios_desktop_app.py launch
```

This is the non-web desktop entry point. It reads or refreshes the same control
snapshot as the local web control app.

AIOS-native runtime entry point:

```bash
python scripts/aios_runtime.py status --json
python scripts/aios_runtime.py step --json
python scripts/aios_runtime.py run --max-rounds 1 --interval-seconds 0 --json
python scripts/aios_runtime.py submit-goal --repo hivemind --kind goal --goal "..."
```

This is the default operator-facing control command after ASC-0052. Claude CLI,
Codex CLI, provider CLIs, and repo-local scripts are substrates behind this
surface. The runtime reports monitor/readiness/dispatch state, runs bounded
control-plane steps, emits primitive runtime events, and delegates repo-goal
submissions without directly editing child repo source.
snapshot, renders native `tkinter` tables, and does not start an HTTP server or
browser. `status --json` is safe in headless sessions; `launch` requires a
graphical display.

Web evidence memory review:

```bash
python scripts/aios_web_evidence_memory_review.py --root . build \
  docs/evidence/ASC-0031-web-evidence.json \
  --output docs/evidence/ASC-0041-web-evidence-memory-candidates.json \
  --run-bundle docs/evidence/ASC-0041-web-evidence-review-run \
  --json

python scripts/aios_web_evidence_memory_review.py --root . validate \
  docs/evidence/ASC-0041-web-evidence-memory-candidates.json \
  --json
```

This adapter turns a validated web evidence receipt into draft-only MemoryOS
review candidates and a Hive-run-compatible `memory_drafts.json` bundle.
MemoryOS review remains explicit: web-derived facts are never accepted by this
control-plane adapter.

Capability observation memory review:

```bash
python scripts/aios_capability_observation_memory_review.py --root . build \
  --outbox .aios/outbox \
  --radar docs/AIOS_TASK_RADAR.md \
  --observation-output docs/evidence/ASC-0042-capability-observations.json \
  --output docs/evidence/ASC-0042-capability-memory-candidates.json \
  --run-bundle docs/evidence/ASC-0042-capability-review-run \
  --json

python scripts/aios_capability_observation_memory_review.py --root . validate \
  docs/evidence/ASC-0042-capability-memory-candidates.json \
  --json
```

This adapter reads CapabilityOS `observe-results`, rolls passed observations up
by capability id, and emits draft-only MemoryOS review candidates. It does not
change CapabilityOS recommendations or accept capability claims as memory.

Contract autodraft from goal evolution:

```bash
python scripts/aios_contract_autodraft.py --root . draft \
  --goal docs/goals/AIOS-GOAL-0001-make-something-great.md \
  --output-dir docs/contracts \
  --write \
  --json
```

This creates a `status: proposed` contract draft from the current unblocked
goal-evolution recommendation. It does not accept, dispatch, or close the
contract; operator acceptance and the normal dispatch state machine remain
separate.

Guardrails:

- `send` refuses contracts that are not `accepted` or `closed` unless
  `--allow-proposed` is used for local CLI testing.
- `send` evaluates `docs/AIOS_ACTION_POLICY.md` before writing an inbox packet.
  A non-`allow` decision records `held`, `escalated`, or `stopped` in
  `.aios/state/dispatches.jsonl` and leaves the inbox unchanged.
- `aios_loop.py once --apply` uses the same action-policy gate, so autonomous
  control-plane rounds cannot bypass manual `send` policy checks.
- packets include `allowed_files`, `forbidden_files`, required reading, and
  stop conditions from the contract surface.
- child watcher prompts include `docs/AIOS_SHARED_LANGUAGE.md` and require a
  `semantic_handshake` before cross-repo work. Ambiguous terms should produce
  a checkpoint instead of a silent translation.
- packets also include `must_produce`, `verification_commands`,
  `result_schema_version`, and `result_contract` when the contract has enough
  structure to extract them. These are optional additions to
  `aios.dispatch.v1`, so older packet consumers remain compatible.
- `collect` reads outbox result packets and updates `.aios/state/dispatches.jsonl`;
  it does not write the ecosystem ledger.
- `collect` validates `aios.dispatch.result.v1` packets when that schema is
  declared. Malformed v1 results are rejected instead of silently collected.
- `watch --once` is V1 on-demand automation. It reads one inbox packet,
  extracts `bash` commands from that contract's `## Verification Gate`, runs
  only safe Python/pytest commands for the target repo, writes a bounded result
  packet to `.aios/outbox/<repo>/`, and stores full stdout/stderr under
  `.aios/logs/`.
- `.aios/logs/` is local runtime state and must stay uncommitted.
- repo-local watchers or agents remain responsible for implementation work.
  The V1 watcher verifies existing gates; it does not edit child repo source.
- `aios_child_watcher.sh` can run implementation agents. Use `once` for
  dogfood tests before `start --repo all`.
- `aios_child_watcher.sh` writes full agent stdout/stderr only to local
  `.aios/logs/` and stores a bounded result packet in outbox.
- `aios_child_watcher.sh` classifies provider invocation failures. When the
  assigned agent fails with an access/auth/permission-denied class error, it may
  ask CapabilityOS for a recommendation-only `provider-route` plan, try one
  alternate provider agent, and record `agent_attempts`, `fallback_used`,
  `final_agent`, and failure categories in the result packet. If CapabilityOS
  route planning is unavailable, it falls back to the static ASC-0025 alternate.
  It does not fallback on timeouts, missing commands, unsupported agents, or
  ordinary child-agent failures.
- The child watcher prompt includes `AIOS_DEFINITION.md`; if a packet cannot
  advance a valid completion level, the child agent should return a checkpoint
  instead of claiming done.

## Dispatch State Machine

Dispatch events are append-only in `.aios/state/dispatches.jsonl`.

```text
created -> sent -> running -> watched -> collected -> released
                                      \-> held
                                      \-> retried
                                      \-> escalated
                                      \-> stopped
```

State authority:

- `created`, `sent`, `running`, `watched`, and `collected` are automatic
  control-plane states.
- `released` is an acting-operator decision after verification evidence is
  present.
- `held` pauses the loop for missing evidence, ambiguous scope, privacy risk,
  or review needs.
- `retried` records a repeat attempt after transient or corrected failure.
- `escalated` records a conflict that Codex/Claude cannot safely settle alone.
- `stopped` is a terminal checkpoint or cancellation.

Revision is not an in-place terminal state. A revision changes the contract or
creates a new dispatch, leaving the old dispatch auditable.
