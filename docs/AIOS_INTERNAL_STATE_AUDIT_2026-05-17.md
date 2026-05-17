# AIOS Internal-State Audit — 2026-05-17

A fine-grained, parallel audit of all 5 AIOS repos (5 subagents, one per OS).
Founder request: "even you haven't grasped AIOS's internal state — grasp it
to the fine detail and come back."

## Per-OS findings

### myworld (control plane)
- **Real**: 81 `aios_*.py` scripts; 183 ASC contracts (154 closed); round
  controller running (pid 4154660); the autopoietic organs (dream, librarian,
  local_operator, verify, self_evolve) genuinely wired into `run_round`.
  Paper substantially drafted (`docs/papers/AIOS_AGENT_OPERATING_LAYER_DRAFT.md`,
  24.6 KB, 12 sections). DNA: 8 invariants + Authority Model v0.1.
- **Gap**: "COMPLETE" verdict is self-graded (a script grading its own
  criteria, not external validation); dispatch backlog lopsided (inbox 105 /
  outbox 160 myworld) with `aios-feedback-run_*` packets `contract=None`;
  paper's benchmark (ASC-0162) designed but **not executed**; operator
  sovereignty actually 0.38.

### hivemind (execution layer)
- **Real**: 34 modules, ~21,600 LOC; ~56 CLI subcommands; **404 tests pass**;
  398 runs with full artifact sets; local LLM execution verified end-to-end
  (ran a classifier worker on qwen3:1.7b, no provider); 3 Hive debates real.
  The most concretely-built sub-OS.
- **Gap**: harness.py is a 305 KB monolith; verification wired but **not
  auto-firing** on provider-loop runs (`verdict: not_run`); cold-model load
  timeouts; Ollama the only working local backend.

### memoryOS (memory substrate)
- **Real**: 198,485 nodes / 306,213 edges; multi-platform importers
  (ChatGPT/Claude/Gemini/DeepSeek/Grok/Perplexity/KakaoTalk); MCP server, 38
  tools; draft/review lifecycle used (187 MemoryObjects).
- **Gap (the worst)**: **0% embedding coverage**, **0% health**; 135 drafts
  (72%) unreviewed; the `reviewed` lifecycle stage is dead; cli.py is an
  828 KB monolith. Verdict: "an unindexed hoard with a curation layer bolted
  on — curation governs 0.09% of the graph."

### CapabilityOS (capability map)
- **Real**: 17 capability cards; `recommend`/`audit`/`observe` all genuine;
  recommendation-only invariant enforced at runtime; 21 tests pass;
  `observe-results` produces 156 observations + 60 radar signals from the
  real `.aios/outbox`.
- **Gap**: observation is recomputed on-demand and **never persisted**;
  catalogs ship with zero baked-in `observation_count`; the helper layer's own
  `observations.jsonl` (36 invocations) is **not wired into `recommend`**. The
  feedback loop exists in code but is not closed automatically.

### GenesisOS (divergence layer)
- **Real**: 8 modules, ~2,000 LOC; 48 tests pass; append-only, advisory-only
  doctrine genuinely honored; semantic.py and library.py substantive.
- **Gap**: the divergence *intelligence* is keyword/template, not generative.
  critic = lexical heuristics over hardcoded vocab sets (detects vocabulary
  patterns, not reasoning failures); analogy = 31-row lookup + bag-of-words
  (no structural mapping); diverge/branches = string templates. Real bug:
  `--text` expects a file path, not inline text. Verdict: "a divergence
  *scaffold*, not yet an engine" (`no_remote_llm_v1` confirms v1 is
  intentionally non-generative).

## The unifying diagnosis

Across all 5 OS the **same gap repeats**. AIOS has built — with genuine rigor,
~900 passing tests, append-only stores, doctrine compliance, provenance, stop
conditions — the **deterministic scaffold** of every organ. The skeleton is
real and tested.

But the layer that turns the scaffold into **cognition** is thin or unclosed:

| OS | scaffold built | cognition-closing step missing |
|---|---|---|
| memoryOS | 198K-node graph | embeddings (0%) → no semantic retrieval |
| CapabilityOS | observation engine | persistence + feedback into recommend |
| GenesisOS | divergence slots | a generative engine in the slots |
| hivemind | run harness | verification auto-firing on runs |
| myworld | organs wired | feedback/dispatch reconciliation |

**AIOS is a nervous system whose neurons are wired but whose loops do not yet
fire end-to-end.** That is the precise reason "AIOS isn't as smart as the
operator": the operator holds connected, closed-loop cognition; AIOS holds a
connected *scaffold* with the cognition-closing steps unrun.

## Prioritized gap list (for the solidify-and-fill step)

1. **memoryOS embedding** — turn the hoard into a searchable library
   (in progress: the librarian's embed job is running).
2. **CapabilityOS feedback loop** — persist observations; wire
   `observations.jsonl` into `recommend`. Concrete, in-scope.
3. **GenesisOS `--text` bug** — accept inline text. Small, real.
4. **GenesisOS generative layer** — attach LLM-backed generation to the
   divergence slots (the deepest gap; `no_remote_llm_v1` is a design choice
   to revisit).
5. **hivemind verification auto-fire** — runs should self-verify.
6. **myworld dispatch reconciliation** — bind/close the `contract=None`
   feedback backlog.
7. **the paper's benchmark** — ASC-0162 is designed but unexecuted; the
   utility paper needs it run.

## Solidified roles (one sentence each)

- **myworld** — the control plane: contracts, dispatch, the deterministic
  kernel, the always-on autopoietic loop.
- **hivemind** — the execution layer: a local-first blackboard harness that
  turns "run an agent" into a contracted, verifiable, replayable run.
- **memoryOS** — the memory substrate: an append-only, provenance-stamped
  graph that should turn every conversation and outcome into retrievable,
  reviewed memory.
- **CapabilityOS** — the capability map: a recommendation-only catalog that
  ranks and explains which capability fits a task, and observes what worked.
- **GenesisOS** — the divergence layer: forces reasoning to be re-framed
  across fixed axes and (once generative) borrows across domains.
