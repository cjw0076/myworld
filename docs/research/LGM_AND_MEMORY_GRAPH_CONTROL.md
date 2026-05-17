# LGM and Memory-Graph Control — Frontier Research for AIOS

Status: research note (not a contract). Author: claude@myworld operator.
Date: 2026-05-17. Scope: state of the art for (a) graph foundation models /
"LGM" and (b) active control of an ever-growing knowledge/memory graph.
Motivating problem: memoryOS graph is at ~198k nodes / ~306k edges and
growing unbounded; draft-first + review gates are *passive* mitigations.
We need an *active control model* that governs graph growth.

---

## 0. TL;DR

- **"LGM" as a single named paradigm is not (yet) standardized.** The real,
  active research term is **Graph Foundation Model (GFM)**. The founder's
  intuition is directionally correct: graphs *are* being treated as a
  first-class modality deserving foundation models — but the field is
  earlier and more fragmented than the LLM analogy implies.
- The decisive lever for AIOS is **not** swapping the model class. It is the
  **memory-graph control loop**: forgetting/decay, hierarchical abstraction
  (episodic→semantic consolidation), node/edge merging, community
  summarization, and bounded-growth governance.
- Every production agent-memory system that survives scale does the same
  three things: **invalidate** (don't append blindly), **abstract** (roll
  specific nodes into concept/community nodes), and **decay** (let unaccessed
  low-salience nodes fade). AIOS currently does none of these actively.

---

## 1. Large Graph Models / Graph Foundation Models — is the paradigm real?

### 1.1 Yes, it is a real emerging paradigm — but the name is "GFM"

The 2024–2026 literature converged on **Graph Foundation Model (GFM)** rather
than "LGM"/"Large Graph Model". A GFM is "a single model that learns
transferable graph representations that can generalize to any new,
previously unseen graph, including its schema, structure, and features"
(Google Research). Key reference works:

- **Graph Foundation Models: Concepts, Opportunities and Challenges** —
  TPAMI 2025 (arXiv:2310.11829). The agenda-setting survey.
- **Graph Foundation Models: A Comprehensive Survey** — arXiv:2505.15116
  (May 2025). Proposes the now-standard modular decomposition (see §1.3).
- **Graph Foundation Models: Challenges, Methods, and Open Questions** —
  KDD 2025 (ACM 10.1145/3711896.3736568).
- **Towards Graph Foundation Models: A Transferability Perspective** —
  arXiv:2503.09363.
- **Large Graph Generative Models (LGGM)** — arXiv:2406.05109. This is the
  closest thing to a literal "Large Graph Model": trained on 5,000+ graphs
  across 13 domains, discrete denoising diffusion + Graph Transformer,
  zero-shot graph *generation* on unseen domains, text-guided generation.
- **Google "Graph Foundation Models for relational data"** (research.google
  blog, 2025): converts relational DB tables → heterogeneous graphs;
  reports **3×–40× average-precision gains** over tabular baselines on
  internal tasks (e.g. spam detection). Strongest production signal so far.

