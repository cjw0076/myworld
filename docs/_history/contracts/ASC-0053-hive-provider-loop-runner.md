---
contract_id: ASC-0053
slug: hive-provider-loop-runner
status: closed
goal: Add a Hive-owned provider loop runner that treats Claude CLI, Codex CLI, and local LLM workers as durable loop workers with shared receipts, stop conditions, and fallback semantics.
created: 2026-05-12 23:52 KST
accepted: 2026-05-12 23:52 KST by codex acting operator (founder directive)
closed: 2026-05-13 00:02 KST
acceptance_authority: codex@myworld acting operator per founder directive that AIOS should absorb Claude/Codex/local LLM loops into Hive Mind.
---

# ASC-0053 Hive Provider Loop Runner

## Why Now

Claude CLI has Monitor/ScheduleWakeup-style persistence. Codex CLI is
normally one-shot and advances only when the user sends another prompt. Local
LLM workers have a third lifecycle. This makes the operator loop depend on
provider-specific behavior instead of AIOS.

ASC-0050 and ASC-0052 moved monitor/runtime primitives into `myworld`, but the
execution owner for provider orchestration is Hive Mind. This contract adds a
Hive surface that can prepare, run, and inspect provider loop workers using one
artifact schema.

## Required Reading

- `docs/AIOS_DEFINITION.md`
- `docs/AIOS_BUILD_METHOD.md`
- `docs/AIOS_PRIMITIVES.md`
- `docs/contracts/ASC-0050-aios-primitive-surface.md`
- `docs/contracts/ASC-0052-aios-native-runtime-entrypoint.md`
- `hivemind/AGENTS.md`
- `hivemind/hivemind/provider_passthrough.py`
- `hivemind/hivemind/supervisor.py`
- `hivemind/hivemind/hive.py`
- `hivemind/tests/test_provider_passthrough.py`

## Scope

repos:

- `hivemind`
- `myworld`

allowed_files:

- `hivemind/hivemind/provider_loop.py`
- `hivemind/hivemind/hive.py`
- `hivemind/tests/test_provider_loop.py`
- `hivemind/docs/TODO.md`
- `hivemind/docs/AGENT_WORKLOG.md`
- `hivemind/.ai-runs/shared/comms_log.md`
- `docs/contracts/ASC-0053-hive-provider-loop-runner.md`
- `docs/contracts/README.md`
- `docs/AIOS_AGENT_LEDGER.md`

forbidden_files:

- `memoryOS/**`
- `CapabilityOS/**`
- `uri/**`
- `.runs/**`
- `.aios/state/**`
- `.aios/logs/**`
- `.env`
- raw export paths

## Responsibilities

- **hivemind.must_produce**:
  - `hivemind/hivemind/provider_loop.py` with a schema
    `hive.provider_loop.v1`.
  - `hive provider-loop prepare --provider <claude|codex|local> --prompt <text> --json`:
    writes a loop worker plan under the run artifacts without executing the
    provider.
  - `hive provider-loop tick --worker <id> --json`: runs one bounded tick. For
    provider CLIs it must call existing provider passthrough machinery or
    prepare-only receipts; for `local` it must use existing local worker
    boundaries. It must never start an unbounded loop by default.
  - `hive provider-loop status --json`: lists workers, last tick, result
    status, provider mode, and next recommended action.
  - `hive provider-loop stop --worker <id> --json`: records a stop receipt.
  - Tests for prepare/tick/status/stop, Codex one-shot semantics, Claude
    monitor-equivalent semantics as a plan, local worker semantics, and
    provider failure/fallback receipt shape.
- **myworld.must_produce**:
  - Contract closeout, dispatch/result collection, README index update, ledger
    entry, and monitor/readiness verification.
- **memoryos.must_produce**: no source role in this contract.
- **capabilityos.must_produce**: no source role in this contract.

## Verification Gate

