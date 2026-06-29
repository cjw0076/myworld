# AIOS Hivemind v0 — design spec (grounded, team-reviewed)

> Founder: design the AIOS version of the verifier-settled, decomposition-based
> collective-intelligence ecosystem ("GIMPS for agentic power"). Grounded in the
> office-hour mechanism extraction ([[docs/AIOS_HIVEMIND_PROOFS.md]] §Office-hour) — NOT
> from weights. Each component maps a PAPER MECHANISM onto an EXISTING AIOS primitive.
> Unverified leads are flagged [VERIFY]. v0 = the smallest end-to-end falsifiable system.

## The one-paragraph shape

A **Quest** (open-ended goal) is decomposed into a **task DAG**; **agents** execute the
leaves; a per-leaf **verifier** settles correctness (and co-evolves against shortcuts); a
node's result, once USED downstream, pays its producer **backward** through the DAG
(bucket-brigade credit); a contribution is rewarded MORE when it is **novel** (its premises
don't intersect existing conclusions); failures are attributed local→upstream→structural and
trigger **minimal re-decomposition**; the whole history is a **Merkle transparency log**
(Certificate-Transparency, not a blockchain). The first deliverable is an **absorption-probe**:
does the hivemind beat a single strong agent on a *measurable* Quest, and how often does the
composition step fail.

## Component map — mechanism × AIOS primitive

| # | Component | Mechanism (paper) | Built on (AIOS primitive) |
|---|---|---|---|
| 1 | **Quest intake + decomposition** | Meta-Agent: planner → DAG of nodes with typed IO contracts + verification criteria; construction-time verification (simulate before dispatch) | `graph.claims` / `graph.edges_current` (0003) as the DAG; planner = an agent organ |
| 2 | **Leaf dispatch + execution** | — | the CQRS spine WE BUILT: `aios_command_api.write_command` (one-tx event+projection+outbox) → `aios_outbox_relay` (W1) → agent consumer |
| 3 | **Verifier settles leaf** | MASFT: verify at SEMANTIC goal level (+15.6%), not schema; "incorrect verification" is 9.1% of failures | per-domain checker: Lean (proofs) / test-suite (code) / measured outcome; a `verify` organ node in the DAG |
| 4 | **Verifier co-evolution** | Verification Horizon: 37.76%→1.31% via sample passing trajectories → detect new shortcut patterns → add to monitor set P → penalize → redeploy (Rice: no fixed verifier complete) | a recurring AIOS organ (like the dream/consolidation cycle); pattern set P persisted append-only |
| 5 | **Credit = bucket-brigade** | Economy of Minds: result USED downstream pays producer backward (`W_prev += bid`) = marginal contribution, zero central bookkeeping | `uri/src/lib/uri-ledger.ts` — already conservation (Σ=1), evidence-gated, no-jump 0.5. Add: pay along DAG edges on `claim_evidence` use |
| 6 | **Uncommon = computable** | D3MAS: contribution novel iff `Premise(v) ∩ Conclusion(w) = ∅ ∀ existing w`; credit multiplier ∝ low dependency in-degree (cut 47.3%→ +16.5%) | `graph.claim_relations` + `claim_evidence`: novelty = no incoming dependency edge from existing conclusions |
| 6b | **Uncommon-correct WITHOUT an oracle** [VERIFY] | peer-prediction: ISP (label-free, 2nd-order correlation, beats majority vote), RBTS, Numerai MMC | optional module for no-checker leaves — **pending Consensus verification before we rely on it** |
| 7 | **Composition / failure attribution** | Meta-Agent: local retry → upstream re-run → structural re-decompose. OPEN: which subgraph to rebuild is unspecified in all 5 papers | v0 algorithm below (§ composition); the genuinely novel hard part |
| 8 | **Transparency** | Certificate-Transparency (trusted operator + public proofs), NOT trustless consensus | the Merkle log we hardened: `deploy/akashic-worker` `/root` `/proof` `/verify` (append-stable) |
| 9 | **Goal-setting governance + sybil** | team finding: contribution-consensus = plutocracy/capture; consensus is a low-pass filter on novelty | v0: Quest-setting is OPERATOR-gated (founder/curator), NOT contribution-weighted vote. DAO governance deferred (research bet) |
| 10 | **Measurement** | absorption-probe (bare vs pooled, behavior-delta on fixed axes) | `absorption-probe` skill |

## The composition algorithm (v0 — our answer to the open problem)

On a leaf failure, attribute via the DAG:
1. **local** (inputs satisfied contracts, output failed verify) → retry the node (cheap).
2. **upstream** (an input violated its producer's contract) → re-run the producing subtree.
3. **structural** (no node attributable; the verified leaves don't compose to the parent's
   goal-level check) → **minimal re-decomposition**: take the failed parent node + only its
   direct unsatisfied children (via `claim_relations` edges), discard their claims, re-plan
   THAT subgraph only (not the whole DAG), re-dispatch. Bound re-decomposition depth; if a
   subgraph re-decomposes K times, escalate to operator (named stop condition, DNA #4).

This is the hardest, least-precedented piece — v0 is a concrete first cut to be measured,
not a solved claim.

## Gates (carried from AIOS DNA + the office-hour warnings)

- **Verifier is never static** (Verification Horizon / Rice): the co-evolution organ #4 is
  mandatory, not optional. A one-time verifier is the #1 architecture mistake.
- **Draft-first** (DNA #2): claims are `status='draft'` until verified; credit pays only on
  verified+used.
- **Append-only + provenance** (DNA #3/#5): Merkle log; every claim cites `claim_evidence`.
- **Operator override + named stops** (DNA #4/#6): re-decomposition depth bound; Quest-setting
  operator-gated until governance is solved.
- **No over-claim**: the absorption-probe may only re-show known ensemble/proof-search gains
  — verify externally before claiming the hivemind itself is the cause (global rule #2/#5).

## v0 falsifiable deliverable (the first thing to BUILD)

absorption-probe on ONE measurable Quest with checkable leaves (e.g. a multi-lemma Lean
theorem, or a multi-module coding task with a test oracle):
- **Arm A**: one strong agent solves the Quest end-to-end. Score.
- **Arm B**: Quest → DAG (#1) → leaves dispatched (#2) → verified (#3) → bucket-brigade
  credit (#5) → novelty-weighted (#6) → compose with #7 on failure.
- **Measure**: (a) does B beat A (closes more / faster / solves what A can't)? (b) the
  **composition-gap rate** — fraction of runs where all leaves verify but the Quest goal-check
  fails. (b) is the real research signal — it directly tests the hardest unsolved part.

If B doesn't beat A, or the composition-gap rate is high and un-improvable, the thesis is
falsified cheaply before any scale build. That is the point.

## What's reused vs new

REUSE (already built): CQRS spine (A1/W1/W2), `uri-ledger` conservation credit, Merkle log,
`graph.claims` DAG schema, absorption-probe. NEW (v0): planner→DAG organ, per-leaf verifier
+ co-evolution organ, bucket-brigade payment along edges, D3MAS novelty score, the
composition/re-decomposition algorithm. The novelty-without-oracle module (#6b) is gated on
verifying the peer-prediction leads.
