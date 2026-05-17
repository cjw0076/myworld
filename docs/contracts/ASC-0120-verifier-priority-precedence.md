---
contract_id: ASC-0120
slug: verifier-priority-precedence
status: closed
goal: Force codex chain to prioritize verifier-issued contracts (claude as verifier surfacing real discomfort) over codex's own auto-generated contract chain. Today verifier ASCs sit accepted 25-97min while codex auto-issued ASCs close in 6-16min — the discomfort signals never reach execution, defeating the verifier's purpose.
created: 2026-05-13 KST
accepted: 2026-05-13 KST by claude as verifier (round 6)
closed: 2026-05-13 20:19 KST by codex under founder-delegated operator loop
acceptance_authority: claude@myworld (verifier role) per founder /loop directive — verifier discomfort must reach execution
origin: 2026-05-13 round 6 — measured: claude verifier issued ASC-0110 (97min), 0115 (78min), 0116 (54min), 0117 (25min) all status=accepted with 0 dispatch packets. Codex auto-issued ASC-0118 (16min ago) and ASC-0119 (6min ago) both closed. Codex chain picks codex's own contracts first. Verifier signals silenced.
---

# ASC-0120 Verifier Priority Precedence

DNA references: Invariant 4 (every loop has named exit — verifier discomfort
must produce action, not silent timeout), Invariant 5 (provenance — operator
who issued contract has weight in ordering), Invariant 6 (operator override —
verifier IS operator surfacing system flaws), Invariant 8 (classify before
committing — codex must classify ordering choice).

## Why Now

Verified 2026-05-13 round 6:

```
verifier-issued (claude as verifier):
  ASC-0110 retrieval-broken      97min  status=accepted  dispatch=0
  ASC-0115 per-citizen           78min  status=accepted  dispatch=0
  ASC-0116 monitor-attention     54min  status=accepted  dispatch=0
  ASC-0117 capacity-policy       25min  status=accepted  dispatch=0

codex auto-issued (round controller):
  ASC-0118 readiness-binding     16min  status=CLOSED
  ASC-0119 os-activity-evidence   6min  status=CLOSED
```

Pattern: codex chain consistently picks own contracts first. Verifier
contracts queue indefinitely behind capacity cap (and even when capacity
opens, codex priority sorts own chain higher).

This DEFEATS the verifier role founder created with /loop directive. If
verifier can issue contracts but codex chain ignores them, AIOS has
governance theater of its own kind: appearance of feedback loop, no
actual influence.

## What this is NOT

- Not "verifier always wins" — codex chain has legitimate work
- Not "operator overrides safety" — verifier signals are themselves
  about system safety/quality
- Not "manual ordering" — operator shouldn't manually move queue items

## What this IS

A scheduling policy that:
- detects verifier-issued contracts (by acceptance_authority signature
  matching "verifier" role)
- if verifier contract has been waiting > N minutes (default 15) AND
  capacity slot opens, verifier contract takes the slot over codex
  auto-issued queue items
- codex auto-issued contracts retain priority among themselves
- founder GO contracts always take immediate slot regardless

## Required Reading

- `docs/contracts/ASC-0011-control-plane-loop-policy.md` (queue policy origin)
- `docs/contracts/ASC-0117-capacity-policy-retune.md` (effective_active fix
  in flight; this contract layers on top)
- `scripts/aios_loop_policy.py` (where ordering happens)
- `scripts/aios_round_controller.py` (consumer)
- `docs/AIOS_DNA.md` (after ASC-0105) — Invariants 4, 5, 6, 8

## Scope

repos: `myworld`

allowed_files:

- `scripts/aios_loop_policy.py`
- `tests/test_aios_loop_policy.py`
- `docs/AIOS_LOOP_POLICY.md`
- `docs/contracts/ASC-0120-verifier-priority-precedence.md`
- `docs/contracts/README.md`
- `docs/AGENT_WORKLOG.md`
- `docs/AIOS_AGENT_LEDGER.md`

forbidden_files:

