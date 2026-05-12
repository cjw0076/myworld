---
contract_id: ASC-0038
slug: self-resonant-repo-loop
status: closed
goal: Let lower repos submit goals or friction to always-on myworld, receive MemoryOS/CapabilityOS/Hive route packets, and turn returned friction into AIOS improvement candidates.
created: 2026-05-12 17:18 KST
accepted: 2026-05-12 17:18 KST by codex acting operator
closed: 2026-05-12 17:36 KST
---

# ASC-0038 Self-Resonant Repo Loop

## Why Now

ASC-0036 aligned the language used by hivemind, memoryOS, and CapabilityOS.
The next missing capability is resonance: lower repos must be able to submit a
goal, blocker, or friction note to myworld and receive a routed AIOS work
packet instead of relying on chat relay.

This contract creates the first executable surface for that loop. It does not
build the final visualization app. It creates the file/CLI protocol that the
future app can render.

## AIOS Inputs Used

- MemoryOS context build:
  `trace_id=rtrace_7f8eb07cf6b0137e`, selected accepted memory
  `mem_90b5cfe6570e6ee2`, feedback directive: accepted artifact context says
  Hive acts, MemoryOS remembers, and accepted memory returns as future context.
- CapabilityOS route:
  `cap_hivemind_execution_harness` ranked first, with
  `cap_memoryos_import_run`, `cap_memoryos_context_build`, and
  `cap_capabilityos_recommendation` as supporting routes. The route also
  surfaced an outside-research route as out of scope for this local-first
  protocol slice.
- Hive Mind dry-run:
  `run_20260512_171540_45136a`, `route_source=heuristic_fast`, prepared
  artifact `.runs/run_20260512_171540_45136a/agents/codex/executor_result.yaml`.

## Scope

repos:

- `myworld`
- `hivemind`
- `memoryOS`
- `CapabilityOS`

allowed_files:

- `docs/AIOS_REPO_GOAL_LOOP.md`
- `docs/AIOS_OPERATING_LOOP.md`
- `docs/AIOS_WORK_DISPATCH.md`
- `scripts/aios_repo_goal.py`
- `tests/test_aios_repo_goal.py`
- `docs/contracts/ASC-0038-self-resonant-repo-loop.md`
- `docs/contracts/README.md`
- `docs/goals/AIOS-GOAL-0001-make-something-great.md`
- `docs/goals/AIOS-GOAL-0001-evolution.md`
- `docs/AIOS_AGENT_LEDGER.md`
- `hivemind/AGENTS.md`
- `hivemind/.ai-runs/shared/comms_log.md`
- `memoryOS/AGENTS.md`
- `memoryOS/docs/AGENT_WORKLOG.md`
- `CapabilityOS/AGENTS.md`

forbidden_files:

- `hivemind/hivemind/**`
- `memoryOS/memoryos/**`
- `CapabilityOS/capabilityos/**`
- `uri/**`
- `.aios/logs/**`
- `.aios/state/**`
- `.env`
- unreviewed source-dump paths

## Responsibilities

### myworld

must_produce:

- `docs/AIOS_REPO_GOAL_LOOP.md` specifying the repo-goal submission and route
  response protocol.
- `scripts/aios_repo_goal.py` with:
  - `submit`: write a repo-originated goal packet under
    `.aios/goal_inbox/<repo>/`.
  - `route`: read pending goal packets and write a deterministic route packet
    under `.aios/goal_routes/<repo>/`.
  - `status`: summarize pending/routed goal packets.
- `tests/test_aios_repo_goal.py` covering submit, route, status, invalid repo,
  and privacy/path guardrails.
- Documentation updates that connect the goal-intake loop to the standard
  MemoryOS/CapabilityOS/Hive operating sequence.
- Dispatch packets to hivemind, memoryOS, and CapabilityOS for repo-local
  instruction updates.

### Hive Mind

must_produce:

- Update `hivemind/AGENTS.md` and `.ai-runs/shared/comms_log.md` so Hive agents
  submit execution friction or new goals through the repo-goal protocol.
- Preserve Hive authority: Hive executes routed work after contract/dispatch,
  but does not accept memory or capability bindings.

### MemoryOS

must_produce:

