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
