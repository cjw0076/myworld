---
contract_id: ASC-0096
slug: control-plane-pingpong-provider-fallback
status: closed
goal: Prevent the myworld control-plane pingpong loop from stopping when the selected provider CLI is blocked by auth/access denial; fallback to the paired provider and record the attempt.
created: 2026-05-13 KST
accepted: 2026-05-13 12:15 KST by codex under founder-delegated continuation mandate
closed: 2026-05-13 12:16 KST
---

# ASC-0096 Control-Plane Pingpong Provider Fallback

## Why Now

After ASC-0091 closed, `AIOS_CONTINUE_AFTER_READY=1 AIOS_MAX_ROUNDS=1
scripts/aios_pingpong.sh run` proved the control-plane loop still stops when
`codex exec` returns localized access denial:

```text
접근 거부.
```

Child repo watcher fallback already handles this class, but the myworld
pingpong loop did not. This contract makes the control-plane loop use the same
basic provider-failure discipline.

## Scope

repos: `myworld`

allowed_files:

- `scripts/aios_pingpong.sh`
- `tests/test_aios_pingpong.py`
- `docs/contracts/ASC-0096-control-plane-pingpong-provider-fallback.md`
- `docs/contracts/README.md`
- `docs/AIOS_AGENT_LEDGER.md`
- `docs/AGENT_WORKLOG.md`

forbidden_files:

- `hivemind/**`
- `memoryOS/**`
- `CapabilityOS/**`
- `GenesisOS/**`
- `.env`

## Per-OS Responsibility

### myworld.must_produce

- Classify pingpong provider failures, including Korean `접근 거부`, as
  `provider_access_denied`.
- When `AIOS_PINGPONG_AGENT_FALLBACKS=1` (default), retry the same prompt with
  the fallback chain: `codex -> claude -> local`.
- Treat rate limits and quota exhaustion as `provider_backpressure` and
  continue the same fallback chain.
- Support local backdoor execution through `AIOS_LOCAL_AGENT_COMMAND`, falling
  back to Hive provider-loop local mode when available.
- Append `agent_attempt` and `agent_fallback_start` events to
  `.aios/state/aios_pingpong.jsonl`.
- Preserve STOP behavior for unknown failures, timeouts, and failed fallback.

### memoryOS.must_produce

- No implementation role. ASC-0091 now records closeouts as draft memory.

### hivemind.must_produce

- No implementation role. A future contract can route pingpong fallback through
  Hive provider-loop verification.

### capabilityos.must_produce

- No implementation role. A future contract can recommend provider order for
  control-plane pingpong the same way child watcher uses provider routes.

## Verification Gate

```bash
bash -n scripts/aios_pingpong.sh
python -m unittest tests/test_aios_pingpong.py
python -m unittest tests/test_aios_child_watcher.py
python scripts/aios_monitor.py assess --json
```

## Stop Conditions

- `unknown_pingpong_failure`
- `fallback_provider_failed`
- `fallback_loop_without_event_receipts`
- `raw_provider_output_copied_to_ledger`

## Receipts

- Implemented `failure_category`, `fallback_agent_for`, and
  `AIOS_PINGPONG_AGENT_FALLBACKS` in `scripts/aios_pingpong.sh`.
- Added local fallback support for provider backpressure with
  `AIOS_LOCAL_AGENT_COMMAND` / Hive provider-loop local mode.
- Added `tests/test_aios_pingpong.py` with a fake Korean Codex access-denied
  CLI, fake Claude fallback, and fake Claude rate-limit -> local fallback.
- Verification passed:
  - `bash -n scripts/aios_pingpong.sh`
  - `python -m unittest tests/test_aios_pingpong.py`
  - `python -m unittest tests/test_aios_child_watcher.py`
  - `python scripts/aios_monitor.py assess --json`
- Dispatch result: `.aios/outbox/myworld/asc-0096.myworld.result.json`
- Release-hook MemoryOS draft: `mem_4a44670b379ca4ea`
- Actual provider-exhaustion probe:
  - Codex attempt classified `provider_access_denied`.
  - Claude fallback classified `provider_backpressure` from "You've hit your
    limit".
  - Local fallback using `AIOS_LOCAL_AGENT_COMMAND='python3 scripts/aios_loop.py
    once --apply --json'` completed successfully.
  - Receipts: `.aios/state/aios_pingpong.jsonl`,
    `.aios/logs/round-1-local.fallback.log`.
