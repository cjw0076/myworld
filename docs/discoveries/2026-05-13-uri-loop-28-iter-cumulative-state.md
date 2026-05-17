# Uri /loop 28-Iter Cumulative State — Operator Return-to-Loop Brief — 2026-05-13

Surface raised by `claude@uri` /loop iter 29 after 28 autonomous iterations under founder's 2026-05-13 directive. This is the single document the operator pair reads first when they return to the Uri loop. Other 29 memory drafts + 15 capability candidates + 4 prior discoveries are reference depth; this is the action document.

## TL;DR (60 seconds)

- **Sprint 005-011 SHIPPED** via codex@uri dev-shell (campus board → department → avatar → graph → agent guidance → student-life UI → local telemetry → human resource MemoryOS portfolio).
- **Sprint 012 + Sprint 014 QUEUED** as claude-authored packets (URI-016 polish + URI-014 consent preview); chair pickup pending.
- **Sprint 015 READINESS COMPLETE** on claude side: 4 of 5 blockers sketched as capability candidates; #5 graduates to Sprint 016.
- **Retention stage Sprint 016-019 strategy** staged in memory.
- **Pilot interview round 1 logistics + 학생-facing 1-pager** ready for distribution.
- **ASC-0063 escalation** open in ledger (iter 16, 2026-05-13); T2 narrowed to "Bash subprocess permission" by iter 19 evidence.
- **7 operator pair decisions stacked** (3 carry from iter 21 + 4 new from iter 22-27).

## 7 stacked operator pair decisions

| # | Decision                                            | claude@uri recommendation                                            | Surface                                                                                |
| - | --------------------------------------------------- | -------------------------------------------------------------------- | -------------------------------------------------------------------------------------- |
| 1 | 변호사 retain 시점                                  | post-Sprint-014 ship (~1-2주 lead time = Sprint 015 packet drafting) | `uri/memory/drafts/2026-05-13-korean-pipa-lawyer-brief.md`                            |
| 2 | ASC-0063 priority                                   | parallel with Sprint 015 (NOT blocking; dev-shell continues)         | `myworld/docs/discoveries/2026-05-13-asc-0053-execution-layer-escalation.md`           |
| 3 | Sprint 012 polish (URI-016) chair pickup           | fastest — 3 small WPs (badge hide / textarea / consent intent tele) | `uri/hive/packets/URI-016-sprint-012-polish-and-intent-telemetry.md`                  |
| 4 | PIPA lawyer scope (Korean-only vs Korean+GDPR)     | Korean-only first; Sprint 020+ international add                     | iter 22                                                                                |
| 5 | ASC-0035 first-100 cohort flip ASC trigger          | after Sprint 015 + 4 weeks audit data + PIPA lawyer green-light      | `uri/capabilities/asc-0035-self-ingest-dispatch-alignment-2026-05-13.md`              |
| 6 | Sprint 016 cloud target (Drive vs iCloud)          | Google Drive first (Korean student Gmail dominant)                   | `uri/memory/drafts/2026-05-13-retention-stage-strategy.md`                            |
| 7 | Sprint 018 Korean PG                                | 토스페이먼츠 (Korean dev UX strongest)                               | iter 26                                                                                |

## What the loop produced (28 iters cumulative)

| Artifact type            | Count | Location                                                              |
| ------------------------ | ----- | --------------------------------------------------------------------- |
| memory drafts            | 29    | `uri/memory/drafts/`                                                  |
| capability candidates    | 15    | `uri/capabilities/`                                                   |
| claude-authored packets  | 4     | `uri/hive/packets/URI-{008, 010, 014, 016}.md`                       |
| myworld discoveries      | 4 → 5 (this) | `myworld/docs/discoveries/`                                |
| ledger entries           | 4     | `myworld/docs/AIOS_AGENT_LEDGER.md`                                  |
| receipts                 | 28    | `uri/.aios/outbox/uri/claude.{1..28}.result.json`                    |

## Sprint 015 readiness 4-of-5 blocker map (refresh)

| # | Blocker                                | Sketched                                                                        | Status                       |
| - | -------------------------------------- | ------------------------------------------------------------------------------- | ---------------------------- |
| 1 | Notion OAuth provider routing          | `capabilities/notion-oauth-self-ingest-routing-2026-05-13.md`                  | ✅ sketched                   |
| 2 | MemoryOS schema extension              | `capabilities/memoryos-self-ingest-schema-extension-2026-05-13.md`             | ✅ sketched                   |
| 3 | Korean PIPA 변호사 surface             | `memory/drafts/2026-05-13-korean-pipa-lawyer-brief.md` (1-page hand-to-lawyer brief) | ✅ brief ready                |
| 4 | ASC-0035 policy-gated dispatch align   | `capabilities/asc-0035-self-ingest-dispatch-alignment-2026-05-13.md`           | ✅ sketched (6 action keys)   |
| 5 | Account-backed sync                    | graduates to Sprint 016 per retention-stage memory                              | 🔄 retention stage carry      |

## ASC-0063 escalation status

Per `myworld/docs/discoveries/2026-05-13-asc-0053-execution-layer-escalation.md` (iter 16):

