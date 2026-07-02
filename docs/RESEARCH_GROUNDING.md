# Research grounding — the AIOS research spine

This is the single place that answers: **which AIOS design decisions come from which papers, and what did our own experiments (including the negatives) actually show?** The sources already exist — in docstrings, commit messages, and study docs — but were scattered and invisible to a reviewer. This doc collects them and makes each claim checkable by file path.

**Honesty rule for this doc:** negatives are first-class results. Where our own experiment falsified or narrowed a design idea (sheaf/H¹, pooling superiority), the negative is stated straight — not laundered into a win. Every citation below appears verbatim in the repo file it is attributed to; this doc surfaces the citation, it does not vouch for the external paper.

---

## Table 1 — Paper-grounded design decisions

Each row: a design decision, the source **as cited in the repo file**, what that source claims, where the decision lives in code, and whether we have independently verified it (vs. borrowed it as prior art).

| Design decision | Source (as cited in repo) | What the source claims | Where it lives (file) | Our verification |
|---|---|---|---|---|
| Elide old error traces from the prompt (self-conditioning defense, pillar 1) | [arXiv 2509.09677](https://arxiv.org/abs/2509.09677) | An LLM errs *more* after seeing its own past errors in context; persists in 200B+ models — scaling does not fix it | `scripts/aios_turn_loop.py` (`decondition_history`), `scripts/aios_head.py` (sampler) | Borrowed prior art — not re-tested on AIOS data |
| Route long-horizon tasks to a heavier reasoning model (horizon routing) | [arXiv 2509.09677](https://arxiv.org/abs/2509.09677) | Reasoning models evade self-conditioning and run far longer, so long-horizon work should go to a reasoning model | `scripts/aios_routing.py` (`classify_horizon`) | Borrowed prior art — untested internally |
| Force a re-plan when the loop stalls (plan-repair, pillar 3) | [arXiv 2604.11978](https://arxiv.org/abs/2604.11978) | 72.5% of long-horizon failures are process-level (planning / subplanning) | `scripts/aios_turn_loop.py` (`_plan_repair_note`, stall counter) | Borrowed prior art — untested internally |
| Periodically re-surface long-range constraints from memory (pillar 4) | [arXiv 2604.11978](https://arxiv.org/abs/2604.11978) | Catastrophic forgetting is the design-level 27.5% of long-horizon failures; start-of-run constraints fade | `scripts/aios_turn_loop.py` (constraint resurface), `scripts/aios_harness.py` (`make_memory_constraint_provider`) | Borrowed prior art — untested internally |
| Memory backbone = a graph whose nodes are pointers to files (plaintext/semantic tier) | LSFS [arXiv 2410.11843](https://arxiv.org/abs/2410.11843), MemOS [arXiv 2505.22101](https://arxiv.org/abs/2505.22101) | A semantic file system / memory hierarchy lets the header route to memory instead of holding it in context | `scripts/aios_semantic_fs.py` | Backbone **affirmed** by falsifying the sheaf alternative — see Table 2 rows 1–4 |
| Measure frustration *relative to a null*, never the raw nonzero H¹ | Aref & Wilson; PNAS 2011, [doi:10.1073/pnas.1109521108](https://doi.org/10.1073/pnas.1109521108) | Real signed graphs are essentially never perfectly balanced, so H¹≠0 is near-certain and uninformative | `scripts/aios_h1_agent_edges.py` (`frustration_vs_null`) | **Tested** — anchors the below-null verdict, Table 2 row 3 |
| Verify at the semantic *goal* level, not leaf schema; attribute composition failures local→upstream→structural | MASFT [arXiv 2503.13657](https://arxiv.org/abs/2503.13657), Meta-Agent [arXiv 2605.25233](https://arxiv.org/abs/2605.25233) | Semantic-goal verification +15.6%; "incorrect verification" is 9.1% of multi-agent failures; more verifier stages ≠ more correctness | `docs/AIOS_HIVEMIND_DESIGN.md` (#3, #7), `scripts/aios_hivemind_probe.py` | **Tested** — composition gap reproduced + closed, Table 2 row 5 |
| Credit flows backward through the execution path (bucket-brigade) | Economy of Minds [arXiv 2606.02859](https://arxiv.org/abs/2606.02859) | Result used downstream pays its producer backward → marginal contribution with zero central bookkeeping | `docs/AIOS_HIVEMIND_DESIGN.md` (#5) | Design, grounded — not yet run |
| Reward novelty = low dependency in-degree (uncommon = computable) | D3MAS [arXiv 2510.10585](https://arxiv.org/abs/2510.10585) | A contribution is novel iff its premises don't intersect existing conclusions; cutting redundancy +16.5% MMLU | `docs/AIOS_HIVEMIND_DESIGN.md` (#6) | Design, grounded — not yet run |
| The verifier must co-evolve; no static verifier is complete | Verification Horizon [arXiv 2606.26300](https://arxiv.org/abs/2606.26300) | 37.76% of "resolved" SWE-Bench were reward-hacked; a co-evolving monitor loop cut it to 1.31% (Rice: no fixed verifier is complete) | `docs/AIOS_HIVEMIND_DESIGN.md` (#4) | Design, grounded — not yet run |
| Optional label-free scoring for no-oracle leaves | ISP [arXiv 2510.01499](https://arxiv.org/abs/2510.01499) | Inverse Surprising Popularity uses 2nd-order cross-model correlation, provably beats majority vote, label-free | `docs/AIOS_HIVEMIND_DESIGN.md` (#6b) | **[VERIFY]** — flagged unverified in-repo, pending Consensus |
| Turn-loop / harness shape (ReAct, Reflexion, plan-execute, CodeAct, context-as-tool) | Scaffold [arXiv 2604.03515](https://arxiv.org/abs/2604.03515), Terminal agents [arXiv 2603.05344](https://arxiv.org/abs/2603.05344), Cat [arXiv 2512.22087](https://arxiv.org/abs/2512.22087), ACON [arXiv 2510.00615](https://arxiv.org/abs/2510.00615), OpenHands [arXiv 2511.03690](https://arxiv.org/abs/2511.03690) | Comparative loop mechanisms + context-compaction-as-tool for long-horizon agents | `docs/AGENT_LOOP_ARCHITECTURE.md`, `docs/AIOS_AGENT_ENGINEERING_STUDY.md` | Study corpus — informs harness design |
| Agent-behavior scoring / DescentNet targets | τ-bench [arXiv 2406.12045](https://arxiv.org/abs/2406.12045), TOUCAN [arXiv 2510.01179](https://arxiv.org/abs/2510.01179), Holistic Agent Leaderboard [arXiv 2510.11977](https://arxiv.org/abs/2510.11977) | Trajectory-level agent evaluation benchmarks | `docs/AGENT_BEHAVIOR_STUDY.md` | Study corpus — informs behavior scoring |

> Traceability: the hivemind arXiv ids (MASFT, Meta-Agent, Economy of Minds, D3MAS, Verification Horizon, ISP) appear verbatim in `docs/AIOS_HIVEMIND_PROOFS.md` (§Office-hour grounding); the design decisions built on them are documented in `docs/AIOS_HIVEMIND_DESIGN.md`.

---

## Table 2 — Our own experiments and verdicts

These are experiments *we* ran, with their artifacts. The sheaf park chain (rows 1–4) and hivemind v0 (row 5) are included as model examples of falsification-driven design: an idea was built, tested against real data, and narrowed or parked when the data said so.

| Claim tested | Method | Result (honest) | Artifact |
|---|---|---|---|
| Does H¹ sheaf cohomology give a real backbone for detecting composition gaps, beating naive baselines? | 9-node / 11-edge synthetic relative-measurement graph with one fault per triangle; 15/15 tests | **Mechanism sound but no free lunch:** H¹ is numerically identical to a least-squares edge residual (max diff 0.00e+00 — same projection); the bad *edge* is NOT uniquely localized (only the bad *cycle* is); H¹ only beats a per-edge threshold on sub-threshold distributed holonomy | `docs/AIOS_HIVEMIND_H1_GATE.md` Part A, `docs/aios_h1_gate_results.json`, `scripts/aios_h1_gate.py` |
| Does real AIOS memory even carry relative-measurement structure? | Probed 1,438 records (373 in `memoryOS/`, 1,065 in `~/.aios/`) for scalar-claim + relative-comparison edges | **0 / 1,438 (0.0%).** Records are prose decisions/observations, not typed comparable scalars → **sheaf/H¹ parked; backbone stays the semantic FS** | `docs/AIOS_HIVEMIND_H1_GATE.md` Part B |
| Counter-thesis: can a *live agent* INDUCE signed structure (agent = restriction map) so H¹ becomes non-trivial? | Local `qwen2.5:7b` judges nearest memory pairs (+1/−1/0); GF(2) frustration on typed-claim tier (74 nodes, 65 edges, 8 independent cycles) | **H¹ = 0 non-vacuously.** Corrected null-relative instrument: F_obs = 0 vs F_null_mean = 3.48 → **z = −2.36, p = 0.011, BELOW_NULL** — memory is *significantly more coherent than chance*, nothing for a sheaf to detect. Sheaf stays parked; organ repurposed as a dedup/supersede signal | `docs/AIOS_AGENT_INDUCED_H1_RESULTS.md`, `docs/aios_h1_agent_edges_CLAIMS_results.json`, `docs/aios_h1_agent_edges_REAL_results.json`, `scripts/aios_h1_agent_edges.py` |
| World-scale reframe: shared multi-tenant memory will have H¹≠0, so the sheaf detector is alive on the shared tier | Adversarial pressure-test (genesis-challenger) | **RE-INFLATION verdict (0.8).** Raw H¹≠0 is what the null *also* predicts (70-yr structural-balance theory in sheaf vocab); and tenant **isolation** forbids cross-tenant edges → aggregate H¹ = Σ(per-tenant) = 0. Parked at both tiers | `docs/AIOS_AGENT_INDUCED_H1_RESULTS.md` §"World-scale reframe" |
| Composition gap: does pooled+verified beat a single strong agent under equal compute? (hivemind v0) | `aios_hivemind_probe.py`, `qwen3-coder:30b`, equal budget; coding (pytest oracle) + Lean oracle; 4 runs, before/after controls | Composition gap is **real and decisive** (gap 1.0 under weak leaf contracts) and **CLOSEABLE** (1.0 → 0.0 when the interface contract is enforced at the leaf). **Pooling *superiority* NOT shown (honest negative):** on tasks below the single agent's ceiling, pooled only *ties* (1.0 = 1.0); Lean run degenerate (agent below the task floor) | `docs/AIOS_HIVEMIND_V0_RESULTS.md`, `scripts/aios_hivemind_probe.py` |
| **The headline claim: does the behavioral ledger measurably help an agent?** (ledger-on vs ledger-off A/B) | `scripts/aios_headline_ab.py`: 8 counter-prior coding tasks (3 TRAIN seed / 5 TEST, disjoint; leakage unit-tested), real ingest → `predict_behavior` guidance, `phi4-mini` (chosen for headroom — `qwen2.5-coder:7b` was above the battery's ceiling), N=40/arm, matched seeds, pre-registered single run | **Mixed — a mechanism-level finding.** Ledger **helps first-shot**: pass@1 0.45 → 0.60 (+33% rel.), fewer attempts, fewer tokens. Ledger **hurts feedback-retry**: within-budget solve 0.825 → 0.675 — the always-on guidance prefix anchors the model against the concrete oracle error (retry recovery 68% → 19%). Verdict: "carry forward what worked" is **supported for first-shot behavior and falsified as an always-on prefix during retry** → specific design correction: inject guidance on attempt 1 only. Caveats: small n, one 3.8B model, synthetic battery, no fixed-advice control arm | `docs/AIOS_HEADLINE_AB_RESULTS.md`, `docs/aios_headline_ab_results.json`, `experiments/headline_ab/tasks/` |

---

### Follow-up (2026-07-02) — the prescribed correction, tested (Arm C)

The headline verdict prescribed a fix: inject ledger guidance on **attempt 1 only**. Re-ran the same battery with a third arm — **C = ledger guidance on attempt-1 only, dropped on the oracle-feedback retry** — matched-seed vs A(bare)/B(always-on), phi4-mini, N=40/arm.

| Arm | solve (2-attempt budget) | pass@1 | mean attempts | out tokens |
|---|---|---|---|---|
| A — bare | **0.85** | 0.55 | 1.45 | 4907 |
| B — ledger always-on | 0.70 | **0.65** | 1.35 | 4281 |
| C — ledger attempt-1 only | 0.775 | 0.625 | 1.35 | **4200** |

**Confirmed (positive):** C beats B on every axis — solve 0.70→0.775, pass@1 ~held, tokens 4281→4200 (cheapest arm). The always-on-prefix harm reproduced (A 0.85 → B 0.70) and gating to attempt-1 recovered ~half of it. **Design rule landed: ledger guidance is injected on attempt 1 only, never as an always-on prefix** (`scripts/aios_headline_ab.py`, Arm C / `guidance_first_only`).

**Honest boundary (not laundered up):** even corrected, the ledger does **not** beat bare on within-budget solve (A 0.85 > C 0.775). Its genuine measured win is a **better and cheaper first shot** (pass@1 +0.07, −14% tokens vs bare), not a higher final solve rate. n=40, one 3.8B model, synthetic battery, single run.

**Next pivot (loop continues):** ledger still trails bare on final solve → the generic "what worked" prefix likely still mildly anchors. Candidate hypotheses: (a) retrieval-on-demand instead of a standing prefix; (b) difficulty-gated injection; (c) guidance = concrete failure-mode avoidance, not a generic pattern. Artifact: `docs/aios_headline_ab_C_results.json`.

---

## Section 3 — Deliberately design-chosen (not empirical claims)

These are engineering / organizational decisions. They are *not* validated results and should not be read as such — they are how we chose to build, adopted for consistency and safety, not because an experiment ranked them best.

- **The 7 DNA invariants** (recommendation-only, draft-first memory, append-only audit, named stop conditions, provenance chain, operator override, privacy boundary) — a governance choice. See `docs/AIOS_DNA.md`, enforced by `scripts/aios_dna_lint.py`.
- **5-OS decomposition** (HiveMind / MemoryOS / CapabilityOS / GenesisOS + the MyWorld control plane) — an organizational partition of responsibility, not an empirical optimum. See `docs/AIOS_NORTHSTAR.md`.
- **Contract → dispatch → result → ledger governance** — a process choice for cross-repo work. See `docs/AIOS_SMART_CONTRACT.md`, `scripts/aios_dispatch.py`.
- **Draft-first memory / no silent auto-accept** — a safety policy (DNA #2): every memory acceptance is an explicit reviewed object. See `memoryOS/`.
- **Capability routing is recommendation-only** — CapabilityOS recommends; it never silently executes or binds tools (DNA #1).

---

## Section 4 — The gap we know about (open)

- **Headline claim — "agents carry forward what worked → measurable lift" — now FIRST-MEASURED (mixed).** The controlled ledger-on/off A/B (Table 2, last row; `docs/AIOS_HEADLINE_AB_RESULTS.md`) found the lift is real for **first-shot** behavior (pass@1 +15pp) but the naive always-on injection **hurts** feedback-driven retry (within-budget solve −15pp, retry recovery 68%→19%). Open items: (1) implement + re-test the design correction (retry-aware injection: guidance on attempt 1 only), (2) a fixed-advice control arm to separate "memory content" from "any advice prefix", (3) replication on a stronger model and a non-synthetic battery.
- **Cross-agent transfer thesis is unvalidated.** The claim that one agent's accumulated ledger lifts a *different* agent needs a large corpus to test (≥10k entries for restriction-map / DescentNet learning). Current real memory scale is ~1.5k (1,438 records probed in the H¹ gate). Not enough yet.
- **Frontier-research anchors are borrowed, not re-verified.** The self-conditioning (arXiv 2509.09677) and process-level-failure (arXiv 2604.11978) results are external prior art we adopted; we have not re-run them on AIOS data. They are load-bearing for the turn-loop design and should be understood as such.
- **Most hivemind rows are built-but-unmeasured.** Only the composition-gap mechanism (Table 2 row 5) has been run. Backward credit, D3MAS novelty, verifier co-evolution are grounded in papers but not yet measured in AIOS; the ISP label-free scoring is explicitly `[VERIFY]` in-repo.
