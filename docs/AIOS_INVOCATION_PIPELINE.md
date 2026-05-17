# AIOS Invocation Pipeline

ASC-0067 defines the first plan-only invocation surface:

```bash
python scripts/aios_invoke.py --goal "<goal>" --json
```

The command writes role artifacts under `.aios/invocations/<invocation_id>/`:

- `goal.json`
- `session_envelope.json`
- `genesis/branches.json`
- `memory/context_request.json`
- `memory/context_pack.md`
- `capability/route.json`
- `hive/execution_plan.json`
- `dispatch/packets.json`
- `receipt.json`

The wrapper may call local GenesisOS, MemoryOS, and CapabilityOS CLIs, but it
does not edit child repo source files. Missing optional role surfaces degrade
the receipt instead of pretending the invocation passed.

`receipt.json` uses `aios.invocation_receipt.v1` and is the artifact another
agent should inspect before dispatching actual work.

## Session Envelope

`session_envelope.json` uses `aios.session_envelope.v1`. It is the runtime
object that sits in front of Codex/Hive execution packets. It records the goal,
role statuses, role artifact refs, degraded/failed roles, and executor
assignment. Dispatch packets can bind it with:

```bash
python scripts/aios_dispatch.py send \
  --repo myworld \
  --dispatch-id <id> \
  --session-envelope .aios/invocations/<invocation_id>/session_envelope.json
```

The watcher result echoes the envelope projection, so result evidence can be
traced back to the AIOS interface that prepared the work.
