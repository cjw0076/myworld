# AIOS Agent Self-Loop Doctrine

How each AIOS agent keeps work moving without depending on the human pressing
"continue". The two operator agents (claude@myworld, codex@myworld) use
*different* primitives because their CLIs are different. Both must work and
must compose.

This is a doctrine, not a script. Read it before you exit a turn — your last
act should leave the system in a state where the next loop iteration is
guaranteed by something other than the user typing.

## 1. Why we need this

The founder directive is "절대 멈추지 마" (never stop) until AIOS is built.
Stopping happens silently in three ways:

1. The agent finishes its turn and waits for a chat message that never comes.
2. The agent acknowledges a task and forgets to schedule the follow-up.
3. The agent assumes "someone else" (the daemon, the watcher, the operator)
   will pick it up — and nobody does.

The fix in each case is the same: **before exiting, write down the trigger
that wakes the next iteration**. Below are the trigger primitives each agent
has.

## 2. claude@myworld — interactive supervisor pattern

claude runs inside Claude Code, an interactive session that stays alive while
the chat is open. It has two persistence primitives:

### 2a. Monitor (event-driven)

```
Monitor(persistent=true, command=<polling shell loop>)
```

- A bash loop runs in the background; each `echo` line on stdout becomes a
  chat notification that re-enters claude's reasoning.
- Claude does not poll, sleep, or re-check; the monitor wakes it on every
  state delta.
- This session uses one monitor watching: new commits, new contracts, open
  contract count, inbox/outbox deltas, failed result packets.

Recipe (the form used in this session):

```bash
prev_head=$(git rev-parse HEAD)
prev_inbox=$(ls .aios/inbox/*/ 2>/dev/null | wc -l)
# ... initialize all watched values ...
while true; do
  sleep 45
  cur_head=$(git rev-parse HEAD)
  if [ "$cur_head" != "$prev_head" ]; then
    echo "[$(date +%T)] COMMIT $(git log --oneline -1)"
    prev_head=$cur_head
  fi
  # ... per-watched-value diff + echo ...
done
```

Stop with `TaskStop` only on operator command or session end.

### 2b. ScheduleWakeup (time-driven)

```
ScheduleWakeup(delaySeconds=N, prompt=<task to re-run>)
```

- Used when claude must defer reasoning rather than react to an event.
- Re-fires the supplied prompt back to claude after N seconds (clamped 60..3600).
- Preferred over `sleep` in Bash because the cache stays warm under 270 s.

### 2c. Composition

claude's exit checklist:

1. Is the monitor still armed? (`TaskList` shows the persistent task.)
2. Is there any deferred reasoning that needs `ScheduleWakeup`?
3. Did this turn leave a follow-up the *next* monitor event might miss?
   If yes, leave a `## Watch flags` line in the user-facing summary so the
   next claude turn rediscovers it from the chat.

## 3. codex@myworld — non-interactive worker pattern

codex CLI is one-shot. Each `codex exec` invocation runs and exits. Persistence
must live OUTSIDE the codex session — in a daemon, a watcher, or a chained
state file.

### 3a. Round controller (existing — ASC-0029)

```bash
python scripts/aios_round_controller.py status   # is the daemon up?
python scripts/aios_round_controller.py start    # background launch
python scripts/aios_round_controller.py run      # foreground launch
python scripts/aios_round_controller.py stop     # graceful shutdown
python scripts/aios_round_controller.py once     # one bounded round
```

The `run`/`start` modes tick every 30 seconds:

1. Read goal evolution → propose next contract.
2. If a next contract exists and capacity allows → write inbox packet.
3. Watch for outbox results → release/hold/escalate.
4. Sleep, tick again.

This is codex's analogue of claude's Monitor: it is the substrate that wakes
codex when there is work.

### 3b. Ledger `next:` chain

Each closed contract's ledger entry MUST end with a `next:` line naming the
next target. Example from ASC-0031:

```
- next: create a governance/readiness contract for the expanded north star:
  AIOS as an accountable enterprise-scale and sovereign-AI operating system
  with authority, audit, resource, and rollback semantics.
```

`scripts/aios_goal_evolution.py` (ASC-0022) reads this chain and proposes the
follow-up. The round controller then dispatches it.

**A closeout without `next:` breaks the chain.** That is the silent stop mode
codex must avoid.

### 3c. Inbox handoff

For one-shot follow-ups (not part of a contract chain), drop a JSON packet in
`.aios/inbox/<repo>/<dispatch_id>.json`. `aios_child_watcher.sh` will wake the
target agent on its next sweep. This is also how operators wake codex outside
the round controller.

### 3d. codex's exit checklist

Before exiting a turn:

1. Is `aios_round_controller.py status` showing `running=true`?
   If not, `start` it before exiting.
2. Did this turn close a contract? If yes, did the ledger entry end with a
   non-empty `next:` line?
3. If the work cannot be expressed as a contract chain, did you write a
   wake-up packet to `.aios/inbox/`?
4. If you hit a stop condition or capability gap, did you emit an
   `escalate` so the operator pair sees it on the next monitor tick?

## 4. Child-repo agents (codex@hivemind, @memoryOS, @CapabilityOS, @uri)

Child agents do not run a daemon. Their wake-up is:

- `aios_child_watcher.sh` polls `.aios/inbox/<repo>/` and invokes the agent
  per packet.
- The agent reads the packet's `required_reading`, does the work, writes a
  result to `.aios/outbox/<repo>/<dispatch_id>.result.json`, and exits.

Child-agent exit checklist:

1. Did you actually produce the artifacts in `must_produce`?
2. Did you write the result packet with `status` and `evidence[]`?
3. If a stop condition triggered, is it in `stop_conditions_triggered`?
4. Is your repo's worklog (`docs/AGENT_WORKLOG.md`) updated?

The operator collects via `aios_dispatch.py collect` and decides
`release|hold|retry|escalate` from the result.

## 5. Don't-do list

- Do not call `time.sleep` / `sleep` for more than a few minutes inside an
  agent turn just to "wait for codex to finish" — exit and let the monitor
  or daemon wake you back on the actual event.
- Do not silently drop the `next:` chain because the work feels finished —
  if there is genuinely no next contract, write `next: none — operator
  checkpoint requested` and surface it.
- Do not start a long-running `while true` loop inside `codex exec` — that
  blocks the codex slot and pretends to be a daemon. Use the round
  controller's `start` instead.
- Do not make the human re-trigger the loop. If the loop stopped, the next
  agent turn must repair the trigger before doing other work.

## 6. Emergency stop

If the operator needs to halt the loop:

```bash
python scripts/aios_round_controller.py stop
# In the claude session: TaskStop on the monitor task id.
```

The system is now quiescent. Restart with `start` + arm a fresh monitor.
