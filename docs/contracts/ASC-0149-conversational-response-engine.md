---
contract_id: ASC-0149
slug: conversational-response-engine
status: closed
goal: Replace the fixed AIOS chat receipt sentence with a conversational response engine that reflects user intent, route choice, MemoryOS context, session status, and next action.
created: 2026-05-14 KST
accepted: 2026-05-14 KST by founder GO "진행"
closed: 2026-05-14 KST
acceptance_authority: founder
origin: ASC-0148 opened the Control Center conversation surface, but the response still read like a fixed routing receipt instead of direct AIOS dialogue.
---

# ASC-0149 Conversational Response Engine

DNA references: Invariant 1 (decide before acting), Invariant 5 (provenance
chain), Invariant 8 (classify before committing).

## Scope

repos:

- `myworld`

allowed_files:

- `scripts/aios_chat_router.py`
- `tests/test_aios_chat_router.py`
- `docs/contracts/ASC-0149-conversational-response-engine.md`
- `docs/contracts/README.md`
- `docs/AGENT_WORKLOG.md`
- `docs/AIOS_AGENT_LEDGER.md`

forbidden_files:

- `hivemind/**`
- `memoryOS/**`
- `CapabilityOS/**`
- `GenesisOS/**`
- `.env`
- raw export paths
- provider auth files

## myworld.must_produce

- Intent-sensitive chat responses for greeting, status, and executable work
  messages.
- Responses that mention route/substrate, MemoryOS context status, session
  preparation status, stop conditions, and next action.
- Tests proving the old fixed sentence is no longer the response.
- HTTP fallback smoke proving the Control Center receives the improved response
  through `/api/chat`.

## Verification Gate

```bash
cd /home/user/workspaces/jaewon/myworld
python -m py_compile scripts/aios_chat_router.py scripts/aios_chat.py scripts/aios_local_app.py
python -m unittest tests/test_aios_chat_router.py tests/test_aios_chat.py tests/test_aios_local_app.py
python scripts/aios_chat.py --message "hey 안녕" --conversation asc-0149-smoke --json
python -m unittest discover -s tests -p 'test_aios_*.py'
```

Pass criteria:

- Greeting response includes Korean acknowledgement and AIOS connection.
- Multi-step response points to Hive orchestration and promotion to governed
  work.
- Response includes MemoryOS context and session preparation status.
- Full MyWorld AIOS tests pass.

## Stop Conditions

- `chat_response_fixed_receipt_only`
- `chat_response_missing_memory_context`
- `chat_response_missing_next_action`
- `chat_bypasses_aios_router`
- `verification_gate_failed`

## Receipts

- `scripts/aios_chat_router.py` now builds responses from intent, substrate,
  route reason, MemoryOS context, invocation status, stop conditions, and next
  action.
- `tests/test_aios_chat_router.py` proves greeting and multi-step responses are
  no longer the old fixed receipt sentence.
- CLI smoke `asc-0149-smoke` returned:
  `안녕. AIOS와 직접 대화하는 창구가 연결되어 있어.`
- HTTP fallback smoke `asc-0149-http-smoke` returned a next action to promote
  the conversation into a reviewed session envelope or contract.
- Focused tests passed 17/17.
- Full MyWorld AIOS test suite passed 313/313.
- Watcher result:
  `.aios/outbox/myworld/asc-0149.myworld.result.json` passed.
- MemoryOS draft writeback: `mem_3bb98d1e3b7a0d12`.
