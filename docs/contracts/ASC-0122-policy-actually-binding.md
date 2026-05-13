---
contract_id: ASC-0122
slug: policy-actually-binding
status: accepted
goal: Force round_controller to actually USE the loop_policy ordering output (verifier_priority + effective_active) instead of treating policy as measurement-only. ASC-0120 was closed but verifier contracts still didn't dispatch. The policy emits metrics; the dispatcher ignores them. Spec without enforcement is theater.
created: 2026-05-13 KST
accepted: 2026-05-13 KST by claude as verifier (round 8 — policy/enforcement gap)
acceptance_authority: claude@myworld (verifier role) per founder /loop directive
origin: 2026-05-13 round 8 — ASC-0120 closed. policy now reports verifier_starvation_seconds=40729 + priority_inversion_detected=True + ordering. But dispatch progress: ASC-0115/0116/0117/0121 STILL accepted, STILL 0 dispatch packets. Same observation 1h+ after fix supposedly landed. Pattern: round_controller doesn't consume policy output, only the dispatch surface does — and dispatch picks via own logic.
---

# ASC-0122 Policy Actually Binding

DNA references: Invariant 4 (every loop has named exit — fixes that don't
take effect ARE silent timeouts), Invariant 5 (provenance — dispatcher must
trace its choice to policy output), Invariant 8 (classify before committing
— dispatcher choice IS a commitment, must be classified by policy).

## Why Now (the gap behind the gap)

Verified 2026-05-13 round 8:

```
ASC-0120 closed at 20:19 KST.
  Policy now reports:
    open_contract_order: [founder_go..., ASC-0115, ASC-0116, ASC-0117, ASC-0120, ASC-0121, codex_auto...]
    verifier_starvation_seconds: 40729
    priority_inversion_detected: True

40+ minutes after ASC-0120 close:
  ASC-0115 status: accepted, dispatch packets: 0
  ASC-0116 status: accepted, dispatch packets: 0
  ASC-0117 status: accepted, dispatch packets: 0
  ASC-0121 status: accepted, dispatch packets: 0
  → Verifier queue NOT drained. Policy ordering is descriptive, not prescriptive.
```

Sister gap: ASC-0117 added `effective_active` metric to policy output.
Capacity check in round_controller still uses old `open_count`. Effective
no behavior change.

## What's structurally wrong

`scripts/aios_loop_policy.py` is a *reporter*. It computes ordering and
metrics, writes to `docs/AIOS_LOOP_POLICY.md`, exits.

`scripts/aios_round_controller.py` is the *consumer*. Each tick it
chooses what to dispatch next. It currently consults dispatcher state
+ inbox/outbox state directly, not the policy output.

So when policy says "verifier ASC-0117 should be next", the round
controller doesn't know — it just picks whatever's most ready by its
own internal logic.

**Spec without enforcement is the deepest governance theater.**
ASC-0106 governance_audit was supposed to catch this; ASC-0121 strict
close was supposed to catch ASC-0110's fake close. But none of those
have been *implemented* yet — they're all themselves accepted-only,
sitting behind the same broken queue.

## Required Reading

- `scripts/aios_loop_policy.py` (the policy reporter)
- `scripts/aios_round_controller.py` (the dispatcher — currently
  bypasses policy)
- `scripts/aios_dispatch.py` (the actual send call — invoked by
  round_controller)
- `docs/contracts/ASC-0120-verifier-priority-precedence.md` (the
  contract whose closure was theater)
- `docs/contracts/ASC-0117-capacity-policy-retune.md` (sister gap —
  metric without enforcement)
- `docs/AIOS_DNA.md` (after ASC-0105) — Inv 4, 5, 8

## Scope

repos: `myworld`

allowed_files:

- `scripts/aios_round_controller.py`
- `scripts/aios_loop_policy.py` (read-only reference; binding moves to
  consumer)
- `tests/test_aios_round_controller.py`
- `tests/test_aios_loop_policy_binding.py` (NEW — integration test)
- `docs/AIOS_LOOP_POLICY.md` (extend with binding section)
- `docs/contracts/ASC-0122-policy-actually-binding.md`
- `docs/AIOS_AGENT_LEDGER.md`

forbidden_files:

- `docs/contracts/ASC-0117-*.md`, `ASC-0120-*.md` (read-only —
  this contract makes them actually take effect)
- `hivemind/**`, `memoryOS/**`, `CapabilityOS/**`, `GenesisOS/**`, `uri/**`
- `_from_desktop/**`, `dain/**`, `minyoung/**`
- `.env`

## Per-OS Responsibility

### myworld.must_produce

`aios_round_controller.py` change:

- each tick reads `aios_loop_policy.py --json` first
- consumes:
  - `open_contract_order` → uses as authoritative dispatch order (NOT own logic)
  - `effective_active` (from ASC-0117 once that lands) → for capacity gate
  - `verifier_starvation_seconds` → soft signal to escalate ordering
- if policy output stale (>5min), recompute first
- records each dispatch decision with `policy_recommendation_followed: bool`
  in dispatch.events
- if controller chooses different from policy, must log `reason: <slug>`

Integration test (`tests/test_aios_loop_policy_binding.py`):

- synthetic state: 3 contracts (1 verifier waiting 30min, 2 codex_auto
  waiting 5min)
- run controller tick
- assert: dispatch packet written for verifier contract, not codex_auto

### child repos: no change

## Verification Gate

```bash
python -m py_compile scripts/aios_round_controller.py
python -m unittest tests/test_aios_round_controller.py tests/test_aios_loop_policy_binding.py
# Real dogfood: run a controller tick now, observe queue
python scripts/aios_round_controller.py once --json | python -c "
import json, sys
d = json.load(sys.stdin)
# verify policy_recommendation_followed appears in events
"
# Then check whether ASC-0115/0116/0117/0121 actually dispatched
ls .aios/inbox/myworld/asc-0115*.json .aios/inbox/myworld/asc-0116*.json .aios/inbox/myworld/asc-0117*.json .aios/inbox/myworld/asc-0121*.json 2>/dev/null
python -m unittest discover -s tests -p 'test_aios_*.py'
```

Pass criteria (DNA-cited, evaluable):

- Round controller reads policy output before deciding (Inv 5: provenance)
- `policy_recommendation_followed` field per dispatch decision (Inv 8: classify)
- Synthetic test: verifier contract dispatched before codex_auto when
  starvation > 15min (Inv 4: named exit, not silent waiting)
- After this contract closes, ASC-0115/0116/0117/0121 actually receive
  dispatch packets within 1-2 ticks (real dogfood)

## Stop Conditions

- `policy_silently_overridden`: controller picks different from policy
  without logging reason
- `policy_recompute_thrash`: policy regenerated every tick when state
  unchanged (cache it)
- `controller_ignores_starvation`: verifier_starvation > 60min must
  hard-trigger ordering
- `effective_active_unused`: capacity gate must use new metric, not
  open_count
- `child_repo_scope_leak`
- `verification_gate_failed`

## Receipts

Pending. Dogfood requirement: this contract MUST dispatch within 1
round_controller tick after close (verifier-priority binding test of
its own implementation).
