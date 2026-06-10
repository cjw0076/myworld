---
contract_id: ASC-0123
slug: self-check-dispatch-health-scalar
status: closed
goal: Keep AIOS self-check output machine-scalar by preventing the dispatch health probe from emitting multi-line values under pipefail.
created: 2026-05-13 KST
accepted: 2026-05-13 KST by codex acting founder-delegated operator after ASC-0096 closeout exposed noisy self-check output
closed: 2026-05-13 21:20 KST by codex acting founder-delegated operator
origin: ASC-0096 final verification found `integer expression expected` because dispatch_health became `1\n0` under pipefail.
---

# ASC-0123 Self-Check Dispatch Health Scalar

## Why Now

During ASC-0096 closeout, `bash scripts/aios_self_check.sh` exited 0 but
printed:

```text
scripts/aios_self_check.sh: line 203: [: 1
0: integer expression expected
```

The root cause was the dispatch-health probe using `head -1 | grep -c ... ||
echo 0` under `pipefail`, which could produce a two-line scalar.

## Scope

repos:

- `myworld`

allowed_files:

- `scripts/aios_self_check.sh`
- `docs/contracts/ASC-0123-self-check-dispatch-health-scalar.md`
- `docs/contracts/README.md`
- `docs/AIOS_AGENT_LEDGER.md`
- `docs/AGENT_WORKLOG.md`

forbidden_files:

- `hivemind/**`
- `memoryOS/**`
- `CapabilityOS/**`
- `GenesisOS/**`
- `.env`

## Per-OS Responsibility

### myworld.must_produce

- Replace the fragile dispatch-health shell pipeline with a scalar parser that
  consumes full `aios_dispatch.py status` output and prints exactly `0` or `1`.
- Preserve self-check exit behavior and existing attention semantics.

### child repos

- No role.

## Verification Gate

```bash
bash -n scripts/aios_self_check.sh
bash scripts/aios_self_check.sh
```

Pass criteria:

- self-check emits no `integer expression expected` warning.
- summary line contains scalar `dispatch=0` or `dispatch=1`, not a multi-line
  value.
- command exits 0.

## Stop Conditions

- `self_check_exit_regression`
- `dispatch_health_multiline`
- `scope_violation`
- `verification_gate_failed`

## Receipts

- dispatch: `.aios/inbox/myworld/asc-0123.myworld.json`
- result: `.aios/outbox/myworld/asc-0123.myworld.result.json`
- log: `.aios/logs/asc-0123.myworld.log`
- manual_evidence: `bash -n scripts/aios_self_check.sh` passed.
- manual_evidence: `bash scripts/aios_self_check.sh` exited 0 and emitted
  `dispatch=1` as a scalar.
- memory_writeback: release wrote MemoryOS draft `mem_e067e4ab638dcbda`.

## Work Packets

### WP-0123-A — codex@myworld fixes self-check scalar probe

- target_agent: codex
- target_repo: myworld
- status: done
- depends_on: ASC-0096 closeout verification
- brief: make dispatch health parse output without pipefail/head causing a
  two-line scalar.
- result: `.aios/outbox/myworld/asc-0123.myworld.result.json`
