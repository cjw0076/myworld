# AIOS 5-Persona Axis

This axis measures whether AIOS behaves like the founder's reframe:

| Persona | OS | Function |
| --- | --- | --- |
| Agent(Wrapper) | Hivemind | Uses provider/CLI/local-LLM wrapping instead of one brittle substrate. |
| Agent(Retriever) | MemoryOS | Grounds work in accepted memory with positive retrieval signal. |
| Agent(Router) | CapabilityOS | Routes tools, providers, APIs, skills, and fallback plans. |
| Agent(Philosophy) | GenesisOS | Challenges prompt-prison, creates alternatives, and aligns meaning. |
| Agent(Sovereign) | MyWorld | Preserves identity, authority, founder gates, contracts, and ledger. |

## Orthogonal To Governance

Governance audit asks whether the contract had procedure: scope, receipts,
verification, DNA, and ledger evidence.

Persona audit asks whether the cognitive organs actually participated. A
contract can score high on governance and low on persona usage if it only fills
paperwork. A contract can also score high on persona usage but still fail
governance if evidence is missing.

## Score Examples

Wrapper score 1: a contract cites Claude + Codex fallback, Gemini/local worker,
or explicitly justifies a single-provider path.

Wrapper score 0: a contract assumes one provider with no fallback reasoning.

Retriever score 1: a contract cites an `rtrace_...` and positive
`signal_coverage`.

Retriever score 0: a contract mentions MemoryOS abstractly but does not use
retrieved accepted memory.

Router score 1: a contract cites a CapabilityOS recommendation and follows the
top route or documents a deviation.

Router score 0: a contract chooses tools directly without routing evidence.

Philosophy score 1: a contract cites GenesisOS critic output, branches,
alternatives, or escape vectors.

Philosophy score 0: a contract goes straight from prompt to implementation.

Sovereign score 1: operator authority is explicit, and vision-class decisions
show founder/operator gate evidence.

Sovereign score 0: a worker-mode agent silently absorbs a vision decision.

All V1 scores are advisory. They do not block dispatch or replace the
governance axis.
