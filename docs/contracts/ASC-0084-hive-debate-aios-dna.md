---
contract_id: ASC-0084
slug: hive-debate-aios-dna
status: closed
goal: Run a long-round Hive Mind deliberation on the proposed AIOS DNA (7 invariants framing) before any DNA spec is written, so the spec is shaped by adversarial multi-agent review rather than a single operator's draft.
created: 2026-05-13 KST
accepted: 2026-05-13 KST by claude acting operator (founder directive "hive로 토론 진행해. round는 길게")
closed: 2026-05-13 KST by codex@myworld after hivemind fallback completion
acceptance_authority: claude@myworld (operator) per founder delegation. Founder explicitly chose Hive deliberation over operator-drafted spec — DNA is too foundational to ship from one head.
origin: founder turn 2026-05-13 KST proposing "DNA-level adaptation" framing instead of feature-by-feature engineering. Operator (claude) drafted 7-invariant candidate list; founder routed to Hive instead of accepting directly.
---

# ASC-0084 Hive Debate — AIOS DNA Specification

## Why Now

Founder turn 2026-05-13 KST raised a deeper framing: AIOS shouldn't try
to do every feature *well* across every environment. Instead, encode
**DNA-level invariants** — the small set of things that MUST stay true
regardless of substrate, OS, scale, language, or user. Phenotype
(actual feature implementation) adapts; genome (invariants) is conserved.

Claude proposed an initial 7-invariant DNA candidate:

1. Recommendation-only (no auto-binding)
2. Draft-first (accept requires explicit review)
3. Append-only audit (ledger never edited, contracts never re-numbered)
4. Stop conditions named (no silent failure)
5. Provenance chain (every record carries derives_from / evidence_refs)
6. Operator override always possible (automation is last resort)
7. Privacy boundary inviolable (founder-gated paths + secrets never leak)

Founder explicitly chose **Hive deliberation over operator draft**:

> "hive로 토론 진행해. round는 길게"

Rationale: a 7-invariant DNA is too foundational to ship from one
operator's draft. Hive Mind's role is *adversarial* multi-agent
verification — it should run multiple rounds of challenge before any
candidate makes it into a spec contract.

## Scope

repos:

- `hivemind`
- `myworld`

allowed_files:

