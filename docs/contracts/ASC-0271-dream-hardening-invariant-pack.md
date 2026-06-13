---
contract_id: ASC-0271
slug: dream-hardening-invariant-pack
status: accepted
accepted: 2026-06-14T03:10:00+09:00
goal: Harden the ASC-0270 dream expansion map into bounded invariants, stop conditions, owner-bound follow-on contracts, and sequencing gates so AIOS can grow aggressively without becoming unsafe, vague, provider-locked, or local-demo-only.
created: 2026-06-14T02:35:00+09:00
parent: ASC-0270
origin: Claude hardening lane of ASC-0270. Codex opened the dream; Claude turns it into governed growth rails.
aux_ref: docs/contracts/ASC-0271-aios-growth-hardening-invariant-pack.md
---

# ASC-0271 Dream Hardening Invariant Pack

## Semantic Handshake

```text
semantic_handshake:
  contract_id: ASC-0271
  target_repo: myworld
  terms_confirmed:
    - AIOS smart contract
    - dispatch packet
    - memory draft
    - accepted memory
    - capability recommendation
    - provider route
    - stop condition
    - operator checkpoint
    - projection
  ambiguous_terms: []
```

## 1. Growth Invariants

These invariants let AIOS grow aggressively while preventing the four failure
modes named in ASC-0270: unsafe, vague, provider-locked, local-demo-only.

### 1.1 Memory Review Gate (anti-unsafe)

Every knowledge artifact entering MemoryOS through dream vectors (Dream Agora,
Provider Blindspot Harvesting, SMX loser branches, web/research intake) MUST
arrive as `memory_draft` with `review_status: draft`. No pathway from growth
vectors to `accepted_memory` without an explicit review record citing
`evidence_refs`.

Stop: `memory_auto_accepts_dream`

### 1.2 Capability Recommendation Boundary (anti-unsafe)

CapabilityOS growth (new tool routes, MCP server discovery, provider surfaces,
credential grant recommendations) produces `capability_recommendation` only.
Execution authority requires a separate contract dispatched to Hive Mind.
CapabilityOS NEVER executes, installs, or binds a tool directly.

Stop: `capabilityos_executes_tool`

### 1.3 Genesis Speculation Boundary (anti-unsafe)

GenesisOS growth (entropy quotas, SMX branching, recombination candidates,
discomfort injection) produces `speculative_only` artifacts. GenesisOS NEVER
selects final truth, commits a branch, or closes a contract. Selection requires
MyWorld operator decision with verification evidence.

Stop: `genesis_selects_final_truth`

### 1.4 Evidence-Bound Completion (anti-vague)

No growth vector may claim AIOS completion level advancement (L0-L6) without
matching evidence at that level per `AIOS_DEFINITION.md`. Dream prose is L0
(described). A follow-on contract is L1 (contractable). Growth claims above L1
require execution artifacts, verification results, or receipts.

Stop: `dream_becomes_unbounded_prose`

### 1.5 Provider Replaceability (anti-provider-lock)

Every growth vector that names a specific provider (Claude, Codex, Gemini,
local LLM, MCP server) must document what happens when that provider is
unavailable. The credential grant layer must support revocation and
replacement. No growth vector may create a hard dependency on a single
provider's API shape, auth flow, or sandbox model.

Stop: `provider_surface_becomes_aios_boundary`

### 1.6 Production Evidence Gate (anti-local-demo)

Growth vectors that create user-facing surfaces (Agent Company Studio, serving
UI, MemoryOS import product, credential grant UI, DeepIdeaChamber) may NOT
claim production readiness without:
- a visual target selected by operator,
- browser-verified proof at the claimed serving resolution,
- release gate assessment from `aios_serving_release_gate.py`,
- world readiness check from `aios_world_readiness.py`.

Stop: `world_ready_claim_without_release_proof`

### 1.7 Execution Receipt Binding (anti-unsafe, anti-vague)

Hive Mind work dispatched from growth vectors must produce durable receipts
(`aios.run_receipt.v1` or equivalent). Work without receipts cannot close a
contract, advance a completion level, or generate accepted memory.

Stop: `execution_without_receipt`

### 1.8 Privacy Boundary Preservation (anti-unsafe)

