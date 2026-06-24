# AIOS as a Self-Improving Agent OS — the CLS architecture

> The long-haul program (2026-06-24). Founder: "think deep, take all of it on —
> from the partial to the unfinished." This is the spine; phases ship as cycles.

## The deep frame: AIOS is a Complementary Learning System

Neuroscience's CLS theory (McClelland 1995; the modern AI version): intelligence
needs **two** memory systems — a **fast hippocampal** store that captures specific
episodes immediately, and a **slow neocortical** system that gradually consolidates
recurring structure into weights via **replay during sleep**. Fast system avoids
forgetting today's experience; slow system generalizes without catastrophic
overwrite.

A frozen LLM has neither — it cannot store today's run, and its weights never move.
AIOS is the CLS *around* a frozen base model:

| CLS organ | AIOS component | State |
|---|---|---|
| **Hippocampus** (fast, episodic) | AkashicRecord ledger + MemoryOS graph — every run, immediate, provenance-stamped | ✅ live |
| **Sleep / dream** (consolidation + replay) | `aios_dream` — digests, dedups, abstracts memory when idle | 🟡 consolidates memory, does NOT replay into weights |
| **Neocortex** (slow, parametric) | a local LLM whose weights consolidate recurring patterns | 🔴 frozen — the missing half |
| **Replay selection** (what to consolidate) | doom-loop filter, draft-first, opt-in, loop_type | ✅ filters exist |
| **Supervision signal** | the human worker's interventions/corrections | 🟡 captured as outcomes, not modeled as reward |
| **Cross-individual transfer** | global AkashicRecord (other workers/providers) | ✅ live |

**The core insight:** AIOS today is a *hippocampus with no neocortical
consolidation*. "Every run becomes a star" is the hippocampal write — but stars
never become a constellation the model *internalizes*. It remembers; it does not
yet learn at the parameter level. Closing that (the dream→weights bridge) is what
moves the ceiling — the composite self that escapes prompt-dependency
([[project_prompt_dependency_and_composite_self]], [[project_aios_finetune_thesis]]).

## The six questions → CLS components

1. Session logs → graph/embed (capture) — 🟡 capability exists, not auto-onboarded
2. Router learns worker + agent behavior — 🟡 agent yes (DescentNet/Akashic), worker-vs-agent not separated
3. Dream = idle training that changes parameters — 🔴 dream consolidates memory, not weights (THE frontier)
4. Decide what to learn / not — 🟢 filters + draft-first
5. Learn from other workers via AkashicRecord — 🟢 live (cross-provider predict)
6. Capture sub-agents + provider-specific features — 🟡 provider surfaces yes, sub-agent/sidechain recognition no

## The long-haul plan (phases ship as renewal cycles)

**Phase A — complete episodic capture (Q1, Q6).** Wire session-ingest into the
onboarding/round-controller loop (opt-in, privacy-safe); recognize sub-agents
(Task/sidechain) as sub-episodes and attribute tools to them; capture provider
feature semantics, not just tool names. Outcome: the hippocampus records the whole
experience, automatically.

**Phase B — dual behavioral modeling (Q2).** Model the human worker (when they
intervene, what they correct, preferences) separately from each agent's tool
policy, and give the 4 OS agents their own profiles. The worker's corrections are
the supervision signal for Phase C.

**Phase C — the dream→weights bridge (Q3), the frontier.** A training organ that,
during idle dream, replays the consolidated AkashicRecord into a **narrow QLoRA**
on the local model (tool-format reliability + behavioral priors + 5-OS routing),
behind an **eval gate** (draft-first for weights: never deploy a fine-tune without
a held-out behavior eval beating the base). Then hot-swap the adapter. This is the
neocortical consolidation — the frozen model gains a slowly-improving parametric
layer fed by its own and peers' experience.

**Phase D — replay-selection policy (Q4, harden).** Decide which episodes become
weights vs stay episodic: high-value, human-verified, diverse, non-doom-loop.
Forgetting is a feature (abstraction), not a bug.

**Phase E — close the CLS loop + measure.** Prove the model gets measurably better
over time on a fixed behavior benchmark (the README promise, at the parameter
level). Fast memory → slow weights → better next run → richer memory.

## Build status (2026-06-24)

The program is **structurally complete** — every stage runs, is tested, and is wired
into the launcher. The only open step is the founder-gated GPU training run.

| Phase | State | Where |
|---|---|---|
| A — episodic capture | ✅ A1 (hippocampal onboarding status), A2 (sub-agent/sidechain + provider features) | `aios_agent_behavior.py`, `aios_onboard.py` |
| B — dual modeling | ✅ human intervention vs agent policy (`intervention_rate` = supervision signal) | `aios_agent_behavior.py` |
| C — gates | ✅ corpus gate + corpus_quality + held-out eval + draft-first promotion | `aios_cls_gate.py` → `aios cls-gate corpus|eval` |
| D — replay policy | ✅ prioritized replay (value × diversity × inverse-redundancy) | `aios_cls_gate.py` → `aios cls-gate replay` |
| E — close the loop | ✅ `run_cycle()` end-to-end, provenance-stamped report | `aios cls-gate cycle` |
| **GPU QLoRA run** | ⛔ **founder GO** (GPU-heavy, near-irreversible weight artifact) | — |

Also: source-adapter framework + provider-MCP harvest (`aios sources`), and the
doom-loop threshold induced 3→12 from real session data (the 3-name rule was a
false-positive on every real session).

**Two honest open items** (neither is a missing feature):
1. *Corpus scale/diversity.* Only ~5–7 session-derived per-run records exist; the
   1032 agentbank rows are aggregates (excluded). The cycle's held-out eval is
   degenerate until routine ingestion accumulates diverse sessions. The cap is data
   availability, not the pipeline.
2. *The GPU run itself* — gated on (1) being met and on founder GO.

## Memory activation: sparse at runtime, full at sleep (the optimization layer)

The AkashicRecord must not be scanned whole on every inference — it grows without
bound. Apply a **working-set / sparse-activation** policy (active memory control,
[[project_lgm_memory_thesis]]), mirroring how attention recalls only the relevant
slice while sleep replays everything:

- **Runtime (real use): domain-sparse.** Activate only the partitions for the
  domains the operator uses often — a frequency-weighted *hot set*. A coding
  session searches the code/tool partition, not finance or HR. Partial view, fast,
  focused, O(hot-set) not O(whole-ledger). The `category`/domain tag already on
  every entry is the partition key.
- **Sleep (dream/train): full.** Consolidation and the QLoRA replay (Phase C) sweep
  the **entire** ledger — that is exactly when breadth matters and latency doesn't.
  Cross-domain abstraction happens here, not at runtime.

Mechanics: `aios_memory.retrieve(task, …, domain=…)` scopes to a partition at
runtime (domain inferred via the capability spine), `domain=None` = full sweep for
training. A frequency tracker promotes/demotes domains in the hot set over time.
This is MoE-for-memory: route to the relevant expert-partition, not the whole store.

## Gates (never skip)

- **Privacy**: only tool names / action types / outcomes leave a machine — never
  content, args, or private-path data (DNA #7). Opt-in for any ingest.
- **Draft-first for weights**: a fine-tune is a draft until a held-out eval passes;
  operator can always roll back to the base adapter.
- **Provenance**: every weight update cites the corpus slice + eval it came from.

— living document; each phase rewrites its section as it ships.
