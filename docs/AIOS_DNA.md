# AIOS DNA v0

AIOS DNA is the constitutional invariant set for the AIOS control plane. It is
derived from ASC-0084 Hive deliberation, which converged on
`accept_with_dissent` after 5 rounds with proposer, critic, and extender
voices.

Source of truth:

- `hivemind/.runs/aios_dna_debate/final_state.md`
- `hivemind/.runs/aios_dna_debate/round_5/synthesis.md`
- `docs/contracts/ASC-0084-hive-debate-aios-dna.md`
- `docs/contracts/ASC-0105-aios-dna-canonical-spec.md`

## Preamble

1. **Scope**: These invariants govern the AIOS control plane's behavior. They
   do not govern provider internals, substrate implementation details, or
   external service policies.

2. **Security model**: Detection-first. The control plane records enough
   evidence to detect violations after the fact. Prevention at the substrate
   level is a deployment responsibility.

3. **Root of trust**: The operator (human or delegated agent pair) is the root
   of trust for each AIOS instance. The DNA defends against automated
   subsystems exceeding delegated authority, not against a compromised root.

4. **Prompt safety**: The control plane sanitizes prompts at construction time
   but does not guarantee model behavior. Substrate selection should account
   for model-level safety properties.

5. **Liveness**: The DNA prioritizes safety and accountability over speed.
   Every contract period must produce either a result artifact, a documented
   blocker, or an explicit stop decision. Indefinite deferral without
   documented blockers is an operational violation.

## Invariants

### Invariant 1: Decide before acting

Wording: No capability executes without an explicit execution decision

Drift: HIGH — substrate agentic evolution, decision granularity gap

Compliance test: Does every external tool invocation have a preceding
execution decision record?

Known pressure: Provider substrates may perform many internal steps behind one
AIOS-visible decision. If any provider substrate is observed making more than
10 tool calls within a single AIOS execution decision, open an amendment
deliberation for Invariant 1.

Enforcing contracts:

- `docs/contracts/ASC-0034-governance-action-policy-engine.md`
- `docs/contracts/ASC-0035-policy-gated-dispatch.md`
- `docs/contracts/ASC-0081-provider-fallback-execution-binding.md`
- `docs/contracts/ASC-0100-provider-reroute-not-avoidance.md`

### Invariant 2: Draft-first

Wording: Accept requires explicit review; no memory auto-accepted

Drift: HIGH — continuous learning, non-discrete memory models

Compliance test: Does every accepted memory have a preceding ReviewRecord with
non-empty content?

Known pressure: Continuous learning systems can blur the difference between
draft, review, and accepted memory. AIOS preserves review boundaries even when
substrates or future memory systems prefer seamless learning.

Enforcing contracts:

- `docs/contracts/ASC-0001-memoryos-hivemind-loop.md`
- `docs/contracts/ASC-0041-web-evidence-memory-review.md`
- `docs/contracts/ASC-0042-capability-observation-memory-import.md`
- `docs/contracts/ASC-0091-memoryos-auto-writeback.md`

### Invariant 3: No record destroyed

Wording: Audit entries immutable once written; compaction preserves
retrievability by hash; privacy-redaction tombstone exception (Inv 7
precedence)

Drift: MEDIUM — legal erasure (GDPR Art 17)

Compliance test: Does ledger replay detect any hash chain breaks or missing
records?

Known pressure: Privacy redaction and legal erasure can conflict with immutable
audit. AIOS resolves the conflict by allowing privacy-redaction tombstones
while preserving audit-chain continuity.

Enforcing contracts:

- `docs/contracts/ASC-0016-monitor-reconciliation-registry.md`
- `docs/contracts/ASC-0076-contract-closeout-reconciliation.md`
- `docs/contracts/ASC-0091-memoryos-auto-writeback.md`

### Invariant 4: Every loop has a named exit

Wording: Contracts declare stop conditions; unnamed failures trigger default
stop

Drift: LOW — calibration only

Compliance test: Does every contract have at least one named stop condition?
Does the default stop trigger on unnamed failures?

Known pressure: Autonomous loops can normalize stuck states if failure is not
named. AIOS treats documented blockers and explicit stop decisions as valid
outputs.

Enforcing contracts:

