---
contract_id: ASC-0143
slug: aios-session-envelope-runtime-binding
status: closed
goal: Bind the existing AIOS invocation/interface pieces into a mandatory session envelope that sits in front of Codex/Hive execution packets.
created: 2026-05-14 KST
accepted: 2026-05-14 KST by founder GO "진행해"
acceptance_authority: founder
origin: ASC-0124 verdict recommended AIOS session envelope / protocol core as the first downstream contract. Founder clarified that Codex CLI can remain executor, but AIOS must force MemoryOS, CapabilityOS, GenesisOS, and Hive routing before execution.
---

# ASC-0143 AIOS Session Envelope Runtime Binding

DNA references: Invariant 1 (decide before acting), Invariant 4 (named exit),
Invariant 5 (provenance chain), Invariant 8 (classify before committing).

## Why Now

AIOS already has pieces: chat wrapper, Goal Bar, `aios_invoke.py`, repo-goal
packets, dispatch, watcher, and result packets. The missing interface is the
runtime envelope that turns those pieces into one mandatory pre-execution
object.

Codex CLI should remain a real executor. The defect is not that Codex writes
code. The defect is that Codex can receive a direct user prompt without a
single artifact proving:

- MemoryOS context was requested or degraded.
- CapabilityOS route was requested or degraded.
- GenesisOS challenge/divergence was requested or failed.
- Hive wrote an execution plan.
- The dispatch packet carries the same evidence chain.
- The watcher/result cites the envelope.

ASC-0143 creates the first binding layer.

## Scope

repos:

- `myworld`

allowed_files:

- `scripts/aios_invoke.py`
- `scripts/aios_dispatch.py`
- `tests/test_aios_invoke.py`
- `tests/test_aios_dispatch.py`
- `docs/AIOS_INVOCATION_PIPELINE.md`
- `docs/contracts/ASC-0143-aios-session-envelope-runtime-binding.md`
- `docs/contracts/README.md`
- `docs/AGENT_WORKLOG.md`
- `docs/AIOS_AGENT_LEDGER.md`

forbidden_files:

- `hivemind/**`
- `memoryOS/**`
- `CapabilityOS/**`
- `GenesisOS/**`
- `uri/**`
- `.env`
- raw export paths

## myworld.must_produce

- `aios_invoke.py` always writes `.aios/invocations/<id>/session_envelope.json`.
- `session_envelope.json` uses `aios.session_envelope.v1`.
- The envelope contains:
  - `goal`
  - `goal_hash`
  - `role_statuses`
  - `role_artifacts`
  - `degraded_roles`
  - `failed_roles`
  - `executor_assignment`
  - `degraded_receipt`
  - `required_before_execution: true`
- Missing MemoryOS/CapabilityOS/GenesisOS/Hive surfaces become degraded or
  failed role status, not silent absence.
- `aios_dispatch.py send --session-envelope <path>` attaches a projected
  envelope summary to dispatch packets.
- `aios_dispatch.py watch` copies that envelope projection into the result
  packet so execution evidence can be traced back to the AIOS interface.

## Capability Boundary

This contract does not grant autonomous provider execution. It binds evidence
and routing context in front of execution. Codex remains executor only after a
dispatch packet exists.

## Verification Gate

```bash
cd /home/user/workspaces/jaewon/myworld
python -m py_compile scripts/aios_invoke.py scripts/aios_dispatch.py
python -m unittest tests/test_aios_invoke.py tests/test_aios_dispatch.py
python scripts/aios_invoke.py --goal "ASC-0143 session envelope smoke" --write .aios/invocations/asc-0143-smoke --contract-id ASC-0143 --plan-only --json
python -c "exit(0 if __import__('pathlib').Path('.aios/invocations/asc-0143-smoke/session_envelope.json').is_file() else 1)"
python -c "exec('import json\\nfrom pathlib import Path\\np=json.loads(Path(\".aios/invocations/asc-0143-smoke/session_envelope.json\").read_text(encoding=\"utf-8\"))\\nassert p[\"schema_version\"] == \"aios.session_envelope.v1\"\\nassert p[\"required_before_execution\"] is True\\nassert p[\"executor_assignment\"][\"default_executor\"] == \"codex\"\\nassert \"hive_execution_plan\" in p[\"role_artifacts\"]')"
python -m unittest discover -s tests -p 'test_aios_*.py'
```

Pass criteria:

- `session_envelope.json` exists for invocation smoke.
- Unit tests prove dispatch packet carries `session_envelope.ref`.
- Unit tests prove watcher result echoes `session_envelope.ref`.
- Full MyWorld AIOS tests pass.

## Stop Conditions

- `session_envelope_missing`
- `session_envelope_schema_invalid`
- `dispatch_packet_missing_envelope_ref`
- `watcher_result_missing_envelope_ref`
- `executor_runs_without_dispatch_packet`
- `verification_gate_failed`

## Receipts

- 2026-05-14 KST: `scripts/aios_invoke.py` now writes
  `.aios/invocations/<id>/session_envelope.json` with
  `schema_version=aios.session_envelope.v1`.
- The envelope includes `role_statuses`, `role_artifacts`,
  `degraded_roles`, `failed_roles`, `executor_assignment`,
  `degraded_receipt`, and `required_before_execution: true`.
- `scripts/aios_dispatch.py send --session-envelope <path>` validates the
  envelope is under `.aios/invocations/`, projects it into the dispatch packet,
  and adds envelope-specific stop conditions.
- `scripts/aios_dispatch.py watch` echoes the projected session envelope in the
  result packet.
- Smoke invocation:
  `.aios/invocations/asc-0143-smoke/session_envelope.json`.
- Dispatch packet:
  `.aios/inbox/myworld/asc-0143.myworld.json` includes
  `session_envelope.ref`.
- Watcher result:
  `.aios/outbox/myworld/asc-0143.myworld.result.json` passed and echoes the
  same `session_envelope.ref`.
- Focused tests passed 29/29.
- Full MyWorld AIOS test suite passed 309/309.
