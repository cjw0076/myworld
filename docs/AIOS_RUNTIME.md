# AIOS Runtime

`scripts/aios_runtime.py` is the first AIOS-facing runtime command. It wraps the
existing control-plane scripts so the user and future agents can ask AIOS
directly instead of remembering which provider CLI or helper script to call.

Claude CLI and Codex CLI are now substrates. They can still execute work, but
the durable interface is AIOS:

```bash
python scripts/aios_runtime.py status --json
python scripts/aios_runtime.py step --json
python scripts/aios_runtime.py run --max-rounds 1 --interval-seconds 0 --json
python scripts/aios_runtime.py submit-goal --repo hivemind --kind goal --goal "..."
```

## Commands

- `status --json`: aggregates monitor assessment, readiness, dispatch summary,
  round-controller status, and primitive event summary.
- `step --json`: runs one bounded round controller iteration and emits an
  `aios.runtime.step` primitive event.
- `run --max-rounds N --interval-seconds S --json`: runs a bounded foreground
  loop. It never defaults to an infinite loop.
- `submit-goal --repo <repo> --kind <kind> --goal <text> --json`: delegates to
  the repo-goal intake protocol.

## Boundaries

The runtime does not replace Hive Mind, MemoryOS, or CapabilityOS. It calls the
existing AIOS surfaces:

- monitor/readiness/dispatch/round-controller scripts in `myworld`
- primitive event log under `.aios/primitives/events.jsonl`
- repo-goal intake for lower-repo requests

It does not directly edit child repo source, accept MemoryOS drafts, bind
CapabilityOS tools, release dispatches outside the dispatch CLI, or hide failed
subprocesses.

## Meaning

Before this command, the operator had to think in Claude monitor tasks, Codex
exec turns, shell scripts, and repo-specific CLIs. After ASC-0052, those remain
implementation details behind one local command:

```text
AIOS status
AIOS step
AIOS run
AIOS submit-goal
```

The long-term product interface should grow from this runtime, not from the
assistant CLIs.
