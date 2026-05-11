---
goal_id: AIOS-GOAL-0001
slug: make-something-great
status: active
created: 2026-05-12 01:24 KST
owner: codex+claude acting operators
---

# AIOS-GOAL-0001 Make Something Great

## North Star

When the user gives one high-level goal, AIOS should repeatedly discover
context, retrieve memory, choose capabilities, dispatch agents, verify results,
learn from outcomes, and propose or execute the next best step with minimal
user relay.

## Quality Function

- reduce_user_relay: fewer cases where the user must copy context between
  agents or repos.
- increase_verified_execution: more child-repo work closes with tests,
  receipts, result packets, and monitor-clear evidence.
- improve_context_reuse: MemoryOS context, Hive arrival packs, and accepted
  prior decisions shape future work.
- improve_capability_routing: CapabilityOS recommendations and observations
  affect tool/provider choices when execution options matter.
- strengthen_stop_conditions: privacy, scope, stale evidence, and ambiguous
  ownership stop the loop instead of being bypassed.
- increase_repeatability: a future agent can rerun the loop from docs/scripts
  without chat context.

## Anti-Cheat Checks

- Do not count docs-only work as progress when the goal requires execution.
- Do not reopen closed contracts as new work.
- Do not auto-accept private/archive paths or raw exports.
- Do not let myworld become a broad child-repo implementation worker.
- Do not claim goal progress without monitor/readiness/policy evidence.
- Do not accept self-evaluation without adversarial or verification evidence
  for high-risk changes.

## Current Strategy

1. Keep the monitor clear.
2. Use doc scout and loop policy to sense new work.
3. Use this goal file to rank next work by quality-function impact.
4. Open one narrow contract at a time.
5. Dispatch implementation to the owning repo.
6. Verify, collect, release, and record learning.

## Preferred Next Improvements

- capability_observation_memory_import: decide which CapabilityOS observations
  should enter MemoryOS as reviewable durable memory.
- contract_autodraft_from_goal_plan: turn an unblocked goal evolution
  recommendation into a proposed smart contract draft without relying on chat
  memory.

## Completed Improvements

- source_read_registry: ASC-0023 added Hive source-read records and arrival-pack
  reconciliation hints.
- watcher_execution_reliability: ASC-0025 added bounded child watcher
  provider-access fallback and structured attempt evidence.
- capability_routing_memory: ASC-0026 made CapabilityOS recommendations consume
  prior AIOS observation outcomes in-memory.
- memory_feedback_tightening: ASC-0027 added MemoryOS feedback directives and
  Hive context-pack rendering for next-run shaping.
- capability_route_binding: ASC-0028 bound child watcher access-denied fallback
  selection to CapabilityOS provider-route recommendations.
- persistent_control_loop: ASC-0029 added a provider-independent round
  controller that runs monitor, goal evolution, dispatch apply, child watcher
  status, and durable round receipts outside the chat turn.
