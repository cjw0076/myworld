---
contract_id: ASC-0089
slug: hive-debate-asc0088-alternatives
status: closed
goal: Hive deliberation on ASC-0088 alternatives (B1 tiny spec / B2 HTTP / B3 library / B4 augment ASC-0087 / B5 full spec) to choose the right shape for AIOS Universal Agent Interface, since claude's auto-accept of B5 was founder-flagged as prompt-prison.
created: 2026-05-13 KST
accepted: 2026-05-13 KST by claude acting operator
closed: 2026-05-13 KST by codex@myworld after hivemind fallback completion
acceptance_authority: founder directive 2026-05-13 KST "hive 사용해서 토론해봐" — explicitly route ASC-0088 alternative selection through Hive instead of operator decision.
origin: ASC-0088 was auto-accepted by claude → founder corrected ("AIOS처럼 동작해") → claude held ASC-0088 + surfaced 5 branches → founder directs Hive deliberation.
---

# ASC-0089 Hive Debate — ASC-0088 Alternative Selection

## Why Now

ASC-0088 (AIOS Universal Agent Interface) is currently held. Five
alternatives exist:

- **B1** Tiny spec (~50 lines), no buffer/sync infrastructure
- **B2** HTTP endpoint — agents POST to local AIOS daemon
- **B3** Library — `pip install aios-observe`, single function call
- **B4** Augment ASC-0087's `_shared_invariants.md` block with protocol;
       no separate spec file (single-source via include)
- **B5** Full standalone spec + buffer/sync infrastructure (current ASC-0088 draft)

claude's prior judgment leaned B4 but was self-critique, not adversarial
review. Founder routes to Hive. Same long-round format as ASC-0084
(DNA debate) so the operator pair doesn't sneak in convergent-default
selection.

## Scope

repos:

- `hivemind`
- `myworld`

allowed_files:

- `hivemind/.runs/asc0088_alternatives_debate/**`
- `hivemind/docs/AGENT_WORKLOG.md`
- `docs/discoveries/2026-05-13-hive-asc0088-alternatives-debate-result.md`
- `docs/contracts/ASC-0089-hive-debate-asc0088-alternatives.md`
- `docs/contracts/README.md`
- `docs/AIOS_AGENT_LEDGER.md`

forbidden_files:

- `docs/AIOS_AGENT_INTERFACE.md` (NOT created here — downstream)
- `docs/contracts/ASC-0088-aios-universal-agent-interface.md` (read-only;
  result determines whether ASC-0088 is released, superseded, or
  refactored)
- `memoryOS/**`, `CapabilityOS/**`, `uri/**`, `GenesisOS/**`
- `_from_desktop/**`, `dain/**`, `minyoung/**`
- `.env`

## Per-OS Responsibility

### hivemind.must_produce

Same long-round adversarial format as ASC-0084:

- **Minimum 5 rounds**, no early convergence
- **3 voices per round**: proposer / critic / extender
- **7 adversarial probes addressed across 5 rounds**:
  1. **Cost test**: implementation effort + maintenance cost per option
  2. **Drift risk**: how badly does each option drift over 6 months?
  3. **Scaling test**: does each option work at 1B agents?
  4. **Migration path**: if we pick B1 today, can we upgrade to B5 later? Reverse?
  5. **Minimal-surface test**: which option has smallest blast radius?
  6. **Failure recovery test**: what happens when each option breaks (sync fails, spec drifts, library has bug)?
  7. **Substrate-equivalence test**: which option lets a local LLM use AIOS most easily?
- **Per-round artifacts** in `hivemind/.runs/asc0088_alternatives_debate/round_<N>/{proposer,critic,extender,synthesis}.md`
- **Convergence verdict** in `final_state.md`:
  - `pick_B1` / `pick_B2` / `pick_B3` / `pick_B4` / `pick_B5`
  - or `combine_<X>_then_<Y>` (e.g. start with B4, graduate to B5 if drift)
  - or `escalate_to_founder` (Hive disagreement persists)

### myworld.must_produce

- Discovery summary in
  `docs/discoveries/2026-05-13-hive-asc0088-alternatives-debate-result.md`
  (≤ 400 words) pointing into Hive run artifacts.
- Based on Hive verdict:
  - if `pick_B5`: release ASC-0088
  - if `pick_B4`: supersede ASC-0088 with new contract that augments ASC-0087
  - if `pick_B1/B2/B3`: supersede with new contract for that branch
  - if `escalate_to_founder`: surface to founder
- Closeout commit + ledger entry

### memoryos / capabilityos / GenesisOS / uri

- No source change.

## Verification Gate

```bash
ls hivemind/.runs/asc0088_alternatives_debate/round_1/
ls hivemind/.runs/asc0088_alternatives_debate/round_5/
test -f hivemind/.runs/asc0088_alternatives_debate/final_state.md
test -f docs/discoveries/2026-05-13-hive-asc0088-alternatives-debate-result.md
python -m unittest discover -s tests -p 'test_aios_*.py'
python scripts/aios_monitor.py assess --json
```

Pass criteria:

- ≥5 rounds with 3 voices each
- 7 probes addressed
- Verdict named in final_state.md
- Discovery summary written
- ASC-0088 status updated based on verdict (released / superseded /
  escalated) — but the ASC-0088 file itself is read-only here; the
  status update is a follow-up commit by operator after this contract closes

## Stop Conditions

- `early_convergence`
- `single_voice`
- `probe_skipped`
- `verdict_missing`
- `child_repo_scope_leak`
- `verification_gate_failed`

## Receipts

- hive result packet: `.aios/outbox/hivemind/asc-0089.hivemind.result.json`
  with `status=passed`, `fallback_used=true`, and final agent `claude`.
- archived first held result:
  `.aios/logs/asc-0089.hivemind.held-before-baseline-commit.result.json`
  after the initial run correctly stopped on `pending_concurrent_work`.
- hive artifacts:
  `hivemind/.runs/asc0088_alternatives_debate/round_1/` through `round_5/`
  plus `final_state.md`.
- myworld summary:
  `docs/discoveries/2026-05-13-hive-asc0088-alternatives-debate-result.md`

## Work Packets

### WP-0089-A — codex@hivemind runs the alternatives debate

- target_agent: codex
- target_repo: hivemind
- status: done
- closed: 2026-05-13 KST
- depends_on: none (ASC-0084 in-flight provides format reference)
- brief: |
    Run a 5+ round adversarial Hive deliberation on ASC-0088
    alternatives B1/B2/B3/B4/B5. Each round produces 3 voices +
    synthesis. Critic addresses all 7 probes across the rounds.

    Long rounds: do not converge fast. Each agent voice ≥ 600 words
    average per round.

    After round 5+, write final_state.md with verdict + dissent notes.
    Rotate substrates if multiple available.
- result: `.aios/outbox/hivemind/asc-0089.hivemind.result.json`

### WP-0089-B — claude@myworld writes summary + acts on verdict

- target_agent: claude
- target_repo: myworld
- status: done
- closed: 2026-05-13 KST
- depends_on: WP-0089-A
- brief: |
    Read final_state.md. Write discovery summary. Then:
    - if pick_B5: flip ASC-0088 status held → accepted, codex resumes
    - if pick_B4 or others: supersede ASC-0088 with new contract
    - if escalate: surface to founder
- result: `docs/discoveries/2026-05-13-hive-asc0088-alternatives-debate-result.md`