Growth does not override privacy gates. No dream vector may:
- copy raw credentials into dispatch packets or shared docs,
- expose `_from_desktop/`, `dain/`, `minyoung/` paths,
- paste raw provider logs into memory drafts,
- weaken existing credential redaction.

Stop: `raw_private_evidence_leak`

## 2. Owner-Bound Follow-On Contracts

The dream map's 8 growth vectors split across 5 OS repos. Each follow-on
describes the owner, the bounded slice, prerequisites, and which invariants
gate it.

### 2.1 MyWorld — Dream Governance Spine

| Field | Value |
| --- | --- |
| Owner | myworld |
| Slice | Control-plane contracts, dispatch, ledger, and release gates for all dream vectors |
| Prerequisite | ASC-0271 accepted |
| Invariant gates | 1.4, 1.6 |
| Completion target | L2 (dispatchable) |

Work: extend the contract/dispatch/ledger infrastructure to handle the dream
vectors as bounded contracts rather than unbounded prose. Ensure each dream
vector has a contract template, stop conditions, and verification schema before
Codex product work begins.

### 2.2 Hive Mind — SMX and Worker Scaling

| Field | Value |
| --- | --- |
| Owner | hivemind |
| Slice | Speculative Multiverse Execution (§3 of dream), sandbox isolation, worker queue, receipt enrichment |
| Prerequisite | ASC-0271 accepted; Hive already supports bounded provider-loop receipts |
| Invariant gates | 1.3, 1.7 |
| Completion target | L3 (executable) for single-branch SMX |

Work: implement bounded variant execution in isolated workspaces per dream
vector §3. Losers become counterfactual MemoryOS drafts (not auto-accepted).
Winners commit only after verifier scoring. Receipt labels include `failed`,
`degraded`, `recovered`, `false_success` per negative-evidence spec.

### 2.3 MemoryOS — Dream Agora Intake and Failure Memory

| Field | Value |
| --- | --- |
| Owner | memoryOS |
| Slice | Dream Agora draft pipeline (§1 of dream), failure memory schema (§4), Akashic records as asset base (§7) |
| Prerequisite | ASC-0271 accepted; MemoryOS already supports draft lifecycle |
| Invariant gates | 1.1, 1.8 |
| Completion target | L3 (executable) for draft intake; L4 (verifiable) for failure memory |

Work: add `source_receipt` → `memory_draft` intake path for web/research/
provider events. Add `failure_memory` draft schema with provenance fields per
negative-evidence spec. Retrieval must support negative-evidence queries when
the task context asks for risk or prior failure. All entries draft-first.

### 2.4 CapabilityOS — Route Observation and Credential Grant Schema

| Field | Value |
| --- | --- |
| Owner | CapabilityOS |
| Slice | Provider blindspot harvesting (§4 of dream), credential grant schema (§5), negative capability observation |
| Prerequisite | ASC-0271 accepted |
| Invariant gates | 1.2, 1.5, 1.8 |
| Completion target | L2 (dispatchable) for route observation; L1 (contractable) for credential grants |

Work: add classified observation path for provider friction events (refusal,
timeout, hallucination, credential friction, convergence). Add credential grant
schema with scope, expiry, injection target, receipt, and revocation fields.
Add negative capability observation labels per negative-evidence spec.
Recommendation-only: no execution authority.

### 2.5 GenesisOS — Entropy Quotas and Recombination Engine

| Field | Value |
| --- | --- |
| Owner | GenesisOS |
| Slice | Entropy quotas (§6 of dream), recombination candidate output (from negative-evidence spec), discomfort budget per release |
| Prerequisite | ASC-0271 accepted |
| Invariant gates | 1.3 |
| Completion target | L3 (executable) for entropy quota checks |

Work: formalize entropy quota as a verifiable gate: every release candidate
needs a GenesisOS discomfort budget result; every long task needs at least one
non-obvious branch; every consensus closeout needs a counter-branch. Output is
`speculative_only`. Selection remains with MyWorld operator.

## 3. Sequencing: Before vs After Serving UI Prototype

### Safe Now (before serving UI / visual target selection)

