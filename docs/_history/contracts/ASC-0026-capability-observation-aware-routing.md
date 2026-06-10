---
contract_id: ASC-0026
slug: capability-observation-aware-routing
status: closed
goal: Make CapabilityOS recommendations consume prior observation outcomes so later routing decisions reflect real AIOS result history.
created: 2026-05-12 02:31 KST
accepted: 2026-05-12 02:31 KST by codex acting operator
closed: 2026-05-12 02:34 KST
supersedes: none
---

# ASC-0026 Capability Observation-Aware Routing

## Goal

ASC-0009 taught CapabilityOS to observe AIOS dispatch result packets and update
capability confidence in a returned payload. The learning still does not affect
normal routing because `capabilityos recommend` only ranks static catalog
cards.

This contract connects the two surfaces: recommendations may consume prior
observation outcomes from `.aios/outbox`, update card confidence
in-memory, and include observation evidence in route scoring. CapabilityOS
remains recommendation-only and does not execute tools or mutate the catalog.

## Scope

repos:

- `CapabilityOS`
- `myworld`

allowed_files:

- `CapabilityOS/capabilityos/catalog.py`
- `CapabilityOS/capabilityos/observation.py`
- `CapabilityOS/capabilityos/cli.py`
- `CapabilityOS/capabilityos/schema.py`
- `CapabilityOS/tests/test_cli.py`
- `CapabilityOS/tests/test_observation.py`
- `CapabilityOS/README.md`
- `CapabilityOS/AGENTS.md`
- `docs/contracts/ASC-0026-capability-observation-aware-routing.md`
- `docs/contracts/README.md`
- `docs/AIOS_AGENT_LEDGER.md`
- `docs/goals/AIOS-GOAL-0001-make-something-great.md`
- `docs/goals/AIOS-GOAL-0001-evolution.md`

forbidden_files:

- `hivemind/**`
- `memoryOS/**`
- `CapabilityOS/data/**`
- `CapabilityOS/.runs/**`
- `CapabilityOS/.local/**`
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

- Recommendation learning is in-memory for V1. It may read result packets but
  must not write a persistent catalog or observation store.
- Failed and timeout result packets are valid observations. They should lower
  confidence through the existing bounded Beta-style confidence rule instead of
  being only operator-review gaps.
- Skipped, invalid, or unmapped result packets remain gaps.
- Ranking should expose why observations influenced a result, for example a
  confidence score/reason and an observation count.

## Per-OS Responsibility

- **capabilityos.must_produce**:
  - an observation-aware recommend path;
  - CLI support for passing an AIOS outbox to recommendation;
  - tests proving pass/fail observations change confidence or route ordering;
  - recommendation-only audit remains clean.
- **myworld.must_produce**:
  - contract, dispatch, closeout, goal update, and ledger entry.
- **hive_mind.must_produce**: no source change.
- **memoryos.must_produce**: no source change.
- **operator.must_produce**: release only after CapabilityOS tests and live
  CLI smoke show observations influencing recommendation output.

## Verification Gate

```bash
cd /home/user/workspaces/jaewon/myworld/CapabilityOS
python -m pytest tests/test_cli.py tests/test_observation.py -v
python -m capabilityos.cli recommend --task "route AIOS execution after provider failures" --observations-inbox /home/user/workspaces/jaewon/myworld/.aios/outbox --json
python -m capabilityos.cli audit --json
```

Expected evidence:

- tests pass;
- recommendation output includes observation summary/evidence and confidence
  reason codes;
- at least one failed or timeout mapped result can lower confidence in a
  synthetic test;
- `audit` returns `execution_enabled=[]` and `recommendation_only=true`;
- no child repo other than CapabilityOS is modified.

## Stop Conditions

- `execution_creep`: CapabilityOS executes tools, provider CLIs, network calls,
  MCP bindings, or child watchers.
- `persistent_catalog_mutation`: recommendation writes catalog/observation
  files instead of returning a payload.
- `raw_log_leak`: recommendation includes raw stdout/stderr/log bodies.
- `unmapped_auto_capability`: unmapped result packets create new capabilities
  automatically.
- `child_repo_edit`: hivemind or memoryOS source changes.
- `monitor_blocked`: myworld monitor reports blocked after collect/release.

## Work Packets

### WP-0026-A — Codex@CapabilityOS wires observations into recommendations

- target_agent: codex
- target_repo: CapabilityOS
- status: done
- issued: 2026-05-12
- accepted: 2026-05-12 02:31 KST
- closed: 2026-05-12 02:34 KST
- depends_on: ASC-0009, ASC-0025
- brief: |
    Extend CapabilityOS recommendation so it can consume `.aios/outbox`
    observation outcomes in-memory and reflect confidence/evidence in the
    returned routing payload. Keep the recommendation-only invariant intact.
- result: CapabilityOS commit `6182b8f`; dispatch collected and released; see Receipts.

## Receipts

Closed 2026-05-12 02:34 KST by `codex@myworld` acting operator.

- Dispatch:
  - `.aios/inbox/CapabilityOS/asc-0026.CapabilityOS.json`
  - `.aios/outbox/CapabilityOS/asc-0026.CapabilityOS.result.json`
- Implementation:
  - CapabilityOS commit `6182b8f` (`Add observation-aware capability routing`)
  - `CapabilityOS/capabilityos/catalog.py`
  - `CapabilityOS/capabilityos/observation.py`
  - `CapabilityOS/capabilityos/cli.py`
  - `CapabilityOS/tests/test_cli.py`
  - `CapabilityOS/tests/test_observation.py`
  - `CapabilityOS/README.md`
  - `CapabilityOS/AGENTS.md`
- Verification:
  - `python -m pytest tests/test_cli.py tests/test_observation.py -v`
    passed 11/11 in CapabilityOS.
  - `python -m capabilityos.cli recommend --task "route AIOS execution after
    provider failures" --observations-inbox
    /home/user/workspaces/jaewon/myworld/.aios/outbox --json` returned
    `observation_summary.observations_count=17`, `observed_capabilities=3`,
    and confidence/observed reason codes.
  - `python -m capabilityos.cli audit --json` returned `execution_enabled=[]`
    and `recommendation_only=true`.
  - `python scripts/aios_dispatch.py watch --repo CapabilityOS --dispatch-id
    asc-0026 --once` wrote a passed result packet.
  - `python scripts/aios_dispatch.py collect --repo CapabilityOS` collected
    the result packet.
  - `python scripts/aios_dispatch.py release --dispatch-id asc-0026 --reason
    asc_0026_capability_observation_aware_routing_verified` succeeded.
  - `python scripts/aios_monitor.py assess --json` returned `health=clear`
    after generated cache cleanup.
- Stop conditions triggered: none.
