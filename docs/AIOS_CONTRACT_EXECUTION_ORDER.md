# AIOS Contract Execution Order

Updated: 2026-05-13 KST

This queue prevents AIOS from sprinting past accepted-but-unclosed contracts.
The order is evidence-first: close or hold existing contracts before adding
larger runtime surfaces.

## Current Rule

Do not treat a clean monitor as proof that all contracts are complete. Monitor
health says no active alert exists; contract health requires frontmatter,
dispatch state, receipts, tests, and ledger closeout to agree.

## Execution Queue

### P0 — Reconcile Open Contracts

1. `ASC-0076 contract-closeout-reconciliation`
   - Build the status matrix for `ASC-0056` through `ASC-0068`.
   - Classify each as `close_now`, `retry_now`, `hold`, `supersede`, or
     `continue_implementation`.
   - No new feature work until this matrix is written.

### P1 — Close Already-Verified Work

2. `ASC-0066 provider-backpressure-role-distillation`
   - Hive implementation and tests already passed.
   - Needs final contract frontmatter closeout and ledger entry.

3. `ASC-0065 genesisos-bootstrap`
   - GenesisOS repo exists and has a working divergence CLI.
   - Needs MyWorld closeout decision because `GenesisOS/` is a separate git
     repo and should not be silently folded into MyWorld source.

4. `ASC-0063 uri-content-relevance-filter`
   - Already marked closed, but local working tree still contains uncommitted
     URI-filter files. Reconcile commit/state before depending on it.

### P2 — Resolve Blocked Pipeline Contracts

5. `ASC-0056 memoryos-draft-pipeline-closure`
   - Currently held due provider backpressure.
   - Retry only after ASC-0066 closeout confirms role-capsule fallback
     semantics are available.

6. `ASC-0060 action-policy-scope-aware`
7. `ASC-0061 dispatch-escalate-recovery`
8. `ASC-0059 watcher-race-resolution`
   - These harden the control-plane execution path.
   - They should close before broad child-repo watcher runs.

### P3 — Restore Metabolism

9. `ASC-0057 pulse-heartbeat-persistence`
10. `ASC-0058 goal-inbox-processor`
    - These make AIOS continue learning and converting child-repo friction
      into contract candidates.

### P4 — Operator Surface

11. `ASC-0064 live-dashboard-websocket`
    - Useful, but not allowed to block runtime correctness.

### P5 — Runtime Expansion

12. `ASC-0078 aios-work-visibility-layer`
    - The operator must be able to see what AIOS is doing before broad
      autonomous runtime expansion continues.

13. `ASC-0067 unified-os-invocation-pipeline`
    - One goal produces GenesisOS, MemoryOS, CapabilityOS, Hive, and MyWorld
      artifacts.

14. `ASC-0068 global-project-agent-discovery`
    - Any project can be discovered and routed into ASC-0067 without granting
      broad write authority.

### P6 — Shared Meaning Layer

15. `ASC-0077 genesisos-semantic-alignment-kernel`
    - GenesisOS gains a second role: not only divergence, but common-language
      stabilization. It maps local/project/agent terms to AIOS canonical
      meanings so agents do not speak past each other.

## GenesisOS Role Update

GenesisOS now has two bounded roles:

- `divergence`: create non-obvious candidate branches before convergence.
- `semantic_alignment`: build and check shared meaning between agents,
  languages, projects, and OS layers.

GenesisOS still does not own execution, memory acceptance, tool routing, or
final truth. It proposes and stabilizes meaning; Hive, MemoryOS, CapabilityOS,
and MyWorld still keep their authority boundaries.
