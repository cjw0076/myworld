# AIOS Native Install

AIOS native install is a reversible user-space install. It makes AIOS feel
built in without writing to `/usr`, `/etc`, provider credential stores, child
repos, or raw private exports.

## Install Model

The installer creates three managed files:

- `~/.local/bin/aios` — thin launcher that delegates to `myworld/bin/aios`.
- `~/.config/systemd/user/aios.service` — user service that keeps AIOS awake.
- `~/.config/autostart/aios-control.desktop` — optional GUI session entry that
  opens the local Control Center.

The service runs the control app first, then keeps the round controller alive:

```bash
python scripts/aios_local_app.py --root "$AIOS_HOME" up --json
python scripts/aios_round_controller.py run --root "$AIOS_HOME" --interval 30 --execute-children
```

`Restart=always` lets systemd revive the round controller if it exits. AIOS
state remains under the selected MyWorld root, mainly `.aios/`.

## Commands

Normal user interaction stays short:

```bash
aios install
aios status --json
aios open
aios stop
aios uninstall
```

Detailed/operator commands remain available for dry-runs and debugging.

Preview the exact writes:

```bash
python scripts/aios_install.py plan --json
```

Install launcher and service files without starting them:

```bash
python scripts/aios_install.py install --json
```

Install and start the always-on user service:

```bash
python scripts/aios_install.py install --json --enable-now
```

Check install and runtime status:

```bash
aios root --json
aios status --json
python scripts/aios_install.py status --json
systemctl --user status aios.service
```

Remove only installer-managed files:

```bash
python scripts/aios_install.py uninstall --json --disable-now
```

## SSH And Tailscale

The user service can run without a graphical desktop. Over SSH or Tailscale,
use the CLI or forward/open the local Control Center port only on trusted
links:

```bash
aios status --json
python scripts/aios_local_app.py --root "$AIOS_HOME" status --json
```

The default UI URL is `http://127.0.0.1:8765/`. Do not expose it publicly
without a separate authentication contract.

If the service should survive logout and start at boot before the first GUI
login, the operator can enable user lingering:

```bash
loginctl enable-linger "$USER"
```

The installer does not run that command automatically.

## Root Selection

The installed launcher sets `AIOS_HOME` to the root used at install time and
then delegates to `bin/aios --root "$AIOS_HOME"`. Runtime commands may still
accept an explicit `--root` when needed.

## Rollback

Uninstall preserves:

- `.aios/` runtime state;
- child repositories;
- MemoryOS stores;
- provider credentials and auth files.

It removes only files containing the AIOS installer marker. Unmanaged files at
the same paths block install or uninstall unless `--force` is supplied.