- `hivemind/.runs/aios_dna_debate/**` (deliberation artifacts under Hive's run namespace)
- `hivemind/docs/AGENT_WORKLOG.md`
- `docs/discoveries/2026-05-13-hive-aios-dna-debate-result.md`
- `docs/contracts/ASC-0084-hive-debate-aios-dna.md`
- `docs/contracts/README.md`
- `docs/AIOS_AGENT_LEDGER.md`

forbidden_files:

- `docs/AIOS_DNA.md` (NOT created here — that is a downstream contract
  AFTER Hive deliberation completes; this contract only deliberates)
- `memoryOS/**`, `CapabilityOS/**`, `uri/**`, `GenesisOS/**`
- `_from_desktop/**`, `dain/**`, `minyoung/**`
- `.env`

## Per-OS Responsibility

### hivemind.must_produce

A multi-round adversarial debate following these rules:

#### Debate format

- **Minimum rounds: 5**. No early convergence allowed. Even if all
  participants agree by round 2, deliberation continues to round 5
  to surface latent disagreements + edge cases.
- **At least 3 distinct agent voices per round**:
  - `proposer` — argues for accepting the candidate invariant set
  - `critic` — actively tries to break each invariant (counter-examples,
    edge cases, contradictions)
  - `extender` — proposes additions, removals, or rewordings
- **Round artifacts**: each round writes to
  `hivemind/.runs/aios_dna_debate/round_<N>/{proposer,critic,extender}.md`
  with the agent's argument for that round.
- **Synthesis after each round**: a `round_<N>/synthesis.md` notes
  what changed in the candidate set, what is now disputed, what is
  newly raised.

#### Required adversarial probes (critic must address each at least once across rounds)

1. **Substrate test**: name a substrate where each invariant cannot be
   enforced. If found, is it a real risk or is the substrate disqualified?
2. **Scale test**: at 1B users, does each invariant still hold? Where
   does it break?
3. **Adversary test**: can a malicious peer / agent / user violate each
   invariant without detection? If yes, is it acceptable risk?
4. **Composability test**: do any two invariants conflict in some
   plausible scenario? E.g. "operator override always possible" vs
   "privacy boundary inviolable" — what if operator wants to override
   privacy?
5. **Drift test**: 5 years from now, which invariant is most likely to
   need amendment? Why?
6. **Minimal set test**: can any invariant be DERIVED from the others?
   If yes, drop it (DNA should be minimal).
7. **Missing test**: what invariant is MISSING that would be obvious
   to a different framing (biology, constitutions, OS design,
   distributed systems)?

#### Convergence criteria

After minimum 5 rounds, debate may converge to one of:

- `unanimous_accept` — all agents agree to a final invariant set
- `accept_with_dissent` — majority accepts but dissenting view is
  documented as future-revisit candidate
- `escalate_to_founder` — fundamental disagreement persists; flag
  for founder vision-level decision
- `reject` — no coherent invariant set survives all probes; recommend
  no DNA spec at this time

The debate transcript + final state is the contract deliverable. The
actual `docs/AIOS_DNA.md` spec writing is a SEPARATE downstream
contract — this contract only produces the deliberation evidence.

### myworld.must_produce

- `docs/discoveries/2026-05-13-hive-aios-dna-debate-result.md` —
  human-readable summary of debate outcome (≤ 500 words), pointing
  into Hive's run artifacts for full transcript.
- Closeout commit + ledger entry.

### memoryos / capabilityos / GenesisOS

- No source change. Future contracts may import deliberation outcomes
  as memory drafts or capability observations — out of scope here.

## Verification Gate

```bash
ls hivemind/.runs/aios_dna_debate/round_1/  # must exist
ls hivemind/.runs/aios_dna_debate/round_5/  # minimum 5 rounds
test -f hivemind/.runs/aios_dna_debate/final_state.md
test -f docs/discoveries/2026-05-13-hive-aios-dna-debate-result.md
python -m unittest discover -s tests -p 'test_aios_*.py'
python scripts/aios_monitor.py assess --json
```

Pass criteria:

- ≥ 5 rounds with proposer/critic/extender artifacts each
- 7 adversarial probes addressed (synthesis docs cite each)
- Convergence verdict named (unanimous_accept / accept_with_dissent /
  escalate_to_founder / reject)
- Discovery summary in myworld points into Hive run artifacts
- No DNA spec file created (that's downstream)

## Stop Conditions

- `early_convergence`: debate ends before round 5
- `single_voice`: any round has fewer than 3 distinct agent voices
- `probe_skipped`: any of the 7 adversarial probes is not addressed
- `dna_spec_creation`: this contract creates `docs/AIOS_DNA.md`
  (separate downstream contract owns that)
- `child_repo_scope_leak`
- `verification_gate_failed`

## Receipts

- hive result packet: `.aios/outbox/hivemind/asc-0084.hivemind.result.json`
  with `status=passed`, `fallback_used=true`, and final agent `claude`.
- hive artifacts: `hivemind/.runs/aios_dna_debate/round_1/` through
  `round_5/`, each with proposer/critic/extender/synthesis artifacts.
- final state: `hivemind/.runs/aios_dna_debate/final_state.md`
- myworld summary:
  `docs/discoveries/2026-05-13-hive-aios-dna-debate-result.md`

## Work Packets

### WP-0084-A — codex@hivemind runs the debate

- target_agent: codex
- target_repo: hivemind
- status: done
- closed: 2026-05-13 KST
- depends_on: ASC-0065 (GenesisOS), ASC-0066 (provider role distillation)
  closed for context but not strict prerequisites.
- brief: |
    Run a 5+ round adversarial Hive deliberation on the candidate
    AIOS DNA invariant set in this contract's "Why Now" section.

    Format: each round produces 3 artifacts (proposer / critic /
    extender) + 1 synthesis. Critic must address all 7 adversarial
    probes across the 5 rounds (one or more per round, all 7 covered
    by round 5).

    Long rounds: do not optimize for fast convergence. The point is
    to surface hidden disagreement + edge cases. Rounds should average
    ≥ 800 words per agent voice.

    After round 5+, write final_state.md naming the convergence verdict
    and the (possibly modified) invariant set + any dissenting notes.

    Use whatever Hive worker / local LLM substrate is most cost-
    efficient for the proposer/critic/extender roles. If multiple
    substrates are available, rotate them across rounds to avoid
    single-substrate bias.
- result: `.aios/outbox/hivemind/asc-0084.hivemind.result.json`

### WP-0084-B — claude@myworld writes discovery summary

- target_agent: claude
- target_repo: myworld
- status: done
- closed: 2026-05-13 KST
- depends_on: WP-0084-A done
- brief: |
    Read final_state.md + synthesis docs. Write
    docs/discoveries/2026-05-13-hive-aios-dna-debate-result.md
    summarizing: convergence verdict, final invariant set, key
    disagreements that survived, recommendations for the downstream
    DNA spec contract.
- result: `docs/discoveries/2026-05-13-hive-aios-dna-debate-result.md`
