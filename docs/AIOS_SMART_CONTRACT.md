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
  "substrate_surface_knowledge": {
    "substrate_level": "none | primitive | runtime | provider_process | os_service",
    "surface_type": "chat | contract | plugin | mcp | dispatch | direct_hive_execution",
    "knowledge_scope": "local_only | memoryos_context | web_primary_sources | multi_model_review | external_system_dissection",
    "authority": "recommendation_only | draft_only | speculative_only | execute_with_receipt | dangerous_opt_in",
    "owner_repo": "myworld | hivemind | memoryOS | CapabilityOS | GenesisOS | child_repo",
    "required_receipts": ["..."]
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

## Substrate / Surface / Knowledge Gate

Every non-trivial contract should decide how deep the work is allowed to go
before execution begins. Use `docs/AIOS_SUBSTRATE_BOUNDARY.md` as the detailed
classifier.

Required fields for contracts that touch tools, providers, external knowledge,
memory, process lifecycle, or child repo execution:

| Field | Allowed Values | Meaning |
| --- | --- | --- |
| `substrate_level` | `none`, `primitive`, `runtime`, `provider_process`, `os_service` | How close the work gets to AIOS/process substrate. |
| `surface_type` | `chat`, `contract`, `plugin`, `mcp`, `dispatch`, `direct_hive_execution` | The operator/agent-facing interface being created or used. |
| `knowledge_scope` | `local_only`, `memoryos_context`, `web_primary_sources`, `multi_model_review`, `external_system_dissection` | What knowledge may influence the decision. |
| `authority` | `recommendation_only`, `draft_only`, `speculative_only`, `execute_with_receipt`, `dangerous_opt_in` | What the route may do without another contract. |
| `owner_repo` | `myworld`, `hivemind`, `memoryOS`, `CapabilityOS`, `GenesisOS`, or named child repo | Which repo owns the slice. |
| `required_receipts` | list | Evidence required before release. |

Boundary invariants:

- CapabilityOS recommends; it does not execute tools, bind plugins, install
  packages, or handle credentials.
- MemoryOS is draft-first; it does not accept external or provider-derived
  knowledge without review.
- GenesisOS challenges frames and assumptions; it does not select final truth
  or take execution authority.
- Hive Mind executes bounded work and verifies receipts.
- `dangerous_opt_in` requires explicit operator acceptance and must not be the
  default for autonomous development.

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

## AIOS Role Evidence

Generated contract seeds should reserve this compact section before executor
work begins:

```md
## AIOS Role Evidence

### MemoryOS
- context_pack
- retrieval_trace
- accepted_memory_ids
- draft_memory_policy

### CapabilityOS
- route
- recommended_tools
- fallback_plan
- authority

### GenesisOS
- branch_set
- assumption_mutations
- semantic_alignment_notes
- authority

### Hive Mind
- execution_plan
- provider_route
- verification_receipt
- degraded_or_fallback_receipt
```

These fields can be `pending_or_not_required` in a proposal. The point is to
make missing OS participation visible before acceptance, without making seed
generation execute work or accept memories.

Persona-axis note: for work meant to dogfood AIOS itself, the role evidence
section should also say whether the contract uses the five cognitive roles:
Hive=Wrapper, MemoryOS=Retriever, CapabilityOS=Router, GenesisOS=Philosophy,
MyWorld=Sovereign. If a role is skipped, write the reason explicitly. The
persona audit treats an explicit justified absence differently from silent
worker-mode drift in later review.

## Invariants

- Hive Mind owns execution authority.
- MemoryOS owns memory and review lifecycle; it may propose memory but does not
  silently accept it.
- CapabilityOS owns recommendations and binding plans; early versions do not
  install or execute external tools directly.
- Operator checkpoints are valid outputs, not failures.
- Every cross-OS task should close with evidence or a documented violation.
