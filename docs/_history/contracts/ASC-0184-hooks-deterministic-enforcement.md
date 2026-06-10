---
contract_id: ASC-0184
slug: hooks-deterministic-enforcement
status: closed
goal: Add a deterministic enforcement layer — pre-action hooks that hard-block any action violating a DNA invariant or contract scope, regardless of model intent — so AIOS invariants are binding, not advisory.
created: 2026-05-17 05:35 KST
accepted: 2026-05-17 05:40 KST
closed: 2026-05-17 12:30 KST
close_evidence: scripts/aios_hooks.py (engine + 3 built-in hooks); tests/test_aios_hooks.py 9 passed (privacy block, append-only block, contract-scope block/allow/escalate, operator-override conversion, decision log); aios_dispatch.py cmd_send calls hook_preflight() before building a packet — a privacy-gated contract scope is demonstrably blocked (smoke: allowed_files ['dain/private.md'] → verdict block); launcher hooks verb wired. Named exit met.
acceptance_authority: claude@myworld operator — Tier-1 borrow item closing a known bug class; no escalation rule triggered (no new OS, no privacy-boundary change, no external authority).
proposed_by: claude@myworld
origin: AIOS_ECOSYSTEM_BORROW_PLAN.md Tier 1. The 2026-05-17 ecosystem study found Claude Code's hooks are a deterministic enforcement layer (PreToolUse can hard-block an action no matter what the model intends). ASC-0122 ("policy actually binding") and the round-8 "spec without enforcement gap" are the recurring AIOS failure this closes.
---

# ASC-0184 Hooks — Deterministic Enforcement

DNA references: Invariant 1 (decide before acting), Invariant 6 (operator
override), Invariant 7 (privacy boundary inviolable). This contract is the
mechanism that makes all 8 invariants *enforced* rather than *documented*.

## The problem

AIOS has 8 DNA invariants and per-contract scope (`allowed_files` /
`forbidden_files`). Today these are checked by convention — an agent is
*expected* to honor them. ASC-0122 already observed the gap: a policy that is
specified but not enforced is not binding. A model that intends well still
drifts; a model that is prompt-pressured can be steered past a guideline.

Claude Code's answer: a hook layer where a `PreToolUse`-style check can
return "block" and the action does not happen — enforcement is deterministic
code, independent of model intent.

## Scope (proposed)

repos: `myworld`

allowed (if accepted):

- `scripts/aios_hooks.py` (new — the hook engine: register checks, evaluate
  a proposed action, return allow/block/escalate)
- `docs/AIOS_HOOKS.md` (new — the hook contract + the built-in invariant checks)
- `scripts/aios_dispatch.py`, `scripts/aios_action_policy.py` (call the hook
  engine before applying a packet / an action)
- `scripts/aios_round_controller.py` (hook-check guarded steps)

## Design (proposed)

1. **Hook engine** — pure-Python, deterministic. A hook is `(name, check_fn)`
   where `check_fn(action) -> {verdict: allow|block|escalate, reason}`.
2. **Built-in invariant hooks** (ship enabled):
   - privacy-boundary: block any action touching `_from_desktop`, `dain`,
     `minyoung`, `.env`, secrets, raw exports (Invariant 7).
   - contract-scope: block a packet writing outside its contract's
     `allowed_files` / into `forbidden_files`.
   - append-only-audit: block a destructive edit to a ledger / closed
     contract (Invariant 3).
3. **Operator override** — a hook block is overridable by an explicit,
   logged operator decision (Invariant 6); the override itself is audited.
4. **Fail-closed on the privacy hook, fail-open elsewhere** — a crash in the
   privacy check blocks; a crash in a soft check logs and allows (do not let
   a hook bug halt the autopoietic loop on non-privacy matters).

## GenesisOS Escape Review

This review is advisory-only. It names the hidden assumptions before the hook
layer becomes an unquestioned reflex.

### Assumptions

- Assumption 1: deterministic code should have authority over provider intent
  when an action crosses a privacy, scope, or audit boundary.
- Assumption 2: most hook false positives are less damaging than silent
  boundary violations.
- Assumption 3: operator override is enough to keep enforcement from becoming
  a dead hand.

Counter branch: negate those assumptions. If hooks become too broad, they can
turn AIOS into a system that is safe but unable to act. The contract therefore
keeps privacy fail-closed while non-privacy checks fail-open with ledger
evidence and review.

### Plain Language

Plain language: before AIOS touches a file or dispatches work, a small rule
checker asks whether that action is allowed. If the action would cross a hard
line, the checker stops it even if the model says it is fine.

### Cross-Domain Frame

Legal analogy: hooks are courthouse injunctions, not advice columns. A judge
can pause a harmful action before the harm happens, but the court must also
record why it paused the action and how an authorized appeal works.

### Time Horizons

- 1h: enforce only the privacy and scope checks on one controlled path.
- 1 week: attach hooks to dispatch and round-controller actions with false
  positive receipts.
- 1 year: evolve hooks into AIOS's constitutional court while preserving a
  visible operator appeal path.

## Named Exit

Closed when: the hook engine exists, the three built-in invariant hooks are
enabled, `aios_dispatch.py` consults it before applying a packet, an
out-of-scope write is demonstrably blocked, and the operator-override path is
tested.

## Stop Conditions

- A hook would block the autopoietic loop on a false positive → the soft
  checks fail-open and log; only the privacy hook fails-closed.
- Enforcement conflicts with an accepted contract → escalate, do not silently
  override the contract.
