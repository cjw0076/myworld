---
contract_id: ASC-0051
slug: aios-coevolution-heartbeat
status: accepted
goal: Use the new aios_primitives surface (ASC-0050) to arm three persistent co-evolution loops — memory pulse, capability pulse, hive pulse — so AIOS continuously grows MemoryOS knowledge, CapabilityOS catalog, and Hive routing recommendations without operator chat input.
created: 2026-05-12 23:25 KST
accepted: 2026-05-12 23:25 KST by claude acting operator (founder role delegated)
closed:
acceptance_authority: claude@myworld (operator) — founder explicitly delegated their role ("네가 내 역할을 위임받는거야") and asked AIOS to be used rather than direct script-writing ("AIOS를 사용해").
origin: founder directive 2026-05-12 evening "AIOS완성까지 AIOS 사용해서 계속 공진화해. 지식을 끌어와서 memoryOS에 저장해. 도구를 찾아보고, 인터넷을 흡수해서 capabilityOS를 키우고, hive mind를 사용할 수 있도록 계속 개선해."
---

# ASC-0051 AIOS Co-Evolution Heartbeat

## Why Now

ASC-0050 mounted Claude CLI primitives into AIOS. Codex and local LLM
workers can now arm monitors, schedule fires, track tasks, and record web
evidence. The next step is to actually *run* the co-evolution loops the
founder asked for — using those primitives — rather than relying on chat
turns or operator hotfixes.

This contract creates three named, persistent co-evolution monitors. Each
runs a small worker script that performs one pass of useful AIOS work,
sleeps, and repeats. Together they form the heartbeat that grows MemoryOS
knowledge, CapabilityOS observations, and Hive Mind routing recommendations
continuously.

## AIOS Primitives Used

- `scripts/aios_primitives/monitor.py` — `monitor start --name <id> --command "..."`
- `.aios/primitives/events.jsonl` — emitted summary lines per pulse
- Existing `scripts/aios_doc_scout.py` (ASC-0007)
- Existing `memoryOS ingest-doc-radar` (ASC-0008)
- Existing `capabilityos.cli observe-results` and `audit` (ASC-0002, ASC-0009)
- Existing `aios_dispatch.py status` for in-flight observation

## Scope

repos:

- `myworld`

allowed_files:

- `scripts/aios_coevolution/__init__.py`
- `scripts/aios_coevolution/memory_pulse.sh`
- `scripts/aios_coevolution/capability_pulse.sh`
- `scripts/aios_coevolution/hive_pulse.sh`
- `scripts/aios_coevolution/arm.sh`
- `scripts/aios_coevolution/stop.sh`
- `scripts/aios_coevolution/status.py`
- `tests/test_aios_coevolution.py`
- `docs/AIOS_COEVOLUTION.md`
- `docs/contracts/ASC-0051-aios-coevolution-heartbeat.md`
- `docs/contracts/README.md`
- `docs/AIOS_AGENT_LEDGER.md`

forbidden_files:

- `hivemind/**`
- `memoryOS/**`
- `CapabilityOS/**`
- `uri/**`
- `.aios/logs/**`
- `.aios/state/**`
- `.aios/primitives/events.jsonl` (append-only via primitive — never overwrite)
- `.env`

## Per-OS Responsibility

### myworld.must_produce

