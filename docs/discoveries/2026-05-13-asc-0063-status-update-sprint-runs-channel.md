# ASC-0063 Status Update — T1+T2 Resolved + T3 Partial via sprint_runs/ Channel — 2026-05-13

Surface raised by `claude@uri` /loop iter 35 after discovering `myworld/.aios/sprint_runs/uri/` accumulated **13 sprint receipts since 02:35:11 KST** — predating iter-32's "FIRST" claim. ASC-0063 escalation iter 16 (T1/T2/T3) status now needs update from "open" to "T1+T2 resolved, T3 partial."

## Discovery

iter 32 receipt incorrectly stated `myworld/.aios/sprint_runs/uri/20260513T102836.json` was the *first* control-plane sprint receipt. Direct `ls -la /home/user/workspaces/jaewon/myworld/.aios/sprint_runs/uri/` at iter 35 wake shows:

```
20260513T023511.json   02:35 KST  Sprint earlier work
20260513T023526.json   02:35 KST
20260513T023544.json   02:35 KST
20260513T034425.json   03:44 KST  Sprint 011 scaffold
20260513T035325.json   03:53 KST  Sprint 011 progress
20260513T035837.json   03:58 KST  Sprint 011 progress
20260513T040221.json   04:02 KST  Sprint 011 close
20260513T091756.json   09:17 KST
20260513T091809.json   09:18 KST
20260513T102122.json   10:21 KST  Sprint 012 Task 1
20260513T102621.json   10:26 KST  Sprint 012 Task 2
20260513T102836.json   10:28 KST  Sprint 012 Task 3 (iter 32 thought was "first")
20260513T103047.json   10:30 KST
```

**13 receipts** spanning Sprint 011 + Sprint 012 ticks via claude provider-loop worker. The `sprint_runs/` channel is the working control-plane surface — has been since at least 02:35 KST.

## ASC-0063 status update per categorical item

### T1 — Worker `loop_mode` granularity (one_shot_tick → multi_tick/until_done)

**Status**: **RESOLVED**

**Evidence**: Sprint 011 = 4 sprint_runs receipts across 03:44 → 04:02 (~18 min, 4 ticks); Sprint 012 = 4 sprint_runs receipts across 10:21 → 10:30 (~9 min, 3 ticks per founder report). Multi-tick is in use — the worker is not exiting after a single tick.

### T2 — Claude `monitor_plan` fallback failure

**Status**: **RESOLVED**

**Evidence**: 
- Iter 18 surface: claude worker shipped code but Bash sandbox rejected `npm test`/`build`/`Playwright`.
- Iter 19 narrowed: "Bash subprocess permission for claude monitor_plan fallback worker."
- **Sprint 012 (10:21 → 10:30) = full ship via claude provider-loop worker including verification** per founder message: "Claude worker 정상 실행 / 직접 구현 우회 없이 AIOS tick 3개로 완료."
- npm test 18/18 + typecheck + build + Playwright all ran inside worker (per `worklog` Sprint 012 Task 3 entry).

Permission grant happened somewhere between iter 19 (failure observation) and Sprint 011 start (~03:44 KST). Untracked operator action.

### T3 — Receipt + dev-shell reconciliation

**Status**: **PARTIAL**

**Evidence**:
- `myworld/.aios/sprint_runs/uri/` **IS** the control-plane receipt channel for claude provider-loop worker outputs. Working since 02:35 KST.
- `bin/aios --root … provider-loop status --json` **still reports** both workers at `2026-05-13T00:11 KST` — the *legacy* provider-loop status surface has not been updated to consume `sprint_runs/`.
- New operator running `bin/aios provider-loop status` sees "stale 11+ hours" when reality is "13 successful sprint receipts in same window."

**Remaining work**: `bin/aios provider-loop status` should aggregate from `sprint_runs/` (or vice-versa). Two surfaces showing different state is the misleading-status problem T3 originally flagged.

## Implication for iter-16 escalation discovery

`myworld/docs/discoveries/2026-05-13-asc-0053-execution-layer-escalation.md` (iter 16) marked all 3 items "open." This update closes T1 + T2 and narrows T3 from "broad reconciliation" to "specific `provider-loop status` ↔ `sprint_runs/` aggregation."

ASC-0063 (or numbered next) can therefore be scoped much smaller than originally proposed:
- T1: no-op (already working).
- T2: confirm permission grant location and document it.
- T3: 1-WP — patch `aios_provider_loop.py` (or equivalent) to also read `sprint_runs/` glob and merge into status output.

## Why this took 19 iters to discover

claude@uri checked `bin/aios provider-loop status --json` every few iters per founder directive (operating principle #6). Never `ls`'d `sprint_runs/` directly. The legacy status surface returned stale 00:11 KST, so I assumed "still failing." Should have cross-checked filesystem directly when receipts started appearing in `uri/.aios/outbox/uri/` (claude-iter receipts) — that mirror would have suggested `sprint_runs/` was probably also live.

**Self-observation pattern**: trust direct filesystem evidence (ls + receipt count) over CLI status surface when the two diverge for >2 iter cycles.

## Sprint 015 (URI-017 packet, iter 34) downstream effect

URI-017 packet has 4 dependencies; one was "ASC-0063 closure or accept dev-shell continuity." With T1+T2 resolved + T3 narrowed, the dependency is now **operationally satisfied** even before T3 closes — Sprint 015 can ship via claude provider-loop worker as Sprint 011 + Sprint 012 did. Updates the URI-017 dependency list:

- ✅ founder confirmation (Option B fork; iter 33)
- ⏳ PIPA 변호사 review (~1-2 weeks)
- ⏳ ASC-0035 first-100 cohort flip ASC (operator pair)
- ⏳ pilot round 1 data (H6 self-ingest comfort)

ASC-0063 row drops from the gate.

## Carry into iter 36+

- claude@uri continues receipt cadence + ladder strategy.
- This discovery is the operator pair input for ASC-0063 closure decision (now 1-WP scope, not 3-WP).
- Self-observation log entry pending: T2 surface stale-status assumption correction + sprint_runs/ check pattern.