```bash
cd hivemind
python -m pytest tests/test_provider_loop.py -v
python -m pytest tests/test_provider_loop.py tests/test_provider_passthrough.py tests/test_supervisor.py -v
python -m hivemind.hive --root /tmp/asc-0053-hive provider-loop prepare --provider codex --prompt "inspect status" --json
python -m hivemind.hive --root /tmp/asc-0053-hive provider-loop status --json
python -m pytest
cd ..
python scripts/aios_monitor.py assess --json
```

Pass criteria:

- Provider loop artifacts are written under a Hive run directory.
- Codex is represented as one-shot tickable, not as a fake persistent chat.
- Claude monitor-style persistence is represented as a loop worker plan, not
  as a dependency on Claude Code being alive.
- Local workers share the same status/tick/stop surface.
- No provider command executes unless the existing Hive policy gate allows it.
- Full Hive tests pass and MyWorld monitor is clear after release.

## Stop Conditions

- `provider_loop_unbounded_default`: any default command starts an infinite
  provider loop.
- `provider_loop_bypasses_policy`: provider CLI execution skips existing Hive
  passthrough/protocol gates.
- `codex_fake_persistence`: Codex is represented as continuously alive instead
  of one-shot tickable.
- `claude_cli_required_for_status`: status cannot be computed unless Claude
  CLI is running.
- `local_worker_scope_leak`: local worker tick edits outside run artifacts
  without explicit execution policy.
- `child_repo_scope_leak`
- `verification_gate_failed`

## Work Packets

### WP-0053-A — Codex@hivemind builds provider-loop runner

- target_agent: codex
- target_repo: hivemind
- status: done
- issued: 2026-05-12 23:52 KST
- accepted: 2026-05-12 23:52 KST
- closed: 2026-05-13 00:02 KST
- brief: |
    Implement the Hive-owned provider loop runner. Reuse
    `provider_passthrough.py`, supervisor/run artifact conventions, and
    existing provider/local worker receipts. Do not invent a new daemon. The
    runner should expose prepare/tick/status/stop and make provider persistence
    explicit through artifacts.
- result: `.aios/outbox/hivemind/asc-0053.hivemind.result.json`

### WP-0053-B — Codex@myworld closes the control-plane side

- target_agent: codex
- target_repo: myworld
- status: done
- issued: 2026-05-12 23:52 KST
- accepted: 2026-05-12 23:52 KST
- closed: 2026-05-13 00:06 KST
- brief: |
    After Hive returns a result packet, collect/release dispatch, update this
    contract receipts, README, and ledger, then verify monitor clear.
- result: `.aios/outbox/myworld/asc-0053.myworld.result.json`

## Receipts

- Hive implementation commit: `hivemind@89458d7`
- Hive result packet: `.aios/outbox/hivemind/asc-0053.hivemind.result.json`
- Focused tests: `python -m pytest tests/test_provider_loop.py -v` passed 7/7.
- Integration focused tests:
  `python -m pytest tests/test_provider_loop.py tests/test_provider_passthrough.py tests/test_supervisor.py -v`
  passed 23/23.
- CLI smoke: `hive provider-loop prepare/status` under
  `/tmp/asc-0053-hive` wrote one Codex worker with
  `schema_version=hive.provider_loop.v1` and `loop_mode=one_shot_tick`.
- Full Hive suite: `python -m pytest` passed 329/329.
- MyWorld monitor: `python scripts/aios_monitor.py assess --json`.

## Closeout Decision

ASC-0053 closes the immediate provider-loop gap. AIOS can now describe Claude,
Codex, and local LLMs as Hive-owned loop workers without pretending they have
the same runtime lifecycle.

The next contract should add a thin global `aios` launcher. The launcher should
be global, but state should remain workspace-local: it finds the nearest
`myworld` control plane or uses `AIOS_HOME`, then calls the AIOS runtime and
Hive provider-loop surfaces.