- Update `memoryOS/AGENTS.md` and `memoryOS/docs/AGENT_WORKLOG.md` so MemoryOS
  agents submit memory-loop friction, context gaps, and review blockers through
  the repo-goal protocol.
- Preserve MemoryOS authority: submitted goals do not auto-accept memories.

### CapabilityOS

must_produce:

- Update `CapabilityOS/AGENTS.md` so CapabilityOS agents submit routing,
  capability, tool, MCP, API, or fallback gaps through the repo-goal protocol.
- Preserve CapabilityOS authority: submitted goals are route requests or
  observations, not execution.

## Route Packet Contract

`scripts/aios_repo_goal.py route` must emit JSON with:

- `schema_version: aios.repo_goal_route.v1`
- `route_id`
- `goal_id`
- `source_repo`
- `goal`
- `recommended_contract_slug`
- `memoryos`
  - `task`
  - `required_context`
  - `trace_required`
- `capabilityos`
  - `task`
  - `recommended_routes`
  - `risk_notes`
- `hivemind`
  - `task`
  - `execution_owner`
  - `verification_hint`
- `stop_conditions`
- `next_action`

The route packet is a recommendation. It does not directly edit child repos,
accept memory, bind tools, or execute a provider.

## Verification Gate

```bash
python -m py_compile scripts/aios_repo_goal.py
python -m unittest tests/test_aios_repo_goal.py
python scripts/aios_repo_goal.py submit --repo hivemind --goal "dogfood repo goal loop" --kind friction --summary "child repo should be able to ask myworld for a routed packet" --dry-run --json
python scripts/aios_repo_goal.py route --repo hivemind --goal "dogfood repo goal loop" --kind friction --dry-run --json
python scripts/aios_semantic_handshake.py --json
python -m unittest tests/test_aios_instruction_index.py tests/test_aios_loop_policy.py tests/test_aios_doc_scout.py tests/test_aios_readiness.py tests/test_aios_dispatch.py tests/test_aios_loop.py tests/test_aios_monitor.py tests/test_aios_goal_evolution.py tests/test_aios_child_watcher.py tests/test_aios_round_controller.py tests/test_aios_web_research_receipt.py tests/test_aios_institution_readiness.py tests/test_aios_action_policy.py tests/test_aios_semantic_handshake.py tests/test_aios_repo_goal.py
python scripts/aios_monitor.py assess --json
```

Pass criteria:

- A repo goal packet can be created without chat context.
- A route packet can be generated deterministically from that goal.
- Route packet names MemoryOS, CapabilityOS, and Hive responsibilities without
  executing any lower-repo work.
- Lower-repo AGENTS files know when and how to submit AIOS goal/friction
  packets.
- Full tests pass and monitor remains clear.

## Stop Conditions

- `direct_child_repo_edit`: myworld patches child implementation files instead
  of issuing a packet.
- `route_executes_work`: route packet triggers provider, tool, or repo
  execution directly.
- `memory_auto_accept`: submitted goal or route creates accepted memory without
  MemoryOS review.
- `capability_binding_without_review`: route binds or installs tools instead of
  recommending.
- `sensitive_source_content_in_goal`: submission includes unreviewed source
  dump content or key-like values.
- `unbounded_repo_source`: submit accepts an unknown source repo without
  explicit operator allow-list.
- `verification_gate_failed`

## Receipts

- implementation:
  - `docs/AIOS_REPO_GOAL_LOOP.md` defines the repo-goal intake and route
    protocol.
  - `scripts/aios_repo_goal.py` implements `submit`, `route`, and `status`.
  - `tests/test_aios_repo_goal.py` covers submit, route, dry-run route, status,
    unknown repo rejection, and sensitive/private-path guardrails.
  - `docs/AIOS_OPERATING_LOOP.md` and `docs/AIOS_WORK_DISPATCH.md` document
    where repo-goal intake fits in the AIOS loop.
- result packets:
  - myworld: `.aios/outbox/myworld/asc-0038.myworld.result.json`
  - hivemind: `.aios/outbox/hivemind/asc-0038.hivemind.result.json`
  - memoryOS: `.aios/outbox/memoryOS/asc-0038.memoryOS.result.json`
  - CapabilityOS: `.aios/outbox/CapabilityOS/asc-0038.CapabilityOS.result.json`
