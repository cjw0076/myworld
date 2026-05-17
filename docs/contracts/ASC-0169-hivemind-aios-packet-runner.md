---
contract_id: ASC-0169
slug: hivemind-aios-packet-runner
status: closed
goal: Let Hive Mind consume AIOS hivemind inbox packets through its own provider-loop runner instead of relying only on the MyWorld shell child watcher.
created: 2026-05-14 13:24 KST
accepted: 2026-05-14 13:24 KST
closed: 2026-05-14 13:27 KST
acceptance_authority: founder delegated continuation under active AIOS evolution goal.
origin: Founder asked why Hive Mind cannot wake provider CLIs and directly work.
---

# ASC-0169 Hive Mind AIOS Packet Runner

## Scope

repos:

- `hivemind`
- `myworld`

allowed_files:

- `hivemind/hivemind/aios_packet_runner.py`
- `hivemind/hivemind/hive.py`
- `hivemind/tests/test_aios_packet_runner.py`
- `hivemind/docs/AGENT_WORKLOG.md`
- `docs/contracts/ASC-0169-hivemind-aios-packet-runner.md`
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

- Add a Hive-owned CLI entry point that reads an AIOS dispatch packet targeting
  `hivemind`.
- Build a bounded provider-loop prompt from packet goal, reading, allowed
  files, forbidden files, and stop rules.
- Prepare and tick a Hive provider-loop worker.
- Optionally write a result packet to the packet's `return_to` path.
- Do not grant broad writable provider execution by default.

## Result

Implemented `hive aios-packet --packet ... --myworld-root ...` with
`hive.aios_packet_runner.v1` receipts.

Verification:

```bash
cd hivemind
python -m unittest tests/test_aios_packet_runner.py tests/test_permission_preflight.py tests/test_provider_loop.py
python -m hivemind.hive aios-packet --packet ../.aios/inbox/hivemind/asc-0168.hivemind.json --myworld-root .. --provider local --json
```

Observed result:

- unittest passed 19/19.
- CLI smoke returned `status=prepared`, `authority.executor=hivemind`,
  `uses_provider_loop=true`, and a local provider-loop tick receipt.
- Hive repo commit: `ba057f7 Add AIOS packet provider-loop runner`.

## Stop Conditions

- `target_repo_not_hivemind`
- `return_path_missing`
- `provider_tick_failed`
- `provider_secret_leak`
- `scope_violation`
- `verification_gate_failed`

## Follow-Up

The next step is to route Hive-targeted packets through this command from
MyWorld instead of the shell child watcher path. Writable provider execution
should be a separate policy-bound contract, because the current provider-loop
uses safe prepare/tick behavior by default.
