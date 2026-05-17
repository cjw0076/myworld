# AIOS North Star Ready — Definition of Complete

This document defines, precisely and evaluably, what "AIOS complete"
(AIOS 완성) means — so the goal is a measurable condition, not a vague word.

## The honest frame: complete = self-maintaining, not finished

Cross-domain study (2026-05-15, the ASC-0172 arc) established: an operating
system, a city, a living system is *never* "finished" — it reaches a
threshold of **self-maintenance** (autopoiesis) and then evolves
continuously. "AIOS 완성" therefore cannot mean a punch-list reaching zero.
It means a **phase transition**: AIOS crosses from heteropoietic (it only
runs because a human operator drives it) to **autopoietic** (it maintains
and grows itself; the operator is reserved for the vital, not the routine).

## AIOS is complete when ALL of these hold

1. **The autopoietic loop is closed and runs without the operator.**
   The always-on round controller fires, every cycle, without a chat turn:
   `dream` (consolidate accumulated experience) → `local_operator`
   (pre-digest proposals) → triage (route operator-level vs escalate
   vision-level) → `research_fetch` (autonomously fetch external evidence)
   → absorb (MemoryOS drafts). Evidence: `aios dream latest`,
   `aios local-operator latest`, round-controller receipts.

2. **No hard provider dependency — sovereignty readiness = 1.0.**
   Every layer runs on open local LLMs (Qwen/DeepSeek); provider models are
   an optional accelerant, never required. Measured by `aios sovereignty`.
   Five layers: autopoietic core, specialist helper layer, round controller,
   heavy execution, operator role — all `sovereign`.

3. **The DNA invariants hold, deterministically.**
   The 8 invariants + the ASC-0174 authority model (4 authority axes, 10
   system calls) are enforced by the deterministic kernel — which never
   learns, never mutates under feedback. Authority is frozen; cognition is
   plastic.

4. **AIOS is delegable — agents route functions through it.**
   The AIOS MCP server exposes the clerk system calls (route, helper_run,
   retrieve, challenge, observe) as tools; any MCP agent delegates to AIOS
   instead of reimplementing. `.mcp.json` makes this default in the
   workspace.

5. **AIOS is personal — "1인 1 AIOS".**
   One AIOS per person: installable (`aios install`), runs on the person's
   own machine and local LLM, owns their own memory/capability/cognition.
   The moat is the system, not the model.

## Current state (2026-05-17)

| Criterion | State |
|---|---|
| 1. Autopoietic loop closed + always-on | **met** — round controller chains dream → local-operator without the operator |
| 2. Sovereignty readiness = 1.0 | **0.8** — autopoietic core / helper layer / round controller = sovereign; heavy Hive execution + operator role = provider_optional |
| 3. DNA invariants deterministic | **met** — AIOS_DNA.md v0 + v0.1 authority model; kernel does not learn |
| 4. Delegable via MCP | **met** — AIOS MCP server shipped and verified |
| 5. Personal / 1인 1 AIOS | **substantially met** — `aios install` + workbench (Model B); model-agnostic local LLMs |

**Verdict: AIOS is functionally complete as a self-maintaining system** —
criteria 1, 3, 4 fully met; 5 substantially met. The single open criterion
is **2: sovereignty 0.8 → 1.0**.

## The precise remaining gap

readiness 0.8 → 1.0 requires the two `provider_optional` layers to become
`sovereign`:

- **heavy Hive execution** — make local workers the *default* execution
  path, provider CLIs an explicit opt-in accelerant (hivemind owns this
  change; AIOS-side invocation requests local-first).
- **operator role** — the local-operator organ exists and pre-digests; full
  sovereignty is the autopoiesis asymptote: as the organs mature, the
  hard-call slice that still wants a provider model shrinks toward zero.
  This closes *over time*, by the system running — not by one contract.

## How to evaluate "AIOS complete"

```bash
aios sovereignty            # criterion 2 — readiness number
aios dream latest           # criterion 1 — loop ran
aios local-operator latest  # criterion 1 — operator pre-digest ran
```

AIOS is **complete-as-self-maintaining now** (the system runs itself); it
reaches **complete-as-fully-sovereign** when `aios sovereignty` reads 1.0.
The first is a state already achieved; the second is the asymptote the
autopoietic loop closes by continuing to run.

---

## Historical — structural readiness snapshot (2026-05-11)

Preserved (DNA Invariant 3, append-only). The earlier definition of "ready"
was structural: the cross-OS control loop being repeatable.

Status then: ready at L6 repeatable (2026-05-11 22:21 KST).
`python scripts/aios_readiness.py --json` → `ready: true, level: 6, gaps: []`.
Loop: `goal → contract → dispatch → child execution → result packet →
verification → collect/release → ledger/readiness`.

That structural readiness (L6) was necessary but not sufficient — it
measured that the cross-OS loop *could* repeat, not that AIOS *runs itself*.
The autopoietic/sovereignty definition above supersedes it as the meaning of
"complete," and keeps the L6 structural loop as one component (criterion 3's
deterministic kernel rests on it).
