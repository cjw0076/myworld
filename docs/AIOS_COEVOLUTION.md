# AIOS Co-Evolution Heartbeat

ASC-0051 adds three persistent pulse loops built on `aios_primitives monitor`.
Each pulse script performs one bounded pass and emits one summary line. The
monitor primitive turns those lines into append-only events in
`.aios/primitives/events.jsonl`.

## Commands

```bash
bash scripts/aios_coevolution/memory_pulse.sh
bash scripts/aios_coevolution/capability_pulse.sh
bash scripts/aios_coevolution/hive_pulse.sh

bash scripts/aios_coevolution/arm.sh
python scripts/aios_coevolution/persistent.py --json
python scripts/aios_coevolution/status.py --json
bash scripts/aios_coevolution/stop.sh
```

## Pulses

- `aios-memory-pulse`: runs the workspace doc scout, then imports the scout
  JSON into a separate MemoryOS root under `.aios/primitives/coevolution/`.
  This keeps the canonical MemoryOS repo untouched.
- `aios-capability-pulse`: asks CapabilityOS to observe local AIOS outbox
  results and audits that the capability catalog remains recommendation-only.
- `aios-hive-pulse`: counts current dispatch state, asks CapabilityOS for a
  Hive execution-harness route recommendation, and writes the latest routing
  recommendation under `.aios/primitives/coevolution/`.

The heartbeat does not dispatch work directly, accept memories, bind tools, or
write child-repo source files. It only senses, records, and recommends.

## Persistence

ASC-0057 makes pulse monitors resilient. `scripts/aios_round_controller.py`
runs `scripts/aios_coevolution/persistent.py` on every round. The helper lists
`aios_primitives monitor` state, starts only missing or dead pulse monitors,
and returns a JSON receipt with `started`, `failed`, and per-pulse actions.

The helper is idempotent: already-alive pulse monitors are not restarted, and
the round controller does not spawn any process outside the three named pulse
monitors.

## Intervals

- memory pulse: 1800 seconds
- capability pulse: 3600 seconds
- hive pulse: 900 seconds

The intervals live in `arm.sh`. Change them there only under a contract.

## Status

`status.py --json` reads primitive monitor events and returns the latest event
per pulse:

```json
{
  "schema_version": "aios.coevolution.status.v1",
  "pulses": {
    "aios-memory-pulse": {
      "events": 1,
      "last_at": "2026-05-12T23:30:00+09:00",
      "last_line": "memory_pulse stage=done scout_signals=60 imported=12 skipped=0 warnings=0"
    }
  }
}
```

## Add A Pulse

1. Create a one-pass script that emits exactly one summary line.
2. Add a named monitor to `arm.sh`.
3. Add the matching stop command to `stop.sh`.
4. Add the pulse name to `status.py`.
5. Add tests before arming it on the live control plane.
