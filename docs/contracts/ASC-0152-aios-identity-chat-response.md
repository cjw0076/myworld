---
contract_id: ASC-0152
slug: aios-identity-chat-response
status: closed
goal: Make the Control Center chat answer identity questions as AIOS before showing route receipts.
created: 2026-05-14 KST
accepted: 2026-05-14 KST by founder observation "너는 누구니" returned a routing receipt
closed: 2026-05-14 KST
acceptance_authority: founder
origin: The inline chat answered "너는 누구니" with a generic router receipt instead of explaining that AIOS is the control interface over Hive, MemoryOS, CapabilityOS, GenesisOS, and provider substrates.
---

# ASC-0152 AIOS Identity Chat Response

DNA references: Invariant 1 (decide before acting), Invariant 5 (provenance
chain), Invariant 8 (classify before committing).

## Scope

repos:

- `myworld`

allowed_files:

- `scripts/aios_chat_router.py`
- `tests/test_aios_chat_router.py`
- `docs/contracts/ASC-0152-aios-identity-chat-response.md`
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

- Identity-intent detection for Korean and English identity questions.
- A first-line answer that says the speaker is AIOS, not a single provider.
- A concise explanation that AIOS binds `myworld`, Hive Mind, MemoryOS,
  CapabilityOS, GenesisOS, and provider substrates.
- Existing route, MemoryOS, session status, stop-condition, and next-action
  receipts remain present after the identity answer.

## Verification Gate

```bash
cd /home/user/workspaces/jaewon/myworld
python -m py_compile scripts/aios_chat_router.py scripts/aios_chat.py scripts/aios_local_app.py
python -m unittest tests/test_aios_chat_router.py tests/test_aios_chat.py tests/test_aios_local_app.py
python scripts/aios_chat.py --message "너는 누구니" --conversation asc-0152-smoke --json
python -m unittest discover -s tests -p 'test_aios_*.py'
```

Pass criteria:

- Identity response starts with `나는 AIOS야.`
- Response names `myworld control plane`, Hive Mind, MemoryOS, CapabilityOS,
  GenesisOS, and provider substrates.
- Response does not start with the generic router receipt.
- Full MyWorld AIOS tests pass.

## Stop Conditions

- `identity_question_returns_receipt_first`
- `identity_response_claims_single_provider`
- `identity_response_hides_aios_roles`
- `chat_bypasses_aios_router`
- `verification_gate_failed`

## Receipts

- `scripts/aios_chat_router.py` adds identity-intent detection and a
  self-description branch before greeting/status/action fallbacks.
- `tests/test_aios_chat_router.py` proves `너는 누구니` starts with
  `나는 AIOS야.` and names the OS roles and provider substrate distinction.
- Focused tests passed 21/21.
- CLI smoke `asc-0152-smoke` returned identity-first text with MemoryOS trace
  `rtrace_d5b1cffc330672ea` and draft `chatdraft_e638877d7bfcd018`.
- Full MyWorld AIOS test suite passed 317/317.
- Watcher result:
  `.aios/outbox/myworld/asc-0152.myworld.result.json` passed.
- HTTP `/api/chat` smoke in `control-center` returned identity-first text with
  MemoryOS trace `rtrace_f45226be7871b062`.
- MemoryOS draft writeback: `mem_d6a6940e01e78aa8`.
