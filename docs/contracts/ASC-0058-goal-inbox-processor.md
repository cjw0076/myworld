---
contract_id: ASC-0058
slug: goal-inbox-processor
status: closed
goal: Process the 11 pending goal/friction packets in `.aios/goal_inbox/` (uri:7, hivemind:2, CapabilityOS:1, myworld:1) into operator-reviewable contract candidates so child-repo voices actually reach the contract chain.
created: 2026-05-13 KST
accepted: 2026-05-13 KST by claude acting operator (founder role delegated)
closed: 2026-05-13 KST by codex@myworld
acceptance_authority: claude@myworld (operator) per founder directive.
origin: claude diagnostic showed ASC-0038 repo-goal protocol successfully accepts child→myworld submissions (11 packets across 4 repos), but no processor converts them to contract candidates. They sit unprocessed.
---

# ASC-0058 Goal Inbox Processor

## Why Now

ASC-0038 created the repo-goal protocol so child agents (codex@hivemind,
codex@memoryOS, codex@CapabilityOS, codex@uri) can submit goals/friction
to myworld via `.aios/goal_inbox/<repo>/`. As of now:

- 11 packets pending (uri 7, hivemind 2, CapabilityOS 1, myworld 1)
- No processor reads them
- No path from packet → contract candidate

Without this, child voices are heard but never acted on. Especially
problematic for uri's 7 packets — uri is doing real product work and
its friction signals need to reach the contract chain.

## Scope

repos:

- `myworld`

allowed_files:

- `scripts/aios_goal_inbox_processor.py`
- `tests/test_aios_goal_inbox_processor.py`
- `docs/AIOS_REPO_GOAL_LOOP.md`
- `docs/operator_queue/<goal_id>-<classification>.md`
- `docs/contracts/ASC-0081-provider-fallback-execution-binding.md`
- `docs/contracts/ASC-0082-product-repo-sprint-driver.md`
- `docs/contracts/ASC-0083-research-to-sprint-context-primitive.md`
- `docs/contracts/ASC-0058-goal-inbox-processor.md`
- `docs/contracts/README.md`
- `docs/AIOS_AGENT_LEDGER.md`

forbidden_files:

- `hivemind/**`, `memoryOS/**`, `CapabilityOS/**`, `uri/**`
- `.aios/goal_inbox/**` (read only — never delete or modify)
- `.env`

## Per-OS Responsibility

### myworld.must_produce

- `scripts/aios_goal_inbox_processor.py` — reads all packets across
  `.aios/goal_inbox/<repo>/`, classifies each:
  - `auto_promote` — well-formed goal that maps to existing capabilities → write a `proposed` ASC contract draft to `docs/contracts/`
  - `needs_operator_review` — ambiguous → write to `docs/operator_queue/<id>.md` for human triage
  - `reject_out_of_scope` — outside AIOS scope → write rejection note with reason
  - `defer_capability_gap` — needs new capability → write to CapabilityOS observed_gaps for next pulse
- Writes a single processing receipt: `.aios/primitives/goal_inbox_run/<run_id>.json` per execution
- Idempotent: re-running same packets skips already-processed
- NEVER deletes packets from `.aios/goal_inbox/` (audit trail)
- Tests: synthetic packet → expected classification path; idempotency; reject malformed
- Documentation: extend `AIOS_REPO_GOAL_LOOP.md` with the processor stage

### child repos

- No source change. Processor reads their submissions only.

## Verification Gate

```bash
python -m unittest tests/test_aios_goal_inbox_processor.py
python scripts/aios_goal_inbox_processor.py --json --assert-min-classified 11
python scripts/aios_goal_inbox_processor.py report --json
python -m unittest discover -s tests -p 'test_aios_*.py'
python scripts/aios_monitor.py assess --json
```

Pass criteria:

- All 11 pending packets classified.
- At least one auto_promote → proposed contract file exists with
  `status: proposed` (operator must accept before dispatch).
- Processor never deletes from goal_inbox.
- Receipt written.

## Stop Conditions

- `processor_deletes_packets`
- `processor_auto_accepts_contract`: any new contract status is `proposed`,
  never `accepted` automatically.
- `processor_writes_to_child_repo`
- `verification_gate_failed`

## Receipts

- processor receipt:
  `.aios/primitives/goal_inbox_run/gir_20260513T101137_cdc6f06d0599.json`
- watcher result:
  `.aios/outbox/myworld/asc-0058.myworld.result.json`
- outcome:
  - 15 goal inbox packets classified.
  - 15 `auto_promote`.
  - 0 `needs_operator_review`.
  - 0 `reject_out_of_scope`.
  - 0 `defer_capability_gap`.
  - proposed contracts created:
    - `docs/contracts/ASC-0081-provider-fallback-execution-binding.md`
    - `docs/contracts/ASC-0082-product-repo-sprint-driver.md`
    - `docs/contracts/ASC-0083-research-to-sprint-context-primitive.md`
- verification:
  - `python -m unittest tests/test_aios_goal_inbox_processor.py` passed 4/4.
  - `python scripts/aios_goal_inbox_processor.py --json --assert-min-classified 11` passed with 15 classified.
  - `python scripts/aios_goal_inbox_processor.py report --json` reported processed_index_count 15.
  - `python -m unittest discover -s tests -p 'test_aios_*.py'` passed 177/177.
  - `python scripts/aios_dispatch.py watch --repo myworld --dispatch-id asc-0058 --once` passed.
  - `python scripts/aios_dispatch.py collect --repo myworld` collected the passed result.
- monitor:
  - `asc-0058` pending alert cleared after collect.
  - Monitor still reports pending results for `asc-0064` and `asc-0068`; those are the next control-plane queue items.

## Work Packets

### WP-0058-A — codex@myworld implements processor

- target_agent: codex
- target_repo: myworld
- status: done
- closed: 2026-05-13 KST
- brief: |
    Implement the goal inbox processor with the four classification
    paths above. Process the 11 currently pending packets as the
    dogfood run. Write the receipt. Add tests + doc.
- result: `.aios/outbox/myworld/asc-0058.myworld.result.json`
