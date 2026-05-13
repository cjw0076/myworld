---
contract_id: ASC-0121
slug: strict-close-condition
status: accepted
goal: Forbid contract closure when stated goal is verifiably unmet. Today ASC-0110 (memoryOS retrieval broken) was closed despite retrieval STILL returning selected=0 for the same queries the contract listed as proof of breakage. Closure became a paperwork milestone, not a goal-met assertion.
created: 2026-05-13 KST
accepted: 2026-05-13 KST by claude as verifier (round 7 — deepest discomfort yet)
acceptance_authority: claude@myworld (verifier role) per founder /loop directive — "계속 Contract를 발행해" + governance theater concern
origin: 2026-05-13 round 7 — ASC-0110 status flipped to closed. Re-running its own evidence query (`context build "founder DNA invariants"`) returns selected=0, identical to the broken state ASC-0110 was issued to fix. Receipt itself acknowledges "WP-0110-A still needs MemoryOS-owned diagnosis/fix". Closed contract did NOT close gap.
---

# ASC-0121 Strict Close Condition

DNA references: Invariant 4 (every loop has named exit — but not "fake exit"),
Invariant 5 (provenance — closure must trace to actually-met criteria),
Invariant 8 (classify before committing — closing requires final classification
of goal-met vs goal-unmet vs partial-with-followup).

## Why Now (the cleanest fake-close in this session)

Verified 2026-05-13 round 7:

```
ASC-0110 (memoryOS retrieval broken):
  status: closed
  Pass criteria from contract body:
    "DNA Invariant 5 — drafts retrievable by their own evidence_refs / derives_from terms"
    "Audit shows ≥50% retrieval rate (improvement from 0%)"
    "ASC-0091 dogfood draft mem_940ad99fcc2ed445 retrievable by query containing 'ASC-0091'"
  Reality after closure:
    context build "founder DNA invariants" → selected=0  (still 0)
    audit script: 4/4 hits, but on a DIFFERENT QUERY SET than contract specified
    ASC-0091 draft retrieval: NOT VERIFIED in receipt
  Receipt admits: "WP-0110-A still needs MemoryOS-owned diagnosis/fix for the underlying retrieval semantics"
```

A contract whose own receipt says "still needs fix" is closed.

This is the cleanest example of governance theater this session. ASC-0106
(governance_audit) was issued to detect this — but ASC-0106 itself is
accepted, not yet implemented, so the audit wouldn't catch ASC-0110's
fake-close.

The deeper pattern: **closure is currently a paperwork milestone**
(receipt section non-empty + status flipped) rather than a **goal-met
assertion**.

## What "strict close" means

Three explicit close types, classified at close time (Inv 8):

- `closed_goal_met`: the stated goal verifiably accomplished — pass
  criteria evaluated and PASSED at closure time
- `closed_partial_with_followup`: stated goal partially met, with
  explicit named follow-up contract for the remainder. CANNOT close
  without naming the follow-up ASC-NNNN.
- `closed_goal_unmet_documented`: explicitly admitting the goal was
  not achieved with cited reason. Counts as failure for governance audit.

Plain `closed` becomes invalid. Existing contracts already plain-closed
get retro-classified by audit (assume `closed_partial_with_followup`
default with grace period).

## Required Reading

