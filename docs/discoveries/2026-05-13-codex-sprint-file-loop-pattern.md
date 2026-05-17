# Codex local-sprint-file loop pattern — founder hypothesis confirmed + ASC-0053 binding — 2026-05-13

Surface raised by founder on 2026-05-13 KST during `/loop` dynamic mode on `claude@uri`. Founder articulated the loop mechanism explicitly and quoted `codex@uri` on the implementation-primitive gap. Cross-checking against `myworld/docs/AIOS_AGENT_LEDGER.md` shows the gap is **already closed** by ASC-0053 / 0054 / 0055 on 2026-05-13.

## Founder hypothesis (verbatim intent)

> "Codex가 계속 돌 수 있는 방법은 local sprint file을 참고하게 만들고, 해야할 일을 완수하면 멈추는데, 계속해서 해야할 일이 생기면 loop처럼 동작하지 않나?"

Mechanism:

1. **local sprint file as work queue** — `uri/hive/packets/URI-NNN-sprint-NNN-<slug>.md`.
2. **Codex one-shot worker** — consumes one packet → chair decision → implementation → typecheck/build/Playwright verify → receipt to `docs/AGENT_WORKLOG.md` → exit.
3. **new-to-do producer** — chair's own next candidate, `claude@uri` review packet (URI-008 / URI-010), founder/operator `.aios/goal_inbox/uri/` submission.
4. **natural stop + resume** — queue empty → codex exits; queue refills → next cycle.

## Codex's quoted gap (founder intake)

> "local sprint file + AIOS runner + Codex one-shot worker 조합이면 충분히 loop처럼 동작한다.
> 지금 막힌 부분은 개념이 아니라 실행 primitive야. Hive provider-loop가 Codex를 read-only sandbox로 호출해서 실제 repo 작업을 못 했고, Claude fallback도 non-interactive writable mode가 불안정했어. 고칠 건 'Codex가 loop를 못 돈다'가 아니라:"

Quoted sentence truncates. The continuation is *answered by ASC-0053/0054/0055* — see binding below.

## Uri evidence that the pattern works (current)

Sprint 001 → 008 inside `uri/` over a single session window:

| Sprint | Driver (new-to-do producer)                         | Result                                            |
| ------ | --------------------------------------------------- | ------------------------------------------------- |
| 001    | claude@uri spec / founder direction                 | Next.js scaffold + 4 routes                       |
| 002    | codex chair (auto)                                  | map gamification                                  |
| 003    | codex chair                                         | Kakao map provider + fallback                     |
| 004    | codex chair                                         | campus graph platform                             |
| 005    | codex chair (universe A over B+C)                   | department contribution layer                     |
| 006    | codex chair                                         | avatar agent surface + web research               |
| 007    | claude@uri `URI-008` packet — cross-agent producer  | agent guidance surface (3 cards)                  |
| 008    | claude@uri `URI-010` packet — review-driven         | partial WP-4 (mobile compact) so far              |

Three producer classes (chair self, claude review, founder/operator goal-inbox) all observed. Loop reaches a natural pause when the queue empties — exactly the founder's described mechanism.

## Binding to myworld closed contracts (2026-05-13)

The quoted gap is *not open*. `myworld/docs/AIOS_AGENT_LEDGER.md` shows it closed on the same date:

- **ASC-0053 Hive provider-loop runner closed** — `hivemind/hivemind/provider_loop.py` "absorb[s] Claude monitor-style plans, Codex one-shot ticks, and local LLM worker ticks into a Hive-owned provider-loop artifact surface." Hive commit `89458d7`. Decision: "AIOS should expose providers through Hive loop receipts, not rely on direct Claude/Codex chat prompting as the operating interface."
- **ASC-0054 global AIOS launcher closed** — `bin/aios` + `scripts/aios_launcher.py` + `bin/aios --root . provider-loop status --json` returning `hive.provider_loop.v1`. Decision: "AIOS should be globally reachable but workspace-local in state."
- **ASC-0055 Ollama Qwen provider absorption closed** — six-stage recipe (evidence → local registry → CapabilityOS card → Hive worker spec → observation collection → MemoryOS draft review). Demonstrates multi-provider beyond Codex / Claude.

**The founder's hypothesis is the design intent of ASC-0053.** Uri is its first child-repo instance.

## What is still open (carry into next ASC)

The pattern works; what remains is **control-plane visibility of claude@uri's iteration cycle**.

