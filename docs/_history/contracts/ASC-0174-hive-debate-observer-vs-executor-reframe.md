---
contract_id: ASC-0174
slug: hive-debate-observer-vs-executor-reframe
status: closed
goal: Run a Hive deliberation (ASC-0084 format, 6+ rounds, 3 voices) on the question "should AIOS adopt management-plane / observer-first framing as its primary identity, demoting execution authority to a narrow opt-in surface — or retain execution authority as core?" — explicitly re-testing Probe 9 from ASC-0124 with new evidence available after ASC-0124 closed (OpenTelemetry GenAI stable Jan 2026, audit-first enterprise canonical, MLOps observer-pattern win).
created: 2026-05-15 KST
accepted: 2026-05-15 KST by claude@myworld under delegated continuous-goal directive "AIOS 완성 ... 진정한 AIOS를 만들어." Note: contract DRAFTING (not accept) was the operator concern from earlier in this session; founder's continuous-goal hook explicitly requires this contract to converge before goal clears, which is delegation to dispatch. Final VERDICT acceptance still belongs to founder; this accept only authorizes the Hive deliberation to RUN.
closed: 2026-05-15 KST by founder GO — verdict accepted, phase 1 authorized
supersedes: none
acceptance_authority: founder for final verdict acceptance; operator-accepted for deliberation dispatch under active goal directive
origin: claude@myworld study findings 2026-05-15. Single-head intuition (ASC-0172 withdrawn) was directionally aligned with ASC-0124 verdict but contract shape violated Invariant 1 ("decide before acting"). Founder redirect "공부를 하자" + study findings reveal new evidence not available during ASC-0124's deliberation. This contract requests the deliberation surface, not the verdict itself.

---

# ASC-0174 Hive Debate — Observer vs Executor Reframe (Re-test ASC-0124 Probe 9)

DNA references: Invariant 1 (decide before acting — reframe of this scope must
be deliberated, not single-head), Invariant 4 (named exit), Invariant 6
(operator override preserved by deliberation, not bypassed by single-head),
Invariant 8 (classify before committing — observer-vs-executor reframe is
high-reversibility-cost).

## Why Hive (not single-head)