- `docs/contracts/ASC-0004-dispatch-watcher-and-state-machine.md`
- `docs/contracts/ASC-0011-control-plane-loop-policy.md`
- `docs/contracts/ASC-0029-persistent-control-loop.md`
- `docs/contracts/ASC-0096-control-plane-pingpong-provider-fallback.md`

### Invariant 5: Provenance chain

Wording: Every record carries derives_from / evidence_refs

Drift: LOW — grows more important, not less

Compliance test: Does every record in the audit trail have non-empty
`derives_from` or `evidence_refs`?

Known pressure: As AIOS coordinates more agents, unproven assertions become
more expensive. Provenance is the minimum handle that lets future agents decide
whether a record can be trusted.

Enforcing contracts:

- `docs/contracts/ASC-0003-dispatch-packet-enrichment.md`
- `docs/contracts/ASC-0013-workspace-instruction-index.md`
- `docs/contracts/ASC-0095-provider-output-projection.md`
- `docs/contracts/ASC-0102-dispatch-praxis-binding.md`

### Invariant 6: Operator override always possible

Wording: Except privacy boundary (Inv 7); privacy definitions founder-gated

Drift: MEDIUM — multi-stakeholder governance

Compliance test: Can the operator issue stop/hold/release at any point during
execution?

Known pressure: Multi-stakeholder deployments will complicate who counts as
operator. AIOS v0 keeps the root of trust explicit and preserves override
unless it would violate the privacy boundary.

Enforcing contracts:

- `docs/contracts/ASC-0004-dispatch-watcher-and-state-machine.md`
- `docs/contracts/ASC-0061-dispatch-escalate-recovery.md`
- `docs/contracts/ASC-0102-dispatch-praxis-binding.md`

### Invariant 7: AIOS never sends private-gated data

Wording: Scoped to control plane; founder-gated paths, secrets, raw private
exports excluded from dispatch, prompts, shared artifacts

Drift: LOW — tightens, doesn't loosen

Compliance test: Does a scan of dispatch packets and prompts find zero matches
against private-path patterns?

Known pressure: As AIOS gains web, provider, and project routing, the pressure
to include raw context grows. The DNA makes private-gated data exclusion a
control-plane invariant, not a per-agent preference.

Enforcing contracts:

- `docs/contracts/ASC-0030-capabilityos-web-research-route.md`
- `docs/contracts/ASC-0031-web-evidence-execution-loop.md`
- `docs/contracts/ASC-0062-peer-share-privacy-projection.md`
- `docs/contracts/ASC-0100-provider-reroute-not-avoidance.md`

### Invariant 8: Classify before committing

Wording: Reversibility assessed and recorded before external actions;
irreversible actions require explicit confirmation

Drift: LOW — well-established principle

Compliance test: Does every external action record have a
`reversibility_class` field? Do irreversible actions have an explicit
confirmation record?

Known pressure: AIOS can become more useful only by touching more external
state. The reversibility class determines whether an action can proceed,
requires confirmation, or must be held.

Enforcing contracts:

- `docs/contracts/ASC-0034-governance-action-policy-engine.md`
- `docs/contracts/ASC-0060-action-policy-scope-aware.md`
- `docs/contracts/ASC-0101-aios-production-praxis-gate.md`

## Invariant Interaction Map

| Pair | Relationship |
|---|---|
| Inv 3 ↔ Inv 7 | Conflict resolved: privacy (Inv 7) takes precedence; privacy-redaction tombstone preserves audit chain continuity |
| Inv 6 ↔ Inv 7 | Hierarchy: privacy boundary limits operator override; privacy definitions are founder-gated |
| Inv 1 ↔ Inv 8 | Related but independent: Inv 1 governs whether a decision exists; Inv 8 governs the quality of that decision for irreversible actions |
| Inv 2 ↔ Inv 5 | Composable: draft/review lifecycle generates provenance records |
| Inv 3 ↔ Inv 5 | Overlapping coverage: provenance is a schema constraint within the audit system, but conceptually independent (immutability vs. traceability) |
| Inv 4 ↔ Inv 6 | Semi-derivable: named exits automate what operator override could achieve manually; kept for proactive safety |

## Authority Model (v0.1 amendment — ASC-0174)

Added by ASC-0174 Hive deliberation (6 rounds, 3 voices, verdict
`proceed_authority_routed_management_plane`, founder-accepted 2026-05-15).
This amendment is append-only and does not modify Invariants 1–8; it adds the
vocabulary the invariants are enforced *through*.