Three pulse worker scripts (each does ONE pass per invocation; sleep loop
is in the monitor's command, not the script):

1. **`memory_pulse.sh`** — runs `aios_doc_scout.py` on the jaewon
   workspace, pipes top signals into `memoryos ingest-doc-radar` (drafts
   only, idempotent via stable_id). Emits one summary line:
   `memory_pulse stage=done scout_signals=N imported=M skipped=K`.
   Uses scout output key `top_tasks` (verified — not `top_signals`).

2. **`capability_pulse.sh`** — runs `capabilityos observe-results
   --inbox .aios/outbox` to ingest dispatch result outcomes as
   `CapabilityObservation`s, then `audit --json` to assert
   `recommendation_only=true`. Emits one summary line.

3. **`hive_pulse.sh`** — counts dispatches in flight, scans
   `docs/AIOS_TASK_RADAR.md` for hive keywords, asks
   `capabilityos recommend` whether `cap_hivemind_execution_harness`
   ranks for current state, writes a recommendation file under
   `.aios/primitives/coevolution/hive_routing_recommendation.json`. Does
   NOT dispatch — recommendation only. Emits one summary line.

Plus:

4. **`arm.sh`** — invokes `aios_primitives monitor start` for all three
   pulses with appropriate sleep intervals (memory 1800s, capability
   3600s, hive 900s). Idempotent via `monitor start`'s already-running
   check.

5. **`stop.sh`** — invokes `aios_primitives monitor stop` for all three.

6. **`status.py`** — reads `.aios/primitives/events.jsonl`, returns last
   pulse event per loop with timestamps and summary fields. JSON output.

7. **`tests/test_aios_coevolution.py`** — unit tests covering: each
   pulse runs without error in a temp root; status.py parses event log
   correctly; arm.sh / stop.sh exit 0 (does NOT actually arm in tests
   to avoid leaving processes).

8. **`docs/AIOS_COEVOLUTION.md`** — documents the heartbeat: what each
   pulse does, how to start/stop/status, what events to expect, how to
   add a new pulse.

### child repos

- No source role. Memory ingest writes into a SEPARATE memoryos root
  (`.aios/primitives/coevolution/memory_root/`) so the canonical
  memoryOS store is untouched. CapabilityOS reads only its own state.

## Verification Gate

```bash
python -m unittest tests/test_aios_coevolution.py
bash scripts/aios_coevolution/memory_pulse.sh
bash scripts/aios_coevolution/capability_pulse.sh
bash scripts/aios_coevolution/hive_pulse.sh
bash scripts/aios_coevolution/arm.sh
sleep 5
python scripts/aios_coevolution/status.py --json
bash scripts/aios_coevolution/stop.sh
python -m unittest discover -s tests -p 'test_aios_*.py'
python scripts/aios_monitor.py assess --json
```

Pass criteria:

- All three pulse scripts exit 0 standalone.
- `arm.sh` brings all three monitors to `alive=True` per
  `aios_primitives monitor list`.
- `status.py --json` returns last event per pulse within the last 60 s.
- `stop.sh` returns all three monitors to `alive=False`.
- Full test suite stays green.
- Monitor health remains clear.

## Stop Conditions

- `pulse_writes_child_repo_source`
- `pulse_accepts_memory`: ingest must stay draft-only.
- `pulse_binds_capability`: capability_pulse must keep `recommendation_only=true`.
- `pulse_dispatches_without_contract`: hive_pulse must not call
  `aios_dispatch.py send` directly.
- `monitor_orphan`: arm.sh starts but no PID survives.
- `event_log_corrupt`: events.jsonl becomes unparseable.
- `verification_gate_failed`

## Receipts

Pending until verification + arm dogfood.

## Work Packets

### WP-0051-A — Codex@myworld implements the three pulses + arm/stop/status

- target_agent: codex
- target_repo: myworld
- status: accepted
- issued: 2026-05-12 23:25 KST
- accepted: 2026-05-12 23:25 KST
- closed: pending
- depends_on: ASC-0050 (primitive surface), ASC-0007 (doc scout),
  ASC-0008 (memoryos ingest), ASC-0009 (capability observe).
- brief: |
    Implement the three pulse worker scripts plus arm/stop/status under
    `scripts/aios_coevolution/`. Use the AIOS primitive surface
    (`python scripts/aios_primitives.py monitor start ...`) — do NOT
    spawn watchers via raw bash + setsid. After implementation:
    1. Dogfood by running arm.sh, sleeping 30 s, checking status.py
       reports at least one pulse event per loop.
    2. Run stop.sh to leave a clean tree.
    3. Close the contract with receipts.

    Required reading:
      1. /home/user/workspaces/jaewon/myworld/docs/AIOS_PRIMITIVES.md
      2. /home/user/workspaces/jaewon/myworld/docs/AIOS_AGENT_SELF_LOOP.md
      3. /home/user/workspaces/jaewon/myworld/docs/AIOS_OPERATOR_PLAYBOOK.md
      4. /home/user/workspaces/jaewon/myworld/docs/contracts/ASC-0050-aios-primitive-surface.md
      5. /home/user/workspaces/jaewon/myworld/scripts/aios_doc_scout.py (existing)
      6. /home/user/workspaces/jaewon/myworld/scripts/aios_dispatch.py (existing)

    Constraints:
    - Pulse scripts emit ONE summary line each, not the full JSON output.
    - Memory ingest writes to a SEPARATE memoryos root, not the canonical
      one (per scope: cannot touch canonical memoryOS).
    - Hive pulse is recommendation-only — no aios_dispatch.py send call.
    - Use scout JSON key `top_tasks` (NOT `top_signals` or `signals`).

    After closeout, suggest follow-up ASC-0052 — adapter that lets child
    repo agents (codex@hivemind etc.) call aios_primitives from their
    cwd without sys.path hacks.
- result: pending
