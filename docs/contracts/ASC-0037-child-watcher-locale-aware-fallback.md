---
contract_id: ASC-0037
slug: child-watcher-locale-aware-fallback
status: accepted
goal: Make child-watcher provider-fallback recognize codex CLI access-denied messages in Korean (and other locales) so ASC-0025 fallback triggers when codex CLI rejects non-interactive auth in localized text.
created: 2026-05-12 KST
accepted: 2026-05-12 KST by claude acting operator
closed:
acceptance_authority: claude@myworld (operator) — ASC-0036 child dispatches just failed because the existing English-only regex did not catch the actual codex CLI Korean error.
---

# ASC-0037 Child Watcher Locale-Aware Fallback

## Why Now

ASC-0036 fan-out dispatched 3 child packets (hivemind, memoryOS, CapabilityOS).
All 3 failed identically:

```
틀렸습니다. (1/3)
틀렸습니다. (2/3)
접근 거부.
```

`scripts/aios_child_watcher.sh` line 314 categorized them as
`child_agent_failed`, not `provider_access_denied`, because its regex matches
only English ("access denied", "permission denied", "unauthorized", etc.). The
result: `AIOS_CHILD_AGENT_FALLBACKS=1` was set, but the fallback condition at
line 470 (`category == "provider_access_denied"`) never fired, so claude was
not tried as the alternate agent. ASC-0025 was supposed to recover from
exactly this; the gap is locale coverage.

This contract closes that gap. It does not redesign the fallback — it teaches
the failure-category classifier the actual strings the codex CLI emits.

## Scope

repos:

- `myworld`

allowed_files:

- `scripts/aios_child_watcher.sh`
- `tests/test_aios_child_watcher.py`
- `docs/contracts/ASC-0037-child-watcher-locale-aware-fallback.md`
- `docs/contracts/README.md`
- `docs/AIOS_AGENT_LEDGER.md`

forbidden_files:

- `hivemind/**`
- `memoryOS/**`
- `CapabilityOS/**`
- `uri/**`
- `.aios/logs/**`
- `.env`
- raw export paths

## Per-OS Responsibility

### myworld.must_produce

- `aios_child_watcher.sh` `failure_category` regex now also matches:
  - `접근.*거부` (Korean: "access denied")
  - `틀렸습니다` (Korean codex CLI auth-prompt failure line)
  - any other locale strings codex CLI emits for the same failure (operator
    discretion if more locales surface).
- Regression test in `tests/test_aios_child_watcher.py` that:
  - Feeds a synthetic log file containing the Korean strings.
  - Asserts `failure_category` resolves to `provider_access_denied`.
  - (If feasible) asserts the fallback path is taken and `fallback_used=true`.
- Contract closeout commit, ledger entry, monitor assessment clear.

### child repos

- No source change. Child repos consume the corrected fallback indirectly the
  next time they are dispatched.

### operator

- After close: `aios_dispatch.py retry --dispatch-id asc-0036` to re-run the
  3 held child packets through the corrected watcher.

## Verification Gate

```bash
python -m unittest tests/test_aios_child_watcher.py
python -m unittest tests/test_aios_instruction_index.py tests/test_aios_loop_policy.py tests/test_aios_doc_scout.py tests/test_aios_readiness.py tests/test_aios_dispatch.py tests/test_aios_loop.py tests/test_aios_monitor.py tests/test_aios_goal_evolution.py tests/test_aios_child_watcher.py tests/test_aios_round_controller.py tests/test_aios_web_research_receipt.py tests/test_aios_institution_readiness.py tests/test_aios_action_policy.py tests/test_aios_semantic_handshake.py
python scripts/aios_monitor.py assess --json
```

Pass criteria:

- `test_aios_child_watcher.py` includes a Korean-locale failure-category test
  and it passes.
- Full myworld test suite passes.
- Monitor assessment is clear.
- After close, retried ASC-0036 child packets either succeed (claude fallback
  works) or cleanly trigger a NEW recognized stop condition (no silent
  `child_agent_failed` masking auth issues).

## Stop Conditions

- `regex_too_broad`: new pattern matches non-auth failures (e.g. routine
  Korean error messages from unrelated tools).
- `fallback_loop`: fallback agent (claude) also fails with same category and
  watcher recurses without bound.
- `child_repo_source_edit`: this contract changes child repo source.
- `english_pattern_regression`: existing English patterns no longer match.

## Receipts

Pending until verification.

## Work Packets

### WP-0037-A — Codex@myworld extends locale coverage

- target_agent: codex
- target_repo: myworld
- status: accepted
- issued: 2026-05-12 KST
- accepted: 2026-05-12 KST
- closed: pending
- depends_on: ASC-0025 closed (existing fallback structure)
- brief: |
    Extend `scripts/aios_child_watcher.sh` `failure_category` regex with
    Korean codex CLI auth-failure strings. Add a regression test in
    `tests/test_aios_child_watcher.py`. Do not change fallback semantics or
    the existing English patterns.

    Required reading:
      1. /home/user/workspaces/jaewon/myworld/AGENTS.md
      2. /home/user/workspaces/jaewon/myworld/docs/AIOS_AGENT_SELF_LOOP.md
      3. /home/user/workspaces/jaewon/myworld/docs/contracts/ASC-0025-child-watcher-provider-fallback.md
      4. /home/user/workspaces/jaewon/myworld/scripts/aios_child_watcher.sh (lines 310-330, 460-480)
      5. /home/user/workspaces/jaewon/myworld/.aios/logs/asc-0036.hivemind.child.log (sample real-world failure log)

    After closeout: surface readiness for `aios_dispatch.py retry --dispatch-id asc-0036`
    so ASC-0036 fan-out can resume through the corrected watcher.
- result: pending
