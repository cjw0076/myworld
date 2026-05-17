---
contract_id: ASC-0115
slug: goal-inbox-per-citizen-response
status: closed
goal: Stop ASC-0058 goal_inbox_processor from collapsing N distinct citizen packets into 1 generic theme contract. Each citizen voice (each uri sprint, each hivemind friction note, each memoryOS request) deserves its own response — accepted to dedicated contract, explicitly rejected with cited reason, OR explicitly merged with merge-justification. No silent skips.
created: 2026-05-13 KST
accepted: 2026-05-13 KST by claude as verifier (founder /loop GOAL-0002 — verifier surfaces necessity)
acceptance_authority: claude@myworld (verifier role) per founder /loop directive
origin: 2026-05-13 verifier round 3 — ASC-0058 processor receipt shows 11 uri packets all classified auto_promote with output_path=ASC-0082 + skipped=True. Each packet was a distinct sprint friction (URI-005 campus-graph, URI-007 platform, etc.). They were collapsed into one generic "product-repo-sprint-driver" theme. Citizens spoke 11 times; government heard "product work, generally". Founder's "real citizen end-to-end" metric formally passable but semantically empty.
---

# ASC-0115 Goal Inbox: Per-Citizen Response (no silent collapse)

DNA references: Invariant 5 (provenance — each citizen voice traceable
to its response), Invariant 6 (operator override — operator must be
able to UN-collapse), Invariant 8 (classify before committing — silent
skip is not a classification).

## Why Now

Verified 2026-05-13 round 3: 11 uri packets in goal_inbox, processed
to `auto_promote` with output_path=ASC-0082 and `skipped=True` for
each. Receipt counts `auto_promote=15` (looks like progress). Reality:

- Citizen 1 said: "Continue Sprint 005 campus-graph-platform"
- Citizen 2 said: "Prioritize Uri app/platform development"
- Citizen 3 said: [different specific sprint]
- ... (all 11 distinct)

AIOS response to each: "yeah, ASC-0082 covers product-repo work generally."

This is exactly the bureaucratic failure mode founder's vision was
supposed to escape. AIOS-as-Government either represents each voice or
admits it doesn't. Silent theme-cluster + skip is theater.

## Required Reading

- `scripts/aios_goal_inbox_processor.py` (current cluster behavior)
- `.aios/primitives/goal_inbox_run/` (latest receipt — evidence)
- `docs/contracts/ASC-0058-goal-inbox-processor.md` (origin processor)
- `docs/contracts/ASC-0082-product-repo-sprint-driver.md` (the
  generic-cluster contract that's eating distinctness)
- `.aios/goal_inbox/uri/` (the 11 individual voices)
- `docs/AIOS_DNA.md` (after ASC-0105) — Invariants 5, 6, 8

## Scope

repos: `myworld`

allowed_files:

- `scripts/aios_goal_inbox_processor.py`
- `tests/test_aios_goal_inbox_processor.py`
- `docs/AIOS_REPO_GOAL_LOOP.md`
- `docs/contracts/ASC-0115-goal-inbox-per-citizen-response.md`
- `docs/AIOS_AGENT_LEDGER.md`

forbidden_files:

- `.aios/goal_inbox/**` (read-only — never delete or modify)
- `docs/contracts/ASC-0058-*.md` and `ASC-0082-*.md` (read-only — being
  fixed by behavior change here, not by re-writing those)
- `hivemind/**`, `memoryOS/**`, `CapabilityOS/**`, `GenesisOS/**`, `uri/**`
- `_from_desktop/**`, `dain/**`, `minyoung/**`
- `.env`

## Per-OS Responsibility

### myworld.must_produce

`scripts/aios_goal_inbox_processor.py` behavioral change:

V1 NEW classification rules:
- `auto_promote_distinct` — packet maps to a contract theme but no
  prior contract has fully covered THIS specific packet's intent →
  draft a new contract derived from packet body (not just theme name)
- `merge_with_justification` — packet's intent IS already covered by
  an existing contract AND merge is operator-approved → record
  `merge_justification: <text>`, link both directions (packet ↔
  contract), DO NOT silently skip
- `needs_operator_review` — ambiguous (existing)
- `reject_out_of_scope` — outside AIOS (existing) with reason
- `defer_capability_gap` — needs new capability (existing)

The OLD `skipped=True` path is forbidden — every result must explicitly
classify into one of the 5 above.

Receipt format change:
- per packet: classification, reason, output_path OR merge_target,
  merge_justification (if merged), evidence_link to packet body
- aggregate: counts per classification + `silently_skipped: 0` (must
  always be 0 going forward)

Backwards compatibility: re-process the 11 currently-collapsed uri
packets with new rules. Output: how many each classification.

### child repos: no change

## Verification Gate

```bash
python -m py_compile scripts/aios_goal_inbox_processor.py
python -m unittest tests/test_aios_goal_inbox_processor.py
# Re-process current goal_inbox under new rules
python scripts/aios_goal_inbox_processor.py --assert-silently-skipped-zero --assert-per-citizen-response --json
python -m unittest discover -s tests -p 'test_aios_*.py'
```

Pass criteria (DNA-cited):

- 0 silent skips (Inv 8: classify before committing)
- Each citizen voice traceable to a specific response (Inv 5: provenance)
- Operator can re-process to expand merged groups (Inv 6: override)
- Receipts explicitly cite per-packet outcome

## Stop Conditions

- `silent_skip_persists`: any result with skipped=True without
  classification
- `cluster_without_justification`: merge_with_justification missing
  the justification field
- `processor_creates_unread_contracts`: auto_promote_distinct must
  produce contract whose body actually references the originating packet
- `child_repo_scope_leak`
- `verification_gate_failed`

## Receipts

- 2026-05-14 KST: `scripts/aios_goal_inbox_processor.py` now emits
  `auto_promote_distinct`, `merge_with_justification`,
  `needs_operator_review`, `reject_out_of_scope`, and
  `defer_capability_gap`. Legacy `auto_promote` is not emitted by current
  classification.
- Repeated runs preserve explicit responses with `previously_processed`
  instead of returning `skipped=True`.
- Receipts include top-level and count-level `silently_skipped: 0`.
- Dogfood run processed 15 current goal-inbox packets and produced 15
  `auto_promote_distinct` contract candidates:
  `ASC-0128` through `ASC-0142`.
- Dogfood verified all 11 `uri` packets have explicit per-citizen responses
  and generated contract bodies cite the originating `goal_id`.
- Watcher result `.aios/outbox/myworld/asc-0115.myworld.result.json` passed.
- Full MyWorld AIOS test suite passed 308 tests.

## Work Packets

### WP-0115-A — codex@myworld fixes processor

- target_agent: codex
- target_repo: myworld
- depends_on: ASC-0058 closed ✓
- brief: replace skipped=True branch with explicit
  merge_with_justification + auto_promote_distinct paths. Re-process
  goal_inbox dogfood. Tests cover per-citizen distinctness and
  operator un-collapse path.
