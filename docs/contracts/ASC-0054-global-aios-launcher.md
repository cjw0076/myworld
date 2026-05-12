---
contract_id: ASC-0054
slug: global-aios-launcher
status: closed
goal: Add a thin global `aios` launcher candidate that resolves the active MyWorld control plane while keeping AIOS state workspace-local.
created: 2026-05-13 00:09 KST
accepted: 2026-05-13 00:09 KST by codex acting operator (founder directive)
closed: 2026-05-13 00:14 KST
acceptance_authority: codex@myworld acting operator per founder directive that AIOS should become the final provider-independent interface.
---

# ASC-0054 Global AIOS Launcher

## Why Now

ASC-0052 made `scripts/aios_runtime.py` the AIOS-native runtime entrypoint.
ASC-0053 put Claude, Codex, and local LLM workers behind Hive provider-loop
artifacts. The remaining operator friction is that the user still has to know
where `myworld` lives and which script to call.

AIOS should be reachable as `aios`, but its state must not become global. The
global command is a thin locator and dispatcher. The control plane, contracts,
dispatch state, primitive events, and repo-local artifacts remain inside the
workspace root.

## Scope

repos:

- `myworld`

allowed_files:

- `bin/aios`
- `scripts/aios_launcher.py`
- `tests/test_aios_launcher.py`
- `docs/AIOS_RUNTIME.md`
- `docs/AIOS_WORK_DISPATCH.md`
- `docs/contracts/ASC-0054-global-aios-launcher.md`
- `docs/contracts/README.md`
- `docs/AIOS_AGENT_LEDGER.md`

forbidden_files:

- `hivemind/**` source edits
- `memoryOS/**`
- `CapabilityOS/**`
- `uri/**`
- `.aios/state/**`
- `.aios/logs/**`
- `.env`
- raw export paths

## Responsibilities

- **myworld.must_produce**:
  - `bin/aios`: executable launcher candidate suitable for PATH or symlink use.
  - `scripts/aios_launcher.py`: root resolution and dispatch logic.
  - root resolution order: explicit `--root`, nearest ancestor containing
    `scripts/aios_runtime.py`, `AIOS_HOME`, then launcher-relative myworld root.
  - default command delegation to `scripts/aios_runtime.py`.
  - `aios provider-loop ...` delegation to Hive's provider-loop CLI without
    making Hive source changes.
  - tests for root resolution, runtime command construction, and provider-loop
    command construction.
- **hivemind.must_produce**: no source role; existing ASC-0053 provider-loop
  surface is consumed.
- **memoryos.must_produce**: no source role.
- **capabilityos.must_produce**: no source role.

## Verification Gate

```bash
python -m py_compile scripts/aios_launcher.py
python -m unittest tests/test_aios_launcher.py
python scripts/aios_launcher.py --root . status --json
python scripts/aios_launcher.py --root . provider-loop status --json
python -m unittest discover -s tests -p 'test_aios_*.py'
python scripts/aios_monitor.py assess --json
```

Pass criteria:

- `bin/aios` can be called from the workspace without direct script knowledge.
- Runtime commands still report `aios.runtime.status.v1`.
- Provider-loop commands route through Hive and report `hive.provider_loop.v1`.
- No AIOS state is moved out of `.aios/` or lower-repo run artifacts.
- Monitor remains clear.

## Stop Conditions

- `global_state_leak`: launcher writes AIOS state outside the selected root.
- `root_resolution_ambiguous`: launcher cannot explain which root it selected.
- `provider_cli_bypass`: launcher calls Claude/Codex directly instead of AIOS
  runtime or Hive provider-loop surfaces.
- `child_repo_source_edit`: contract touches child repo source.
- `verification_gate_failed`

## Work Packets

### WP-0054-A — Codex@myworld builds global launcher

- target_agent: codex
- target_repo: myworld
- status: done
- issued: 2026-05-13 00:09 KST
- accepted: 2026-05-13 00:09 KST
- closed: 2026-05-13 00:14 KST
- brief: |
    Implement a thin `aios` launcher candidate. Keep the launcher stateless:
    it only resolves the control-plane root and delegates to
    `scripts/aios_runtime.py` or Hive `provider-loop`. Do not install it into
    system PATH from the contract; document the command shape and leave
    operator installation as a later packaging decision.
- result: `.aios/outbox/myworld/asc-0054.myworld.result.json`

## Receipts

- Launcher: `bin/aios`
- Root/delegation logic: `scripts/aios_launcher.py`
- Tests: `tests/test_aios_launcher.py`
- `python -m py_compile scripts/aios_launcher.py` passed.
- `python -m unittest tests/test_aios_launcher.py` passed 6/6.
- `bin/aios --root . root --json` returned `aios.launcher.v1`.
- `bin/aios --root . status --json` returned `aios.runtime.status.v1`.
- `bin/aios --root . provider-loop status --json` returned
  `hive.provider_loop.v1`.
- `python -m unittest discover -s tests -p 'test_aios_*.py'` passed 131/131.
- `python scripts/aios_monitor.py assess --json` returned `health=clear`.

## Closeout Decision

ASC-0054 answers the global setup question: AIOS should be globally reachable
through a thin command, but not globally stateful. The launcher resolves the
selected control-plane root and delegates to AIOS runtime or Hive provider-loop
surfaces. This keeps contracts, dispatches, primitive events, and run artifacts
inside the workspace that owns the goal.

The next layer should make `aios` a richer chair command: natural-language goal
intake, MemoryOS context request, CapabilityOS route request, Hive provider-loop
execution plan, verification, and learning receipt in one operator-facing flow.
