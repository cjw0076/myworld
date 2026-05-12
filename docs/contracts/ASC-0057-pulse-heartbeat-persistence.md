---
contract_id: ASC-0057
slug: pulse-heartbeat-persistence
status: accepted
goal: Make co-evolution pulses (memory/capability/hive) and the doc scout run continuously without operator intervention, so AIOS actually evolves between contract turns.
created: 2026-05-13 KST
accepted: 2026-05-13 KST by claude acting operator (founder role delegated)
closed:
acceptance_authority: claude@myworld (operator) per founder directive "Gap 해소 다음 작업으로 잡아 / 전부 contract 발행".
origin: claude diagnostic showed all 3 pulses alive=False since ASC-0051 dogfood (2026-05-12 23:21), AIOS_TASK_RADAR.md unchanged for 24h.
---

# ASC-0057 Pulse Heartbeat Persistence

## Why Now

ASC-0051 created the pulse code (memory/capability/hive) and proved one
dogfood pass. After dogfood close, all three pulses stopped. Result:
AIOS catalog/memory/hive observations are NOT actually accumulating
between contract turns. The system has the metabolism wired but the
heart is off.

Round controller daemon (PID 4154660) runs continuously and dispatches
contracts. The pulses must run with the same persistence so each
contract turn benefits from accumulated observations.

## Scope

repos:

- `myworld`

allowed_files:

- `scripts/aios_round_controller.py`
- `scripts/aios_coevolution/arm.sh`
- `scripts/aios_coevolution/persistent.py`
- `tests/test_aios_round_controller.py`
- `tests/test_aios_coevolution.py`
- `docs/AIOS_COEVOLUTION.md`
- `docs/contracts/ASC-0057-pulse-heartbeat-persistence.md`
- `docs/contracts/README.md`
- `docs/AIOS_AGENT_LEDGER.md`

forbidden_files:

- `hivemind/**`
- `memoryOS/**`
- `CapabilityOS/**`
- `uri/**`
- `.env`

## Per-OS Responsibility

### myworld.must_produce

- `aios_round_controller.py` `run` mode now also ensures the three pulse
  monitors are alive on every tick. If any pulse `alive=False`, the
  controller arms it via the existing `aios_primitives monitor start`
  surface. Idempotent: already-alive pulses are not re-armed.
- `scripts/aios_coevolution/persistent.py` — small helper: checks
  pulse state, arms missing pulses, returns JSON status. Called by
  round controller and exposed for direct invocation.
- New test in `tests/test_aios_round_controller.py`: simulates round
  with all pulses dead, asserts they get armed.
- Documentation update: `AIOS_COEVOLUTION.md` explains that pulses
  are now resilient — if killed, next round re-arms.

### child repos

- No source change. Pulses observe child state read-only.

## Verification Gate

```bash
# Stop any current pulses to simulate cold start
bash scripts/aios_coevolution/stop.sh
python -m unittest tests/test_aios_round_controller.py tests/test_aios_coevolution.py
python scripts/aios_round_controller.py once --root . --json
sleep 5
python scripts/aios_primitives.py monitor list --json | python -c "
import json, sys
d = json.load(sys.stdin)
for m in d:
    if m['name'].startswith('aios-') and 'pulse' in m['name']:
        assert m.get('alive'), f\"{m['name']} not alive after round\"
        print(f\"OK {m['name']} alive\")"
python -m unittest discover -s tests -p 'test_aios_*.py'
python scripts/aios_monitor.py assess --json
```

Pass criteria:

- After stop.sh + one controller round, all 3 pulses are alive.
- Re-running the round does not duplicate or restart alive pulses.
- Full test suite green; monitor health clear.

## Stop Conditions

- `pulse_duplicate_arm`: same pulse spawned twice.
- `controller_starts_unowned_processes`: controller spawns processes
  that are not pulses.
- `child_repo_scope_leak`
- `verification_gate_failed`

## Receipts

Pending.

## Work Packets

### WP-0057-A — codex@myworld wires pulse persistence into round controller

- target_agent: codex
- target_repo: myworld
- status: accepted
- brief: |
    Add pulse-arm step to round controller's tick. Add helper
    persistent.py. Add tests. Update doc. Idempotent.
- result: pending