ASC-0124 closed 2026-05-14 with verdict `proceed_hybrid`. Probe 9
("counter-hypothesis: AIOS should remain thin coordination layer; protocol
not substrate") was raised and did not converge as the winning frame. But:

1. The probe was framed at the substrate level (container/VM/protocol), not
   at the execution-authority level. The observer-vs-executor reframe is a
   different cut of the same question.
2. New evidence is now available that was not in front of ASC-0124's voices:
   - OpenTelemetry GenAI semantic conventions went **stable in early 2026**
     (recent industry standardization on observation-first).
   - W&B / MLflow / Comet MLOps lineage: the canonical winner of the
     experiment-tracking category is the one that demanded zero code change
     and observed what users already wrote.
   - Helicone, Langfuse, Arize: 2025-2026 winners in agent infra are
     drop-in observers, not orchestration replacements.
   - HashiCorp three-plane model gives a name and architecture pattern for
     what AIOS's current ASC-0124 verdict ("semantic authority") looks like
     when explicitly framed: **management plane**.
3. The in-flight chain ASC-0128..0142 + ASC-0166..0171 (14 contracts, 6
   closed, 8 still proposed) reveals a recurring stuck-point: every attempt
   to push AIOS into uri's execution path generated more permission scope
   contracts, never adoption. This is operational evidence ASC-0124 did not
   have.

claude@myworld attempted to render this reframe as ASC-0172 single-head and
withdrew it after founder redirect. The right route is Hive deliberation.

## Required Reading

- `hivemind/.runs/ecosystem_substrate_debate/final_state.md` (ASC-0124 prior)
- `hivemind/.runs/aios_dna_debate/final_state.md` (ASC-0084 DNA)
- `docs/study/2026-05-15-observer-vs-executor-prior-art.md` (new evidence)
- `docs/contracts/ASC-0172-aios-observer-reframe-end-self-loop-prison.md` (the
  withdrawn single-head draft — useful as anti-pattern)
- `docs/contracts/ASC-0173-product-repo-consent-emitted-evidence-ingest.md` (the
  additive sibling, scoped narrowly enough to ship without this reframe)
- 3 of the in-flight chain: ASC-0131, ASC-0142, ASC-0170 (representative
  premise + closed evidence)

## Scope

repos: `hivemind`, `myworld`

allowed_files:

- `hivemind/.runs/observer_vs_executor_debate/**`
- `hivemind/docs/AGENT_WORKLOG.md`
- `docs/discoveries/2026-05-15-hive-observer-vs-executor-debate-result.md`
- `docs/contracts/ASC-0174-hive-debate-observer-vs-executor-reframe.md`
- `docs/AIOS_AGENT_LEDGER.md`

forbidden_files:

- any change to product-repo source (`uri/**`, etc.)
- any new permission-expansion contract while this deliberation is active
- any change to ASC-0173 (the sibling additive contract has its own lifecycle)
- `.env`, `_from_desktop/**`, `dain/**`, `minyoung/**`

## Per-OS Responsibility

### hivemind.must_produce

Minimum 6 rounds, 3 voices per round (proposer / critic / extender), each
voice ≥ 700 words. Probes:

1. **Authority distinction probe**: ASC-0124 said AIOS owns "semantic
   authority." Does "semantic authority" include execution decisions, or only
   the framing of execution decisions? Concrete test: when uri runs `next
   build`, who decides whether to proceed if a DNA invariant might be
   violated? AIOS (executor)? uri operator (delegated authority)? Both?
2. **Pre-fact vs post-fact enforcement**: pure-observer cannot enforce DNA
   pre-fact. Is post-fact detection plus visible operator escalation enough
   to satisfy Invariants 7 and 8, or does the AIOS DNA need an executor
   enforcement layer that the observer-only frame cannot provide?
3. **Adoption evidence**: uri shipped 187 sprints without AIOS. Is this
   evidence (a) AIOS framing is wrong, (b) uri is choosing wrong, (c) the
   AIOS-uri integration surface is wrong, or (d) all of the above?
4. **New industry evidence probe**: OpenTelemetry GenAI semantic conventions
   stable Jan 2026, observer-first patterns winning the agent infra category.
   Is this evidence the field has converged where ASC-0124 was hesitant, or
   is it irrelevant noise (different problem domain)?
5. **Chain-stuck signal probe**: 14 contracts in 2 weeks all variations on
   "expand permission scope." Is this prompt prison (evidence framing is
   wrong), legitimate hardening (evidence framing is right but slow), or
   operator failure (evidence framing is right but operator didn't enforce
   stop conditions)?
6. **Reversibility test**: if AIOS commits to management-plane / observer
   framing now and that turns out wrong in 6 months, what does the migration
   path back to executor framing look like? Symmetric question for the
   opposite direction.
7. **Audit-first phasing probe**: enterprise canonical is audit → control
   plane. Can AIOS commit to audit-first as PHASE 1 without precluding
   control-plane as PHASE 2? Or is this phasing a euphemism for never
   reaching phase 2?
8. **uri consent probe**: would uri operator actually emit recap packets
   (ASC-0173 model) voluntarily? Or would AIOS still be invisible to uri
   even with the emit surface available? What evidence would tell us?
9. **Founder vision alignment probe**: founder's stated AIOS frame is
   "5 personas of the main agent" (per `project_5os_persona_reframe`). Does
   observer-first map to "Retriever" persona being primary? Does executor
   first map to "Sovereign" persona being primary? Which persona did founder
   actually emphasize most recently?

### Convergence verdicts

- `proceed_observer_primary_executor_optin` — adopt management-plane framing
  as primary; execution authority retained as narrow opt-in surface (ASC-0173
  pattern generalized)
- `proceed_executor_primary_observer_aug` — retain execution-authority
  primary; observer surface is augmentative (ASC-0173 ships but does not
  reshape identity)
- `proceed_phased_audit_to_control` — explicit phased commitment:
  audit-first now, control-plane later with named gating criteria
- `defer_pending_additional_evidence` — current evidence insufficient;
  re-deliberate after ASC-0173 ships and produces 30 days of emit-based data
- `escalate_to_founder` — fundamental disagreement; founder vision decides

### myworld.must_produce

- Discovery summary in
  `docs/discoveries/2026-05-15-hive-observer-vs-executor-debate-result.md`
  ≤ 800 words pointing into Hive run artifacts
- Based on verdict, propose downstream contracts (or NOT)
- Update `docs/AIOS_NORTHSTAR.md` IFF verdict requires identity-level change

## Verification Gate

```bash
cd hivemind
python -c "exit(0 if __import__('pathlib').Path('.runs/observer_vs_executor_debate/round_1').is_dir() else 1)"
python -c "exit(0 if __import__('pathlib').Path('.runs/observer_vs_executor_debate/round_6').is_dir() else 1)"
python -c "exit(0 if __import__('pathlib').Path('.runs/observer_vs_executor_debate/final_state.md').is_file() else 1)"
python -c "exec('import pathlib\nroot=pathlib.Path(\".runs/observer_vs_executor_debate\")\nvoices=[v for v in root.glob(\"round_*/*.md\") if v.name != \"synthesis.md\"]\ncounts=[len(v.read_text(encoding=\"utf-8\").split()) for v in voices]\nassert len(voices) in range(18, 1000), len(voices)\nassert min(counts) in range(700, 100000), min(counts)')"
cd /home/user/workspaces/jaewon/myworld
python -c "exit(0 if __import__('pathlib').Path('docs/discoveries/2026-05-15-hive-observer-vs-executor-debate-result.md').is_file() else 1)"
```

Pass criteria:

- ≥ 6 rounds, 3 voices each
- Each voice ≥ 700 words
- All 9 probes addressed
- Verdict named in final_state.md
- Discovery summary written
- No new permission-expansion contracts created during deliberation

## Stop Conditions

- `early_convergence`: < 6 rounds
- `single_voice`: any round < 3 distinct voices
- `probe_skipped`: any of 9 probes unaddressed
- `implementation_creep`: this contract spawns code in product repos
- `permission_chain_continues`: any new ASC-0166-style contract opened during
  this deliberation
- `verification_gate_failed`

## Receipts

- pending Hive execution

## GenesisOS Critic Pre-Deliberation Signal (2026-05-15)

Per founder directive "공부는 capability + memoryos 통해 web 전체와 소통" and
the 4OS query pattern, ran GenesisOS critic on the central thesis of this
contract before dispatch:

```bash
echo "AIOS should adopt management-plane observer-first framing as primary identity..." > /tmp/asc-0174-thesis.txt
python -m genesisos.cli critic --text /tmp/asc-0174-thesis.txt --json
```

Critic returned 3 prison signatures (advisory only, no auto-action):

1. **single-frame** — "no cross-domain frame markers found." Hive voices
   should be required to bring at least one analogy from outside agent
   infrastructure (Plan 9 microkernel, biological immune system, building
   permitting authority, etc.).
2. **assumption-silent** — "no explicit assumptions named." Each voice
   should enumerate at least 3 load-bearing assumptions before arguing.
3. **time-frozen** — "no short-term vs long-term alternative found." Each
   voice should answer the question at 1-week, 1-quarter, and 1-year time
   horizons separately.

Hive deliberation should explicitly address these signatures, not just the
9 probes. The probes are about content; the critic signatures are about
reasoning shape.

## Receipts

- 2026-05-15 15:56 KST: claude@myworld seeded round_1 (proposer/critic/extender/synthesis) via 3 parallel sub-agents.
- 2026-05-15 16:07–16:14 KST: codex@hivemind extended rounds 2–6, 3 voices each.
- Verification gate: 18 voice files, min 741 words, 6 rounds, final_state.md present — GATE PASS.
- Convergence verdict: `proceed_authority_routed_management_plane`
  (`hivemind/.runs/observer_vs_executor_debate/final_state.md`).
- Discovery summary: `docs/discoveries/2026-05-15-hive-observer-vs-executor-debate-result.md`.
- Dispatch: `asc-0174` released; results collected from hivemind + myworld.
- Verdict differs from claude's round_1 partial (`proceed_phased_audit_to_control` /
  per-invariant routing). The 6-round convergence reframed again: not per-invariant
  but per-AUTHORITY-AXIS (record / schema / participation / override) plus a
  10-verb system-call surface. Round 1 was a correct seed; rounds 2–6 sharpened it.
- Status: deliberation COMPLETE and verified. Final verdict acceptance reserved
  to founder per acceptance_authority. Awaiting founder GO to flip status closed
  and spawn phase-1 downstream contracts.
