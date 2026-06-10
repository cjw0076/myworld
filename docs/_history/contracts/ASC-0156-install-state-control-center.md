---
contract_id: ASC-0156
slug: install-state-control-center
status: closed
goal: Show AIOS install, service, local UI, and loop reachability in the Control Center with simple end-user wording.
created: 2026-05-14 11:15 KST
accepted: 2026-05-14 11:15 KST
closed: 2026-05-14 11:22 KST
acceptance_authority: founder delegated continuation under active AIOS maturation goal.
origin: ASC-0080 made AIOS installable as a user-space background process; operator then clarified that interaction must stay intuitive and detailed explanation should live in docs.
---

# ASC-0156 Install State Control Center

## Why Now

ASC-0080 added the reversible native install path. The next user-facing gap is
visibility: a user should not have to inspect systemd files, ports, or PID
files to know whether AIOS is installed, running, reachable, and looping.

## Scope

repos:

- `myworld`

allowed_files:

- `scripts/aios_control_snapshot.py`
- `apps/control/index.html`
- `apps/control/app.js`
- `apps/control/styles.css`
- `tests/test_aios_control_snapshot.py`
- `docs/contracts/ASC-0156-install-state-control-center.md`
- `docs/contracts/README.md`
- `docs/AIOS_AGENT_LEDGER.md`
- `docs/AGENT_WORKLOG.md`

forbidden_files:

- `hivemind/**`
- `memoryOS/**`
- `CapabilityOS/**`
- `GenesisOS/**`
- `.env`
- `.env.*`
- provider credentials
- raw private exports
- real user install targets under `~/.local` or `~/.config`

## Per-OS Responsibility

### myworld.must_produce

- Snapshot field `installation` with command, service, Control Center, and
  round-loop reachability.
- Control Center runtime band that uses short labels and command chips rather
  than implementation explanations.
- Tests proving snapshot install state is derived without writing to the real
  user home.

### hivemind

- No source role.

### memoryOS

- No source role. Closeout may produce a draft memory.

### CapabilityOS

- No source role.

### GenesisOS

- Advisory UX constraint: keep the visible interaction direct and put detail
  in docs.

## Verification Gate

```bash
python -m unittest tests/test_aios_control_snapshot.py
python scripts/aios_control_snapshot.py --check-app-js apps/control/app.js --json
python -m unittest discover -s tests -p 'test_aios_*.py'
python scripts/aios_monitor.py assess --json
```

Pass criteria:

- Snapshot includes `installation`.
- Unit tests use a temporary `HOME`/`XDG_CONFIG_HOME`.
- UI has a visible runtime section and no long install explanation copy.
- No live install or uninstall is performed.

## Receipts

- watcher result: `.aios/outbox/myworld/asc-0156.myworld.result.json`
- screenshot: `.aios/screenshots/aios-control-install-runtime.png`
- snapshot write: `apps/control/aios-control-snapshot.json` and
  `apps/control/aios-control-data.js`

## Stop Conditions

- `real_home_install_during_test`
- `system_path_write`
- `provider_credential_touch`
- `ui_explains_internals_instead_of_status`
- `verification_gate_failed`

## Work Packets

### WP-0156-A — codex@myworld adds install state to Control Center

- target_agent: codex
- target_repo: myworld
- status: done
- issued: 2026-05-14
- accepted: 2026-05-14
- closed: 2026-05-14
- depends_on: ASC-0080
- brief: |
    Add snapshot-derived AIOS install/runtime status to the Control Center.
    Keep visible interaction simple: installed/running/reachable/looping and
    short command chips. Do not run a live install. Verify with temporary
    home/config roots and existing MyWorld tests.
- result: `.aios/outbox/myworld/asc-0156.myworld.result.json`
