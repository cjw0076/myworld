---
contract_id: ASC-0080
slug: aios-native-installation
status: closed
goal: Make AIOS feel built-in on the local machine through a reversible user-space installation: global `aios` command, user-systemd runtime service, optional desktop entry, and explicit uninstall/health checks.
created: 2026-05-13 KST
accepted: 2026-05-14 11:11 KST
closed: 2026-05-14 11:13 KST
acceptance_authority: operator must accept before writing outside the repository.
origin: Operator asked whether AIOS can be built in at the same level as existing program-file/launcher installations after inspecting local program entrypoints.
---

# ASC-0080 AIOS Native Installation

## Why Now

The current AIOS control plane already has the core pieces:

- `bin/aios` delegates to `scripts/aios_launcher.py`.
- `scripts/aios_launcher.py` resolves an AIOS root from explicit `--root`,
  nearest ancestor, `AIOS_HOME`, or launcher-relative root.
- `scripts/aios_runtime.py` provides `status`, `step`, `run`,
  `submit-goal`, and `sprint-loop`.
- `scripts/aios_round_controller.py` can run persistently.
- `scripts/aios_desktop_app.py` provides a native Tk desktop surface when a
  GUI session exists.

Local inspection also shows the normal user-space installation pattern:

- `~/.local/bin/hive` and `~/.local/bin/hivemind` are Python console scripts.
- `~/.local/bin/claude` is a symlink into a versioned local install.
- `systemd --user` is running and can host per-user services.

Therefore AIOS can be made "built-in" as a reversible user-space application.
It should not require root, system package installation, kernel integration,
or global mutable state.

## Scope

repos:

- `myworld`

allowed_files:

- `scripts/aios_launcher.py`
- `scripts/aios_install.py`
- `tests/test_aios_install.py`
- `tests/test_aios_launcher.py`
- `docs/AIOS_NATIVE_INSTALL.md`
- `docs/contracts/ASC-0080-aios-native-installation.md`
- `docs/contracts/README.md`
- `docs/AIOS_AGENT_LEDGER.md`

external_write_targets_after_acceptance:

- `~/.local/bin/aios`
- `~/.config/systemd/user/aios.service`
- `~/.config/autostart/aios-control.desktop`

forbidden_files:

- `hivemind/**`
- `memoryOS/**`
- `CapabilityOS/**`
- `GenesisOS/**`
- `uri/**`
- `/usr/**`
- `/etc/**`
- `/bin/**`
- `/opt/**`
- `.env`
- `.env.*`
- raw private exports
- provider credential files

## Built-In Definition

This contract targets **L1 user-space built-in**, not OS-kernel built-in.

Required behavior:

- `aios` works from any shell without remembering the MyWorld path.
- `aios status --json` resolves the selected control-plane root.
- A user service can keep `scripts/aios_round_controller.py run` alive.
- The service can be stopped, disabled, and uninstalled without deleting
  `.aios/` state or child repo data.
- Optional desktop entry can open the native control app only when a GUI
  session exists.

Non-goals:

- no root install;
- no `/usr/local/bin` write;
- no systemd system service;
- no provider credential installation;
- no child repo source edits;
- no automatic acceptance of contracts.

## Per-OS Responsibility

### myworld.must_produce

- `scripts/aios_install.py` with subcommands:
  - `plan --json`: show exact files that would be written and current status.
  - `install --json`: create or update user-space launcher/service files.
  - `status --json`: report command path, service state, root resolution,
    desktop entry state, and reversibility.
  - `uninstall --json`: remove files created by this installer only.
- Thin launcher aliases so end-user interaction stays simple:
  - `aios install`
  - `aios up`
  - `aios open`
  - `aios stop`
  - `aios uninstall`
- `docs/AIOS_NATIVE_INSTALL.md`: explain install model, root selection,
  service lifecycle, SSH/Tailscale caveat, GUI caveat, and rollback.
- Tests using a temporary home/config/bin root. Tests must not write to the
  real user home.

### hivemind

- No source role. Existing provider-loop may be reached through `aios
  provider-loop ...`.

### memoryOS

- No source role. Installation does not import or accept memory.

### CapabilityOS

- No source role. Installation does not bind new tools or credentials.

### GenesisOS

- No source role.

## Verification Gate

```bash
python -m py_compile scripts/aios_install.py
python -m unittest tests/test_aios_install.py
python scripts/aios_install.py plan --json
python scripts/aios_install.py status --json
python -m unittest discover -s tests -p 'test_aios_*.py'
python scripts/aios_monitor.py assess --json
```

Optional live dogfood after operator acceptance is manual, not part of the
automatic verification gate: install with `aios install`, inspect with
`aios status --json` and `systemctl --user status aios.service`, then roll back
with `aios uninstall`.

Pass criteria:

- Dry-run plan reports exact write targets.
- Tests prove no real home directory writes during unit tests.
- Installed launcher is a thin delegation to `bin/aios` or
  `scripts/aios_launcher.py`; it does not duplicate runtime logic.
- User service runs the round controller, not provider CLIs directly.
- Uninstall removes only files created by the installer.
- `AIOS_HOME` or explicit root remains the authority for selecting the
  control plane.

## Receipts

- myworld watcher result:
  `.aios/outbox/myworld/asc-0080.myworld.result.json`
- install plan/status stayed dry-run by default; no real home install was
  performed during verification.
- full MyWorld `test_aios_*.py` suite passed 329/329 under the watcher.

## Stop Conditions

- `root_required`
- `system_path_write`
- `global_state_leak`
- `provider_cli_direct_service`
- `credential_file_written`
- `uninstall_deletes_aios_state`
- `child_repo_scope_leak`
- `verification_gate_failed`

## Work Packets

### WP-0080-A — codex@myworld implements user-space installer

- target_agent: codex
- target_repo: myworld
- status: done
- issued: 2026-05-14
- accepted: 2026-05-14
- closed: 2026-05-14
- brief: |
    Implement the reversible AIOS native installer. Use temporary HOME/config
    roots in tests. Do not perform a real install during tests. The installer
    may support live install only after operator acceptance. Keep AIOS state
    workspace-local; only launcher/service/desktop entry live in user config.
- result: `.aios/outbox/myworld/asc-0080.myworld.result.json`
