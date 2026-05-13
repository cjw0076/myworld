---
contract_id: ASC-0112
slug: aios-chat-wrapper
status: accepted
goal: Build aios_chat as the persistent unified chat surface (CLI + Web) wrapping all substrates (Claude Code, Codex CLI, Ollama, future chatbot/web/mobile providers) with 5 mandatory capabilities so AIOS becomes the single entry point users actually live in — not a tool layer behind direct CLI use.
created: 2026-05-13 KST
accepted: 2026-05-13 KST by claude as verifier (founder explicit GO "5가지 모두 다 진행시켜야")
acceptance_authority: claude@myworld (verifier role) per founder direct delegation 2026-05-13 KST.
origin: founder turn diagnosing AIOS=tool-layer-behind-CLIs as undifferentiated. Vision: ONE interface, AIOS routes substrate behind. Layer 0 of 3-layer "living organism" arc.
---

# ASC-0112 AIOS Chat Wrapper (L0 of organism arc)

DNA references: Invariant 1 (decide before acting), Invariant 5 (provenance),
Invariant 6 (operator override), Invariant 7 (private data never sent),
Invariant 8 (classify before committing).

## Why Now

Verified 2026-05-13: AIOS has 5 surfaces (dashboard, Goal Bar, ask CLI,
hive ask, hive flow) — none persistent dialogue. Founder still uses Claude
Code CLI directly = AIOS adds no surface value yet.

Founder vision: ONE entry point that wraps Claude/Codex/Ollama/future. AIOS
chats. AIOS routes. User sees one conversation thread.

5 mandatory capabilities (per founder turn):
1. Substrate auto-select (this question → ollama; that one → claude)
2. Context persistence (history survives session via memoryOS)
3. Multi-step orchestration (complex task → Hive flow chains substrates)
4. Friction reduction (no CLI memorization)
5. Cost optimization (free local first, paid only when necessary)

## Required Reading

- `scripts/aios_invoke.py` (4-OS routing surface)
- `hivemind/hivemind/hive.py` ask + flow + provider_loop
- `apps/control/live.js` (existing WebSocket client)
- `scripts/aios_dashboard_ws.py` (existing WS server)
- `docs/contracts/ASC-0066-provider-backpressure-role-distillation.md`
- `docs/AIOS_DNA.md` (after ASC-0105) — Invariants this wrapper must respect

## Scope

repos: `myworld`, `hivemind`

allowed_files:

- `scripts/aios_chat.py` (CLI REPL)
- `scripts/aios_chat_router.py` (substrate selection backend)
- `apps/control/chat.html` (Web chat surface)
- `apps/control/chat.js`
- `apps/control/styles.css` (chat additions)
- `scripts/aios_dashboard_ws.py` (extend with /chat endpoint)
- `tests/test_aios_chat.py`
- `tests/test_aios_chat_router.py`
- `hivemind/hivemind/provider_loop.py` (extend if router needs new entry)
- `hivemind/tests/test_provider_loop.py`
- `docs/AIOS_CHAT.md`
- `docs/contracts/ASC-0112-aios-chat-wrapper.md`
- `docs/AIOS_AGENT_LEDGER.md`

forbidden_files:

- `memoryOS/**`, `CapabilityOS/**`, `GenesisOS/**`, `uri/**`
- `_from_desktop/**`, `dain/**`, `minyoung/**`
- `.env`

## Per-OS Responsibility

### myworld.must_produce

`scripts/aios_chat_router.py`:
- input: user message + conversation_id
- step 1 (substrate auto-select, capability #1):
  - call `aios_invoke --plan-only` → 4-OS plan
  - choose substrate from CapabilityOS top recommendation: ollama_qwen → claude → codex → gemini per cost-tier (capability #5)
  - operator override: user can prefix message with `@claude`/`@codex`/`@local` to force
- step 2 (context persistence, capability #2):
  - load conversation_id history from `.aios/chat/<id>/messages.jsonl`
  - load relevant memoryOS context (`memoryos context build`)
  - inject as system prompt prefix
- step 3 (multi-step, capability #3):
  - if Hive plan classifies as multi-step → use `hive flow` execution
  - else single substrate call
- step 4 (friction reduction, capability #4):
  - intent classifier maps NL queries to right CLI behind scenes
  - never expose ASC-IDs / dispatch packets in user reply unless asked
- step 5 (cost tracking):
  - record token cost per turn in `.aios/chat/<id>/cost.json`
  - warn if turn would exceed threshold

`scripts/aios_chat.py` — CLI REPL:
- `aios chat` opens REPL
- `aios chat --resume <id>` resumes prior conversation
- `aios chat --list` shows past conversations

`apps/control/chat.html` — Web surface:
- chat pane added next to existing dashboard
- WebSocket reuses `aios_dashboard_ws.py` with new `/chat` route
- mobile-responsive (uses existing styles)

### hivemind.must_produce

- `provider_loop.py` extended with `chat_turn` mode if not already
  supported — accepts conversation history, returns single substrate
  response with metadata `{substrate, role, tokens_in, tokens_out}`

### child repos: no other change

## Verification Gate

```bash
python -m py_compile scripts/aios_chat.py scripts/aios_chat_router.py
python -m unittest tests/test_aios_chat.py tests/test_aios_chat_router.py
# Substrate auto-select test
python scripts/aios_chat_router.py --message "summarize this short text" --json | python -c "
import json, sys; d=json.load(sys.stdin)
assert d.get('chosen_substrate') in ['ollama_qwen','local_llm'], f'cheap task should route local, got {d.get(\"chosen_substrate\")}'
"
# Cost tracking test
python scripts/aios_chat.py --message "test" --conversation cli-test --json
test -f .aios/chat/cli-test/messages.jsonl
test -f .aios/chat/cli-test/cost.json
# Web surface
python scripts/aios_local_app.py up --json
sleep 2
# manual: visit http://localhost:8088/chat.html, send message
python scripts/aios_local_app.py stop
python -m unittest discover -s tests -p 'test_aios_*.py'
```

Pass criteria (DNA-cited):

- All 5 capabilities present in router (Inv 1: decide before acting → router decides substrate consciously, not random)
- Cost record exists (Inv 5: provenance — every turn traceable to substrate + cost)
- @substrate override works (Inv 6: operator override always possible)
- Private founder paths never appear in chat history dump (Inv 7)
- Reversibility recorded — chat clearable without breaking memoryOS (Inv 8)

## Stop Conditions

- `chat_bypasses_substrate_select`: never call substrate without router
- `chat_persists_to_chat_only`: messages must also flow to memoryOS as drafts
- `chat_exposes_internal_jargon`: ASC-IDs / dispatch packets hidden by default
- `chat_silent_cost`: every turn must record cost
- `chat_loses_history_on_restart`: conversation_id must be replayable
- `child_repo_scope_leak`
- `verification_gate_failed`

## Receipts

Pending.

## Work Packets

### WP-0112-A — codex@myworld + codex@hivemind build router + REPL + web

- target_agent: codex
- depends_on: ASC-0064 (live dashboard) ✓, ASC-0066 backpressure ✓
- brief: implement chat_router (substrate-select + persistence + flow +
  cost), CLI REPL, web chat pane. Provider_loop chat_turn mode.
  Tests cover all 5 capabilities. Dogfood: 3-turn conversation through
  ollama → 1 turn through claude (override) → resume after restart.
