---
contract_id: ASC-0190
slug: hivemind-verification-autofire
status: accepted
goal: Make Hive Mind run verification auto-fire at run completion so provider-loop runs are self-verified instead of leaving verdict=not_run.
created: 2026-05-17 18:50 KST
accepted: 2026-05-17 18:50 KST
acceptance_authority: claude@myworld operator — audit gap #5; operator-level wiring fix in hivemind, no escalation rule triggered (no new capability, no privacy change, no external authority).
origin: The 2026-05-17 internal-state audit, gap #5 — hivemind has 404 passing tests and a real verification gate, but verification is "wired but not auto-firing on provider-loop runs (verdict: not_run)". A verification gate that does not fire is not a gate.
---

# ASC-0190 Hive Mind — Verification Auto-Fire

DNA references: Invariant 4 (named exit — a run's named exit is its verified
verdict), Invariant 5 (provenance — the verdict is run evidence), Invariant 8
(classify before committing — an unverified run must not read as success).

## Scope

repos: `hivemind`

This is a hivemind-owned contract. The control plane states the requirement;
codex@hivemind owns the implementation and decides the mechanism.

allowed_files:

- `hivemind/**` (implementation — codex@hivemind's call)

forbidden_files:

- `.env`, `.env.*`, provider credentials, raw private exports

## The requirement

Every Hive run that reaches completion must run its verification gate before
the run is reported, and the run receipt must carry the resulting verdict.
`verdict: not_run` must become a rare, explicitly-explained state (e.g. a run
that crashed before any output), not the default for provider-loop runs.

Concretely:

1. Verification fires automatically at run completion — it is part of the run
   lifecycle, not a separate manual step an operator must remember.
2. The run receipt records `verdict` as one of: passed / failed / degraded /
   not_run-with-reason.
3. A `failed` or `degraded` verdict does not silently read as success — it is
   surfaced in the receipt and the run status.

## Named Exit

Closed when: a provider-loop run produces a receipt whose `verdict` is set by
an auto-fired verification gate, demonstrated on at least one real run, and
`verdict: not_run` no longer appears for runs that produced output.

## Stop Conditions

- A run genuinely produced no output to verify → `not_run` is allowed but the
  receipt must say why.
- Verification itself errors → record `verdict: degraded` with the error, do
  not drop the run or fake a pass.

## Work Packets

### codex@hivemind

Wire the existing verification gate into the run-completion path so it
auto-fires; ensure the receipt schema carries the verdict; add a test that a
completed provider-loop run has a non-`not_run` verdict. Report back with the
receipt of one real run as evidence.
