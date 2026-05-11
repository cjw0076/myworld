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

- source_read_registry: record which source artifacts each agent read and flag
  shared-source divergent interpretations.
- watcher_execution_reliability: remove provider access-denied fallbacks from
  child watcher implementation runs.
- capability_routing_memory: make CapabilityOS observations influence later
  routing decisions.
- memory_feedback_tightening: make MemoryOS accepted context shape more next
  Hive runs without manual relay.
