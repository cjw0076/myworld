---
contract_id: ASC-0121
slug: strict-close-condition
status: closed
goal: Forbid contract closure when stated goal is verifiably unmet. Today ASC-0110 (memoryOS retrieval broken) was closed despite retrieval STILL returning selected=0 for the same queries the contract listed as proof of breakage. Closure became a paperwork milestone, not a goal-met assertion.
created: 2026-05-13 KST
accepted: 2026-05-13 KST by claude as verifier (round 7 — deepest discomfort yet)
closed: 2026-05-13 20:33 KST
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
- `scripts/aios_retro_close_classify.py` (NEW — retro close baseline)
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
python -m py_compile scripts/aios_close_condition.py scripts/aios_retro_close_classify.py scripts/aios_dispatch.py
python -m unittest tests/test_aios_close_condition.py tests/test_aios_dispatch.py
python scripts/aios_close_condition.py docs/contracts/ASC-0110-memoryos-retrieval-broken.md --json
python scripts/aios_retro_close_classify.py --json
python -m unittest discover -s tests -p 'test_aios_*.py'
```

Pass criteria (DNA-cited, evaluable):

- file_exists:scripts/aios_close_condition.py — evaluator exists (Inv 4:
  named exit)
- must_contain:scripts/aios_close_condition.py::def evaluate_contract —
  evaluator has a callable contract evaluator
- must_contain:tests/test_aios_close_condition.py::test_asc_0110_is_not_classified_as_goal_met
  — ASC-0110 is covered as a strict-close regression fixture (Inv 8)
- must_contain:tests/test_aios_dispatch.py::test_release_blocks_closed_contract_with_unmet_criteria_without_classification
  — dispatch release rejects unclassified unmet closure (Inv 5)
- must_contain:scripts/aios_retro_close_classify.py::def build_report —
  retro audit has a callable baseline report

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

Implemented:

- `scripts/aios_close_condition.py` extracts `Pass criteria:` bullets,
  evaluates `file_exists:`, `must_contain:`, command, retrieval, audit, and
  diagnostic criteria into `met` / `unmet` / `manual`, and emits
  `aios.close_condition.v1`.
- `scripts/aios_retro_close_classify.py` retro-classifies existing closed
  contracts without reopening them.
- `scripts/aios_dispatch.py release` now runs strict-close evaluation when the
  created contract file is closed. Unmet criteria hold release unless the
  operator supplies `--close-type closed_partial_with_followup --followup-asc
  ASC-NNNN`, `--close-type closed_goal_unmet_documented`, or an audited
  `--operator-override-strict-close --reason`.
- `docs/AIOS_CLOSE_CONDITION.md` records the close vocabulary, evaluator,
  dispatch enforcement, and retro baseline.

Verification:

- `python -m py_compile scripts/aios_close_condition.py scripts/aios_retro_close_classify.py scripts/aios_dispatch.py` passed.
- `python -m unittest tests/test_aios_close_condition.py tests/test_aios_dispatch.py` passed 24/24.
- `python scripts/aios_close_condition.py docs/contracts/ASC-0110-memoryos-retrieval-broken.md --json` returned `met=2`, `unmet=2`, `manual=0`, `recommended_close_type=closed_partial_with_followup`.
- `python scripts/aios_retro_close_classify.py --json` returned `total=97`, `goal_met=83`, `partial=14`, `unmet=0` after ASC-0121 entered the baseline.
- `python scripts/aios_close_condition.py docs/contracts/ASC-0121-strict-close-condition.md --json` returned `met=5`, `unmet=0`, `manual=0`, `recommended_close_type=closed_goal_met`.
- `python -m unittest discover -s tests -p 'test_aios_*.py'` passed 274/274; non-failing subprocess `ResourceWarning` lines remain from existing tests.

Dogfood:

- `python scripts/aios_dispatch.py create docs/contracts/ASC-0121-strict-close-condition.md --dispatch-id asc-0121` created the dispatch.
- `python scripts/aios_dispatch.py send --repo myworld --agent codex --dispatch-id asc-0121` wrote `.aios/inbox/myworld/asc-0121.myworld.json`.
- `python scripts/aios_dispatch.py watch --repo myworld --dispatch-id asc-0121 --once` passed and wrote `.aios/outbox/myworld/asc-0121.myworld.result.json`.
- `python scripts/aios_dispatch.py collect --repo myworld` collected the passed result.
- `python scripts/aios_dispatch.py release --dispatch-id asc-0121 --reason "ASC-0121 strict close condition watcher passed and contract closed" --close-type closed_goal_met` succeeded and wrote MemoryOS draft `mem_80f00995290213fb`.
