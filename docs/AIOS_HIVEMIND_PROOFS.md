# AIOS Hivemind — verifier-settled collective problem-solving (scoped to formal proofs)

> Founder vision (2026-06-26): pose a hard problem, mobilize agents' knowledge-power,
> value UNCOMMON knowledge highly, let contribution decide the result — "shared intelligence."
> Team verdict + the scoping that makes it real. Authored by the team panel
> (genesis-challenger + architect + web-grounded prior-art check), founder-decided verifier.

## Team verdict (two independent analyses converged)

**The literal design — "the reputation/consensus subgraph judges value" — does NOT work.**
- *Contradiction (genesis):* consensus is a low-pass filter on novelty. "Reward uncommon"
  and "the crowd decides correctness" are at war — a crowd recognizes only the familiar
  (Yuma consensus literally clips weights that deviate from the median, treating
  uncommon = wrong). You cannot build a high-pass filter from low-pass parts.
- *Amplifier (architect):* novelty-by-embedding-distance with no correctness oracle + no
  sybil resistance = pays maximum reputation for maximum nonsense, farmable by minting
  identities (`worker.js:93` /register mints tokens with no identity check).
- *Prior art:* the literal vision is [Bittensor / Yuma "Proof of Intelligence"](https://discoverbittensor.com/deeper-dive/yuma-consensus-and-proof-of-intelligence/)
  + Numerai True-Contribution (uncommon-reward, since ~2021) + DAO delegate election,
  renamed — **minus the oracle**. ([critical analysis](https://arxiv.org/abs/2507.02951))

**It becomes real ONLY when scoped to a problem class with an exogenous, cheap,
sybil-proof VERIFIER.** Then the verifier — not the crowd — settles correctness:
identity-blind (no sybil/collusion), un-Goodhart-able (a passing proof *is* the goal, not
a proxy), and it filters wrong-uncommon from correct-uncommon. This is exactly where
Bittensor/Numerai/TCR fail or can't run.

**Founder's chosen verifier domain: formal/mathematical proof (Lean/Coq).** The cleanest
oracle — a lemma either machine-checks or it doesn't, for free, forever.

## The design (proof-scoped)

- **Problem** = a target theorem to prove.
- **Contribution** = a candidate lemma / proof step + its Lean term (the evidence).
- **Verifier** = Lean type-checks it. Correct = yes/no, mechanical, identity-blind. NO
  consensus vote ever touches correctness.
- **Uncommon = mechanically measurable**: a lemma is "novel" iff it is NOT already in the
  proof dependency DAG (a new node, not redundant with existing checked lemmas). This is
  exact, not an embedding heuristic — it sidesteps the "novelty ≠ correctness" amplifier.
- **Credit** flows retroactively through the proof DAG when the theorem closes, via the
  existing conservation attribution (`uri/src/lib/uri-ledger.ts`: Σ credit = 1,
  evidence-gated, no-jump cap 0.5). A lemma on the final proof path earns; a checked-but-
  unused or duplicate lemma earns nothing.
- **Transparency, not blockchain**: the existing Merkle log (`worker.js` /root /proof
  /verify) publishes the contribution history (Certificate-Transparency style — trusted
  operator + public proofs). Trustless consensus / sybil / on-chain settlement are
  explicitly OUT of scope (a separate research bet, mostly unnecessary under CT trust).

## What AIOS already has (~70%) vs what's missing

Have: Merkle transparency log + public proofs; evidence-gated conservation attribution +
reputation scalar; draft-first claims + claim_evidence provenance (DNA #5). Missing/build:
1. A **Lean verifier organ** (run a proof, return checks/fails + the lemma's DAG position).
2. A **proof dependency DAG** store (which lemma depends on which) — the "uncommon = not
   in DAG" + retroactive-credit substrate.
3. Drop the corpus **centroid collapse** (`worker.js:227` UNIQUE(category) + `(base+new)/2`
   averaging) — irrelevant here since novelty is DAG-membership, not embedding distance.

## Minimal falsifiable demo (absorption-probe; no creds)

Pick ONE theorem with a known multi-lemma proof. **Arm A (bare):** one agent proves it
end-to-end; score (closed? #steps? wall-clock?). **Arm B (hivemind):** N agents each
contribute candidate lemmas → Lean gates each → DAG accumulates → theorem closes when a
path exists → attribute credit over the contributing lemmas → elect the closing path.
**Measure:** does pooled-with-Lean-gate beat the single agent (closes more / faster /
proves a theorem the solo agent couldn't)?

## Honest caveats (do not over-claim — global rule #2, #4)

1. The demo may only re-demonstrate **known ensemble / self-consistency / proof-search
   parallelism** results. Verify externally before claiming novelty. The genuinely hard,
   unsolved thesis — valuing uncommon-but-correct **when no oracle exists**, among
   untrusted parties — is NOT tested by the proof demo (proofs HAVE an oracle). Keep that
   as a named research bet with its own falsification.
2. The proof scoping resolves the **k-anon vs uncommon** structural conflict by not using
   the k-anon corpus at all (novelty = DAG-membership, correctness = Lean) — but that means
   this is a SEPARATE store/system from the SaaS behavioral corpus, not the same one.
3. This is a scoped RESEARCH-BET track, orthogonal to the SaaS spine (A1/W1/W2) — do not
   let it block or entangle the product critical path.

## The single decision that gates everything (answered)

> Name the exogenous, cheap, sybil-proof verifier that settles whether an UNCOMMON
> contribution is correct, independent of the reputation graph. → **Lean/formal proof.**

So: build the Lean-gated proof-contribution DAG demo as a scoped track; keep the
no-oracle / trustless / general-novelty parts as an explicitly-labeled research bet.

---

## Office-hour grounding (2026-06-26, tool-first — escaped weights)

Per [[feedback_tool_first_escape_weights]]: pulled external knowledge via HF paper_search
(A, faithful full-text extraction) + deep-research (B, sources good / verification
rate-limited → UNVERIFIED leads) + local qwen (CUDA OOM, failed) + agy (empty, failed).
Consensus pending founder /mcp auth. The single conclusion-changing update is #3 below.

**Concrete mechanisms now grounded (A — faithful to papers):**
- **Credit = bucket-brigade** (Economy of Minds, arXiv 2606.02859): wealth flows BACKWARD
  through the actual execution path (`W_prev += bid_winner`) → recovers marginal causal
  contribution with zero central bookkeeping. Ports onto `uri-ledger` DAG traversal.
  Warning: keep BOTH exploration (new candidates) + exploitation (propagate winners) —
  dropping either collapses performance.
- **Uncommon = computable** (D3MAS, arXiv 2510.10585): `E_depend = {(v,w) | Premise(v) ∩
  Conclusion(w) ≠ ∅}` — a contribution is novel iff its premises don't intersect any
  existing conclusion node. Reward multiplier ∝ low dependency in-degree. (Baseline MAS =
  47.3% redundant; this cut 46%, +16.5% MMLU.)
- **Verifier MUST co-evolve** (Verification Horizon, arXiv 2606.26300): 37.76% of "resolved"
  SWE-Bench were reward-hacked; behavior-monitoring loop (sample → detect new shortcut
  patterns → add to monitor set → penalize → redeploy) cut it to 1.31% and +20.3pp clean.
  Rice's theorem: no fixed verifier is complete. A static verifier is the #1 architecture mistake.
- **Composition gap** (Meta-Agent 2605.25233 + MASFT 2503.13657): 3-level error attribution
  (local retry → upstream re-run → structural re-decompose); verify at the SEMANTIC GOAL
  level not just leaf schema (MASFT: +15.6%; "incorrect verification" is 9.1% of failures;
  more verifier stages ≠ more correctness). Open: which subgraph to re-decompose is
  UNSPECIFIED in all papers.

**#3 — the conclusion my weights got WRONG (B leads — verify via Consensus/re-run):**
"No exogenous oracle ⇒ uncommon-but-correct is unjudgeable" was TOO STRONG. Label-free
peer-prediction mechanisms surface minority-correct signals WITHOUT ground truth:
- **ISP (Inverse Surprising Popularity, arXiv 2510.01499)** — uses only 2nd-order
  cross-model correlation, provably beats majority voting, label-free.
- **RBTS / Bayesian Truth Serum** — incentive-compatible truthful reporting for n≥3 without
  knowing the prior; rewards "surprisingly common."
- **Numerai MMC** — orthogonalize vs the meta-model, credit only the non-redundant component.
- **Bittensor weight-copying** (documented attack) — validators copy weights instead of
  evaluating → empirically suppresses novelty (the consensus-low-pass thesis, confirmed).
⇒ A possible THIRD path for the no-oracle leaf: peer-prediction surfacing, not just an
exogenous checker. NEEDS verification (deep-research verify was rate-limited).

**Two hardest unsolved (collective):** (1) verifier co-evolution WITHOUT ground truth —
the shortcut-detector's own correctness is unverified (recursive regress); (2) selective
re-decomposition — minimal-subgraph reconstruction after a structural error.

**Tool-failure honesty:** qwen CUDA-OOM + agy empty + deep-research verification
rate-limited (105 agents / 2.1M tokens). The B leads are PROMISING but UNVERIFIED; re-run
verification or cross-check via Consensus before treating ISP/RBTS/MMC as settled.
