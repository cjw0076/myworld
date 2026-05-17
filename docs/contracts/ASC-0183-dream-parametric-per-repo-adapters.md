---
contract_id: ASC-0183
slug: dream-parametric-per-repo-adapters
status: proposed
goal: Build dream phase 2 — periodic parametric self-evolution that re-fits a per-repo LoRA adapter from each OS's verified-good experience and hot-swaps it on context switch. The named heavier follow-on already declared in scripts/aios_self_evolve.py.
created: 2026-05-17 03:35 KST
proposed_by: claude@myworld
escalation: VISION-LEVEL — founder GO required before build (parametric mutation, hardware cost, catastrophic-forgetting risk).
origin: Founder framing (2026-05-17) — "when memory is idle, periodically consolidate (embed), and swap fine-tuned layers per repo — this is human 'dream'." AIOS already declared this: aios_self_evolve.py names "Parametric self-evolution (LoRA/QLoRA retrain on the verified set)" as the heavier follow-on and already produces the verified dataset it would train on.
---

# ASC-0183 Dream — Parametric Per-Repo Adapters

DNA references: Invariant 2 (draft-first — a re-fit adapter is a DRAFT, not
auto-bound), Invariant 4 (named exit), Invariant 6 (operator override),
Invariant 8 (no unearned promotion).

## The framing

AIOS already has both halves of "dream":

- **Phase 1 — consolidation.** `aios_dream.py` now embeds the memory
  append-store during the idle round (wired 2026-05-17). Hippocampal fast
  append during wake → neocortical slow indexing during dream.
- **Phase 2 — parametric replay (this contract).** `aios_self_evolve.py`
  today does *non-parametric* evolution: it distills verified-good helper
  invocations into a prompt-prepended principles file. Its docstring names
  the follow-on explicitly: re-fit a LoRA adapter on that verified set.

The founder's "fine-tuned layer per repo, swapped in" is exactly this: each
OS repo (hivemind / memoryOS / CapabilityOS / GenesisOS) gets its own LoRA
adapter trained on that repo's verified-good experience. Wake = base model +
the active repo's adapter. Dream = re-fit the adapters.

## Scope (proposed)

repos: `myworld` (orchestration); per-repo adapter artifacts live under each
sibling's `.aios/` (gitignored runtime state).

allowed (if accepted):

- `scripts/aios_adapter_evolve.py` (new — the dream phase-2 organ)
- `scripts/aios_self_evolve.py` (extend — emit the training set in a trainer-ready shape)
- `scripts/aios_round_controller.py` (new time-gated adapter_evolve step)
- `docs/AIOS_DEPLOY_MANIFEST.md` (declare the trainer dependency)

## Design (proposed)

1. **Dataset** — `aios_self_evolve.py` already gathers per-helper verified-good
   invocations. Phase 2 reuses that set, never raw/unverified output
   (self-distillation collapse guard, already doctrine).
2. **Train** — QLoRA fine-tune of the small local model (qwen3:1.7b/8b) on the
   per-repo verified set. Per-repo isolation is itself the catastrophic-
   forgetting mitigation: each adapter is narrow; the base model is untouched.
3. **Draft, not bind** — the re-fit adapter is written as a DRAFT adapter.
   It is NOT swapped into wake use until a verification gate (held-out
   verified invocations) shows it does not regress. Dream proposes; the
   deterministic kernel + operator promote. (Invariant 2.)
4. **Swap** — once promoted, the model-tier resolver loads base + repo adapter
   for that repo's specialist calls. Operator override always reverts to the
   bare base model. (Invariant 6.)

## GenesisOS Escape Review

This section is advisory-only and exists to keep the contract from becoming a
jargon loop.

### Assumptions

- Assumption 1: a repo-specific adapter can improve local style without
  corrupting the base model.
- Assumption 2: verified-good invocations are enough signal for a small adapter.
- Assumption 3: per-repo isolation is cheaper than one global personality.

Counter branch: negate those assumptions. If a repo adapter merely memorizes
old decisions, then the useful output is not a model layer but a better
retrieval and verifier loop. If the verified set is small, the right next step
is dataset quality scoring, not training.

### Plain Language

Plain language: when AIOS is idle, it studies only work that was already
verified as good. It may create a small removable training layer for each repo.
That layer is a draft until tests prove it helps, and the operator can turn it
off.

### Cross-Domain Frame

Biology analogy: this is closer to sleep replay than to rewriting DNA. The
organism keeps its body, rehearses useful movements, and refuses a rehearsal
that makes tomorrow's motion worse.

### Time Horizons

- 1h: produce only a trainer-ready verified dataset and do not train.
- 1 week: run one tiny adapter experiment on a small local model with a held-out
  no-regression check.
- 1 year: decide whether adapters remain local private organs or become an
  installable AIOS capability with explicit hardware and rollback contracts.

## Open questions for founder

- Hardware: QLoRA on qwen3:8b needs a GPU or a long CPU run. Acceptable to
  gate phase 2 on `--full` deploy / a GPU being present, and ship phase 1
  (consolidation) as the universal default?
- Cadence: re-fit per dream cycle is too frequent (not enough new verified
  data per 30 min). Propose: re-fit only when a repo has accrued ≥ N new
  verified-good invocations since its last adapter.

## Named Exit

Closed when: a per-repo adapter is re-fit from a verified set, gated as a
draft, passes the no-regression check, and is swappable by the tier resolver
with an operator-override path to the bare base model.

## Stop Conditions

- No GPU and CPU re-fit exceeds the round budget → ship phase 1 only, hold
  phase 2 until hardware is present (do not block the autopoietic loop).
- A re-fit adapter regresses on held-out verified invocations → discard the
  draft, keep the prior adapter, record the regression as negative evidence.
