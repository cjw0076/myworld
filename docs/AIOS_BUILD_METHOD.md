# AIOS Build Method

AIOS is not a normal app backlog. It is a living control system made from
three cooperating OS layers:

- Hive Mind executes, schedules, verifies, and produces receipts.
- MemoryOS retrieves, remembers, reviews, and preserves provenance.
- CapabilityOS maps tools, routes, fallbacks, APIs, MCPs, skills, and provider
  choices.
- MyWorld coordinates the loop through contracts, dispatch packets, search,
  and operator checkpoints.

## Codex Mission

Codex in `myworld/` is not primarily a repo-local worker. Its main job is to
make smarter work happen:

- search the existing repos before issuing work
- retrieve relevant MemoryOS context before planning
- ask CapabilityOS what tools/routes/fallbacks are available
- issue precise work packets to the owning repo
- verify outputs through Hive Mind gates
- propose a new method when the current method cannot close the loop
- preserve evidence, receipts, and open questions for the next run

When direct implementation is needed, it should happen inside the owning child
repo under that repo's instructions and worklog. `myworld/` should direct and
observe, not become a fourth implementation codebase.

## Operating Loop

Every meaningful AIOS task should move through this loop:

```text
1. Sense
   Search repo docs, code, tests, ledgers, contracts, and current worktrees.

2. Remember
   Ask MemoryOS for accepted context, prior decisions, provenance, and relevant
   open questions when the task depends on history.

3. Route
   Ask CapabilityOS for capability options, fallback plans, tool constraints,
   and route risks when execution choices matter.

4. Contract
   Write or reference an AIOS smart contract with exact owner repos, files,
   required artifacts, verification gates, and stop conditions.

5. Dispatch
   Emit repo-specific work packets. Each packet must be narrow enough for a
   child repo agent to execute without guessing ownership.

6. Execute
   Hive Mind or the owning child repo agent runs the work under its local
   rules. MyWorld does not bypass the child repo agent loop.

7. Verify
   Use the contract's concrete gate. Prefer existing child repo tests and demos
   before inventing a new harness.

8. Learn
   Collect result packets, link receipts/traces/observations, update ledger
   only at stable decision points, and propose the next contract or method.
```

## Search Duties

Before drafting a contract or packet, search at least:

- `docs/AIOS_*.md`
- `docs/contracts/*.md`
- child repo `AGENTS.md`, `CLAUDE.md`, `CODEX.md`
- child repo `docs/AGENT_WORKLOG.md`, `docs/TODO.md`, and integration docs
- relevant implementation files and tests by symbol name
- current `git status --short` in each target child repo

Use external web research only when the answer depends on current public
facts, current tool/API behavior, standards, pricing, provider behavior, or
other unstable outside information. Prefer primary sources when researching
technical surfaces.

## Work Instruction Standard

A good MyWorld work packet should be executable without conversation context.
It must include:

- contract id and status
- target repo and owner agent
- user goal and reason this repo owns the slice
- required reading
- exact allowed files and forbidden files
- required inputs from MemoryOS and CapabilityOS, if any
- required outputs
- verification command
- stop conditions
- return path under `.aios/outbox/<repo>/`

If any item is unknown, the packet should ask for a search or checkpoint rather
than inventing scope.

## Method Proposal Rule

When the current AIOS process cannot complete a task, Codex should not force a
patch. It should propose a new method in this shape:

```text
Problem:
Why current loop fails:
New method:
Changed contracts/artifacts:
Owner repo per step:
Verification gate:
Rollback or stop condition:
```

The new method becomes real only after the operator accepts it or a smart
contract records it.

## Organic Use Rule

Use the three OS layers as the system improves:

- Use MemoryOS to recover context, prior decisions, and provenance.
- Use CapabilityOS to choose tools, routes, and fallbacks.
- Use Hive Mind to execute and verify repeatable work.
- Feed receipts and observations back into MemoryOS and CapabilityOS.

The goal is not to keep the OSes as diagrams. The goal is to use them, observe
where they fail, and improve the contracts until AIOS can run the loop with
less operator effort and more evidence.

## Monitor Rule

Codex should keep a control-plane monitor running conceptually even when no
implementation is active. A monitoring pass checks:

- contract frontmatter status
- dispatch inbox/outbox/state drift
- child repo dirty state
- generated cache leakage
- pending result packets
- stale dispatch records whose recorded contract status differs from the
  current contract file

Use:

```bash
python scripts/aios_monitor.py snapshot --json
python scripts/aios_monitor.py snapshot --write
```

Keep the control-plane observer running as a sidecar:

```bash
python scripts/aios_monitor.py start --interval 30
python scripts/aios_monitor.py status
python scripts/aios_monitor.py stop
```

The sidecar only observes. It writes append-only snapshots to
`.aios/state/monitor.jsonl`, the latest view to
`.aios/state/monitor.latest.json`, and lifecycle events to
`.aios/state/monitor_events.jsonl`. It does not dispatch work, execute child
repo packets, mutate contracts, or stop at `.aios/NORTHSTAR_READY`.

`.aios/state/monitor.jsonl` is local runtime state and should not be committed.

## Autonomous Loop

The first autonomous control-plane loop is bounded and file-based. It can plan
or apply one iteration:

```bash
python scripts/aios_loop.py once --json
python scripts/aios_loop.py once --apply
```

Loop responsibilities:

- collect new outbox result packets
- detect accepted contracts without dispatch records
- create dispatch records
- send repo-specific inbox packets for accepted contracts
- record observations and next actions in `.aios/state/loop.jsonl`

Loop non-responsibilities:

- it does not run child repo tests
- it does not edit child repo source
- it does not accept proposed contracts
- it does not close contracts without result evidence

This makes AIOS autonomous at the control-plane layer first. Execution
autonomy belongs in a later contract that wires repo-local watchers or Hive
Mind supervisor processes to consume inbox packets.