| Move | Why safe | Invariant check |
| --- | --- | --- |
| Dream Agora intake pipeline (MemoryOS) | Internal infrastructure; no user-facing surface | 1.1 |
| Provider blindspot harvesting (CapabilityOS) | Observation-only; no execution | 1.2 |
| Failure memory schema (MemoryOS) | Schema/draft work; no user data flow | 1.1, 1.8 |
| Entropy quota gates (GenesisOS) | Speculative-only checks; no user surface | 1.3 |
| SMX single-branch prototype (Hive Mind) | Internal execution; receipts required | 1.7 |
| Credential grant schema design (CapabilityOS) | Schema only; no credential injection | 1.5, 1.8 |
| Negative capability observation labels (CapabilityOS) | Metadata extension; no execution | 1.2 |
| Contract templates for dream vectors (MyWorld) | Control-plane docs; no implementation | 1.4 |
| Recombination candidate output format (GenesisOS) | Schema/spec; advisory only | 1.3 |

### Blocked Until Serving UI Evidence

| Move | What blocks it | Required evidence |
| --- | --- | --- |
| Agent Company Studio product surface | Visual target not selected; no browser proof | Operator selects design option; `aios_serving_design_gate.py select --confirmed-by-user`; browser screenshot at target resolution |
| MemoryOS import/review product UI | Same as above | Visual target; browser proof; user-flow verification |
| Credential grant UI (approval queue) | No serving surface exists to embed it | Serving UI prototype at 375/1280; release gate `met` for credential surface |
| DeepIdeaChamber productized surface | User-facing product; needs hosting proof | Serving UI prototype; world readiness partial |
| Distribution wedge #1 (end-user task workflow) | The foundational serving UI is the prerequisite | Serving UI prototype; release gate honest |
| "Company of agents" user-facing framing | Marketing without product evidence | At least one wedge shipped with user-verifiable artifacts |

### Sequencing Summary

```text
Phase 1 (now):  internal hardening — schemas, gates, observation paths, contract templates
Phase 2 (after visual target selection):  serving UI prototype with browser proof
Phase 3 (after serving proof):  product surfaces (Studio, import UI, credential UI, chamber)
Phase 4 (after ≥1 wedge shipped):  distribution claims and multi-tenant/world-ready framing
```

## 4. Dream Preservation Without Vague Prose

The dream map (`docs/discoveries/2026-06-14-aios-dream-explosive-expansion.md`)
is a valuable L0 artifact. To prevent it from decaying into unbounded prose:

1. Each dream vector has a corresponding follow-on contract (§2 above).
2. Each follow-on has a completion target level and invariant gates.
3. Dream prose that is not backed by a contract within 2 weeks should be
   flagged as `stale_dream` in the next operator checkpoint.
4. Dream vectors that produce implementation must advance at least one
   completion level with evidence; otherwise the implementation is premature.
5. The dream map itself is append-only — new vectors are added, old ones are
   not deleted but may be marked `superseded` or `blocked` with a reason.

## 5. Stop Conditions (consolidated)

| Stop Condition | Triggers On |
| --- | --- |
| `dream_becomes_unbounded_prose` | dream vector has no follow-on contract after 2 weeks |
| `memory_auto_accepts_dream` | any dream intake path auto-accepts memory |
| `capabilityos_executes_tool` | CapabilityOS directly executes instead of recommending |
| `genesis_selects_final_truth` | GenesisOS output treated as final without operator decision |
| `provider_surface_becomes_aios_boundary` | growth vector creates hard single-provider dependency |
| `world_ready_claim_without_release_proof` | production/world claim without release gate evidence |
| `execution_without_receipt` | Hive work closes without durable receipt |
| `raw_private_evidence_leak` | private data enters shared docs or dispatch |
| `apps_serving_implementation_before_visual_target` | `apps/serving/**` code created before operator selects design option |
| `claude_hardening_replaced_by_codex_patch` | Claude's invariant/gate work silently replaced by implementation |
| `credential_grant_injection_without_schema` | credentials injected into sandbox without grant schema |

## Verification

```bash
test -f docs/contracts/ASC-0271-dream-hardening-invariant-pack.md
grep -c "stop_condition\|Stop Condition" docs/contracts/ASC-0271-dream-hardening-invariant-pack.md
python3 scripts/aios_serving_release_gate.py assess --root . --json 2>/dev/null | python3 -c "import sys,json; d=json.load(sys.stdin); print('production_ready:', d.get('ready_for_production_serving', 'unknown'))" 2>/dev/null || echo "release gate: not changed by this contract"
```

Expected: contract file exists; stop conditions documented; production serving
remains not ready (this contract does not change serving state).
