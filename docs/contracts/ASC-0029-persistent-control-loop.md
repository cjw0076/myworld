---
contract_id: ASC-0029
slug: persistent-control-loop
status: closed
goal: Add a persistent control-plane round controller so AIOS continuation does not depend on a chat turn staying open.
created: 2026-05-12 03:08 KST
accepted: 2026-05-12 03:08 KST
closed: 2026-05-12 03:13 KST
---

# ASC-0029 Persistent Control Loop

## Why Now

ASC-0028 closed with the loop healthy, but the next selected goal was
`goal:persistent_control_loop`. The failure mode is concrete: after an agent
sends a final chat response, the API turn ends. Existing watchers may consume
packets, and `aios_pingpong.sh` can run provider agents, but there is no
small, provider-independent control-plane round controller that keeps sensing
monitor state, refreshing the goal plan, applying dispatch state, and recording
the next action.

This contract fixes that stop mode. It does not make `myworld` a broad worker
and does not directly edit child repos.

## Scope

repos:

- `myworld`

allowed_files:

- `scripts/aios_round_controller.py`
- `tests/test_aios_round_controller.py`
- `docs/AIOS_BUILD_METHOD.md`
- `docs/AIOS_WORK_DISPATCH.md`
- `docs/contracts/ASC-0029-persistent-control-loop.md`
- `docs/contracts/README.md`
- `docs/goals/AIOS-GOAL-0001-make-something-great.md`
- `docs/goals/AIOS-GOAL-0001-evolution.md`
- `docs/AIOS_AGENT_LEDGER.md`

forbidden_files:

- `hivemind/**`
- `memoryOS/**`
- `CapabilityOS/**`
- `.aios/logs/**`
- `.aios/outbox/**`
- `.aios/inbox/**`
- `.aios/state/**`
- `.env`
- raw export paths

## Responsibilities

### myworld.must_produce

- A provider-independent controller command that can run one bounded
  control-plane round.
- Optional background `start`, `stop`, and `status` commands with PID/stop
  files under `.aios/run/`.
- JSON round receipts written to `.aios/state/round_controller.jsonl`.
- A latest state file at `.aios/state/round_controller.latest.json`.
- Documentation explaining when to use the controller instead of relying on a
  chat turn.

### hive_mind.must_produce

- No source change in this contract. Future accepted contracts may dispatch
  Hive packets through the existing dispatch/child watcher surfaces.

### memoryos.must_produce

- No source change in this contract. Future accepted contracts may ask
  MemoryOS to import controller receipts as durable memory candidates.

### capabilityos.must_produce

- No source change in this contract. Existing CapabilityOS route selection is
  used indirectly by child watcher fallback when child execution runs.

### operator.must_produce

- Acting-operator closeout by Codex after verification passes.
- Stop or hold if the controller mutates child repo source, bypasses contract
  status, or runs unbounded child agents by default.

## Design Answers

Q1. Is the loop autonomous completion or persistent sensing?

Pick persistent sensing plus bounded control-plane application. The controller
should keep the loop awake by running monitor assessment, goal evolution, and
dispatch apply rounds. It should not auto-author new contracts or auto-close
contracts without evidence. That keeps the loop controllable while removing
the dependency on a live chat response.

Q2. Should child execution run by default?

No. The default controller round is provider-independent and does not run
Codex/Claude child agents. Child execution can be enabled explicitly with an
execution flag so a background controller does not accidentally spend provider
time or mutate child repos.

Q3. Where does the verification gate live?

In myworld tests. This is a control-plane behavior, so the gate belongs beside
`tests/test_aios_loop.py`, `tests/test_aios_monitor.py`, and
`tests/test_aios_goal_evolution.py`.

## Verification Gate

Run:

```bash
python -m unittest tests/test_aios_round_controller.py
python -m unittest tests/test_aios_instruction_index.py tests/test_aios_loop_policy.py tests/test_aios_doc_scout.py tests/test_aios_readiness.py tests/test_aios_dispatch.py tests/test_aios_loop.py tests/test_aios_monitor.py tests/test_aios_goal_evolution.py tests/test_aios_child_watcher.py tests/test_aios_round_controller.py
python scripts/aios_round_controller.py once --json
python scripts/aios_round_controller.py status
python scripts/aios_monitor.py assess --json
```

Pass criteria:

- Unit tests pass.
- `once --json` returns `schema_version=aios.round_controller.v1`.
- A round receipt includes monitor, goal evolution, dispatch loop, child
  watcher status, and a recommended next action.
- `status` reports the latest round without requiring a chat turn.
- Monitor remains `health=clear`.

## Stop Conditions

- `privacy_violation`: controller writes raw logs, private exports, or secrets
  into committed docs.
- `scope_violation`: controller edits child repo source or bypasses child repo
  ownership.
- `unbounded_execution`: controller runs child agents forever or runs provider
  agents by default.
- `missing_stop_file`: background mode cannot be stopped through
  `.aios/run/aios_round_controller.stop`.
- `missing_round_receipt`: a round runs without appending a durable receipt.
- `contract_status_bypass`: controller accepts, closes, or releases contracts
  without explicit evidence and operator semantics.

## Receipts

- Implementation: `scripts/aios_round_controller.py` and
  `tests/test_aios_round_controller.py`.
- Dispatch: `.aios/inbox/myworld/asc-0029.myworld.json`.
- Result packet: `.aios/outbox/myworld/asc-0029.myworld.result.json`.
- Release: `python scripts/aios_dispatch.py release --dispatch-id asc-0029
  --reason asc_0029_persistent_control_loop_verified`.
- Verification:
  - `python -m unittest tests/test_aios_round_controller.py` passed 5/5.
  - Full myworld suite with `tests/test_aios_round_controller.py` included
    passed 42/42.
  - `python scripts/aios_round_controller.py once --json` returned
    `schema_version=aios.round_controller.v1` and wrote a durable latest
    receipt.
  - `python scripts/aios_round_controller.py status` reported
    `latest_status=passed`.
  - Final `python scripts/aios_monitor.py assess --json` returned
    `health=clear`.

## Work Packets

### WP-0029-A — Codex@myworld implements persistent control round controller

- target_agent: codex
- target_repo: myworld
- status: accepted
- issued: 2026-05-12
- accepted: 2026-05-12
- closed: 2026-05-12
- depends_on: none
- brief: |
    Implement `scripts/aios_round_controller.py` as a provider-independent
    control-plane round runner. It should run monitor assessment, goal
    evolution planning for the active goal, `aios_loop.py once --apply --json`,
    child watcher status, and optionally one explicit child watcher pass when
    requested. It must write durable round receipts under `.aios/state/` and
    support `once`, `run`, `start`, `stop`, and `status`.
- result: `.aios/outbox/myworld/asc-0029.myworld.result.json`
