# AIOS Renewal — One Foundation

> Stake in the ground (2026-06-24). Bold by design, fixable by default —
> 저질러놓고, 만들고, 고친다. Sharpened by the running deep-research and the
> deep-interview that follows. This is a north-star, not a spec.

## The bet

AIOS is **the operating layer for personal AI**. One system per person that
wraps every provider, learns from every run, persists sovereign memory, and that
other developers build on. Not an agent. Not a framework. A *foundation* — the
layer Linux is to the OS, Kubernetes is to orchestration, MCP is to tool
connection. This is that layer for the personal-AI era.

## What's wrong now (honestly)

We have a powerful organism but a **fragmented** one — 132+ standalone organs,
two runners (`aios_head`, `aios_harness`), three UIs, scripts that bypass the
kernel. That is not failure; it is **research assets not yet condensed into a
foundation.** The renewal is the condensation.

## The renewal — collapse to one spine

Everything routes through a single coherent core:

- **One kernel** — authority + audit + reversibility + provenance. Every action
  passes the gate; every record cites evidence; no loop without a named exit.
- **One runner** — the turn-loop. Merge `aios_head` and `aios_harness`; one
  organism loop, robust on stock models (and, in time, on an AIOS-tuned model).
- **One memory** — the provenance graph + the AkashicRecord ledger. Every run
  becomes a star; the system gets measurably smarter over time.
- **One capability spine** — absorb the device (onboard), route to what's ready,
  wrap all providers. No hard dependency on any one model.
- **One head, two doors** — humans via the CLI/web, agents via MCP. Same core.

## What the research changed (Cycle 1 deep-research, 106 agents)

The frontier's #1 chronic problem is **long-horizon execution reliability** — not
graceful decline but *non-linear collapse* past a breaking point in subtask count.
Two mechanisms dominate, and **model scaling does not fix them**:

1. **Self-conditioning** — a model errs more after seeing its own past errors in
   context; persists in 200B+ models (arXiv 2509.09677). Injecting errors into
   history measurably degrades later accuracy.
2. **Process-level failures dominate (72.5%)** — planning/subplanning errors, vs
   27.5% design-level (memory/forgetting) (arXiv 2604.11978, Dawn Song et al.,
   3,100+ trajectories).

Convergent remedy across sources: **hierarchical sub-planning + execution-time
plan verification & repair + memory that re-surfaces long-range constraints.**
And the cheapest lever: **reasoning models structurally evade self-conditioning**
(DeepSeek-R1 runs 100+ steps where V3 fails at 4) — route long-horizon work to
thinking models and keep error traces out of the active context.

### The four research-backed renewal pillars (AIOS is already shaped for these)

| # | Pillar | Research basis | AIOS position |
|---|--------|----------------|---------------|
| 1 | **Self-conditioning defense** — keep error traces out of active context; clean-context retry | self-conditioning persists at scale (2509.09677) | turn-loop already has loop-detection; make error-trace exclusion first-class — *cheapest, highest-leverage, build first* |
| 2 | **Horizon-aware routing** — long/multi-step tasks → reasoning models | R1: 100+ steps vs V3: 4 | substrate_router + role_router already route by role; add horizon signal |
| 3 | **Execution-time plan verification & repair** — hierarchical sub-planning | 72.5% failures are process-level (2604.11978) | HiveMind verification + kernel; make sub-planning + plan-repair first-class in the one turn-loop |
| 4 | **Long-range constraint re-surfacing** — memory that resurfaces constraints during execution | memory field fragmented; unified provenance memory = hardest + most differentiating | MemoryOS (provenance graph, draft-first) is exactly this substrate — make it resurface, not just store |

**Build order:** Pillar 1 first (cheapest, research says highest-leverage), inside
the unified turn-loop that merges `aios_head` + `aios_harness`.

### Status — all four pillars SHIPPED (2026-06-24, one session)

| # | Pillar | Mechanism | Commit |
|---|--------|-----------|--------|
| 1 | self-conditioning defense | `decondition_history()` compresses old error traces | 7a05345 |
| 2 | horizon-aware routing | `classify_horizon` → reasoning model for long tasks | 3e8639b |
| 3 | plan verify+repair | stall-triggered `plan_repair` re-plan injection | 031f404 |
| 4 | constraint re-surfacing | MemoryOS `constraint_provider` re-injects `[REMEMBER]` | c42e3b3 |

**Integration verified:** all four fire together in one `run_loop` with no conflict
(decondition + plan-repair ×3 + resurface ×3 in a single scripted run). Each has a
permanent unit test; 57 turn-loop+harness tests pass. The four research-backed
reliability levers now live in the shared kernel turn-loop — the spine of the one
foundation. Remaining renewal work: merge `aios_head` into this one runner; then
the unified head, memory, and capability spine per the sections above.

## The chronic frontier problems we structurally escape

| Frontier problem | AIOS structural answer |
|---|---|
| Statelessness / no learning transfer | behavioral ledger — learns from every run |
| Frozen-model / prompt-prison ceiling | memory + GenesisOS divergence + (eventual) local fine-tune |
| Fragmentation / glue-code sprawl | one kernel everything routes through |
| Provider lock-in | wrap every CLI + local LLM; churn-survivable |
| Tool-calling unreliability | onboard e2e verify now; AIOS-tuned model next |
| Unverifiable agent output | Merkle-provable receipts + deterministic verification |

## The loop (this is one cycle)

`research → deep-interview → build (ralph/ult) → verify → repeat`

Operating mode: **action-bias.** Commit the move, build it, fix it. Don't hedge
the scale; don't wait for certainty. The kernel's invariants are the guardrails
that make bold building safe.

— living document; the deep-research report and interview will rewrite sections
of this, and that is the point.
