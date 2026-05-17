# AIOS MyWorld Paper Charter

Status: seed charter for ASC-0098.

## Operator Intent

Write a paper using AIOS, with the full `myworld` repository ecosystem as the
subject.

## Working Title

AIOS: An Agent Operating Layer for Reliable Long-Running AI Work

## One-Sentence Thesis

AIOS does not replace provider CLIs; it turns them from one-shot executors into
a persistent, governed, inspectable, memory-bearing operating loop for
long-running agentic work.

## System Under Study

The paper treats the repository as a living system:

- `myworld`: control plane, contracts, dispatch, monitor state, global ledger,
  operator checkpoints.
- `hivemind`: execution, scheduling, provider wrapping, proofs, verification,
  adversarial synthesis.
- `memoryOS`: memory, context packs, provenance, retrieval traces, review
  lifecycle.
- `CapabilityOS`: capability maps, routes, provider/tool recommendations,
  fallback plans.
- `GenesisOS`: divergence, assumption mutation, semantic alignment, pre-close
  challenge surfaces.

## Core Claims To Prove Or Downgrade

1. AIOS is not a chat wrapper; it is a contract-bound operating loop.
2. Separating execution, memory, capability routing, divergence, and control
   plane duties reduces silent scope drift.
3. Durable artifacts such as contracts, receipts, ledgers, traces, and claim
   downgrades make agent work reviewable across sessions.
4. Local-first operation provides a practical privacy and provenance boundary
   for high-context personal or organizational AI work.
5. The current repo demonstrates repeatable parts of the loop, but not a fully
   autonomous general-purpose AI institution.

## Likely Contribution Shape

- A system model for contract-bound multi-agent operating loops.
- A repository-backed architecture separating MyWorld, Hive Mind, MemoryOS,
  CapabilityOS, and GenesisOS roles.
- A completion-level ladder from described to repeatable, plus later governance
  readiness layers.
- A dispatch and receipt discipline for turning broad goals into auditable
  work packets.
- A limitations-first case study of building AIOS with AIOS.

## Evidence Plan

Primary evidence should come from:

- AIOS definition and north-star documents.
- Smart contracts and dispatch packet history.
- Agent ledger entries.
- Monitor, round-controller, and provider fallback receipts.
- MemoryOS retrieval traces and review lifecycle records.
- CapabilityOS route recommendations and observations.
- Hive synthesis, verification, and adversarial review artifacts.
- GenesisOS divergence/challenge artifacts.

Every major paper claim should be entered into a claim ledger as one of:

- `evidence_bound`: directly supported by repository artifacts.
- `hypothesis`: plausible but not yet verified.
- `blocked`: cannot be claimed without new evidence or operator approval.

## Initial Outline

1. Abstract
2. Introduction: why chat continuity is not enough for serious agent work
3. Problem statement: ephemeral agents, hidden context, tool drift, weak
   verification, and memory ambiguity
4. AIOS model: stateful operating loop rather than rigid pipeline
5. Architecture: MyWorld, Hive Mind, MemoryOS, CapabilityOS, GenesisOS
6. Artifact protocol: contracts, work packets, receipts, ledgers, traces,
   observations, and memory drafts
7. Case study: the MyWorld repository as a self-hosted AIOS build loop
8. Evaluation: direct provider CLI workflow versus AIOS-wrapped provider CLI,
   including operational overhead
9. Limitations and failure modes
10. Related work placeholders
11. Future work
12. Conclusion

## Immediate Next Step

Accept or revise ASC-0098, then dispatch the first three parallel packets:
MemoryOS context pack, CapabilityOS route recommendation, and GenesisOS framing
divergence. Hive synthesis should wait until those artifacts exist.
