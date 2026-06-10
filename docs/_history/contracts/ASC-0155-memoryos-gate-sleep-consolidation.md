---
contract_id: ASC-0155
slug: memoryos-gate-sleep-consolidation
status: closed
goal: Reverse-engineer prompt-Agent execution loop pairs from AIOS/MemoryOS traces and consolidate them into a personalized Gate few-shot/policy pack before any fine-tuning.
created: 2026-05-14T03:44:02+09:00
accepted: 2026-05-14T03:44:02+09:00
closed: 2026-05-14T03:46:33+09:00
---

# ASC-0155 MemoryOS Gate Sleep Consolidation

## Why

The founder proposed that AIOS can reverse-engineer prompt-Agent execution loop
pairs from MemoryOS and runtime traces, then make the Gate increasingly behave
like a personalized provider CLI/operator for each user. The analogy is sleep:
short-term experience is consolidated into long-term operating behavior.

This contract implements the safe V1: reviewed retrieval and policy-pack
distillation, not model fine-tuning. Fine-tuning remains a later contract after
dataset size, eval, rollback, and privacy gates exist.

## Scope

- repos: `myworld`
- allowed_files:
  - `scripts/aios_gate_sleep.py`
  - `scripts/aios_chat_router.py`
  - `scripts/aios_chat.py`
  - `tests/test_aios_gate_sleep.py`
  - `tests/test_aios_chat_router.py`
  - `tests/test_aios_chat.py`
  - `docs/AIOS_CHAT.md`
  - `docs/contracts/ASC-0155-memoryos-gate-sleep-consolidation.md`
  - `docs/contracts/README.md`
  - `docs/AGENT_WORKLOG.md`
  - `docs/AIOS_AGENT_LEDGER.md`
- read_only_sources:
  - `.aios/chat/*/messages.jsonl`
  - `.aios/chat/*/gate_decisions/*.json`
  - `.aios/chat/*/cost.json`
  - `.aios/chat/*/memory_drafts.json`
  - `memoryOS/memory/objects.jsonl`
  - `memoryOS/memory/reviews.jsonl`
- generated_artifacts:
  - `.aios/gate/founder/loop_pairs.jsonl`
  - `.aios/gate/founder/gate_pack.json`
  - `.aios/gate/founder/sleep_report.json`
- forbidden_files:
  - provider credentials, PINs, `.env`
  - raw private provider logs
  - MemoryOS raw exports
  - child repo implementation files

## Responsibilities

### myworld.must_produce

- `scripts/aios_gate_sleep.py`.
- A sleep report with:
  - extracted prompt -> Gate decision -> route/substrate -> response loop
    pairs.
  - accepted MemoryOS hints overlaid as Gate context.
  - `finetune_ready=false`.
- Chat router projection of the active Gate pack into each
  `aios.chat.gate_decision.v1` artifact.

### memoryos.must_produce

- Existing append-only memory objects and review ledger only.
- Accepted memory hints may be read; no MemoryOS records are auto-accepted or
  modified by this contract.

### capabilityos.must_produce

- No direct execution. The generated Gate pack can reinforce that current-info
  routes require CapabilityOS/source-aware capability before provider answer.

### genesisos.must_produce

- No direct execution. The pack records that fine-tuning is not allowed until
  an eval/rollback/privacy contract exists.

### hive_mind.must_produce

- No child Hive work. Hive remains the route for multi-step execution after
  the Gate classifies work.

## Verification Gate

```bash
python -m py_compile scripts/aios_gate_sleep.py scripts/aios_chat_router.py scripts/aios_chat.py
python -m unittest tests/test_aios_gate_sleep.py tests/test_aios_chat_router.py tests/test_aios_chat.py
python scripts/aios_gate_sleep.py --json
python scripts/aios_chat.py --message "오늘 날씨는 ?" --conversation asc-0155-gate-pack-smoke --json
python -m unittest discover -s tests -p 'test_aios_*.py'
```

Pass criteria:

- Sleep report writes `.aios/gate/founder/gate_pack.json`.
- Gate pack has `schema_version=aios.gate.pack.v1`.
- Gate pack has `finetune_ready=false`.
- Chat smoke includes a `gate_pack` projection inside `gate_decision`.
- No private/PIN/API-key content appears in the pack.

## Stop Conditions

- `gate_pack_missing`
- `private_content_in_gate_pack`
- `draft_memory_promoted_as_accepted_hint`
- `finetune_marked_ready_without_eval`
- `chat_router_ignores_gate_pack`
- `verification_gate_failed`

## Receipts

- sleep_report: `.aios/gate/founder/sleep_report.json`
- gate_pack: `.aios/gate/founder/gate_pack.json`
- loop_pairs: `.aios/gate/founder/loop_pairs.jsonl`
- watcher_result: `.aios/outbox/myworld/asc-0155.myworld.result.json`
- final_sleep_report:
  - gate_pack_id: `gatepack_843ecd92b888c664`
  - source_pair_count: `10`
  - accepted_memory_hint_count: `12`
  - finetune_ready: `false`

## Work Packets

### WP-0155-A — Build Gate sleep consolidation V1

- target_agent: codex
- target_repo: myworld
- status: done
- issued: 2026-05-14
- accepted: 2026-05-14
- closed: 2026-05-14
- depends_on: ASC-0154
- brief: |
    Extract prompt-Agent loop pairs from chat/Gate artifacts, overlay accepted
    MemoryOS hints, write a Gate pack with fine-tune held false, and make the
    chat router project that pack into new gate decisions.
- result: `.aios/outbox/myworld/asc-0155.myworld.result.json`
