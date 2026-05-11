# AIOS Definition

AIOS is not a chat wrapper, a folder of scripts, or a collection of agents. It
is a contract-bound operating loop that turns a user goal into planned work,
retrieved memory, selected capabilities, verified execution, and durable
learning.

## One Sentence

AIOS is the local-first control system where `myworld` coordinates Hive Mind,
MemoryOS, and CapabilityOS to complete user goals while preserving evidence,
ownership, verification, and memory.

## Necessary Conditions

A turn is not acting as AIOS unless all of these are true:

1. There is a user goal or operator-approved contract.
2. Work ownership is assigned to the correct OS/repo.
3. MemoryOS provides or records relevant context, provenance, or memory drafts.
4. CapabilityOS provides or records capability recommendations, observations,
   or fallback plans when tool choice matters.
5. Hive Mind or the owning repo executes the work under bounded scope.
6. Verification evidence exists: tests, smoke output, receipt, trace, review,
   or an explicit checkpoint.
7. Results are written back as durable records, not only chat messages.
8. Stop conditions are respected instead of bypassed.

If any condition is missing, the correct output is a checkpoint, gap report, or
proposal. It is not a completed AIOS turn.

## What AIOS Is Not

- Not "Codex edits files until tests pass."
- Not "Claude writes a design note."
- Not "Hive Mind runs agents without memory or capability feedback."
- Not "MemoryOS stores everything automatically."
- Not "CapabilityOS installs or executes every tool it finds."
- Not "`myworld` directly patches all lower repos."
- Not "a loop that keeps running without release, hold, or stop semantics."

## Anti-Cheat Invariants

Agents must not claim AIOS progress by satisfying only the easiest visible
surface.

| Shortcut | Why it is invalid | Required instead |
| --- | --- | --- |
| Docs-only completion for implementation work | No execution evidence | Contract, dispatch, implementation, verification |
| Direct lower-repo edit from `myworld` | Bypasses ownership | Dispatch packet to owning repo |
| Memory accepted without review | Breaks MemoryOS lifecycle | Draft first, ReviewRecord later |
| Tool use without capability evidence | Bypasses CapabilityOS | Capability recommendation or observation |
| Test pass without receipt/log | Cannot be audited | Store command summary, receipt, or result packet |
| Infinite loop without stop criteria | Not controllable | Stop file, checkpoint, or ready marker |
| Raw private data in shared docs | Privacy violation | Link by source id/path summary only |
| Overclaiming "AIOS complete" | North star not operational | Mark only specific contract/sprint done |

## Completion Levels

Use these levels instead of vague "done":

```text
L0 described
  The concept is written down.

L1 contractable
  A smart contract can assign the work.

L2 dispatchable
  myworld can send a packet to the owning repo.

L3 executable
  the owning repo agent can run and return a result packet.

L4 verifiable
  tests, receipts, traces, or review evidence prove the result.

L5 learnable
  MemoryOS and CapabilityOS receive records that improve future runs.

L6 repeatable
  a future agent can rerun the flow from docs and scripts without chat context.
```

The AIOS north star is not met until the core loop is at least L6 for one real
cross-OS task.

## Control Tower Rule

`myworld/` is the control tower. A control tower does not fly every aircraft.
It issues routes, tracks state, enforces holds, and records decisions.

Therefore:

- `myworld` owns contracts, dispatch, global ledger, and readiness.
- child repos own implementation.
- operator checkpoints are part of the system, not a failure.