- **T1**: worker `loop_mode=one_shot_tick` → need `multi_tick` or `until_done` for sprint-sized work.
- **T2**: claude `monitor_plan` fallback failure → narrowed to "Bash subprocess permission for claude monitor_plan fallback worker" by iter 19 evidence (Sprint 011 claude worker shipped code but couldn't run `npm test`/`build`/`Playwright`).
- **T3**: receipt + dev-shell reconciliation → `status=superseded_by_dev_shell` annotation; reaffirmed by Sprint 011 close (04:02:14) not registering as provider-loop tick.

**Fix surface**: extend `hivemind/hivemind/provider_loop.py` worker schema; add multi-tick mode; grant Bash subprocess permission for claude fallback worker. ASC-0063 (or numbered next) authors this.

## Provider-loop status (snapshot)

```
$ bin/aios --root /home/user/workspaces/jaewon/myworld provider-loop status --json
count: 2
ploop_ce1a3a94310aa3dc codex one_shot_tick stopped completed updated: 2026-05-13T00:11:06+09:00
ploop_0992ac5f5e38265d claude monitor_plan active failed updated: 2026-05-13T00:11:47+09:00
```

Both workers stuck since 00:11 KST (~9.5 hours stale at iter 29 wake). Sprint 008-011 all shipped via dev-shell *despite* this. dev-shell continues to be the producing path.

## Pilot round 1 readiness (iter 24 + iter 27)

Ready to launch when Sprint 014 ships + 1 week baseline:

- n=10 Ulsan students; 학과 balance (공대3/인문대2/상경대2/자연대1/예체능대1/의약대1).
- Budget ~₩200K (₩10K × 10 incentive + ₩50K printing + buffer).
- Optimistic start: 2026-05-22 KST (or whenever Sprint 014 ships + 1 week).
- Korean PIPA-aligned consent form; no audio recording.
- 학생-facing 1-pager (`uri/memory/drafts/2026-05-13-pilot-intro-1-pager-student-facing.md`) ready for kakao distribution.
- 4 operator pair adjustments before launch: 학교명 / tunnel URL / 발송 형식 / 인센티브 종류.

## What operator pair acts on (priority order)

If operator pair has ~30 min to act:

1. **Read this discovery** + iter-21 v1 cross-section + iter-28 v2 cross-section (15 min).
2. **Decide #3 Sprint 012 polish chair pickup** (fastest unblocker; URI-016 has 3 small WPs).
3. **Decide #2 ASC-0063** (open contract or accept dev-shell path; T1+T2+T3 sketch in iter 16 escalation discovery).
4. **Decide #1 PIPA lawyer retain timing** (post Sprint 014 ship recommended; 1-2주 lead).

If operator pair has ~2 hours:

5. **Read all 5 myworld discoveries** for full claude@uri /loop context.
6. **Sequence Sprint 014 + 015 chair pickup** (URI-014 first or parallel; depends on lawyer retain decision).
7. **Decide #4-#7** (PIPA scope / first-100 flip ASC / cloud target / PG).

If operator pair has a day:

8. **Author Sprint 015 packet** using 4 capability sketches + PIPA lawyer brief.
9. **Open ASC-0063** for provider-loop tuning if dev-shell sustainability concerns growing.
10. **Schedule pilot round 1** after Sprint 014 ship + 1 week.

## Operator silence pattern

9.5 hours since iter 16 escalation; 8 claude@uri surfaces accumulated (now 9 with this discovery):
- iter 16 escalation
- iter 21 cross-section v1
- iter 22 PIPA brief
- iter 23 polish packet URI-016
- iter 24 pilot logistics
- iter 25 ASC-0035 alignment
- iter 26 retention strategy
- iter 27 student 1-pager
- iter 28 cross-section v2
- iter 29 this cumulative discovery

**Interpretation**: founder /loop runs autonomously; operator presence is bursty (return when ready). Surface durability validated by 28 iters. Receipt summary fields enable fast skim. v1 + v2 + this discovery = entry stack.

## What this loop has NOT done (by design / by constraint)

- Direct edits to `uri/docs/URI_NORTHSTAR.md` / `PRODUCT_BRIEF.md` etc. (codex chair owns those; claude review-only).
- Direct edits to `hivemind/` / `memoryOS/` / `CapabilityOS/` source (operator pair lane).
- Push to remote / opened PRs (operator pair authorization required).
- Pilot interview execution (founder/operator does, not claude).
- Lawyer retainer (operator pair).
- Spending money (operator pair).

claude@uri stays in narrative + policy + sketch + review lane per founder's iter-1 directive.

## Next iter direction

iter 29+ candidates:

- **A**: continue receipt cadence + Sprint 020+ campus expansion preliminary sketch.
- **B**: MemoryOS provenance schema refresh (ASC-0050 primitive integration).
- **C**: pause sketching; wait for operator return; only emit receipt + worklog catch-up per iter.
- **D**: deeper claude self-evaluation (which of 28 outputs added load-bearing value vs noise).

claude@uri default: **A + receipt cadence**. (C is the safety pattern if operator silence becomes a load concern.)

## Carry into iter 30+

- Receipt cadence continues per founder /loop directive.
- This discovery becomes the *single document* operator pair reads first on return.
- Cross-section v2 (iter 28) is the deeper depth; this is the surface.
- Other 29 drafts + 15 capabilities are reference for specific decisions.
