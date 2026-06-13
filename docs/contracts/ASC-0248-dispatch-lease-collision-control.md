---
contract_id: ASC-0248
slug: dispatch-lease-collision-control
status: closed
goal: Prevent multiple operator agents from implementing the same AIOS dispatch concurrently by adding an auditable dispatch lease/claim gate.
created: 2026-06-13T15:16:00+09:00
accepted: 2026-06-13T15:16:00+09:00
human_approved: true
closed: 2026-06-13T15:30:00+09:00
origin: ASC-0247 exposed a concurrent close race: codex and claude both implemented the same dispatch while the contract delegated implementation to Claude.
---

# ASC-0248 Dispatch Lease Collision Control

## Why Now

ASC-0247 succeeded, but its result packet recorded a service-readiness failure:
two operator agents worked the same dispatch concurrently. That is acceptable
as a discovered failure, not as an AIOS operating model.

AIOS is supposed to be an agent company. Parallel work is useful, but two
workers should not unknowingly take the same ticket. The control plane needs a
small, auditable lease/claim gate before implementation begins.

This contract delegates implementation to Claude. Codex must not patch the
implementation in this slice.

## Scope

repos:

- `myworld`

allowed_files:

- `scripts/aios_dispatch.py`
- `scripts/aios_round_controller.py`
- `scripts/aios_child_watcher.sh`
- `tests/test_aios_dispatch.py`
- `tests/test_aios_child_watcher.py`
- `tests/test_aios_round_controller.py`
- `docs/contracts/ASC-0248-dispatch-lease-collision-control.md`
- `docs/AIOS_AGENT_LEDGER.md`

forbidden_files:

- `.env`
- `.env.*`
- provider auth files
- sensitive vault contents
- raw provider logs
- private history stores
- child repo implementation files
- `uri/**`
- `CapabilityOS/**`
- `artifacts/**`
- `gemini/**`
- `gemini-cli/**`
- `1.md`

## Required Work For Claude

Add a minimal dispatch lease/claim guard so an implementation worker can tell
whether a dispatch is already owned by another live or recent worker.

Minimum requirements:

1. Before a watcher/worker starts implementation for a dispatch, it must record
   a lease/claim event with dispatch id, repo, agent, owner pid or process ref,
   started_at, and expiry/heartbeat semantics.
2. A second worker trying to claim the same dispatch must either:
   - fail closed with a structured collision receipt; or
   - take over only when the previous lease is expired/stale and record why.
3. Lease records must be local runtime state under `.aios/` and must not be
   committed.
4. `aios_dispatch.py status` or monitor diagnostics should make collisions or
   stale leases visible enough for an operator to triage.
5. Tests must cover:
   - first claim succeeds;
   - concurrent second claim is blocked;
   - stale/expired claim can be reclaimed with evidence;
   - collision result does not mark the dispatch as successfully implemented.

Do not implement provider routing, planner receipts, turn-loop defaulting, or
new hosted worker infrastructure in this contract.

## Plain-Language Framing

This is a ticket lock. One worker can own a ticket at a time. If another worker
tries to take it, AIOS must say "someone already has it" instead of silently
duplicating work.

## Assumptions

- Assumption 1: local file-based leases are sufficient for this stage.
- Assumption 2: leases are runtime state, not source history.
- Assumption 3: a stale lease may be reclaimed only with explicit evidence.

Negated checks:

- Do not prevent different dispatches from running in parallel.
- Do not turn lease collision into success.
- Do not delete historical dispatch records.

## Verification Gate

Claude must run:

```bash
python3 -m unittest tests.test_aios_dispatch tests.test_aios_child_watcher tests.test_aios_round_controller -v
python3 -m py_compile scripts/aios_dispatch.py scripts/aios_round_controller.py
bash -n scripts/aios_child_watcher.sh
git diff --check
```

Pass criteria:

- Focused tests pass.
- A second worker cannot unknowingly implement a live claimed dispatch.
- Stale claim recovery is explicit and receipt-backed.
- Current collected dispatches remain readable.

## AIOS Role Evidence

### MemoryOS

- source_context: ASC-0247 concurrency note.
- draft_policy: no accepted memory mutation in this slice.

### CapabilityOS

- route: local control-plane dispatch/watch primitives only.
- authority: no capability binding changes.

### GenesisOS

- challenge: AIOS should increase parallelism without creating duplicate
  authority over the same work ticket.
- authority: advisory only.

### Hive Mind

- execution_plan: Claude implements lease guard; watcher tests and result
  packet prove collision behavior.

## Work Packets

### WP-0248-A — Claude dispatch lease collision control

- target_repo: `myworld`
- target_agent: `claude`
- status: issued
- instruction: Implement the Required Work For Claude section. Keep the slice
  tight. Return a result packet with changed files, tests run, lease schema,
  collision behavior, and remaining scheduler gaps.
- result: pending

## Stop Conditions

- `lease_collision_unreported`
- `stale_claim_takeover_without_evidence`
- `parallel_different_dispatches_blocked`
- `test_gate_failed`
- `scope_violation`
- `privacy_violation`
