# AIOS Control App

The control app is the first local visualization surface for myworld. It is a
static app backed by a generated snapshot, so it can run without a server,
package install, or child-repo execution.

Refresh the snapshot:

```bash
python scripts/aios_control_snapshot.py \
  --write-json apps/control/aios-control-snapshot.json \
  --write-js apps/control/aios-control-data.js \
  --json
```

Open:

```text
apps/control/index.html
```

Run as a local app:

```bash
python scripts/aios_local_app.py up --json
python scripts/aios_local_app.py status --json
python scripts/aios_local_app.py stop --json
```

Default URL:

```text
http://127.0.0.1:8765/
```

Run as a native desktop app:

```bash
python scripts/aios_desktop_app.py status --json
python scripts/aios_desktop_app.py snapshot --json
python scripts/aios_desktop_app.py launch
```

The desktop app uses Python `tkinter` and the same generated control snapshot.
It does not start an HTTP server or require a browser. In a headless shell,
`status --json` may report `display_available=false`; run `launch` from a
graphical desktop session.

The app renders:

- active goal and goal-evolution recommendation
- contract counts and latest contracts
- dispatch counts and latest dispatches
- repo loop state for hivemind, memoryOS, and CapabilityOS
- MemoryOS trace IDs, CapabilityOS route IDs, and Hive run IDs found in recent
  contracts
- stop-condition lanes and monitor next actions

The snapshot script reads control-plane artifacts and repo status only. It must
not read `.aios/logs` bodies or mutate child repos.