Labs/groups active: Google Research; HKUDS (LLM4Graph survey, KDD'24);
BUPT-GAMMA (GFMPapers list); OSU-NLP (HippoRAG line); Microsoft Research
(GraphRAG); plus the Zehong-Wang "Foundation-Models-on-Graphs" corpus.

### 1.2 Positioning relative to LLMs

GFMs explicitly copy the LLM recipe — "large-scale pre-training over
well-curated multi-domain data" — and apply it to graphs as a distinct
modality. The bet: **fundamental structural patterns transfer across
domains** (citation graphs → product graphs → molecules) the way linguistic
patterns transfer across text. But honest assessments ("Beyond the Buzz",
Data Science Collective, 2025) note GFMs are *not* at LLM maturity:
transferability across structurally dissimilar graphs is unsolved, there is
no canonical benchmark, and cross-domain pattern *conflict* (a motif means
different things in different domains) is an open theoretical problem.

### 1.3 Technical content — three architecture families

The May-2025 survey decomposes GFMs into **Backbone × Pre-training ×
Adaptation**:

- **Backbones**: (a) pure **Graph Transformers / GNNs**; (b) **LLM-as-graph**
  — serialize the graph into tokens (node tokenizers like NT-LLM); (c)
  **hybrid GNN+LLM** — dual encoders fused via cross-modal attention or
  co-training. Hybrids reportedly beat GNN-only by up to ~25% accuracy.
- **Pre-training**: contrastive, generative (diffusion, as in LGGM), or
  predictive (masked-node/edge) objectives.
- **Adaptation**: fine-tuning, graph prompt-tuning, test-time adaptation,
  zero-shot.

### 1.4 Implication for AIOS

Designing toward a GFM-style substrate is defensible **as a long-horizon
research direction** — it aligns with "memory as the moat". But the
near-term, high-leverage work is **not** training a graph model. It is the
**control model over memoryOS's existing graph**. A GFM would *consume* a
well-governed graph; it does not fix an ungoverned one. Govern first.

---

## 2. Controlling an ever-growing knowledge/memory graph (the core problem)

Naive append-only graphs degrade in five documented ways (SSGM framework,
arXiv:2603.11768): **semantic drift** (iterative summarization loses
nuance), **temporal obsolescence** (stale facts conflict with current ones),
**index bloat** (retrieval latency scales linear/quadratic with history),
**memory poisoning**, and **goal/procedural drift**. The control mechanisms
the literature uses to fight this:

### 2.1 Forgetting / decay

- **Ebbinghaus forgetting curve** (MemoryBank): each memory has a retention
  strength; frequently-accessed/important items are reinforced, neglected
  ones exponentially fade and are pruned below a threshold.
- **ACT-R-style activation** (Human-Like Remembering/Forgetting, HAI 2025):
  activation = semantic similarity + use frequency + temporal decay +
  probabilistic noise. Retrieval and forgetting both driven by this score.
- **Access-based decay beats time-based decay** (consensus finding): reset
  decay clock on *retrieval*, not creation. A fact recalled monthly stays
  prominent; a never-touched recent fact fades. Relevance ≈ engagement, not
  age.
- **Weibull decay** (SSGM, SuperLocalMemory): more expressive than plain
  exponential — the shape parameter tunes fast-early vs delayed forgetting
  per domain.

### 2.2 Hierarchical abstraction (episodic → semantic consolidation)

The single most important bounding mechanism. Specific, low-level nodes get
**rolled up** into fewer abstract concept nodes:

- **Generative-Agents-style reflection**: periodically synthesize many
  low-level episodes into higher-level abstractions, added back as new nodes.
- **Consolidation as a background job**: on session end, scan raw episodic
  history, extract structured facts, map entities, resolve contradictions,
  write distilled semantic knowledge. Episodic raw log can then be pruned or
  cold-stored.
- **GraphRAG community summarization** (Microsoft, arXiv:2404.16130):
  **Hierarchical Leiden** recursively clusters the graph until communities
  hit a size threshold; an LLM writes a natural-language summary per
  community at each level. Queries hit summaries, not raw nodes — global
  questions answered with 50–70% better comprehensiveness. The hierarchy
  *is* the growth bound: the graph can grow, but the queryable surface stays
  O(communities).

### 2.3 Node merging / dedup / entity resolution

- **Graphiti/Zep** (arXiv:2501.13956): every extracted entity is embedded
  (1024-d), matched against existing nodes via cosine + full-text search,
  then an LLM **entity-resolution prompt** decides merge. Edge dedup is
  constrained to edges between the *same entity pair* — bounds the
  comparison cost and prevents spurious cross-pair merges.
- HippoRAG links synonyms into the KG so the same concept isn't re-created.

### 2.4 Salience scoring & bounded-growth governance

- Salience = a learned/heuristic score (importance × recency × frequency ×
  centrality) gating what is *worth* keeping or abstracting.
- **SSGM** governance principles, directly portable to AIOS:
  1. **Pre-consolidation validation** — a Truth Maintenance System checks a
     proposed update against protected core facts *before* it lands.
  2. **Temporal & provenance grounding** — read-time filter applies decay +
     provenance check; prune below freshness threshold.
  3. **Access-scoped retrieval** — identity-based access control.
  4. **Reversible reconciliation** — keep a mutable active graph *and* an
     immutable episodic log; periodically re-align to bound cumulative
     drift. (Note: this is exactly AIOS's append-only-audit invariant.)

---

## 3. Production agent-memory systems — how each bounds growth

| System | Graph? | Growth-bounding mechanism |
|---|---|---|
| **Zep / Graphiti** | Temporal KG, 3 tiers | Edge **invalidation** not deletion (`t_valid`/`t_invalid` bi-temporal model); entity-resolution merge on ingest; **community tier** via label propagation; periodic community refresh. Episodic tier is non-lossy but lower tiers are the queried surface. |
| **Mem0** | Vector + optional graph | Native **memory expiration** (`expiration_date`), **decay of low-relevance entries**, automatic filtering to prevent bloat, **compression engine** (~80% prompt-token reduction). Open admission: staleness of *high*-relevance memory is unsolved. |
| **HippoRAG / HippoRAG 2** | Open KG + PPR | Synonym linking prevents duplicate concept nodes; Personalized PageRank does *retrieval-time* salience so the graph can grow but recall stays focused; cheaper offline indexing than GraphRAG/RAPTOR/LightRAG. |
| **GraphRAG** (Microsoft) | KG + community hierarchy | **Hierarchical Leiden** + LLM community summaries; queryable surface = communities, not nodes. The abstraction hierarchy is the bound. |
| **A-MEM** (NeurIPS'25) | Zettelkasten note-graph | Memory **evolution**: new notes trigger updates/refinement of linked old notes — keeps the network coherent rather than monotonically appending. |
| **AriGraph** (IJCAI'25) | KG world-model | Integrates episodic + semantic in one graph; episodic edges link episodes to extracted triples — semantic layer is the compact, reusable surface. |
| **Cognitive architectures (ACT-R, SOAR)** | symbolic memory | ACT-R: base-level **activation decay** + reinforcement on use; SOAR: **chunking** compiles repeated reasoning into single rules — abstraction-by-compilation, the original "consolidation". |

**Pattern across all of them:** raw/episodic layer may be append-only, but
the *queried* layer is actively governed — invalidated, merged, summarized,
decayed. AIOS today treats its whole graph as the queried layer; that is the
gap.

---

## 4. "Memory design" as the decisive factor

Per current research, a well-designed memory system has:

1. **Episodic vs semantic separation.** Episodic = timestamped, contextual,
   specific ("what happened"). Semantic = timeless, abstracted, general
   ("what is true"). Keep them in *distinct tiers*; never let raw episodes
   be the retrieval surface.
2. **Consolidation as a first-class process.** A scheduled background job
   that converts episodic→semantic: extract facts, resolve contradictions,
   abstract patterns, write concept nodes. This is *the* mechanism that
   bounds growth — fewer, denser semantic nodes replace many episodic ones.
3. **Hierarchical structure.** Concept nodes → community nodes → global
   summaries. Query at the right altitude.
4. **Forgetting curves / decay.** Access-reinforced, Weibull/Ebbinghaus
   decay. Forgetting is a *feature* — it is how the system stays bounded and
   relevant.
5. **Retrieval-driven reinforcement.** What gets used gets strengthened;
   what is never retrieved decays. The graph self-prunes by usage.

**Known failure modes of naive append-only memory** (name these as AIOS
stop conditions): unbounded retrieval latency / index bloat; semantic drift
from repeated summarization; temporal obsolescence (stale beats current);
duplicate/near-duplicate node proliferation; context dilution (signal lost
in volume); memory poisoning; high-relevance staleness.

---

## 5. Synthesis for AIOS — what the "graph control model" should do

Recommendation: AIOS should add a **Graph Control Model** that runs as a
stage of the **dream cycle** (the existing offline/consolidation organ).
It does not replace draft-first/review; it is the active governor on top.
Each pass over memoryOS's graph performs, in order:

1. **Score** — compute a per-node/per-edge **salience** = f(importance,
   recency, access-frequency, degree/centrality, provenance strength).
   Persist as graph metadata. Cheap, runs every cycle.

2. **Resolve & merge** — embed entity nodes, cosine + lexical candidate
   search, LLM entity-resolution adjudication; merge duplicates;
   collapse near-duplicate edges (constrained to same entity pair, à la
   Graphiti). Directly attacks node-count growth.

3. **Invalidate, don't delete** — when a new fact contradicts an old edge,
   set the old edge's `t_invalid` (bi-temporal model). Honors AIOS's
   append-only-audit invariant: nothing destroyed, but the *current* view
   is clean. Add `t_valid`/`t_invalid` to the edge schema if absent.

4. **Consolidate (episodic→semantic)** — the core bounding step. Cluster
   low-level episodic nodes, have an LLM abstract each cluster into a
   semantic **concept node** with provenance back-links to its episodes.
   Mark episodes as consolidated → eligible for cold storage / decay. This
   is what turns unbounded episodic growth into bounded semantic growth.

5. **Community layer** — run hierarchical clustering (Leiden for batch
   refresh; label-propagation incremental step for cheap online updates,
   per Graphiti) and generate LLM community summaries. Queries hit
   communities/summaries first. The queryable surface becomes
   O(communities), not O(nodes).

6. **Decay & prune** — apply access-reinforced Weibull/Ebbinghaus decay.
   Nodes/edges below a retention threshold AND already consolidated AND
   low-salience → move to cold tier (never hard-deleted; append-only audit).
   Retrieval *resets* the decay clock — usage protects.

7. **Validate & bound-check** — a Truth Maintenance pass: new
   consolidations must not contradict protected core facts. Emit a
   **named stop condition** if: node count grows faster than consolidation
   reclaims it; community count exceeds budget; contradiction rate rises;
   retrieval latency crosses an SLO. Surface to the operator — silent
   degradation is forbidden (DNA invariant 4).

**Invariant alignment.** This design respects AIOS's 7 DNA invariants:
recommendation-only (the control model proposes consolidations as drafts;
review still gates acceptance into semantic tier), append-only audit
(invalidate/cold-store, never destroy), provenance chain (concept nodes
link to source episodes), named stop conditions (step 7), operator override
(thresholds are operator-tunable).

**Suggested target metric.** Track the **bound ratio** =
consolidation/merge reclamation rate ÷ raw ingest rate. While < 1 the graph
is still unbounded; the control model's job is to drive it ≥ 1 on the
*queryable* (semantic + community) surface while the episodic tier is
allowed to grow but is cold-tiered and decay-pruned.

**Next step.** This justifies a contract (suggest ASC-018x): "memoryOS
Graph Control Model — bounded-growth dream-cycle stage", with work packets
to memoryOS (schema: salience, `t_valid`/`t_invalid`, tier label,
consolidated-flag; cold-storage tier) and to the round controller (wire the
control model as a dream-cycle stage + stop-condition emission).

---

## Sources

Graph foundation models / LGM:
- https://arxiv.org/abs/2406.05109 — Large Graph Generative Models (LGGM)
- https://arxiv.org/abs/2505.15116 — Graph Foundation Models: A Comprehensive Survey
- https://arxiv.org/pdf/2310.11829 — GFM: Concepts, Opportunities and Challenges (TPAMI'25)
- https://arxiv.org/abs/2503.09363 — Towards GFMs: A Transferability Perspective
- https://dl.acm.org/doi/10.1145/3711896.3736568 — GFM: Challenges, Methods, Open Questions (KDD'25)
- https://research.google/blog/graph-foundation-models-for-relational-data/ — Google GFM for relational data
- https://github.com/HKUDS/Awesome-LLM4Graph-Papers — LLM4Graph survey (KDD'24)
- https://github.com/BUPT-GAMMA/GFMPapers — GFM must-read paper list

Memory-graph control / agent memory:
- https://arxiv.org/abs/2501.13956 — Zep: Temporal Knowledge Graph Architecture for Agent Memory
- https://github.com/getzep/graphiti — Graphiti open source
- https://arxiv.org/abs/2502.14802 — HippoRAG 2 / From RAG to Memory
- https://arxiv.org/abs/2405.14831 — HippoRAG (NeurIPS'24)
- https://arxiv.org/html/2404.16130v2 — GraphRAG: From Local to Global
- https://microsoft.github.io/graphrag/ — Microsoft GraphRAG docs
- https://arxiv.org/abs/2502.12110 — A-MEM: Agentic Memory for LLM Agents (NeurIPS'25)
- https://arxiv.org/abs/2407.04363 — AriGraph: KG World Models with Episodic Memory
- https://arxiv.org/html/2603.11768v1 — SSGM: Stability and Safety Governed Memory framework
- https://dl.acm.org/doi/10.1145/3765766.3765803 — Human-Like Remembering/Forgetting (ACT-R + LLM, HAI'25)
- https://mem0.ai/blog/state-of-ai-agent-memory-2026 — Mem0 state of agent memory 2026
- https://dev.to/sudarshangouda/ai-agent-memory-part-2-the-case-for-intelligent-forgetting-4i48 — intelligent forgetting
