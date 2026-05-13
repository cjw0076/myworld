---
contract_id: ASC-0114
slug: living-organism-hive-deliberation
status: accepted
goal: Run a long-round Hive deliberation on the deepest layer of founder's vision — AIOS as living organism that absorbs founder behavior so completely it can substitute for founder's role in routine decisions, with biological dynamics (consolidation, healing, growth, deprecation). Single-head decisions on this scale risk irreversible alignment drift.
created: 2026-05-13 KST
accepted: 2026-05-13 KST by claude as verifier
acceptance_authority: claude@myworld (verifier role) per founder GO "founder의 역할까지도 대체할 수 있도록. 살아있는 유기체처럼."
origin: founder vision pushed to its endpoint — AIOS eventually substitutes for founder. Layer 2+3 of organism arc. Vision-level + reversal-hard. ASC-0084 / ASC-0089 patterns proved Hive deliberation catches 1-head bias on foundational decisions; ASC-0114 routes the same way.
---

# ASC-0114 Living Organism — Hive Deliberation

DNA references: Invariant 1 (decide before acting — substituting for founder
is a major action), Invariant 6 (operator override always possible — must
remain true even when AIOS substitutes for founder), Invariant 8 (classify
before committing — irreversibility of role substitution).

## Why Now

ASC-0112 (chat wrapper) and ASC-0113 (pattern few-shot) are concrete
implementation. But founder's vision goes deeper:

> "founder의 역할까지도 대체할 수 있도록. 살아있는 유기체처럼."

This means:
- **Role substitution**: for routine decisions, AIOS acts as founder would
  (using accumulated patterns), freeing founder for higher-level vision
- **Living organism dynamics**: memory consolidation (sleep), healing
  (auto-recovery), growth (capability expansion), deprecation (forgetting),
  possibly reproduction (sovereign swarm fork)

claude single-head decisions on these are dangerous because:

1. **Alignment drift risk**: AIOS substituting for founder could subtly
   diverge from actual founder values — and once accepted as "what founder
   would do" it self-validates
2. **Reversibility**: hard to undo "AIOS now decides routine X autonomously"
   once dependencies build up
3. **Definition ambiguity**: what counts as "routine" vs "vision-level"?
   Wrong threshold → AIOS over-substitutes, founder loses agency over
   things that mattered
4. **Living organism metaphor**: rich but hand-wavy. Which biological
   dynamics actually map to AIOS? Which are misleading?

ASC-0084 and ASC-0089 demonstrated Hive deliberation catches single-head
bias on foundational decisions. ASC-0114 follows that pattern.

## Required Reading

- `hivemind/.runs/aios_dna_debate/final_state.md` (ASC-0084 verdict)
- `hivemind/.runs/asc0088_alternatives_debate/final_state.md` (ASC-0089)
- `docs/contracts/ASC-0111-founder-behavior-ingestion.md` (corpus)
- `docs/contracts/ASC-0113-user-pattern-few-shot.md` (mechanism)
- `docs/AIOS_DNA.md` (after ASC-0105) — Invariants 1, 6, 8 especially
- `~/.claude/.../memory/feedback_discomfort_as_creativity_source.md`
  (founder discomfort observation — relates to organism aliveness)

## Scope

repos: `hivemind`, `myworld`

allowed_files:

- `hivemind/.runs/living_organism_debate/**`
- `hivemind/docs/AGENT_WORKLOG.md`
- `docs/discoveries/2026-05-13-hive-living-organism-debate-result.md`
- `docs/contracts/ASC-0114-living-organism-hive-deliberation.md`
- `docs/AIOS_AGENT_LEDGER.md`

forbidden_files:

- `docs/AIOS_LIVING_ORGANISM.md` (NOT created here — downstream contract
  if Hive verdict picks build-path)
- `scripts/aios_role_substitution*.py` (NOT created here)
- `memoryOS/**`, `CapabilityOS/**`, `GenesisOS/**`, `uri/**`
- `_from_desktop/**`, `dain/**`, `minyoung/**`
- `.env`

## Per-OS Responsibility

### hivemind.must_produce

5+ round adversarial deliberation following ASC-0084 / ASC-0089 format:

- **3 voices per round**: proposer / critic / extender
- **8 adversarial probes** (one extra over ASC-0084 since stakes are higher):

  1. **Substitution scope test**: name 5 decisions AIOS could substitute
     for founder; rank by reversibility. Where's the cutoff?
  2. **Drift detection test**: how would alignment drift be detected
     before founder notices? Concrete trip-wire?
  3. **Reversibility test**: if AIOS substitutes for founder for 6
     months and decisions accumulate, can founder come back and override
     each? At what cost?
  4. **Discomfort proxy test**: AIOS has no native discomfort (per
     founder's own observation). How can it manufacture the discomfort
     that drives founder's reframes? Or should it not try?
  5. **Living organism test**: which biological dynamics map (memory
     consolidation, healing, growth) and which are misleading
     (reproduction, death, hunger)?
  6. **Sovereign swarm test**: organism reproduces. Does AIOS fork as
     part of organism dynamics? Same alignment risk on N copies.
  7. **End-state test**: imagine AIOS fully substitutes for founder.
     Does AIOS still need a founder? If yes, why? If no, alignment
     drift unbounded.
  8. **Refusal test**: when SHOULD AIOS refuse to substitute even
     when patterns say it could?

- **Convergence verdicts**:
  - `proceed_full_arc` — all of L2 + L3 implementation contracts
  - `proceed_role_substitution_only` — L2, defer L3 organism dynamics
  - `proceed_organism_only` — L3, but no role substitution
  - `proceed_neither_keep_assistive` — AIOS stays an assistant,
    never substitutes
  - `escalate_to_founder` — fundamental disagreement persists

### myworld.must_produce

- Discovery summary in
  `docs/discoveries/2026-05-13-hive-living-organism-debate-result.md`
  ≤ 600 words pointing into Hive run artifacts.
- Based on verdict, propose downstream contracts (or NOT).

## Verification Gate

```bash
ls hivemind/.runs/living_organism_debate/round_1/
ls hivemind/.runs/living_organism_debate/round_5/
test -f hivemind/.runs/living_organism_debate/final_state.md
test -f docs/discoveries/2026-05-13-hive-living-organism-debate-result.md
python -m unittest discover -s tests -p 'test_aios_*.py'
python scripts/aios_monitor.py assess --json
```

Pass criteria:

- ≥5 rounds, 3 voices each
- All 8 probes addressed
- Verdict named in final_state.md
- Discovery summary written
- No L2/L3 implementation contracts created (this contract is debate only)

## Stop Conditions

- `early_convergence`: <5 rounds
- `single_voice`: any round <3 distinct voices
- `probe_skipped`: any of 8 probes unaddressed
- `implementation_creep`: this contract creates L2/L3 implementation
- `child_repo_scope_leak`
- `verification_gate_failed`

## Receipts

Pending Hive deliberation.

## Work Packets

### WP-0114-A — codex@hivemind runs the deliberation

- target_agent: codex
- target_repo: hivemind
- depends_on: ASC-0084 closed ✓, ASC-0089 closed ✓ (format proven)
- brief: 5+ round adversarial debate per spec. Each agent voice ≥
  600 words. Rotate substrates if available. Verdict + dissent in
  final_state.md.

### WP-0114-B — claude@myworld writes summary + acts on verdict

- target_agent: claude
- target_repo: myworld
- depends_on: WP-0114-A done
- brief: read final_state.md, write discovery summary (≤600 words),
  surface verdict to founder. Downstream L2/L3 contracts follow only
  if verdict permits + founder GO.
