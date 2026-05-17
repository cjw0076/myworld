---
contract_id: ASC-0148
slug: inline-aios-conversation-surface
status: closed
goal: Add a direct AIOS conversation window to the Control Center so end users can talk with AIOS without leaving the main operating interface.
created: 2026-05-14 KST
accepted: 2026-05-14 KST by founder directive "소통 창구는 있어야하지 않나 ?"
closed: 2026-05-14 KST
acceptance_authority: founder
origin: ASC-0112 created a separate chat page, but the Control Center still lacked an always-visible communication surface.
---

# ASC-0148 Inline AIOS Conversation Surface

DNA references: Invariant 1 (decide before acting), Invariant 5 (provenance
chain), Invariant 7 (private-gated data stays out of prompt artifacts),
Invariant 8 (classify before committing).

## Scope

repos:

- `myworld`

allowed_files:

- `apps/control/index.html`
- `apps/control/app.js`
- `apps/control/styles.css`
- `tests/test_aios_chat.py`
- `docs/contracts/ASC-0148-inline-aios-conversation-surface.md`
- `docs/contracts/README.md`
- `docs/AIOS_CONTROL_APP.md`
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

- Inline `Conversation` panel inside `apps/control/index.html`.
- Browser JS that connects to existing `ws://.../chat` and sends chat turns
  through `aios_dashboard_ws.py`.
- Chat response rendering that shows response text, chosen substrate, route
  reason, MemoryOS draft id, cost, and artifact refs.
- Tests proving the main Control Center references the inline chat form and the
  existing `/chat` route.

## Verification Gate

```bash
cd /home/user/workspaces/jaewon/myworld
python -m py_compile scripts/aios_chat.py scripts/aios_chat_router.py scripts/aios_dashboard_ws.py
python -m unittest tests/test_aios_chat.py tests/test_aios_chat_router.py tests/test_aios_control_snapshot.py tests/test_aios_local_app.py
python scripts/aios_control_snapshot.py --check-app-js apps/control/app.js --json
python scripts/aios_chat.py --message "ASC-0148 inline chat smoke" --conversation asc-0148-smoke --json
python -m unittest discover -s tests -p 'test_aios_*.py'
```

Pass criteria:

- Control Center has `inline-chat-form` and `inline-chat-thread`.
- Inline chat JS connects to `/chat`, not a direct provider.
- Chat smoke writes persisted `.aios/chat/<conversation>/` artifacts.
- WebSocket `/chat` smoke returns `chat_response`.
- Full MyWorld AIOS tests pass.

## Stop Conditions

- `chat_bypasses_aios_router`
- `chat_not_visible_in_control_center`
- `chat_response_missing_receipts`
- `chat_private_artifact_leak`
- `verification_gate_failed`

## Receipts

- `apps/control/index.html` now includes `Conversation / Talk to AIOS`.
- `apps/control/app.js` connects inline chat to `/chat`, renders response
  metadata, MemoryOS draft ids, cost, and artifact refs.
- `apps/control/app.js` now falls back to `POST /api/chat` when the separate
  `8766` WebSocket is unavailable through SSH/Tailscale forwarding.
- `scripts/aios_local_app.py` now exposes `POST /api/chat` on the same
  `8765` HTTP server and routes through `scripts/aios_chat.py`, not a direct
  provider.
- `apps/control/styles.css` adds the inline conversation panel.
- CLI chat smoke:
  `.aios/chat/control-center-smoke/messages.jsonl`,
  `.aios/chat/control-center-smoke/memory_drafts.json`, and
  `.aios/chat/control-center-smoke/cost.json`.
- WebSocket smoke returned `chat_ready` then `chat_response` with
  `ok=true`, substrate `ollama_qwen`, and MemoryOS draft
  `chatdraft_1875a2b97d46c242`.
- HTTP fallback smoke returned `ok=true`, substrate `ollama_qwen`, and
  MemoryOS draft `chatdraft_9fb3c1477cde39c4`.
- Visual verification:
  `.aios/screenshots/aios-control-inline-chat.png`.
- Focused tests passed 18/18.
- Full MyWorld AIOS test suite passed 311/311.
- Watcher result:
  `.aios/outbox/myworld/asc-0148.myworld.result.json` passed.
- MemoryOS draft writeback: `mem_0a408f327f03cb34`.
