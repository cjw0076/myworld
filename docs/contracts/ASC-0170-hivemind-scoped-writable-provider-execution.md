---
contract_id: ASC-0170
slug: hivemind-scoped-writable-provider-execution
status: closed
goal: Open Hive Mind writable provider execution only behind AIOS packet scope, explicit execution request, and operator grant.
created: 2026-05-14 13:32 KST
accepted: 2026-05-14 13:32 KST
closed: 2026-05-14 13:36 KST
acceptance_authority: founder delegated continuation under active AIOS evolution goal.
origin: Founder asked to open the read-only Hive provider-loop restriction.
---

# ASC-0170 Hive Mind Scoped Writable Provider Execution

## Why Hive Was Read-Only

Hive provider-loop used Codex `exec --sandbox read-only` by default because the
first provider-loop surface was a durable receipt and fallback wrapper, not an
unbounded repo worker. Provider CLIs can modify broad repo state and follow
their own provider instructions once started, so writable execution needed an
AIOS authority boundary.

## Scope

repos:

- `hivemind`
- `myworld`

allowed_files:

- `hivemind/hivemind/provider_passthrough.py`
- `hivemind/hivemind/provider_loop.py`
- `hivemind/hivemind/aios_packet_runner.py`
- `hivemind/hivemind/harness.py`
- `hivemind/hivemind/hive.py`
- `hivemind/tests/test_aios_packet_runner.py`
- `hivemind/tests/test_provider_passthrough.py`
- `hivemind/docs/AGENT_WORKLOG.md`
- `docs/contracts/ASC-0170-hivemind-scoped-writable-provider-execution.md`
- `docs/contracts/README.md`
- `docs/AIOS_AGENT_LEDGER.md`

forbidden_files:

- `memoryOS/**`
- `CapabilityOS/**`
- `GenesisOS/**`
- `.env`
- `.env.*`
- provider credentials
- raw private exports
- private chat transcripts

## Requirements

- Preserve read-only provider execution as the default.
- Allow Codex workspace-write only through Hive packet execution with all of:
  - `--execute`
  - `--writable-provider-execution`
  - `--operator-grant <reason>`
- Keep dangerous/full-access/approval-never combinations blocked.
- Record verifier/user approval votes through the existing Hive execution
  protocol before workspace-write execution.
- Expose CLI flags for provider-loop tick and AIOS packet execution.

## Result

Implemented scoped writable execution:

```bash
python -m hivemind.hive aios-packet \
  --packet <packet.json> \
  --provider codex \
  --execute \
  --writable-provider-execution \
  --operator-grant "<operator scoped grant>" \
  --json
```

Provider-loop also exposes:

```bash
python -m hivemind.hive provider-loop tick \
  --execute \
  --allow-workspace-write \
  --workspace-write-grant "<operator scoped grant>" \
  --json
```

Verification:

```bash
cd hivemind
python -m unittest tests/test_aios_packet_runner.py tests/test_provider_passthrough.py tests/test_provider_loop.py
python -m hivemind.hive aios-packet --packet ../.aios/inbox/hivemind/asc-0168.hivemind.json --myworld-root .. --provider codex --execute --writable-provider-execution --json
python -m hivemind.hive aios-packet --help
python -m hivemind.hive provider-loop tick --help
```

Observed result:

- unittest passed 26/26.
- no-grant writable smoke held with `operator_grant_missing`.
- CLI help exposes `--writable-provider-execution`, `--operator-grant`,
  `--allow-workspace-write`, and `--workspace-write-grant`.
- Hive repo commit: `716abbf Gate writable provider execution by operator
  grant`.

## Stop Conditions

- `operator_grant_missing`
- `writable_requires_execute`
- `writable_provider_only_codex_supported`
- `provider_tick_failed`
- `provider_secret_leak`
- `scope_violation`
- `verification_gate_failed`

## Follow-Up

MyWorld should route Hive-targeted dispatch packets to `hive aios-packet`.
Writable grants should be passed only after CapabilityOS route, Hive permission
preflight, and operator decision.