- lower repo commits:
  - hivemind `33fdc56` (`Add repo-goal submission rule`)
  - memoryOS `457bbf2` (`Add repo-goal submission rule to MemoryOS AGENTS.md
    (ASC-0038 WP-0038-C)`)
  - memoryOS `9f8b8bb` (`Fix repo-goal command path`)
  - CapabilityOS `ff25f5c` (`Add repo-goal submission rule for ASC-0038`)
- dispatch evidence:
  - `asc-0038` was sent to `myworld`, `hivemind`, `memoryOS`, and
    `CapabilityOS`.
  - all four result packets passed; child repos used claude fallback after
    codex provider access denial.
  - dispatch released with reason `asc_0038_self_resonant_repo_loop_verified`.
- verification:
  - `python -m py_compile scripts/aios_repo_goal.py` passed.
  - `python -m unittest tests/test_aios_repo_goal.py` passed 6/6.
  - dry-run `submit` and `route` commands emitted `aios.repo_goal.v1` and
    `aios.repo_goal_route.v1` JSON.
  - `python scripts/aios_semantic_handshake.py --json` passed.
  - full myworld suite passed 69/69.
  - `python scripts/aios_monitor.py assess --json` returned `health=clear`.
- learned:
  - CapabilityOS needed an `observation` repo-goal kind. The myworld CLI schema
    now accepts it.

## Work Packets

### WP-0038-A — Codex@myworld builds repo-goal intake and route surface

- target_agent: codex
- target_repo: myworld
- status: done
- issued: 2026-05-12
- accepted: 2026-05-12
- closed: 2026-05-12
- depends_on: ASC-0036, ASC-0037
- brief: |
    Build the first executable repo-goal loop in myworld. Add
    `docs/AIOS_REPO_GOAL_LOOP.md`, `scripts/aios_repo_goal.py`, and
    `tests/test_aios_repo_goal.py`. Keep the route recommendation-only and do
    not edit child repo implementation code.
- result: `.aios/outbox/myworld/asc-0038.myworld.result.json`;
  `scripts/aios_repo_goal.py`; `tests/test_aios_repo_goal.py`; full suite
  passed 69/69.

### WP-0038-B — Codex@hivemind adds repo-goal submission rule

- target_agent: codex
- target_repo: hivemind
- status: done
- issued: 2026-05-12
- accepted: 2026-05-12
- closed: 2026-05-12
- depends_on: WP-0038-A
- brief: |
    Update only `hivemind/AGENTS.md` and `.ai-runs/shared/comms_log.md`.
    Add the ASC-0038 rule: Hive agents submit execution friction or new AIOS
    goals through myworld's repo-goal protocol before expecting cross-repo
    coordination.
- result: `.aios/outbox/hivemind/asc-0038.hivemind.result.json`; hivemind
  commit `33fdc56`; claude fallback used after codex
  `provider_access_denied`.

### WP-0038-C — Codex@memoryOS adds repo-goal submission rule

- target_agent: codex
- target_repo: memoryOS
- status: done
- issued: 2026-05-12
- accepted: 2026-05-12
- closed: 2026-05-12
- depends_on: WP-0038-A
- brief: |
    Update only `memoryOS/AGENTS.md` and `memoryOS/docs/AGENT_WORKLOG.md`.
    Add the ASC-0038 rule: MemoryOS agents submit context, provenance, review,
    and memory-loop friction through myworld's repo-goal protocol.
- result: `.aios/outbox/memoryOS/asc-0038.memoryOS.result.json`; memoryOS
  commits `457bbf2` and `9f8b8bb`; claude fallback used after codex
  `provider_access_denied`.

### WP-0038-D — Codex@CapabilityOS adds repo-goal submission rule

- target_agent: codex
- target_repo: CapabilityOS
- status: done
- issued: 2026-05-12
- accepted: 2026-05-12
- closed: 2026-05-12
- depends_on: WP-0038-A
- brief: |
    Update only `CapabilityOS/AGENTS.md`. Add the ASC-0038 rule: CapabilityOS
    agents submit routing, capability, MCP/API/tool, and fallback gaps through
    myworld's repo-goal protocol.
- result: `.aios/outbox/CapabilityOS/asc-0038.CapabilityOS.result.json`;
  CapabilityOS commit `ff25f5c`; claude fallback used after codex
  `provider_access_denied`.
