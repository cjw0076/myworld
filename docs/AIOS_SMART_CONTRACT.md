# AIOS Smart Contract

An AIOS smart contract is a local-first, machine-checkable work agreement
between Hive Mind, MemoryOS, CapabilityOS, and the operator.

It is not blockchain consensus. It is a contract for role boundaries,
permissions, required artifacts, validation gates, and stop conditions.

## Minimal Contract Shape

```json
{
  "contract_id": "asc_...",
  "goal": "Prepare MemoryOS public alpha",
  "scope": {
    "repos": ["hivemind", "memoryOS", "CapabilityOS"],
    "allowed_files": ["docs/**", "tests/**", "memoryos/**"],
    "forbidden_files": ["data/**", ".env", "raw_exports/**"]
  },
  "hive_mind": {
    "responsibility": "plan_execute_verify",
    "must_produce": ["execution_receipt", "test_report", "memory_drafts"]
  },
  "memoryos": {
    "responsibility": "retrieve_remember_review",
    "must_produce": ["context_pack", "retrieval_trace", "review_queue"]
  },
  "capabilityos": {
    "responsibility": "recommend_capabilities",
    "must_produce": ["capability_plan", "fallback_plan", "risk_notes"]
  },
  "operator": {
    "responsibility": "release_revise_cancel",
    "checkpoint_required": true
  },
  "stop_conditions": [
    "privacy_violation",
    "scope_violation",
    "missing_required_artifact",
    "test_gate_failed",
    "ownership_conflict",
    "contract_ambiguous"
  ]
}
```

## Contract Flow

```text
draft contract
  -> MemoryOS context offer
  -> CapabilityOS route offer
  -> Hive Mind execution offer
  -> operator or scheduler acceptance
  -> execution
  -> receipt / trace / observation closeout
```

## Invariants

- Hive Mind owns execution authority.
- MemoryOS owns memory and review lifecycle; it may propose memory but does not
  silently accept it.
- CapabilityOS owns recommendations and binding plans; early versions do not
  install or execute external tools directly.
- Operator checkpoints are valid outputs, not failures.
- Every cross-OS task should close with evidence or a documented violation.
