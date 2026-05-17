---
contract_id: ASC-0185
slug: leased-jobs-queue
status: accepted
goal: Replace bare file-drop dispatch with a leased jobs queue — kind + job_key + lease_until + retry_remaining + ownership_token — so concurrent watchers cannot double-claim work or collide on IDs.
created: 2026-05-17 05:35 KST
accepted: 2026-05-17 05:40 KST
acceptance_authority: claude@myworld operator — Tier-1 borrow item closing a known bug class; no escalation rule triggered (no new OS, no privacy-boundary change, no external authority).
proposed_by: claude@myworld
origin: AIOS_ECOSYSTEM_BORROW_PLAN.md Tier 1. The 2026-05-17 ecosystem study found Codex CLI's leased jobs queue. It is a turnkey fix for the AIOS watcher-race / ID-collision bug class (ASC-0059 watcher-race-resolution; the claude+codex autodraft ID-collision pattern).
---

# ASC-0185 Leased Jobs Queue

DNA references: Invariant 3 (append-only audit), Invariant 4 (named exit —
a lease expiry is a named exit for a stuck job), Invariant 5 (provenance).

## The problem

AIOS dispatch is a bare file drop into `.aios/inbox/<repo>/`. Two watchers
waking together can both pick up the same packet; two autodrafters can mint
the same ASC id. ASC-0059 patched one race; the class remains. There is no
ownership, no lease, no retry accounting — a crashed worker leaves a packet
either lost or double-run.

Codex CLI's answer: a leased jobs queue. A job carries `kind`, `job_key`
(idempotency key), `lease_until`, `retry_remaining`, and an `ownership_token`.
A worker *claims* a job by taking a lease; only the lease holder may complete
it; an expired lease returns the job to the queue.

## Scope (proposed)

repos: `myworld`

allowed (if accepted):

- `scripts/aios_jobs.py` (new — the leased queue: enqueue / claim / heartbeat
  / complete / expire-sweep)
- `docs/AIOS_JOBS_QUEUE.md` (new — the job record schema + lease protocol)
- `scripts/aios_dispatch.py` (dispatch enqueues a job; collect completes it)
- `scripts/aios_child_watcher.sh` / watcher scripts (claim via lease, not bare read)

## Design (proposed)

1. **Job record** — `job_id`, `kind`, `job_key` (dedup: a second enqueue
   with the same `job_key` is a no-op), `contract_id`, `target_repo`,
   `state` (queued/leased/done/failed), `lease_until`, `ownership_token`,
   `retry_remaining`, `provenance`.
2. **Claim** — a worker atomically moves a job queued→leased, stamping its
   `ownership_token` and `lease_until`. Atomicity via an os-level rename
   (the same primitive a file-drop already relies on, used correctly).
3. **Heartbeat / expiry** — a long job extends its lease; an expiry sweep
   returns lapsed leases to `queued` and decrements `retry_remaining`. At
   zero retries the job goes `failed` with a named stop reason (Invariant 4).
4. **Append-only** — job state transitions are logged, never overwritten in
   place (Invariant 3); the queue file is the index, the log is the truth
   (the JSONL-truth pattern from the same borrow plan).

## Named Exit

Closed when: dispatch enqueues leased jobs, a watcher claims by lease, a
double-claim is demonstrably rejected, a duplicate `job_key` is a no-op, and
an expired lease is demonstrably re-queued.

## Stop Conditions

- Migration risk: existing in-flight `.aios/inbox` packets must be adopted
  into the queue without loss → ship a one-time adopt step; do not strand
  live packets.
- If atomic rename is unavailable on the target filesystem → fall back to a
  lock file, do not silently drop the lease guarantee.
