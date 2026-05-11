# AIOS North Star

MyWorld is a local-first AI operating system for turning a user goal into
planned work, retrieved context, selected capabilities, verified execution, and
durable memory.

See `AIOS_DEFINITION.md` for the strict definition and anti-cheat invariants.

The target user experience is:

```text
User gives a goal.
AIOS plans, retrieves, routes, executes, verifies, remembers, and reports.
User reads logs and makes checkpoint decisions.
```

The user should not need to think in directories, apps, provider CLIs, MCP
servers, API surfaces, or skill names. Those remain implementation details
behind the AIOS control plane.

## Three OS Roles

```text
Hive Mind
= executor, scheduler, verifier, provider harness

MemoryOS
= local-first memory graph, context pager, provenance ledger, review lifecycle

CapabilityOS
= capability map, router, binding planner, fallback recommender
```

When a task arrives:

1. Hive Mind decides how to do the work: decomposition, agent roles, scheduler,
   verification gates, receipts, and operator checkpoints.
2. MemoryOS decides what knowledge to bring: accepted memory, project state,
   prior decisions, constraints, related work, production examples, and
   evidence-linked context packs.
3. CapabilityOS decides what can help: provider CLIs, local models, MCP servers,
   APIs, skills, scripts, browser tools, external services, and fallback routes.
4. Hive Mind executes through the harness.
5. MemoryOS records receipts, drafts, retrieval traces, and review outcomes.
6. CapabilityOS records capability observations so future routing improves.

## Final Shape

```text
Prompt in.
Work plan from Hive Mind.
Context from MemoryOS.
Capability plan from CapabilityOS.
Execution through Hive Mind.
Evidence and memory back into MemoryOS.
Capability observations back into CapabilityOS.
Operator checkpoints when the contract is uncertain.
```

This is not a monolithic app. It is a contract-bound ecosystem where each OS has
its own ledger and agent loop, but shares one user goal. `myworld/` acts as the
control tower: it does not do every task itself, but coordinates the systems
that do.

## Readiness Bar

AIOS is not ready merely because the docs describe it. The north star is ready
only when one cross-OS task is repeatable without chat context:

```text
goal
  -> contract
  -> dispatch to owning repo
  -> MemoryOS context/provenance
  -> CapabilityOS route/observation
  -> Hive Mind or repo-local execution
  -> verification evidence
  -> durable closeout in the AIOS ledger
```

Until that loop is repeatable, agents should report a concrete level:
`described`, `contractable`, `dispatchable`, `executable`, `verifiable`,
`learnable`, or `repeatable`.
