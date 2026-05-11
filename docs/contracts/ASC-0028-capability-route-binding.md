---
contract_id: ASC-0028
slug: capability-route-binding
status: closed
goal: Bind child watcher provider fallback selection to CapabilityOS observation-aware provider route recommendations.
created: 2026-05-12 03:00 KST
accepted: 2026-05-12 03:00 KST by codex acting operator
closed: 2026-05-12 03:04 KST
supersedes: none
---

# ASC-0028 Capability Route Binding

## Goal

ASC-0025 made child watcher provider fallback reliable but still static:
`codex` falls back to `claude`, and `claude` falls back to `codex`.
ASC-0026 made CapabilityOS recommendations observation-aware, but myworld does
not yet use those recommendations for provider route choice.

This contract connects the two: CapabilityOS emits a recommendation-only
provider route plan from local result-packet observations, and myworld's child
watcher reads that route plan before choosing a provider fallback.

## Scope

repos:

- `CapabilityOS`
- `myworld`

allowed_files:

- `CapabilityOS/capabilityos/catalog.py`
- `CapabilityOS/capabilityos/cli.py`
- `CapabilityOS/tests/test_cli.py`
- `CapabilityOS/README.md`
- `CapabilityOS/AGENTS.md`
- `scripts/aios_child_watcher.sh`
- `tests/test_aios_child_watcher.py`
- `docs/AIOS_WORK_DISPATCH.md`
- `docs/contracts/ASC-0028-capability-route-binding.md`
- `docs/contracts/README.md`
- `docs/AIOS_AGENT_LEDGER.md`
- `docs/goals/AIOS-GOAL-0001-make-something-great.md`
- `docs/goals/AIOS-GOAL-0001-evolution.md`

forbidden_files:

- `hivemind/**`
- `memoryOS/**`
- `CapabilityOS/data/**`
- `.aios/**`
- `.runs/**`
- `.ai-runs/**`
- `raw_exports/**`
- `exports/**`
- `logs/**`
- `weights/**`
- `**/*secret*`
- `**/*credential*`
- `.env`
- `.env.*`

## Design Decisions

- CapabilityOS still does not execute providers. It only recommends a route.
- Provider observations are derived from local result packets and
  `agent_attempts[]`; raw stdout/stderr/log bodies are not read into durable
  output.
- Child watcher uses CapabilityOS route plans only for access/auth-denied
  fallback selection. Timeout, missing command, unsupported agent, and ordinary
  child-agent failure behavior stays unchanged.
- If CapabilityOS route planning is unavailable or returns no valid alternate,
  child watcher falls back to the ASC-0025 static alternate.

## Per-OS Responsibility

- **capabilityos.must_produce**:
  - `provider-route` JSON command;
  - bounded agent confidence from result-packet attempt history;
  - tests proving failed agent attempts lower route ranking;
  - recommendation-only audit remains clean.
- **myworld.must_produce**:
  - child watcher route-plan call and fallback selection;
  - fake-provider/fake-CapabilityOS tests proving route-selected fallback;
  - contract, dispatch, closeout, and ledger.
- **hive_mind.must_produce**: no source change.
- **memoryos.must_produce**: no source change.
- **operator.must_produce**: release only after CapabilityOS and myworld tests
  pass and monitor is clear.

## Verification Gate

```bash
cd /home/user/workspaces/jaewon/myworld/CapabilityOS
python -m pytest tests/test_cli.py -v
python -m capabilityos.cli provider-route --task "child watcher provider fallback" --assigned-agent codex --observations-inbox /home/user/workspaces/jaewon/myworld/.aios/outbox --json
python -m capabilityos.cli audit --json

cd /home/user/workspaces/jaewon/myworld
python -m unittest tests/test_aios_child_watcher.py
```

Additional operator syntax check:

- `bash -n scripts/aios_child_watcher.sh`

Expected evidence:

- CapabilityOS route plan returns `contract=capabilityos.provider_route.v1`,
  `recommendation_only=true`, `fallback_agents[]`, and per-agent reason codes.
- Synthetic observations can make `claude` preferred over `codex`.
- Child watcher writes a route plan file and chooses the route-selected fallback
  in a fake-provider test.
- Existing no-fallback-on-ordinary-failure behavior remains unchanged.

## Stop Conditions

- `execution_creep`: CapabilityOS executes provider CLIs or starts watchers.
- `raw_log_leak`: route plans include raw stdout/stderr/log bodies.
- `fallback_on_wrong_failure`: child watcher uses route fallback for timeout,
  missing command, unsupported agent, or ordinary child-agent failure.
- `child_repo_edit`: hivemind or memoryOS source changes.
- `monitor_blocked`: myworld monitor is blocked after collect/release.

## Work Packets

### WP-0028-A — Codex@CapabilityOS adds provider route recommendation

- target_agent: codex
- target_repo: CapabilityOS
- status: done
- issued: 2026-05-12
- accepted: 2026-05-12 03:00 KST
- closed: 2026-05-12 03:03 KST
- depends_on: ASC-0026
- brief: |
    Add a recommendation-only provider route command over result-packet
    `agent_attempts[]`, with tests and audit preserved.
- result: CapabilityOS commit `80ab22a`; dispatch result passed.

### WP-0028-B — Codex@myworld binds child watcher fallback to route plan

- target_agent: codex
- target_repo: myworld
- status: done
- issued: 2026-05-12
- accepted: 2026-05-12 03:00 KST
- closed: 2026-05-12 03:03 KST
- depends_on: WP-0028-A, ASC-0025
- brief: |
    Make `scripts/aios_child_watcher.sh` consult CapabilityOS provider-route
    output before selecting an access-denied fallback agent.
- result: myworld child watcher route binding passed; dispatch result passed.

## Receipts

Closed 2026-05-12 03:04 KST by `codex@myworld` acting operator.

- Dispatch:
  - `.aios/inbox/CapabilityOS/asc-0028.CapabilityOS.json`
  - `.aios/inbox/myworld/asc-0028.myworld.json`
  - `.aios/outbox/CapabilityOS/asc-0028.CapabilityOS.result.json`
  - `.aios/outbox/myworld/asc-0028.myworld.result.json`
- Implementation:
  - CapabilityOS commit `80ab22a` (`Add CapabilityOS provider route plan`)
  - `scripts/aios_child_watcher.sh`
  - `tests/test_aios_child_watcher.py`
  - `docs/AIOS_WORK_DISPATCH.md`
- Verification:
  - CapabilityOS `python -m pytest tests/test_cli.py -v` passed 8/8.
  - CapabilityOS `provider-route --assigned-agent codex
    --observations-inbox .aios/outbox --json` returned
    `contract=capabilityos.provider_route.v1`, `recommendation_only=true`, and
    `fallback_agents=["claude"]` with relative evidence refs.
  - CapabilityOS `python -m capabilityos.cli audit --json` returned
    `execution_enabled=[]` and `recommendation_only=true`.
  - myworld `python -m unittest tests/test_aios_child_watcher.py` passed 2/2.
  - `bash -n scripts/aios_child_watcher.sh` passed.
  - `python scripts/aios_dispatch.py watch --repo CapabilityOS --dispatch-id
    asc-0028 --once` and `--repo myworld` both wrote passed result packets.
  - `python scripts/aios_dispatch.py collect --repo CapabilityOS` and
    `--repo myworld` collected both result packets.
  - `python scripts/aios_dispatch.py release --dispatch-id asc-0028 --reason
    asc_0028_capability_route_binding_verified` succeeded.
  - `python scripts/aios_monitor.py assess --json` returned `health=clear`
    after generated cache cleanup.
- Stop conditions triggered: none.
