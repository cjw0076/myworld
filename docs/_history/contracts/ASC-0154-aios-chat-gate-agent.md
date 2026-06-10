---
contract_id: ASC-0154
slug: aios-chat-gate-agent
status: closed
goal: Add an explicit AIOS Gate/Chair Agent layer to chat so provider chatbots and CLIs are routed as substrates, while current-info questions are held for CapabilityOS/source-aware routing instead of answered by cheap local turns.
created: 2026-05-14T03:37:10+09:00
accepted: 2026-05-14T03:37:10+09:00
closed: 2026-05-14T03:38:56+09:00
---

# ASC-0154 AIOS Chat Gate Agent

## Why

The founder observed that Control Center chat is routed systemically, but the
missing layer is the intelligent Gate role that Codex currently performs in
this conversation: decide whether to answer, use AIOS, ask for missing input,
route to MemoryOS/CapabilityOS/GenesisOS/Hive, or delegate to a provider
substrate.

The failure example was `오늘 날씨는 ?`: the old chat response treated this as a
lightweight local turn. A Gate must classify it as current information and not
let a local LLM guess without location/source evidence.

## Scope

- repos: `myworld`
- allowed_files:
  - `scripts/aios_chat_router.py`
  - `scripts/aios_chat.py`
  - `scripts/aios_local_app.py`
  - `tests/test_aios_chat_router.py`
  - `tests/test_aios_chat.py`
  - `tests/test_aios_local_app.py`
  - `docs/AIOS_CHAT.md`
  - `docs/contracts/ASC-0154-aios-chat-gate-agent.md`
  - `docs/contracts/README.md`
  - `docs/AGENT_WORKLOG.md`
  - `docs/AIOS_AGENT_LEDGER.md`
- forbidden_files:
  - provider credentials, PINs, `.env`
  - raw private chat/provider logs
  - child repo implementation files

## Responsibilities

### myworld.must_produce

- `aios.chat.gate_decision.v1` artifact per chat turn.
- Explicit Gate decisions:
  - `route_normally`
  - `clarify_location`
  - `require_current_info_route`
  - `answer_architecture`
- Weather/current-info questions must not flow as cheap local answers when
  required inputs or source adapters are missing.
- Provider chatbot/CLI architecture questions must explain that providers are
  substrates behind `user -> AIOS Gate -> OS routing -> provider substrate`.

### capabilityos.must_produce

- Advisory route names only in this contract:
  - `cap_web_research_route`
  - `weather_or_current_info_adapter`
- No direct external tool execution is added here.

### memoryos.must_produce

- Existing chat memory draft and context-pack behavior remains intact.
- Gate decisions are referenced as chat artifacts; they are not auto-accepted
  memories.

### genesisos.must_produce

- No direct execution. The Gate preserves GenesisOS as the divergence layer for
  future high-level or ambiguous work.

### hive_mind.must_produce

- No child Hive implementation in this contract. Multi-step work still routes
  to `hive_flow` through the existing chat router.

## Verification Gate

```bash
python -m py_compile scripts/aios_chat_router.py scripts/aios_chat.py scripts/aios_local_app.py
python -m unittest tests/test_aios_chat_router.py tests/test_aios_chat.py tests/test_aios_local_app.py
python scripts/aios_chat.py --message "오늘 날씨는 ?" --conversation asc-0154-weather-smoke --json
python scripts/aios_chat.py --message "provided chatbot들도 AIOS에 연결할 수 있나? codex(CLI)의 역할을 대신하는 gate 역할의 Agent가 붙어있어야해." --conversation asc-0154-gate-smoke --json
python -m unittest discover -s tests -p 'test_aios_*.py'
```

Pass criteria:

- Weather smoke returns `chosen_substrate=gate_clarification`,
  `route_reason=gate_requires_input`, and a `gate_decision` artifact with
  `missing_inputs=["location"]`.
- Provider chatbot smoke returns `chosen_substrate=aios_gate`,
  `route_reason=gate_answer`, and explains the Gate/Chair Agent architecture.
- Existing chat persistence, cost, MemoryOS context, and invocation receipts
  still exist.

## Stop Conditions

- `gate_decision_missing`
- `weather_question_answered_by_local_llm`
- `provider_substrate_replaces_aios`
- `current_info_without_source_route`
- `memory_draft_or_cost_missing`
- `verification_gate_failed`

## Receipts

- weather_smoke: `.aios/chat/asc-0154-weather-smoke-2/gate_decisions/*.json`
- architecture_smoke: `.aios/chat/asc-0154-gate-smoke-2/gate_decisions/*.json`
- watcher_result: `.aios/outbox/myworld/asc-0154.myworld.result.json`

## Work Packets

### WP-0154-A — Add Gate/Chair Agent to AIOS chat

- target_agent: codex
- target_repo: myworld
- status: done
- issued: 2026-05-14
- accepted: 2026-05-14
- closed: 2026-05-14
- depends_on: ASC-0112
- brief: |
    Add an explicit Gate/Chair Agent decision artifact to each chat turn. Make
    current-info/weather questions hold for missing location or source-aware
    route instead of using a cheap local answer. Make provider chatbot/CLI
    architecture questions explain providers as AIOS substrates behind the
    Gate.
- result: `.aios/outbox/myworld/asc-0154.myworld.result.json`
