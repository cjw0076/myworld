---
contract_id: ASC-0103
slug: aios-ask-interface
status: closed
goal: Add a first-class AIOS ask interface so the founder can issue one natural-language work instruction and receive AIOS role artifacts, a validated praxis envelope, and a dispatch-ready instruction surface.
created: 2026-05-13 KST
accepted: 2026-05-13 KST by Codex under founder instruction
closed: 2026-05-13 KST
praxis_required: true
praxis_ref: docs/praxis/ASC-0103-aios-ask-interface.json
origin: founder request 2026-05-13 KST - "AIOS에서 직접 작업 지시할게 인터페이스 있나?"
---

# ASC-0103 AIOS Ask Interface

## Why

AIOS currently has the pieces of a work interface, but they are scattered:

- `aios_invoke.py` builds role artifacts.
- `aios_work_praxis.py` drafts and validates praxis envelopes.
- `aios_dispatch.py` creates and sends packets.
- `aios_runtime.py submit-goal` submits repo-originated goals.
- the control app visualizes state.

The founder should not need to manually chain these commands to direct AIOS.
`ask` becomes the first intent intake interface.

## Scope

repos:

- `myworld`

allowed_files:

- `docs/contracts/ASC-0103-aios-ask-interface.md`
- `docs/praxis/ASC-0103-aios-ask-interface.json`
- `docs/AIOS_WORK_DISPATCH.md`
- `scripts/aios_ask.py`
- `scripts/aios_launcher.py`
- `tests/test_aios_ask.py`
- `tests/test_aios_launcher.py`
- `docs/AGENT_WORKLOG.md`

forbidden_files:

- `.env`
- raw exports
- private provider auth files
- child repo implementation files
- UI application files

## Responsibilities

### myworld

must_produce:

- `python scripts/aios_ask.py "goal" --json`
- `bin/aios ask "goal" --json`
- ask receipt under `.aios/asks/<ask_id>/receipt.json`
- ask instruction under `.aios/asks/<ask_id>/instruction.md`
- praxis envelope under `.aios/asks/<ask_id>/praxis.json`
- invocation artifact link to `.aios/invocations/<ask_id>/`

## Non-Goals

- `ask` does not execute child repo work.
- `ask` does not accept contracts.
- `ask` does not bypass `praxis_required`, action policy, or repo ownership.
- `ask` does not write child repo implementation files.

## Verification Gate

```bash
cd .
python -m unittest tests/test_aios_ask.py tests/test_aios_launcher.py tests/test_aios_invoke.py
python scripts/aios_work_praxis.py validate docs/praxis/ASC-0103-aios-ask-interface.json --json
python scripts/aios_ask.py "AIOS ask smoke" --write .aios/asks/asc-0103-smoke --json
bash bin/aios --root . ask "AIOS launcher ask smoke" --write .aios/asks/asc-0103-bin-smoke --json
python scripts/aios_monitor.py assess --json
```

## Stop Conditions

- `ask_executes_without_contract`
- `ask_missing_memory_context`
- `ask_missing_capability_route`
- `ask_missing_genesis_reframe`
- `ask_missing_hive_plan`
- `ask_bypasses_praxis`
- `ask_writes_child_repo_source`

## Receipts

- Implemented `scripts/aios_ask.py`.
- Wired `bin/aios ask ...` through `scripts/aios_launcher.py`.
- Ask artifacts:
  - `.aios/asks/<ask_id>/goal.json`
  - `.aios/asks/<ask_id>/instruction.md`
  - `.aios/asks/<ask_id>/praxis.json`
  - `.aios/asks/<ask_id>/receipt.json`
  - `.aios/invocations/<ask_id>/receipt.json`
- `ask` composes existing GenesisOS, MemoryOS, CapabilityOS, and Hive planning
  through `aios_invoke.py`, then emits a validated praxis envelope for the
  operator's next dispatch.
- `ask` remains plan-only and does not execute child repo implementation work.
- Verification passed:
  - `python -m unittest tests/test_aios_ask.py tests/test_aios_launcher.py tests/test_aios_invoke.py`
  - `python scripts/aios_work_praxis.py validate docs/praxis/ASC-0103-aios-ask-interface.json --json`
  - `python scripts/aios_ask.py "AIOS ask smoke" --write .aios/asks/asc-0103-smoke --json`
  - `bash bin/aios --root . ask "AIOS launcher ask smoke" --write .aios/asks/asc-0103-bin-smoke --json`
- Dispatch result:
  - `.aios/outbox/myworld/asc-0103.myworld.result.json` passed and collected.