- `docs/contracts/ASC-0110-memoryos-retrieval-broken.md` (the example)
- `docs/contracts/ASC-0106-aios-governance-audit.md` (sister tool —
  measures, doesn't enforce)
- `scripts/aios_dispatch.py release` (where closure is committed)
- `docs/AIOS_DNA.md` (after ASC-0105) — Inv 4, 5, 8

## Scope

repos: `myworld`

allowed_files:

- `scripts/aios_dispatch.py` (release classification)
- `scripts/aios_close_condition.py` (NEW — pass-criteria evaluator)
- `tests/test_aios_close_condition.py`
- `tests/test_aios_dispatch.py` (extended)
- `docs/AIOS_CLOSE_CONDITION.md`
- `docs/contracts/README.md` (close vocabulary update)
- `docs/contracts/ASC-0121-strict-close-condition.md`
- `docs/AIOS_AGENT_LEDGER.md`

forbidden_files:

- `docs/contracts/ASC-*.md` except this one (close-classifier reads
  contracts; doesn't edit existing closures retroactively, only
  audits them)
- `hivemind/**`, `memoryOS/**`, `CapabilityOS/**`, `GenesisOS/**`, `uri/**`
- `_from_desktop/**`, `dain/**`, `minyoung/**`
- `.env`

## Per-OS Responsibility

### myworld.must_produce

`scripts/aios_close_condition.py`:

- input: contract path
- extracts pass criteria from contract body (looks for "Pass criteria:"
  section, bullets)
- attempts to evaluate each criterion programmatically:
  - if criterion cites a CLI command → run it, check exit
  - if criterion asserts numeric threshold → query corresponding metric
  - if criterion is purely textual → mark as `manual_evaluation_required`
- output: `{contract_id, criteria: [...], met: int, unmet: int,
  manual: int, recommended_close_type: closed_goal_met | _partial | _unmet}`

`aios_dispatch.py release` extension:

- before flipping status to closed, must call close_condition evaluator
- if any criterion `unmet`:
  - require `--close-type closed_partial_with_followup --followup-asc ASC-NNNN`
    OR `--close-type closed_goal_unmet_documented --reason <slug>`
- new flag `--operator-override-strict-close --reason <slug>` for
  emergency bypass (logged in dispatch.events)
- existing close path with no flags = ERROR if any criterion unmet

Retro-audit:

- a one-time script `aios_retro_close_classify.py` that classifies
  existing 80+ closed contracts as `_met`, `_partial`, or `_unmet`
  based on body inspection (no automatic re-opening — just labeling)

### child repos: no change

## Verification Gate

```bash
python -m py_compile scripts/aios_close_condition.py scripts/aios_dispatch.py
python -m unittest tests/test_aios_close_condition.py tests/test_aios_dispatch.py
# Test ASC-0110 specifically — should be marked unmet
python scripts/aios_close_condition.py docs/contracts/ASC-0110-memoryos-retrieval-broken.md --json | python -c "
import json, sys
d = json.load(sys.stdin)
assert d.get('unmet', 0) > 0, 'ASC-0110 should have unmet criteria (retrieval still broken)'
print(f'  ASC-0110: met={d[\"met\"]} unmet={d[\"unmet\"]} manual={d[\"manual\"]}')
print(f'  recommended_close_type: {d.get(\"recommended_close_type\",\"?\")}')
"
# Retro audit
python scripts/aios_retro_close_classify.py --json | python -c "
import json, sys
d = json.load(sys.stdin)
print(f'  total closed: {d[\"total\"]}')
print(f'  goal_met: {d[\"goal_met\"]} partial: {d[\"partial\"]} unmet: {d[\"unmet\"]}')
"
python -m unittest discover -s tests -p 'test_aios_*.py'
```

Pass criteria (DNA-cited, evaluable):

- `aios_close_condition.py` exists and runs (Inv 4: named exit)
- Running on ASC-0110 returns recommended_close_type=closed_goal_unmet_documented
  or closed_partial_with_followup (Inv 8: classify before)
- `aios_dispatch.py release` rejects unclassified closure on contracts
  with unmet criteria (Inv 5: provenance — closure type traceable)
- Retro audit shows current 80+ closes' actual breakdown (baseline)

## Stop Conditions

- `strict_close_breaks_existing`: existing closures stay valid (no
  retroactive invalidation)
- `pass_criteria_silent_skip`: every criterion must evaluate to met /
  unmet / manual — never silently dropped
- `override_without_reason`: emergency bypass must record reason slug
- `circular_followup`: ASC-A close cites ASC-B as followup, ASC-B close
  cites ASC-A — must detect
- `child_repo_scope_leak`
- `verification_gate_failed`

## Receipts

Pending. Dogfood: this contract's own close must satisfy strict_close
condition (criteria evaluable + all met).
