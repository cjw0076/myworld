# AIOS Shared Language

This is the common vocabulary that myworld, Hive Mind, MemoryOS, CapabilityOS,
and working repos must use during cross-repo AIOS work. It exists to reduce
semantic drift between agents trained on different data.

## Terms

| Term | Contract Meaning |
| --- | --- |
| AIOS | The local-first control system where myworld coordinates Hive Mind, MemoryOS, and CapabilityOS to complete goals with evidence, ownership, verification, and learning. |
| myworld | The control plane. It owns contracts, dispatch, global ledger, goal evolution, monitor state, and operator checkpoints. |
| Hive Mind | The execution and verification layer. It plans work, schedules agents, wraps provider CLIs, records run artifacts, and produces receipts. |
| MemoryOS | The memory and provenance layer. It retrieves accepted context, creates draft memories, preserves review lifecycle, and records retrieval traces. |
| CapabilityOS | The capability routing layer. It recommends tools, providers, APIs, skills, fallback routes, and risk notes without taking execution authority. |
| AIOS smart contract | A bounded work agreement naming owner repos, allowed files, forbidden files, required outputs, verification gates, and stop conditions. |
| dispatch packet | A repo-specific JSON handoff from myworld to one target repo/agent. It is not permission to exceed the contract. |
| memory draft | A proposed memory object. It is not accepted memory until MemoryOS review records approve it. |
| accepted memory | A reviewed MemoryOS object that may be used as context for later runs, with provenance and retrieval trace evidence. |
| capability route | A recommendation from CapabilityOS about what tool, provider, skill, or fallback should be used. It does not execute the tool. |
| hive execution | Work performed through Hive Mind or an owning repo under scoped artifacts, receipts, and verification. |
| verification gate | The concrete command, artifact, trace, or review that decides whether a contract can close. |
| stop condition | A named condition that pauses the loop instead of broadening scope or guessing. |
| semantic handshake | A short pre-work statement by an agent confirming the contract terms it will use, the repo it owns, and any ambiguous term it is not sure about. |
| self-resonant repo loop | A loop where working repos submit goals to myworld, receive memory/capability/hive routes, return results/friction, and feed that friction back into AIOS improvements. |

## Required Handshake

Before cross-repo work, a child repo agent should write or report:

```text
semantic_handshake:
  contract_id: <ASC id>
  target_repo: <repo>
  terms_confirmed:
    - AIOS smart contract
    - dispatch packet
    - memory draft
    - capability route
    - hive execution
    - stop condition
  ambiguous_terms: []
```

If `ambiguous_terms` is not empty, the agent should stop at a checkpoint rather
than silently translating the task into its own vocabulary.