Source of truth:

- `hivemind/.runs/observer_vs_executor_debate/final_state.md`
- `docs/contracts/ASC-0174-hive-debate-observer-vs-executor-reframe.md`
- `docs/discoveries/2026-05-15-hive-observer-vs-executor-debate-result.md`

### AIOS identity

AIOS is an **authority-routed management plane**. It is neither a passive
observer nor a universal executor. AIOS is active at the operating layer and
bounded at the product-artifact layer.

### Authority axes

Every AIOS action is classified along four axes:

| Axis | Question | Default |
|---|---|---|
| `record_authority` | Who owns the durable artifact? | AIOS-owned records are pre-fact gated; product-owned records are observed post-fact unless the repo delegates a hook |
| `schema_authority` | Who designed the format/UI shaping the artifact? | AIOS remains responsible for AIOS-authored schemas even when product repos fill them |
| `participation_authority` | Does AIOS assist / route / summarize / package / publish / improve this action? | AIOS may refuse participation even when it cannot block the external action |
| `override_authority` | Who can force a route despite a hold, with what ceremony? | Operator override remains possible (Invariant 6); high-risk overrides require structured receipts and extra confirmation |

### System-call surface

Long-running agentic work is expressed as ten AIOS system calls:

`observe` · `ingest` · `retrieve` · `route` · `challenge` · `execute` ·
`refuse` · `override` · `promote` · `close`

- `observe` — read emitted evidence without controlling the source
- `ingest` — create an AIOS-owned derived record from emitted evidence
- `retrieve` — ask MemoryOS for accepted context and negative evidence
- `route` — ask CapabilityOS for provider/tool/fallback/refusal choices
- `challenge` — ask GenesisOS for assumption mutation and discomfort
- `execute` — ask Hive to run a bounded provider envelope
- `refuse` — decline AIOS participation and provide allowed alternatives
- `override` — accept operator/founder override with structured receipt
- `promote` — turn a reviewed envelope into dispatch or accepted memory
- `close` — verify, record, and publish the next action

### Pre-fact vs post-fact rule

- AIOS-owned records and AIOS participation: **pre-fact gated**.
- Product-owned records: **post-fact observed**, unless the product repo
  explicitly delegates a pre-fact hook (ASC-0173 consent-emit pattern is the
  reference delegation primitive).
- Dangerous / full-access execution: an **opt-in system call** with operator
  grant and structured receipt — never the default identity of AIOS.

## Amendment Clause

This DNA is version 0, with the v0.1 Authority Model amendment above. Changes
require a Hive Mind deliberation (minimum 3 rounds) with documented evidence
that an existing invariant fails under a concrete scenario. Amendments are
append-only: the original invariant and deliberation evidence are preserved
alongside the new version.

## Dissent Register

These dissent points are not objections to the DNA's adoption. They are
documented disagreements that future DNA deliberations should revisit.

### D1: Detection-first security model is forensic, not protective

The DNA explicitly adopts a detection-first posture. This means violations are
detectable but not preventable at the DNA level. For privacy violations (Inv 7)
and irreversible action mistakes (Inv 8), detection after the fact may be
insufficient. Future DNA versions should evaluate whether these two invariants
need prevention guarantees.

Source: Critic, Rounds 2 and 5.

### D2: Review quality is unspecified

Invariant 2 requires "explicit review" but defines no independence requirement
or quality threshold. A single-agent self-review technically satisfies the
invariant. Operational policies should address review quality until the DNA
does.

Source: Critic, Rounds 2 and 5.

### D3: Privacy-redaction tombstone is untested

The tombstone mechanism (Inv 3 exception for Inv 7 precedence) introduces new
record types, precedence rules, and authority requirements. It has not been
implemented or tested. If the mechanism fails (hash reversibility, authority
exploitation), the Inv 3/7 conflict becomes unresolvable.

Source: Critic, Round 5.

### D4: Decision granularity will force early amendment

Invariant 1's "execution decision" does not specify recording depth. As LLM
substrates gain multi-step autonomous execution, the gap between AIOS-visible
decisions and substrate-internal actions will grow. Estimated timeline for
required amendment: 12-18 months.

Recommended trigger: if any provider substrate is observed making >10 tool
calls within a single AIOS execution decision, open a DNA amendment
deliberation for Invariant 1.

Source: Critic and Proposer, Rounds 3 and 5.
