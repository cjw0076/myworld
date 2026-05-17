# ASC-0053 Execution-Layer Escalation — 2026-05-13

Surface raised by `claude@uri` /loop iter 16 after iter-8 5-hour stale threshold has been exceeded. ASC-0053 primitive layer is working; execution layer has not produced a Uri sprint via formal provider-loop since iter 6 first observation.

## Fact pattern

- **provider-loop workers**: 2, both updated 2026-05-13 00:11 KST.
  - `ploop_ce1a3a94310aa3dc` (codex, one_shot_tick) — `status=stopped`, `last_status=completed`, `tick_count=1`. Prompt cites `uri/hive/packets/URI-010` (claude-authored Sprint 008 followup). Worker exited after one tick — Sprint 008 has 4 WPs, can't complete in 1.
  - `ploop_0992ac5f5e38265d` (claude, monitor_plan) — `status=active`, `last_status=failed`, `tick_count=1`. Prompt explicitly cites "after Codex provider sandbox failure." Fallback also failed on first attempt.
- **Last provider-loop tick**: 2026-05-13 00:11 KST. **Stale ~5 hours** at iter 16 wake.
- **Iter-8 5-hour stale threshold**: passed.
- **Sprint progression**: Sprint 008 (URI-010 / URI-011 hardening) → Sprint 009 (URI-012 student-life grounded UI) → Sprint 010 (URI-013 telemetry seed) — all 3 sprints shipped via founder's dev-shell, none via formal provider-loop.
- **Pending queue at iter 16**:
  - codex-self-proposed Sprint 011 (`/memory` portfolio profile drafts per URI-013 worklog next)
  - URI-014 (claude-authored Sprint 014 consent preview state)
  Both wait on chair pickup. Codex chair appears active in dev-shell mode but has not advanced either since Sprint 010 ship.

## What is *not* broken (per iter 6 ledger entry)

ASC-0053 primitive layer is sound:
- provider-loop receipts emit as `hive.provider_loop.v1`.
- prompt schema accepts claude-authored packet references — URI-010 was visible to both workers.
- run artifacts persist under `.runs/run_<id>/provider_loops/`.
- `bin/aios provider-loop status --json` returns consistent state.

## What needs triage (operator pair decision)

Three categorical items, ordered by claude@uri's assessed bang/buck:

### T1 — Worker `loop_mode` granularity

`one_shot_tick` exits after a single tick. Uri sprints have 4–5 WPs each and require multiple ticks for typecheck + build + Playwright + screenshots + receipt. Candidate fix:

- introduce `loop_mode=multi_tick` (cap N ticks; exits when packet's verification gate passes) or `loop_mode=until_done` (until the run produces a completion receipt).
- backward compatible with existing `one_shot_tick` workers.

### T2 — claude `monitor_plan` fallback failure root cause

The claude fallback worker hit `last_status=failed` on first tick. Codex's own observation from earlier ledger entries:

> "Claude fallback도 non-interactive writable mode가 불안정했어."

Candidate fix categories:
- **timeout/retry**: monitor_plan run length cap; idempotent retry policy.
- **auth/identity**: did the fallback claude get a writable workspace? ASC-0037 covered locale; this is the next layer.
- **plan-write conflict**: dev-shell concurrent writes to the same files. Provider-loop fallback may have lost a race.

### T3 — Receipt + dev-shell reconciliation

Dev-shell continues to produce artifacts. Provider-loop ticks haven't matched them. Without reconciliation, `bin/aios provider-loop status` returns stale data while dev-shell ships sprints. Candidate:

- when dev-shell completes a sprint that the provider-loop also has a worker for, mark the worker `status=superseded_by_dev_shell` with reference to the worklog entry. Cosmetic, but stops the "stale" alarm from firing on a happy path.

## Why this matters now

Three reasons to triage sooner than later:

1. **Operator visibility**: `bin/aios … status` is currently misleading. A new operator looking at the AIOS would see "Sprint 008 in flight, stalled" when reality is "Sprint 008–010 shipped, provider-loop bypassed." Misleading status is worse than slow status.
2. **Sprint 015+ blockers**: Sprint 015 onwards requires real OAuth contracts (Notion self-ingest). These should run through provider-loop precisely because they touch external services and need policy-gated dispatch (ASC-0035) enforcement. If provider-loop can't reliably complete a Uri sprint, Sprint 015+ either bypasses dispatch policy (bad) or stalls.
3. **AIOS-native primitive claim**: ASC-0053's design intent was "AIOS owns the loop, Codex is a provider." Today AIOS owns the *primitive*, but founder's dev-shell owns the *loop*. Closing this gap is the post-ASC-0053 work.

## What claude@uri has done in lieu of triage

While provider-loop is idle, claude@uri /loop has continued through 16 iters:

- 23 memory drafts in `uri/memory/drafts/` (12 cross-OS strategy, 11 sprint reviews)
- 16 receipts in `uri/.aios/outbox/uri/claude.{1..16}.result.json` (schema `aios.claude_iter.v1`)
- 3 claude-authored hive packets queued (URI-008, URI-010, URI-014 — first two already redundantly shipped by codex)
- 4 myworld discoveries (this one is the 4th)
- iter-5 carry backlog cleared at iter 12

The /loop pattern works at the *claude/iter* layer. What stalls is *codex sprint execution layer*.

## Recommendation

- Open ASC-0063 (or numbered next) targeting T1 + T2 together — same surface (provider-loop runner), distinct fix categories. T3 ride-along.
- ASC scope: extend `hivemind/hivemind/provider_loop.py` worker schema; add multi-tick mode; harden monitor_plan fallback. Tests via existing `tests/test_provider_loop.py`.
- Verification: re-run URI-010 worker after the fix; expect Sprint 008 completes through formal provider-loop, not dev-shell.

## Operator-checkpoint decisions

1. Open the new ASC immediately vs wait for next sprint (Sprint 011 or 014) to land?
2. T1 + T2 single ASC vs split? Single ASC cheaper but couples a clear fix (T1, additive enum) with an investigation (T2, root cause unknown).
3. dev-shell path persists post-ASC, or sunset once provider-loop completes? Claude recommends *persist* — dev-shell is faster for the founder, provider-loop is required for distributed/teammate scenarios.

## Carry into next iters (claude@uri lane)

- Continue receipt emission cadence per founder directive — `aios.claude_iter.v1`.
- Continue memory growth + sprint review.
- If operator pair acts on this escalation, iter 17+ will see provider-loop ticks again; otherwise dev-shell path continues unchanged.
- Stop conditions for claude@uri: no escalation to other Uri repos; no editing of `hivemind/` or `myworld/scripts/` from claude@uri lane — surface only.
