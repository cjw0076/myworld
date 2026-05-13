# Claude Code Session Maintenance — Founder Reverse-Engineering

Author: 재원 (founder) — direct reverse-engineering of Claude Code session
mechanism, contributed to AIOS reverse-engineering corpus 2026-05-13 KST.

Importance: founder's observation is more concrete than any prior claude
self-observation because it identifies the 5 LAYERS of session continuity
mechanism. Each layer maps to a concrete AIOS improvement target.

## The 5 layers (founder)

### Layer 1 — Task List (in-session state)

Tasks re-injected via system reminder periodically. Survives context
compaction. Only official mechanism for in-session state continuity.
Claude reads the re-injected task list and reconstructs "where am I".

### Layer 2 — Async experiment management

`Bash(command, run_in_background=True)` → immediate background task ID
→ Claude works on other things → completion notification arrives →
Claude reads results, decides next step. "Completion notification = wake-up
trigger."

### Layer 3 — ScheduleWakeup (only autonomous loop mechanism)

Used by `/loop`. Claude MUST call ScheduleWakeup each turn to keep the
loop alive. Loop ends if Claude doesn't call it. Cache TTL boundary
matters: 270s vs 300s. Under 270s = cache hot, next turn fast.

### Layer 4 — Monitor (streaming event subscription)

`Monitor(process_id)` → stdout lines as notifications. Push not pull.
Claude doesn't poll. But Claude is bound to the stream while it's open.

### Layer 5 — Session-to-session continuity (file-based)

Claude Code sessions are stateless. Continuity is entirely file-based:
- `MEMORY.md` — user role, feedback, project context
- `comms_log.md` — prior decisions, current state
- Task list (re-injected) — progress
- Without these files, session restart = start from scratch.

## What AIOS must absorb (founder mapping)

| Claude mechanism | Limit | AIOS improvement target |
|---|---|---|
| Task list re-inject | session-only | contract lifecycle = session-independent |
| ScheduleWakeup | claude must call it | daemon externally calls agent at intervals |
| Background + notify | completion only, no progress | Monitor parallel or receipt polling |
| File-based continuity | manual file management | MemoryOS auto write/retrieve |

## Cross-check vs current AIOS state (2026-05-13)

| AIOS state | Founder's expected behavior | Reality |
|---|---|---|
| Contract lifecycle session-independent | ✓ | ✓ already (`docs/contracts/` is files) |
| Daemon externally calls agent | partial | round_controller calls dispatch BUT doesn't call same-session claude back |
| Receipt polling | partial | dispatch.py status exists, but no continuous progress stream |
| MemoryOS auto write/retrieve | designed | **NOT WORKING** — 0 drafts in last 24h despite 80+ contracts |

## Cross-questions founder asked alongside this

1. **MemoryOS 반영?** Verified 2026-05-13 KST: NO. 34 drafts all from
   2026-05-11. Last 24h = 0. Last 1h = 0. ASC-0056 in-flight to fix.
2. **Hive used memoryOS context?** Verified: NO. ASC-0084 debate
   synthesis docs cite 0 mem_/trace_id references. Hive deliberated
   in isolation.
3. **Agent identity registry?** Verified: NO formal registry. Social
   convention `<agent>@<host>` only.

## Implied next contracts (proposed, not yet drafted)

1. **agent identity registry**: `~/.aios/identity.json` per agent with
   stable id, capabilities, public key seed (later for swarm), substrate.
   Every observation / contract / packet cites the agent_id. Replaces
   ad-hoc strings.

2. **memoryOS auto-write hook**: every contract closeout triggers
   `memoryos draft create` with structured fields. Fixes Q2 gap.

3. **Hive context binding**: every Hive deliberation receives a
   `memoryos context build --task <X>` result as required reading.
   Fixes Q3 gap.

4. **External agent waker** (daemon-side ScheduleWakeup equivalent):
   round_controller can wake a specific agent session by sending a
   "wake packet" through aios_primitives or by injecting into the
   agent's known input path (claude: comms_log, codex: round tick,
   local LLM: queue). Lifts ScheduleWakeup-style autonomy out of
   in-session claude into the daemon layer.

5. **Background-with-progress primitive**: `aios_primitives bg start
   --name X --command "..." --stream-to events.jsonl` so progress
   flows live, not just on completion. Bridges Layers 2 and 4.

Each should be a separate contract — drafting them is the next operator
action, not the act of writing this discovery doc.
