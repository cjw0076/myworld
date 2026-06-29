# Agent-Induced Consistency H¹ — real-memory results (founder #1 gate)

> Tests the founder's counter-thesis to the parked sheaf decision
> ([[project_memory_backbone_decision]] / `docs/AIOS_HIVEMIND_H1_GATE.md`): prose AIOS
> memory has 0/1438 *relative-measurement* structure, BUT a **live agent** could INDUCE
> structure by judging pairs (the agent IS the restriction map), emitting a SIGN per near
> pair (supports +1 / contradicts −1 / unrelated 0). If the induced SIGNED graph has a
> **frustrated cycle** (sign-product −1 around a loop — A⊕B⊕C inconsistent), that is genuine
> non-trivial H¹ over the O(1)/sign sheaf, which would justify the sheaf backbone for THAT
> edge type. Instrument: `scripts/aios_consistency_edges.py` (live-agent signed edges) +
> `scripts/aios_h1_agent_edges.py` (frustration via direct GF(2) fundamental-cycle holonomy;
> verdict `count>0 ⟺ unbalanced` is basis-invariant). Judge: **local** `qwen2.5:7b` (DNA #7 —
> judging memory pairs must never egress to a cloud model). Embeddings: local nomic-embed.

## Runs

| run | corpus | nodes (signed) | signed edges (S/−) | indep. cycles | frustrated | verdict |
|---|---|---|---|---|---|---|
| 1 | full store (300, log-heavy) | 16 | 10 (7 / 3) | **0 (forest)** | 0 | TRIVIAL_H1 (**vacuous**) |
| 2 | typed claims (186: decision+observation) | 74 | 65 (50 / 15) | **8** | **0** | TRIVIAL_H1 (**non-vacuous**) |

Tallies — run 1: 150 judged → 7 supports / 3 contradicts / 140 unrelated. run 2: 600 judged
→ 50 / 15 / 535. (~89–93% of even embedding-NEAREST pairs judged "unrelated" in both.)

## Reading (honest)

1. **The mechanism is sound and built end-to-end.** semantic FS → agent-induced signed edges
   → frustration/H¹ runs on real memory. The agent DOES act as a restriction map (it emits
   signs). The instrument is unit-validated (a constructed frustrated triangle → NON_TRIVIAL,
   a balanced graph → TRIVIAL; `tests/test_aios_h1_agent_edges.py`).

