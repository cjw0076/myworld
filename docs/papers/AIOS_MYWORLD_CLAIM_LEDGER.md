# AIOS MyWorld Paper Claim Ledger

Status: claim ledger for ASC-0098 (accepted 2026-05-18). As of 2026-05-18,
11 of 25 claims are `evidence_bound`; the remaining 7 `evidence_needed` claims
depend on matched-run benchmark data and 7 are explicitly held as `hypothesis`.
Claims are not manuscript-ready until backed by concrete repository evidence or
explicitly marked.

## Claim Status Labels

- `evidence_bound`: directly supported by cited repository artifacts.
- `hypothesis`: plausible framing, not yet verified enough for a paper claim.
- `blocked`: cannot be claimed without new evidence, external review, or
  operator approval.
- `evidence_needed`: likely claim, but source artifacts still need to be
  collected and linked.

## Seed Claims

| ID | Claim | Status | Evidence Needed |
| --- | --- | --- | --- |
| C-001 | AIOS defines agent work as a contract-bound loop rather than chat continuation. | evidence_bound | `docs/AIOS_DEFINITION.md`, `docs/AIOS_SMART_CONTRACT.md`; 206 `ASC-NNNN` contracts in `docs/contracts/` instantiate the proposed→accepted→closed loop |
| C-002 | `myworld` acts as the control plane and should not directly implement broad child-repo work. | evidence_bound | `AGENTS.md`, `CLAUDE.md`, `docs/AIOS_WORK_DISPATCH.md`; the control plane edits contracts, ledger, and `.aios/` dispatch state, not child-repo source — boundary stated and followed in `docs/AIOS_AGENT_LEDGER.md` decisions |
| C-003 | Hive Mind, MemoryOS, CapabilityOS, and GenesisOS have separate ownership boundaries. | evidence_bound | `docs/agents/HIVEMIND_AGENT.md`, `MEMORYOS_AGENT.md`, `CAPABILITYOS_AGENT.md`; each contract's `repos`/`Scope` block names the owning repo |
| C-004 | AIOS uses durable artifacts such as contracts, dispatch packets, ledgers, receipts, traces, and observations to make work reviewable across sessions. | evidence_bound | `docs/contracts/` (206 contracts), `docs/AIOS_AGENT_LEDGER.md` (append-only), 186 result packets under `.aios/outbox/`, per-repo worklogs |
| C-005 | Completion should be stated as levels from described through repeatable rather than claimed as vague progress. | evidence_bound | `docs/AIOS_DEFINITION.md`; `scripts/aios_readiness.py` emits L0–L6 checks and as of 2026-05-18 reports `level 6 (L6 repeatable), ready=True` with per-level evidence |
| C-006 | AIOS has demonstrated repeatable parts of the loop, but the full autonomous institution claim remains unsupported. | hypothesis | closed contracts, monitor state, governance readiness docs, adversarial review |
| C-007 | Local-first operation is a practical privacy boundary for high-context agent work. | hypothesis | privacy stop conditions, MemoryOS review policy, peer-share privacy projection |
| C-008 | Separating memory review from execution reduces the risk of silently accepting unreviewed context. | hypothesis | MemoryOS lifecycle docs, MemoryOS worklogs, contract stop conditions |
| C-009 | Capability routing and provider fallback can be treated as first-class audited system behavior. | evidence_bound | `docs/contracts/ASC-0203-chat-route-against-capabilityos-matrix.md` (routing reads the ranked CapabilityOS recommendation matrix); `scripts/aios_chat_router.py` provider-fallback path; CapabilityOS `recommend` route artifacts under `.aios/invocations/*/capability/route.json` |
| C-010 | GenesisOS adds a necessary divergence and pre-close challenge layer to prevent prompt-prison convergence. | hypothesis | GenesisOS contracts, divergence artifacts, pre-close challenge docs |
| C-011 | AIOS should be evaluated against direct provider CLI workflow using the same provider as executor, not against the provider as a competing model. | evidence_needed | `docs/papers/AIOS_AGENT_OPERATING_LAYER_DRAFT.md`, future matched-run benchmark receipts |
| C-012 | AIOS improves operational properties of long-running work: continuity, reliability, governance, recoverability, memory reuse, capability routing, and user visibility. | hypothesis | matched direct CLI vs AIOS runs, monitor receipts, restart/resume evidence, Control Center artifacts |
| C-013 | AIOS introduces measurable operational overhead through contracts, artifacts, checkpoints, false holds, and user cognitive load. | evidence_needed | artifact counts, task timing, monitor false checkpoint counts, user-facing friction notes |
| C-014 | AIOS dogfooding can convert operating-layer friction into contracts, tests, receipts, and memory drafts. | evidence_bound | `docs/contracts/ASC-0157`, `ASC-0158`; ASC-0202 was drafted directly from an operator verification gap found while closing ASC-0194, with tests and a ledger receipt — friction-to-contract conversion observed in-session |
| C-015 | MemoryOS retrieval usefulness should be evaluated by whether provenance-bearing context improves restart/resume quality or reduces repeated prompting. | evidence_needed | `rtrace_7124ea1c1fee8eff`, matched restart/resume runs, selected-memory usage records |
| C-016 | CapabilityOS route accuracy should be evaluated as route-to-artifact fit rather than provider success alone. | evidence_needed | `.aios/invocations/asc-0160-paper-refinement/capability/route.json`, future task route labels |
| C-017 | GenesisOS reviewer attacks are useful only if they cause paper edits, claim downgrades, or benchmark tasks. | evidence_needed | `.aios/invocations/asc-0160-paper-refinement/genesis/branches.json`, reviewer-pass diffs |
| C-018 | AIOS should be positioned as adjacent to multi-agent orchestration and durable workflow systems, not as the first such system. | evidence_bound | `docs/papers/AIOS_RELATED_WORK_SOURCE_RECEIPT.md`, AutoGen, LangGraph, CrewAI, Temporal, Cloudflare sources |
| C-019 | AIOS's narrower related-work boundary is local provider-CLI operation with contracts, receipts, memory review, capability routing, and closeout ledgers. | evidence_needed | source receipt plus internal AIOS contracts and matched workflow examples |
| C-020 | AIOS needs negative evidence, not only success memories, because agent work absorbs weakly labeled patterns where bad memories and bad tools are reusable signals. | hypothesis | future negative-evidence contract, failed route observations, MemoryOS draft review records |
| C-021 | GenesisOS should be evaluated as a combinatorial creativity layer that turns failure memory, bad-tool observations, founder patterns, and distant analogies into candidate worldlines. | hypothesis | `docs/AIOS_NEGATIVE_EVIDENCE_AND_COMBINATORIAL_CREATIVITY.md`, `.aios/invocations/asc-0163-negative-evidence-creativity/genesis/branches.json`, future promoted/rejected recombination candidates |
| C-022 | AIOS learning claims require both negative evidence preservation and a verification seed showing whether a creative recombination candidate became useful work. | evidence_needed | ASC-0163 receipts, child repo implementation packets, benchmark negative-evidence trace table |
| C-023 | MemoryOS actively governs the growth of its knowledge graph: a seven-stage memory-graph control model runs during idle dream cycles, so the queryable surface stays O(communities) rather than O(nodes) even as the append-only graph grows without bound. | evidence_bound | `docs/contracts/ASC-0194-memoryos-graph-control-model.md`, `docs/contracts/ASC-0202-graph-control-real-work-within-budget.md`; memoryOS commit `91b6be7`; a live run on the ~198K-node store completes within the dream budget, emits `bound_ratio` and `queryable_surface_count`, and halts on named failure modes (`duplicate_proliferation`, `semantic_drift`) |
| C-024 | AIOS chat routing is two-tier: a fast local-LLM pre-router classifies intent, and a post-generation LLM-as-judge quality gate escalates a misrouted cheap turn once to a stronger model. | evidence_bound | `docs/contracts/ASC-0192-aios-interface-two-tier-routing.md`, `ASC-0193-chat-tier2-quality-gate.md`, `ASC-0203-chat-route-against-capabilityos-matrix.md`; `scripts/aios_chat_router.py`; tier-2 live smoke confirmed deterministic catch, LLM-judge catch on an off-topic answer, and no false escalation on an adequate answer |
| C-025 | Operator visibility is a first-class read projection: AIOS surfaces a multi-agent roster (per-agent status digest, out-of-band blocked/needs-input channel) and a five-column contract-lifecycle board, derived from existing state rather than a second store. | evidence_bound | `docs/contracts/ASC-0204-aios-multi-agent-roster-surface.md`; `scripts/aios_control_snapshot.py` (`build_roster`, `build_contract_board`); `apps/control/` render; `tests/test_aios_control_snapshot.py` |

## Downgrade Rules

- If a claim has no source artifact, it stays out of the manuscript body or is
  marked as a hypothesis.
- If a source artifact is only a design note without execution evidence, do not
  phrase the claim as implemented.
- If a claim depends on raw private data, provider auth, or unstated chat
  memory, mark it `blocked`.
- If a claim describes autonomy, production readiness, safety, or governance
  authority, require adversarial review before `evidence_bound`.

## Next Evidence Collection

ASC-0098 should next collect:

1. MemoryOS context pack and retrieval trace.
2. CapabilityOS paper route recommendation.
3. GenesisOS framing divergence and unsupported-claim critique.
4. Hive synthesis/adversarial review after the first three artifacts exist.
