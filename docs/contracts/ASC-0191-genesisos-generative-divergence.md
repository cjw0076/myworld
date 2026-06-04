---
contract_id: ASC-0191
slug: genesisos-generative-divergence
status: closed
goal: Make GenesisOS divergence genuinely generative — back the critic / analogy / branch slots with a local-LLM helper instead of keyword heuristics and template strings — while keeping the advisory-only, append-only doctrine.
created: 2026-05-17 18:50 KST
proposed_by: claude@myworld
accepted: 2026-05-17 23:18 KST
closed: 2026-05-17 23:18 KST
acceptance_authority: codex@myworld acting operator under the active continuous AIOS-completion directive; local-only helper, no remote model, no authority expansion beyond advisory output.
escalation: VISION-ADJACENT — founder GO requested. This revisits `no_remote_llm_v1`, a deliberate GenesisOS design choice that v1 be non-generative.
origin: The 2026-05-17 internal-state audit, gap #4 (the deepest) — GenesisOS's divergence intelligence is keyword/template, not generative. critic = lexical heuristics over hardcoded vocab sets; analogy = a 31-row lookup + bag-of-words; diverge/branches = string templates. Verdict: "a divergence scaffold, not yet an engine."
---

# ASC-0191 GenesisOS — Generative Divergence

DNA references: Invariant 1 (recommendation-only — GenesisOS proposes, never
selects truth), Invariant 3 (append-only), Invariant 7 (privacy — a local
helper, no remote send).

## The framing — and why this is escalated

GenesisOS v1 was deliberately non-generative (`no_remote_llm_v1` in
`modalities.py`): the divergence slots are deterministic scaffolds. The audit
named this the deepest gap — the scaffold detects vocabulary patterns, it
does not actually reason across frames.

This contract proposes to fill the slots with generation, but **stays inside
AIOS doctrine**: the generator is a *local* LLM helper (the existing
`aios_helper.py` specialist layer), not a remote model. That keeps privacy
(Invariant 7) and sovereignty intact. GenesisOS still only *proposes* —
generation makes the proposals real divergence instead of templates; it does
not give GenesisOS authority to select truth.

Because this revisits a deliberate sub-OS design choice, it is drafted
`proposed` and awaits founder GO before acceptance.

## Scope (proposed)

repos: `GenesisOS`

allowed (if accepted): `GenesisOS/**` — codex@GenesisOS owns the mechanism.

## The requirement (proposed)

1. The critic, analogy, and branch/diverge slots gain a generative path: each
   can call a local-LLM helper to produce genuine cross-frame reasoning, a
   structural analogy mapping, or a counter-branch — not a template fill.
2. The deterministic heuristic stays as the fallback when no local model is
   present (a constrained device) — generation is an upgrade, not a hard
   dependency.
3. Output stays advisory-only and append-only; provenance records whether a
   given divergence was generated or heuristic.

## Named Exit (proposed)

Closed when: at least one divergence slot produces a local-LLM-generated
result that a heuristic could not have produced, the heuristic fallback still
works with no model present, and the advisory-only / append-only doctrine is
intact.

## Open question for founder

`no_remote_llm_v1` named v1 non-generative on purpose. Is making GenesisOS
generative-via-local-helper the right next step now, or should the divergence
scaffold stay deterministic until a later phase? GO / HOLD / redirect.

Resolution: GO for local-helper generation only. Remote generation remains out
of scope. Deterministic fallback remains the default path unless the operator
or caller explicitly asks for `--generated`.

## Close Evidence

- GenesisOS commit: `5a935b1 Add local generative divergence helper`.
- Implementation:
  - `GenesisOS/genesisos/generator.py` adds a local-only helper wrapper using
    `GENESISOS_LOCAL_HELPER_COMMAND` or local Ollama (`GENESISOS_OLLAMA_MODEL`,
    default `qwen3:8b`) with sanitized output, provenance, prompt hash, and
    `mutation_policy: local_generation_only_no_source_mutation`.
  - `GenesisOS/genesisos/cli.py` keeps deterministic defaults, and adds
    optional `--generated` surfaces for `diverge`, `critic`, and
    `analogy match`.
  - Generated outputs remain advisory: GenesisOS does not execute, route tools,
    accept memory, create contracts, or select truth.
- Local LLM dogfood:
  - `GENESISOS_OLLAMA_MODEL=qwen3:8b python -m genesisos.cli diverge --goal "AIOS agents keep converging on contracts and dashboards instead of inventing a new interaction ritual" --generated --json`
    produced five branch augmentations with `generation.status: generated` and
    `generation_policy: local_helper_optional_with_heuristic_fallback`.
  - The generated sample named a non-template interaction-ritual frame:
    predictability over creativity, rigid protocol adherence, and the need for
    ambiguity-rewarding rituals.
- Fallback evidence:
  - Unit tests cover helper-unavailable mode returning `status: unavailable`
    while preserving heuristic fallback.
  - Default `diverge` without `--generated` still emits the existing branch
    types and stop conditions.
- Verification:
  - `cd GenesisOS && python -m pytest tests -q` passed 55/55.
  - `cd GenesisOS && git diff --check` passed before commit.
