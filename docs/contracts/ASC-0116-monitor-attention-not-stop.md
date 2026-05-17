---
contract_id: ASC-0116
slug: monitor-attention-not-stop
status: closed
closed: 2026-05-17 KST — operator reconciliation. The load-bearing fix landed in aios_round_controller.py build_recommended_next: it held dispatch on every non-clear health (watch/attention/blocked); it now holds ONLY on `blocked` — the monitor's real-failure tier. `watch`/`attention` (busy: a repo dirty because an agent works; stale: decisions awaiting review) no longer freeze the dispatch chain. The monitor already grades severity into the three tiers the fix relies on. tests/test_aios_round_controller.py +3, 8 passed. Named exit "round controller halts only on broken" met.
goal: Stop round_controller from blocking dispatch when monitor health=attention is caused by codex's own active work (e.g. memoryOS dirty during ASC-0111 implementation). Distinguish "attention because something is broken" from "attention because someone is working" so AIOS doesn't self-throttle while working.
created: 2026-05-13 KST
accepted: 2026-05-13 KST by claude as verifier
acceptance_authority: claude@myworld (verifier round 4) per founder /loop directive
origin: 2026-05-13 round 4 — readiness dropped L6→L5. Diagnosis: round_controller `latest_next: hold_for_monitor` because monitor health=attention. Cause of attention: memoryOS dirty (cli.py + test_founder_ingest.py being implemented by codex per ASC-0111). System self-throttled while making real progress. Verifier-issued ASC-0110/0111/0115 sit at status=accepted with 0 dispatch packets because the chain stalled.
---

# ASC-0116 Monitor: Attention ≠ Stop

DNA references: Invariant 4 (every loop has a named exit — but not "stuck"
exit), Invariant 5 (provenance — distinguish causes), Invariant 8 (classify
before committing — attention is too coarse a signal).

## Why Now

Verified 2026-05-13 round 4:

```
readiness: L5 (was L6 stable for 2 days)
gap: ASC-0105 packet pending in inbox
round_controller: latest_next=hold_for_monitor
monitor health: attention
finding: repo_dirty owner=memoryOS
actual cause: codex@memoryOS implementing ASC-0111 (founder ingest)
              — adds memoryos/cli.py + tests/test_founder_ingest.py
result: dispatch chain frozen ⇒ ASC-0110/0111/0115 sit accepted/0-dispatch
        ⇒ verifier's discomfort signals don't reach codex execution
        ⇒ self-referential gridlock
```

`hold_for_monitor` was meant to halt on broken state (verification gate
failed, real failure). It's now halting on healthy state (work in progress).
The signal is too coarse. "Attention" lumps:

- **broken**: real test failure, dispatch failure, schema corruption
- **busy**: in-progress codex commits, expected dirty state during impl
- **stale**: decisions waiting on operator review, not blocking work

These need to be distinguished. Round_controller should hold only on
the first.

## Required Reading

- `scripts/aios_round_controller.py` (~line 161 `hold_for_monitor` logic)
- `scripts/aios_monitor.py` (assess findings → severity → owner mapping)
- `scripts/aios_self_check.sh` (active probe outputs — informs)
- `docs/AIOS_DNA.md` (after ASC-0105) — Invariants 4, 5, 8

## Scope

repos: `myworld`

allowed_files:

- `scripts/aios_round_controller.py`
- `scripts/aios_monitor.py`
- `tests/test_aios_round_controller.py`
- `tests/test_aios_monitor.py`
- `docs/AIOS_MONITOR_RECONCILIATIONS.json` (extend with new categories)
- `docs/contracts/ASC-0116-monitor-attention-not-stop.md`
- `docs/AIOS_AGENT_LEDGER.md`

forbidden_files:

- `hivemind/**`, `memoryOS/**`, `CapabilityOS/**`, `GenesisOS/**`, `uri/**`
- `_from_desktop/**`, `dain/**`, `minyoung/**`
- `.env`

## Per-OS Responsibility

### myworld.must_produce

`aios_monitor.py assess` extended with **finding category** alongside severity:

- `broken` — real failure, blocks progress (existing behavior)
- `busy` — work in progress (NEW): repo_dirty + recent commit < 5min
- `stale` — waiting on operator decision (NEW): held >4h, drafts unreviewed
- `clear` — no findings (existing)

Promotion rules:
- repo_dirty + git log shows commit in repo within last 5 min → `busy`, NOT `broken`
- repo_dirty + no recent activity > 5 min → `attention/broken` (existing)
- failed result packet → `broken` (existing)
- held contract > 4h → `stale`

`aios_round_controller.py` hold logic:

- `hold_for_monitor` triggers ONLY on `broken` (not `busy` or `stale`)
- if monitor reports `busy`: continue dispatch but record `busy_concurrent` event
  (operator can see codex working alongside dispatch)
- if `stale`: continue dispatch, record `stale_pending_review` (operator decides)
- only `broken` halts the chain

Tests:
- synthetic monitor finding (repo_dirty + recent commit) → `busy` not `broken`
- round controller doesn't halt when finding=busy
- existing broken-state tests still pass (real failure still halts)

### child repos: no change

## Verification Gate

```bash
python -m py_compile scripts/aios_round_controller.py scripts/aios_monitor.py
python -m unittest tests/test_aios_round_controller.py tests/test_aios_monitor.py
# Synthetic busy state test (write something to a child repo + commit just now → assess)
python scripts/aios_monitor.py assess --json | python -c "
import json, sys
d = json.load(sys.stdin)
findings = d.get('findings', [])
for f in findings:
    if f.get('code') == 'repo_dirty':
        cat = f.get('category', '?')
        assert cat in ('busy', 'broken', 'stale'), f'category missing: {f}'
        print(f'  finding category surfaced: {cat}')
"
# Round controller test — busy doesn't halt
python scripts/aios_round_controller.py once --json | python -c "
import json, sys
d = json.load(sys.stdin)
nxt = d.get('next_action', d.get('next', '?'))
# acceptable next when busy: continue_dispatch, open_next_contract — NOT hold_for_monitor
assert nxt != 'hold_for_monitor' or 'broken' in str(d), f'still halting on busy state: {nxt}'
"
python -m unittest discover -s tests -p 'test_aios_*.py'
```

Pass criteria (DNA-cited):

- `findings.category` field added (Inv 8: classify)
- Round controller halts only on `broken` (Inv 4: named exit, not stuck)
- Recent-commit detection works (Inv 5: provenance — git log shows when)
- Existing broken-state tests still halt correctly

## Stop Conditions

- `controller_silently_proceeds_on_broken`: real failures must still halt
- `category_silent_default`: every finding must explicitly classify
- `recent_commit_window_too_loose`: 5-min window is the cap; longer = stale
- `child_repo_scope_leak`
- `verification_gate_failed`

## Receipts

Pending. Dogfood requirement: after fix, this contract's own dispatch
must succeed during the same period the verifier's other contracts
(ASC-0110/0111/0115) are being implemented.
