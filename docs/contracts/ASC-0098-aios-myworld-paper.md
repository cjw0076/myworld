---
contract_id: ASC-0098
slug: aios-myworld-paper
status: proposed
goal: Produce an evidence-bound research paper about the full MyWorld AIOS repository ecosystem, treating myworld as the control plane and child repos as owned execution, memory, capability, and divergence layers.
created: 2026-05-13 KST
accepted: pending
closed: pending
origin: founder direction 2026-05-13 KST: "AIOS로 논문을 쓸거야. 주제는 myworld 레포 전체"
---

# ASC-0098 AIOS MyWorld Paper

## Why Now

The repository has crossed from scattered architecture notes into an inspectable
AIOS ecosystem: contracts, dispatch, monitor state, MemoryOS review flow,
CapabilityOS routing, Hive execution, Genesis divergence, provider fallback,
and local control surfaces. That makes it possible to write a paper about the
system as a whole without pretending every surface is complete.

The paper must be grounded in repository evidence. It should not overclaim that
AIOS is generally autonomous, production-ready, or externally validated unless
the repo contains verification receipts for that claim.

## Paper Thesis Seed

AIOS is a local-first, contract-bound operating loop for AI agent work. Its core
contribution is not another agent framework, but a control-plane discipline:
user goals become scoped contracts; memory, capabilities, execution, divergence,
verification, and learning are owned by separate cooperating OS layers; and
progress is measured by durable evidence rather than chat continuity.

## Scope

repos:

- `myworld`
- `hivemind`
- `memoryOS`
- `CapabilityOS`
- `GenesisOS`

allowed_files:

- `docs/papers/**`
- `docs/contracts/ASC-0098-aios-myworld-paper.md`
- `docs/discoveries/**` only for paper-specific synthesis notes
- `docs/evidence/**` only for paper-specific receipts
- child repo docs and worklogs as read-only source evidence
- child repo source/tests as read-only source evidence

forbidden_files:

- `.env`
- `.aios/**` except summarized receipt ids and non-sensitive state summaries
- `hivemind/data/**`
- `memoryOS/data/**`
- `uri/node_modules/**`
- raw exports, private history stores, provider auth files, and secret material
- broad child-repo implementation changes

## Per-OS Responsibility

### myworld.must_produce

- paper charter and outline under `docs/papers/`
- claim ledger mapping each paper claim to repository evidence
- final manuscript draft or checkpoint identifying what evidence is missing
- contract closeout with next line for the following writing or validation step

### memoryos.must_produce

- context pack of accepted AIOS memories, prior decisions, and provenance
- retrieval trace showing which MemoryOS records shaped the paper
- draft memory candidates only for new reusable paper insights
- privacy diagnostics for any source material that should stay local-only

### capabilityos.must_produce

- route recommendation for paper work: local repo search, citation policy,
  optional web prior-art route, fallback plan, and risk notes
- capability observation if any external research, PDF tooling, model, or
  provider route materially affects the manuscript

### genesisos.must_produce

- divergence memo with at least three possible paper framings
- prompt-prison critique that identifies seductive but unsupported claims
- pre-close challenge surface before a manuscript is called ready

### hivemind.must_produce

- synthesis run that turns MyWorld, MemoryOS, CapabilityOS, GenesisOS, and Hive
  evidence into a paper outline and claim hierarchy
- adversarial review of the thesis, contributions, limitations, and evaluation
- verification receipt for manuscript claims against repository artifacts

## Work Packets

### WP-0098-A — MemoryOS paper context pack

- target_agent: codex
- target_repo: memoryOS
- status: issued
- issued: 2026-05-13
- accepted: pending
- closed: pending
- depends_on: none
- brief: |
    Build a paper-specific MemoryOS context pack for ASC-0098. Use accepted
    AIOS memories, prior decisions, provenance records, review lifecycle docs,
    and relevant worklog entries. Do not import raw private exports. Return a
    retrieval trace and privacy diagnostics suitable for citation in a paper
    claim ledger.
- result: pending

### WP-0098-B — CapabilityOS paper route

- target_agent: codex
- target_repo: CapabilityOS
- status: issued
- issued: 2026-05-13
- accepted: pending
- closed: pending
- depends_on: none
- brief: |
    Recommend the capability route for writing an evidence-bound AIOS paper.
    Cover local repo search, source citation policy, optional web prior-art
    research, provider/model choices, fallback routes, and risks. CapabilityOS
    must recommend only; Hive executes if external research is approved.
- result: pending

### WP-0098-C — GenesisOS framing divergence

- target_agent: codex
- target_repo: GenesisOS
- status: issued
- issued: 2026-05-13
- accepted: pending
- closed: pending
- depends_on: none
- brief: |
    Produce at least three paper framings for the full MyWorld AIOS ecosystem,
    then critique prompt-prison risks and unsupported claims. Mark speculative
    branches clearly. Return contract seeds or challenge notes only; do not
    execute implementation or accept memory.
- result: pending

### WP-0098-D — Hive paper synthesis and adversarial review

- target_agent: codex
- target_repo: hivemind
- status: issued
- issued: 2026-05-13
- accepted: pending
- closed: pending
- depends_on: WP-0098-A, WP-0098-B, WP-0098-C
- brief: |
    After MemoryOS, CapabilityOS, and GenesisOS return their artifacts,
    synthesize an evidence-bound paper outline, contribution list, limitation
    list, and verification plan. Run an adversarial review that downgrades
    unsupported claims. Return a receipt and claim hierarchy for myworld.
- result: pending

### WP-0098-E — myworld manuscript assembly

- target_agent: codex
- target_repo: myworld
- status: issued
- issued: 2026-05-13
- accepted: pending
- closed: pending
- depends_on: WP-0098-D
- brief: |
    Assemble the first manuscript draft under `docs/papers/` from the verified
    claim hierarchy. Include abstract, introduction, system model, architecture,
    evaluation/evidence, limitations, related work placeholders, and future
    work. Every major claim must link to repository evidence or be marked as a
    hypothesis.
- result: pending

## Verification Gate

Pass when all are true:

- `docs/papers/AIOS_MYWORLD_PAPER_CHARTER.md` exists.
- A claim ledger exists under `docs/papers/` and every major paper claim is
  labeled `evidence_bound`, `hypothesis`, or `blocked`.
- MemoryOS context, CapabilityOS route, GenesisOS divergence, and Hive
  synthesis artifacts are linked from this contract.
- The manuscript draft does not cite raw private data, secrets, provider auth,
  or unstated chat memory.
- An adversarial review identifies unsupported claims and the manuscript either
  downgrades or removes them.

## Stop Conditions

- `scope_violation`
- `privacy_violation`
- `raw_private_data_requested`
- `unsupported_autonomy_claim`
- `missing_memoryos_context`
- `missing_capabilityos_route`
- `missing_genesis_challenge`
- `missing_hive_verification`
- `operator_checkpoint_required`

## Receipts

Pending.