- **codex@uri** writes `.aios/goal_inbox/uri/` + `.aios/goal_routes/uri/` packets per AIOS intake (visible in codex worklog "AIOS intake" lines from Sprint 005 onward, ledger lines 1900–1921). Receipts land.
- **claude@uri** (this loop) does **not** currently emit receipts to `.aios/outbox/uri/`. Memory drafts + hive packets + worklog entries land *in the repo* but are invisible to `bin/aios … provider-loop status` until they trigger a codex pickup.
- **Bridging fix**: claude@uri starts emitting `aios.claude_iter.v1`-shaped receipts to `.aios/outbox/uri/claude.<iter>.result.json` after each /loop iteration. Format: `iter_id`, `evidence_paths`, `packets_authored`, `memory_drafts`, `recommendations`, `next_iter_plan`.

This is the only open recommendation from earlier draft of this discovery. (1) Hive provider-loop writable contract, (2) Claude fallback non-interactive stabilization, (3) Local sprint-file loop primitive formalization — all **closed by ASC-0053**.

## Implication for Uri /loop (claude@uri side)

Starting iter 6: emit `.aios/outbox/uri/claude.<iter>.result.json` after each ScheduleWakeup-bounded iteration. Format proposed inline; operator pair may consolidate with the existing Hive provider-loop receipt schema later.

## Next

- `claude@uri` iter 6: start receipt emission; resume sprint user-test cycle when codex Sprint 008 result lands.
- `claude@myworld` + `codex@myworld`: optional — decide whether claude@uri's per-iter receipt format should merge into Hive provider-loop's existing `hive.provider_loop.v1` artifact or stand as a sibling `aios.claude_iter.v1` schema. Low-priority — both work.

## Update 2026-05-13 KST iter 6 — provider-loop primitive working but Sprint 008 fails through both providers

`bin/aios --root /home/user/workspaces/jaewon/myworld provider-loop status --json` from `claude@uri` iter 6 returned `count=2`:

- **codex worker** `ploop_ce1a3a94310aa3dc`, `loop_mode=one_shot_tick`, `tick_count=1`, `status=stopped`, `last_status=completed`. Prompt cites `hive/packets/URI-010-sprint-008-claude-followup-after-agent-guidance.md` — *claude@uri's review packet DID reach the provider-loop*. But the single-tick limit means it stopped without producing the Sprint 008 artifact.
- **claude worker** `ploop_0992ac5f5e38265d`, `loop_mode=monitor_plan`, `tick_count=1`, `status=active`, `last_status=failed`. Prompt explicitly cites "AIOS-owned Uri Sprint 008 execution **after Codex provider sandbox failure**." The fallback also failed.

This is the *exact* failure mode codex@uri quoted on 2026-05-13:

> "Hive provider-loop가 Codex를 read-only sandbox로 호출해서 실제 repo 작업을 못 했고, Claude fallback도 non-interactive writable mode가 불안정했어."

ASC-0053 closed the **primitive layer** — provider-loop runner exists, accepts prompts, writes receipts under `.runs/run_<id>/provider_loops/`. What is *not yet stable* is the **execution layer** — actually getting a child agent to complete a Sprint inside `uri/` through the provider-loop, rather than via the founder's dev shell.

Sprint 001–007 land via dev-shell. Sprint 008 has so far only land *partially* (mobile-compact screenshot, but no completion receipt). The provider-loop tried twice and failed twice on first-tick.

### Open operator-checkpoint candidates

1. **codex worker single-tick limit** — `loop_mode=one_shot_tick` exits after one tick. Sprint 008 has 4 work packages (WP-1 reflection CTA, WP-2 chip aria-disabled, WP-3 readiness formula, WP-4 mobile padding) — one tick is not enough. ASC-0053 should allow `multi_tick` or `until_done` mode for sprint-sized work.
2. **claude monitor_plan fallback failure** — `last_status=failed`. Diagnose: timeout? auth? non-interactive plan-write conflict with dev-shell concurrent writes?
3. **provider-loop receipt + dev-shell receipt reconciliation** — both paths can leave artifacts in `uri/`; need a merge policy so monitor sees both without double-counting.

These are runtime issues in ASC-0053's implementation, not new contracts — the design is correct, the impl needs tuning. Operator pair to triage.

### Iter 6 claude@uri output (this iter)

- First receipt emitted: `uri/.aios/outbox/uri/claude.6.result.json` (schema `aios.claude_iter.v1`). Includes provider-loop observation above so any future `bin/aios … status` consumer sees the failure context from the claude side.
- Memory growth: `uri/memory/drafts/2026-05-13-competitive-notion-for-education.md` — first self-ingest target candidate for Sprint 010+.
- This update appended here.
