# AIOS Shared Language

This is the common vocabulary that MyWorld, Hive Mind, MemoryOS,
CapabilityOS, GenesisOS, child repos, and provider agents must use during
cross-repo AIOS work.

GenesisOS owns the advisory semantic kernel for this glossary. Its output is a
canonical anchor proposal, not final truth. Ambiguous or unknown terms should
produce an operator checkpoint before dispatch broadens.

## Canonical Terms

| Canonical | Common Surface Forms | Contract Meaning |
| --- | --- | --- |
| `aios` | AIOS, AI OS, AI operating system | The local-first operating layer where MyWorld coordinates Hive Mind, MemoryOS, CapabilityOS, GenesisOS, and owning repos through contracts, dispatch, receipts, verification, and learning. |
| `myworld` | MyWorld, control plane | The control plane. It owns contracts, dispatch state, global ledger, monitor state, goal evolution, and operator checkpoints. |
| `hive_mind` | Hive Mind, hivemind, hive execution, execution layer | The execution and verification layer. It plans work, schedules agents, wraps provider CLIs, records run artifacts, and produces receipts. |
| `memoryos` | MemoryOS, memory OS | The memory and provenance layer. It retrieves accepted context, creates draft memories, preserves review lifecycle, and records retrieval traces. |
| `capabilityos` | CapabilityOS, capability OS | The capability routing layer. It recommends tools, providers, APIs, skills, fallback routes, and risk notes without taking execution authority. |
| `genesisos` | GenesisOS, Genesis OS, divergence layer | The divergence and semantic-alignment layer. It creates branches, mutations, challenge reports, analogy matches, seed captures, and shared-meaning anchors without execution authority. |
| `contract` | AIOS smart contract, contract, 계약, ASC | A bounded work agreement naming owner repos, allowed files, forbidden files, required outputs, verification gates, and stop conditions. |
| `accepted_contract` | accepted contract, 수락된 계약 | A contract whose lifecycle state authorizes downstream dispatch. It is narrower than `contract`. |
| `dispatch_packet` | dispatch packet, dispatch, 디스패치 패킷 | A repo-specific JSON handoff from MyWorld to one target repo or agent. It is derived from a contract and is not permission to exceed scope. |
| `receipt` | receipt, result packet, 영수증 | A durable result or evidence artifact proving what happened, what changed, and which verification ran. |
| `ledger` | ledger, agent ledger, 작업 장부 | The append-only cross-OS record for decisions, closeouts, risks, and next steps. |
| `memory_draft` | memory draft, draft memory, 기억 초안 | A proposed MemoryOS record. It is not accepted memory until MemoryOS review approves it. |
| `accepted_memory` | accepted memory, 수락된 기억, 기억 | A reviewed MemoryOS object that may be used as context for later runs, with provenance and retrieval trace evidence. |
| `capability_recommendation` | capability route, capability recommendation, 능력 추천 | A recommendation from CapabilityOS about what tool, provider, skill, route, or fallback should be considered. It does not execute the tool. |
| `provider_route` | provider route, provider routing, 공급자 경로 | The concrete binding to a provider surface. It still requires authority, scope, and receipt evidence. |
| `projection` | projection, 관측 투영 | A redacted or transformed view of raw output that preserves evidence without exposing private bodies or provider logs. |
| `local_posterior_belief` | local posterior belief, local belief, 사후 믿음 | A bounded current belief derived from local evidence; it is not global truth. |
| `operator_checkpoint` | operator checkpoint, 운영자 체크포인트 | A named pause for human/operator decision when authority, ambiguity, privacy, or scope cannot be resolved locally. |
| `stop_condition` | stop condition, halt condition, 정지 조건 | A named condition that pauses the loop instead of broadening scope, guessing, deleting records, or crossing authority boundaries. |
| `semantic_handshake` | semantic handshake, semantic alignment, 의미 정렬 | A pre-work statement confirming contract terms, target repo, recognized AIOS terms, and unresolved ambiguous terms. |

## Boundary Pairs

These terms must not collapse even when surface language overlaps:

| Pair | Boundary |
| --- | --- |
| `contract` / `dispatch_packet` | A contract is the authority document; a dispatch packet is the runtime handoff derived from it. |
| `contract` / `accepted_contract` | A contract can be proposed, accepted, closed, held, or superseded; an accepted contract is the dispatch-authorizing state. |
| `memory_draft` / `accepted_memory` | Draft memory is review-pending; accepted memory can be retrieved as trusted context. |
| `capability_recommendation` / `provider_route` | CapabilityOS recommends; provider routing binds a substrate but still does not bypass authority or receipts. |

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
    - semantic handshake
  ambiguous_terms: []
```

If `ambiguous_terms` is not empty, stop at an operator checkpoint rather than
silently translating the task into a local vocabulary.

## GenesisOS Kernel

GenesisOS exposes deterministic semantic helpers:

```bash
cd GenesisOS
python -m genesisos.cli semantics normalize --term "작업 장부" --json
python -m genesisos.cli semantics handshake --text "../AGENTS.md" --json
python -m genesisos.cli semantics diff --left "contract" --right "dispatch packet" --json
```

Schemas:

- `genesisos.semantic_normalization.v1`
- `genesisos.semantic_handshake.v1`
- `genesisos.semantic_diff.v1`

All three are `advisory_only`.

## ASC-0068 Consumption

Project discovery should emit `semantic_handshake.json` using
`aios.semantic_handshake.v1` and include:

- recognized canonical terms from this glossary
- unknown local terms that may need project-specific aliases
- ambiguity pairs that require an operator checkpoint
- references to the source files used for the handshake

ASC-0077 does not automatically rewrite ASC-0068. It defines the canonical
language and schema compatibility that a later integration contract can consume.
