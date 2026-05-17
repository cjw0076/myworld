---
contract_id: ASC-0118
slug: readiness-reconciliation-binding
status: closed
goal: Bind AIOS readiness L6 pending-packet checks to the same reconciliation registry used by monitor, so approved historical dispatch drift does not drop readiness from L6 to L5.
created: 2026-05-13 KST
accepted: 2026-05-13 KST by codex acting founder-delegated operator
closed: 2026-05-13 KST by codex@myworld after dispatch gate passed
acceptance_authority: codex@myworld per founder directive to keep AIOS processing contracts autonomously.
origin: ASC-0106 self-check showed readiness L5 because `.aios/inbox/myworld/asc-0105.myworld.json` has no result packet. Monitor already reconciles this as the ASC-0105/ASC-0109 ID-collision artifact, but `scripts/aios_readiness.py` still treats raw pending inbox as a hard L6 failure.
---

# ASC-0118 Readiness Reconciliation Binding

DNA references: Invariant 5 (provenance), Invariant 8 (classify before
committing).

## Why Now

`bash scripts/aios_self_check.sh` reports `READINESS_DROP level=5` even though
`python scripts/aios_monitor.py assess --json` reports `health=clear`.

Concrete cause:

- pending packet: `.aios/inbox/myworld/asc-0105.myworld.json`
- dispatch id: `asc-0105`
- recorded contract path: `docs/contracts/ASC-0105-end-user-ask-surface.md`
- actual executable replacement: `ASC-0109`
- existing reconciliation:
  `reconcile-asc-0105-end-user-surface-id-collision-pending`

Monitor understands the drift; readiness does not. That makes L6 depend on a
known bad historical packet instead of current executable state.

## Scope

repos: `myworld`

allowed_files:

- `scripts/aios_readiness.py`
- `tests/test_aios_readiness.py`
- `docs/contracts/ASC-0118-readiness-reconciliation-binding.md`
- `docs/contracts/README.md`
- `docs/AGENT_WORKLOG.md`
- `docs/AIOS_AGENT_LEDGER.md`

forbidden_files:

- `.aios/inbox/**` (read-only; do not delete stale history)
- `.aios/outbox/**` (read-only except dispatch result written by watcher)
- `hivemind/**`, `memoryOS/**`, `CapabilityOS/**`, `GenesisOS/**`, `uri/**`
- `.env`

## Per-OS Responsibility

### myworld.must_produce

`scripts/aios_readiness.py`:

- loads `docs/AIOS_MONITOR_RECONCILIATIONS.json`
- when checking pending inbox packets, constructs the same alert shape as
  monitor for `dispatch_results_pending`
- ignores only exact reconciliation matches
- ignores a packet whose latest dispatch event is currently `running`, because
  a contract checking readiness from inside its own verification gate has not
  written its result packet yet
- keeps unreconciled pending packets as L6 blockers

Tests:

- unreconciled pending packet still blocks L6
- exact `dispatch_results_pending` reconciliation allows L6
- current running packet does not fail its own readiness gate

### child repos: no change

## Verification Gate

```bash
python -m py_compile scripts/aios_readiness.py
python -m unittest tests/test_aios_readiness.py
python scripts/aios_readiness.py --json
bash scripts/aios_self_check.sh
python -m unittest discover -s tests -p 'test_aios_*.py'
python scripts/aios_monitor.py assess --json
```

Pass criteria:

- `python scripts/aios_readiness.py --json` reports `ready=true`
- self-check no longer emits `READINESS_DROP`
- monitor remains `health=clear`
- stale `asc-0105` inbox file remains on disk as history

## Stop Conditions

- `readiness_deletes_history`
- `readiness_ignores_unreconciled_pending`
- `reconciliation_partial_match`
- `verification_gate_failed`

## Receipts

- First dispatch result: `.aios/outbox/myworld/asc-0118.myworld.result.json`
  initially failed because `python scripts/aios_readiness.py --json` counted
  the currently running `asc-0118` packet as pending. This exposed an additional
  self-verification edge case.
- Fix added: readiness ignores a packet whose latest dispatch event is
  `running`, while unreconciled non-running pending packets still block L6.
- Final dispatch result: `.aios/outbox/myworld/asc-0118.myworld.result.json`
  status `passed`.
- Verification passed:
  - `python -m py_compile scripts/aios_readiness.py`
  - `python -m unittest tests/test_aios_readiness.py` (`5` tests)
  - `python scripts/aios_readiness.py --json` reported `level=6`,
    `ready=true`, `gaps=[]`
  - `bash scripts/aios_self_check.sh` no longer emitted `READINESS_DROP`
  - `python -m unittest discover -s tests -p 'test_aios_*.py'` (`237` tests)
  - `python scripts/aios_monitor.py assess --json` reported `health=clear`
- Historical packet preserved: `.aios/inbox/myworld/asc-0105.myworld.json`
  remains on disk; it is classified through the reconciliation registry rather
  than deleted.
- Release: `python scripts/aios_dispatch.py release --dispatch-id asc-0118
  --reason "ASC-0118 readiness reconciliation binding verified; L6 restored
  without deleting stale history"` returned `status=released`.
- MemoryOS closeout writeback: draft `mem_49585c35d8301405`.

## Work Packets

### WP-0118-A — codex@myworld binds readiness to reconciliation registry

- target_agent: codex
- target_repo: myworld
- status: done
- depends_on: ASC-0109 closed, ASC-0106 closed
- brief: Implement exact reconciliation-aware pending packet checks in
  `scripts/aios_readiness.py`, add tests, and dogfood against the existing
  `asc-0105` stale inbox packet without deleting it.
- result: `.aios/outbox/myworld/asc-0118.myworld.result.json`