2. **Run 1 was a corpus mistake** (global rule #4 — chose corpus by availability). The full
   `~/.aios/memory` store is dominated by execution traces + imported agent trajectories, not
   factual claims; its signed edges were near-duplicates / noise, and the graph was a forest
   (0 cycles), so its TRIVIAL_H1 is *vacuous* (no cycle to frustrate).

3. **Run 2 is the fair test and the robust negative.** On the typed-claim tier the induced
   graph is non-trivial (74 nodes, 65 edges, **8 independent cycles**) yet **fully balanced —
   H¹ = 0 non-vacuously**. No triple of claims is pairwise-signed with an inconsistent loop.

4. **The negative is robust against the judge's known bias.** `qwen2.5:7b` on 200-char
   summaries is conservative (≈89% "unrelated") and *over*-calls "contradicts" (manual review:
   most of the 15 −1 edges are false positives between topically-adjacent-but-non-opposing
   claims; the few genuine ones are explicit "CORRECTION to earlier X" supersessions). Spurious
   contradicts would tend to CREATE phantom frustration, not hide it — and none formed. So a
   stronger/cleaner judge would, if anything, find *fewer* frustrated cycles, not more.

## Conclusion → decision

The founder's counter-thesis is **not supported on real AIOS memory**: the agent can induce
consistency structure, but that structure is **globally consistent (no obstruction)** — there
is nothing for sheaf/H¹ to detect or prune. This **confirms and sharpens** the parked decision:
the bottleneck was never the agent's judging ability; it is that AIOS memory is coherent prose
with very few genuine contradictions. **Backbone stays the semantic FS** (`aios_semantic_fs.py`,
retrieval); **sheaf/H¹ stays parked** for a domain that actually carries relative-measurement
or frustrated structure.

**What the consistency-edge organ IS good for** (keep the value, drop the overclaim — rule #6):
not H¹ pruning, but a **data-quality signal** — it surfaces near-duplicates (run 1) and genuine
supersession ("CORRECTION to earlier X") relations. That is a smaller, defensible role: a
dedup / supersede-suggestion pass on the memory graph, not a cohomological pruner.

## Caveats (do not over-claim — rules #4/#5)

- One local 7b judge, 200-char summaries, one corpus snapshot. Directional, not definitive.
- A stronger judge (30b / full content, GPU permitting) is the obvious next probe IF the
  consistency-edge organ is pursued as a dedup/supersede tool — but it would not change the
  sheaf verdict (more signal ⇒ still balanced or fewer frustrations).
- Results JSON: `docs/aios_h1_agent_edges_REAL_results.json`,
  `docs/aios_h1_agent_edges_CLAIMS_results.json` (counts only; no memory content).

## World-scale reframe — adversarial verdict (2026-06-30)

Under the founder directive "AIOS is for the whole WORLD, not for me"
([[project_aios_for_the_world_not_founder]]), a reframe was raised: *single coherent user
memory is H¹=0, but world-scale SHARED multi-tenant memory will have non-trivial H¹
(frustrated cycles), so the sheaf detector is alive on the shared tier.* It was
adversarially pressure-tested (genesis-challenger) → **RE-INFLATION (0.8 confidence)**:

1. **It is 70-year-old structural balance theory** (Heider 1946; Cartwright–Harary 1956) in
   sheaf vocabulary. Raw "H¹≠0" is **near-certain and uninformative** on any large/noisy
   signed graph — real world-scale signed graphs (Epinions, Slashdot, Wikipedia RfA,
   Bitcoin-OTC) are essentially never balanced (PNAS 2011, doi 1109521108). The informative
   quantity is **frustration relative to a sign-marginal null**, never the raw nonzero.
2. **The robustness argument inverts.** On the personal tier, "a noisy over-calling judge can
   only ADD phantom frustration, and we still found none" *won* the H¹=0 result. At scale that
   *same* property **guarantees H¹≠0 from noise alone** — so the reframe moved the goalpost to
   a tier where the **null hypothesis also predicts the "win."** A claim the null also predicts
   is not a finding.
3. **The architectural killer:** AIOS sovereignty = tenant **isolation**
   ([[project_aios_saas_lakebase_pivot]]). A partitioned store has no cross-tenant edges →
   aggregate H¹ = Σ(per-tenant H¹) = 0. The cross-tenant shared graph the reframe needs is
   **forbidden by AIOS's own privacy DNA** unless a deliberate **opt-in shared pool** with
   cross-source entity resolution is built (it is not).

**Corrected instrument (`frustration_vs_null`, the only honest version of this work):** raw
frustrated-count is replaced by a topology- + sign-marginal-preserving permutation null →
`z_score` / `percentile` / `BELOW_NULL|AT_NULL|ABOVE_NULL`. Applied to the personal claim
graph: **F_obs=0 vs F_null_mean=3.48 (z=−2.36, p=0.011) → BELOW_NULL.** This is a *stronger*
confirmation than raw H¹=0: the memory is **significantly more coherent than chance** (not just
trivially acyclic-balanced; 8 independent cycles, z clears −2 though not overwhelmingly).

**Decision:** sheaf/H¹ stays **parked at BOTH tiers** — personal (measured, below-null
coherent) and shared (architecturally forbidden without an opt-in pool). The honest residual,
if ever pursued, is the rewritten test: **below-null + localization + a non-factorization
witness** (a frustrated cycle that pairwise contradiction detection MISSES — the only version
where H¹ is not a renaming of pairwise NLI), calibrated first on a real SNAP signed graph
(Bitcoin-OTC / Wikipedia RfA, published below-null answers). Not built; named for honesty.
