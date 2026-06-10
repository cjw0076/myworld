---
contract_id: ASC-0117
slug: capacity-policy-retune
status: closed
closed: 2026-05-17 KST — operator reconciliation. aios_loop_policy.py: added in_flight_count() (contracts with a dispatch packet still in the inbox = actually in the execution pipeline); the capacity gate in decide() now compares `in_flight` to capacity instead of the raw open-contract count, so accepted-but-waiting contracts no longer gridlock new acceptance. build_policy reports both open_contract_count and in_flight_count. tests/test_aios_loop_policy.py: test_policy_holds_for_capacity rewritten to dispatch 4 in-flight + new test_accepted_waiting_does_not_gridlock (20 accepted, 0 in-flight → accept_now). 37 loop_policy/round_controller/dispatch tests pass. Named exit "in_flight after policy retune" met.
goal: Distinguish "accepted but waiting" from "actively in-progress" in ASC-0011 capacity policy. Today open_count=22 vs capacity=4 means verifier-issued contracts wait 2-3 hours before dispatch. Founder /loop directs continuous contract issue → policy creates artificial gridlock between issuance and execution.
created: 2026-05-13 KST
accepted: 2026-05-13 KST by claude as verifier (round 5)
acceptance_authority: claude@myworld (verifier role) per founder /loop directive
origin: 2026-05-13 round 5 — open_count=22, capacity=4. ASC-0110 (38min), ASC-0115 (22min), ASC-0116 (22min) all sit accepted with 0 dispatch packets. Verifier discomfort signals queue behind gridlock; "계속 Contract를 발행해" directive then accumulates into starvation.
---

# ASC-0117 Capacity Policy Retune

DNA references: Invariant 4 (every loop has a named exit — but not "starve in
queue"), Invariant 6 (operator override always possible — capacity must be
adjustable in real time), Invariant 8 (classify before committing — accepted
≠ active should be distinguishable).

## Why Now

Verified 2026-05-13 round 5:

```
open_count: 22 (status=accepted contracts)
capacity:   4   (ASC-0011 hard cap)
in-flight:  ~5 (estimated from dispatch.status)
queued:     17+
verifier-issued waiting times:
  ASC-0110: 38 min, 0 dispatch
  ASC-0115: 22 min, 0 dispatch
  ASC-0116: 22 min, 0 dispatch
```

ASC-0011 was set N=4 in V1 with reasonable rationale: "operator pair can
sustain ~4 parallel contracts based on session evidence". That was when
contracts were operator-paced. Now:

- Round controller dispatches autonomously
- Verifier loop continuously issues contracts
- Codex chain auto-issues from goal evolution
- Hive runs deliberations (each = 1 contract slot)

Result: 22 accepted contracts cluster behind the gate.

The gate's purpose was "don't overload operator". The reality: gate now
prevents codex from working because every "accepted" contract counts
toward the cap regardless of whether it's actually being processed.

## Required Reading

- `docs/contracts/ASC-0011-control-plane-loop-policy.md` (the N=4 policy)
- `scripts/aios_loop_policy.py` (capacity check implementation)
- `scripts/aios_round_controller.py` (dispatcher consuming policy)
- `scripts/aios_dispatch.py` (status states: created/sent/collected/closed)
- `docs/AIOS_DNA.md` (after ASC-0105) — Invariants 4, 6, 8

## Scope

repos: `myworld`

allowed_files:

- `scripts/aios_loop_policy.py`
- `scripts/aios_dispatch.py` (state inspection helper, no behavior change)
- `tests/test_aios_loop_policy.py`
- `tests/test_aios_dispatch.py`
- `docs/AIOS_LOOP_POLICY.md`
- `docs/contracts/ASC-0117-capacity-policy-retune.md`
- `docs/AIOS_AGENT_LEDGER.md`

forbidden_files:

- `docs/contracts/ASC-0011-*.md` (read-only — being rebalanced not rewritten)
- `hivemind/**`, `memoryOS/**`, `CapabilityOS/**`, `GenesisOS/**`, `uri/**`
- `_from_desktop/**`, `dain/**`, `minyoung/**`
- `.env`

## Per-OS Responsibility

### myworld.must_produce

Distinguish state in capacity counting (Inv 8: classify before committing):

- `accepted_idle`: status=accepted but no dispatch packet sent yet
- `in_flight`: dispatch packet sent, awaiting result OR running
- `awaiting_close`: result collected, awaiting closeout commit
- `closed`: status=closed (not counted)

`aios_loop_policy.py` capacity computation:

- new metric `effective_active = in_flight + awaiting_close` (was `open_count`)
- `accepted_idle` is queue depth, not active load
- decision rules:
  - `accept_now` if (verdict=executable AND effective_active < N)
  - `hold_for_capacity` if effective_active >= N (NOT just open_count)
  - drain queue (accepted_idle → in_flight) when capacity available

V1 retune:
- N stays 4 for in_flight cap (operator review bandwidth)
- queue depth (accepted_idle) gets soft warning at 10, hard warning at 30
- new metric exposed: `time_to_dispatch_p95` (how long does an accepted
  contract wait before getting in_flight?)

`aios_dispatch.py status` adds queue position field:
- per accepted contract: `queue_position`, `estimated_wait_minutes`
- helps operator/founder see what's actually waiting

### child repos: no change

## Verification Gate

```bash
python -m py_compile scripts/aios_loop_policy.py scripts/aios_dispatch.py
python -m unittest tests/test_aios_loop_policy.py tests/test_aios_dispatch.py
python scripts/aios_loop_policy.py --json | python -c "
import json, sys
d = json.load(sys.stdin)
assert 'effective_active' in d, 'missing effective_active metric'
assert 'queue_depth' in d, 'missing queue_depth'
print(f'  effective_active={d[\"effective_active\"]} queue_depth={d[\"queue_depth\"]}')
"
python scripts/aios_dispatch.py status --json | python -c "
import json, sys
d = json.load(sys.stdin)
# verify queue_position appears for accepted_idle dispatches
"
python -m unittest discover -s tests -p 'test_aios_*.py'
```

Pass criteria (DNA-cited):

- `effective_active` distinguishes from `open_count` (Inv 8)
- ASC-0110/0115/0116 (current verifier-stuck) move from accepted_idle to
  in_flight after policy retune (Inv 4: not stuck, named exit via dispatch)
- Operator can see queue_position per contract (Inv 6: visibility)
- Hard cap can be raised in policy without code change (config)

## Stop Conditions

- `accepted_idle_uncounted_in_warning`: queue depth must still warn
  operator if growing unbounded (founder discomfort signal)
- `unbounded_in_flight`: in_flight cap must remain enforced (operator
  bandwidth)
- `queue_silent_skip`: no contract should drop out of queue without
  reason event
- `child_repo_scope_leak`
- `verification_gate_failed`

## Receipts

Pending. Dogfood: after fix, ASC-0117 itself dispatches within 1
round_controller tick, AND ASC-0110/0115/0116 drain from queue too.