- `docs/contracts/ASC-0011-*.md`, `ASC-0117-*.md` (read-only — depending)
- `hivemind/**`, `memoryOS/**`, `CapabilityOS/**`, `GenesisOS/**`, `uri/**`
- `_from_desktop/**`, `dain/**`, `minyoung/**`
- `.env`

## Per-OS Responsibility

### myworld.must_produce

`aios_loop_policy.py` ordering augmented:

- detect contract issuer:
  - `founder_go`: acceptance_authority cites "founder explicit GO"
  - `verifier`: acceptance_authority cites "verifier" role
  - `codex_auto`: acceptance_authority cites codex / autodraft / round_controller
  - `operator`: any operator cite
- ordering when capacity slot opens:
  - founder_go highest (immediate)
  - verifier second (if waiting > 15min, jumps codex_auto queue)
  - operator + codex_auto FIFO within their group
- new metrics in policy output:
  - `verifier_starvation_seconds` per accepted verifier contract
  - `priority_inversion_detected` if verifier waited > codex closing
- existing capacity = 4 unchanged (in_flight gate)
- soft warn if verifier_starvation > 60min

### child repos: no change

## Verification Gate

```bash
python -m py_compile scripts/aios_loop_policy.py
python -m unittest tests/test_aios_loop_policy.py
python scripts/aios_loop_policy.py --write docs/AIOS_LOOP_POLICY.md --json
python -m unittest discover -s tests -p 'test_aios_*.py'
```

Pass criteria (DNA-cited):

- `issuer` field added per contract in policy decisions (Inv 5: provenance)
- founder_go > verifier (>15min) > codex_auto > FIFO ordering (Inv 4: named)
- `verifier_starvation` surfaced as a policy warning when wait exceeds 60min
  (Inv 6: visibility)
- capacity gate behavior unchanged (Inv 8: in_flight cap remains)

## Stop Conditions

- `verifier_always_wins`: verifier should not preempt founder_go or
  in-flight contract — only takes opening slots
- `priority_silent_skip`: every ordering decision must log issuer +
  reason
- `codex_starvation`: codex_auto must still get slots (verifier doesn't
  monopolize)
- `child_repo_scope_leak`
- `verification_gate_failed`

## Receipts

- implementation: `scripts/aios_loop_policy.py`
  - adds issuer classification: `founder_go`, `verifier`, `codex_auto`,
    `operator`
  - adds `open_contract_order`, `verifier_starvation_seconds`,
    `priority_inversion_detected`, and warning rows for `verifier_starvation`
  - preserves the existing capacity gate instead of dispatching directly
- tests: `tests/test_aios_loop_policy.py`
  - synthetic verifier-vs-codex ordering test passed
  - founder GO still preempts waiting verifier
- policy snapshot: `docs/AIOS_LOOP_POLICY.md`
  - generated at 2026-05-13 20:20 KST
  - `verifier_starvation_seconds=40848`
  - `priority_inversion_detected=True`
  - current order places founder GO contracts first, then verifier contracts
    `ASC-0115`, `ASC-0116`, `ASC-0117`, `ASC-0121`, then operator/codex-auto
    work. `ASC-0120` is absent from the final open queue because this closeout
    changed its status to `closed`.
- verification passed:
  - `python -m py_compile scripts/aios_loop_policy.py`
  - `python -m unittest tests/test_aios_loop_policy.py` passed 4/4
  - `python scripts/aios_loop_policy.py --write docs/AIOS_LOOP_POLICY.md --json`
  - `python -m unittest discover -s tests -p 'test_aios_*.py'` passed 267/267
    with non-failing subprocess `ResourceWarning` output from existing tests.
- dispatch and release:
  - action-policy checkpoint escalated the first send as
    `human_checkpoint_required:legal_or_safety_impact`
  - founder-delegated operator release wrote
    `.aios/inbox/myworld/asc-0120.myworld.json`
  - watcher result `.aios/outbox/myworld/asc-0120.myworld.result.json` passed
    with no stop conditions
  - release writeback wrote MemoryOS draft `mem_da5509a16be7f6a3`

Dogfood: after ASC-0117 + ASC-0120 close, ASC-0110/0115/0116 should drain
from queue within 1-2 ticks.
