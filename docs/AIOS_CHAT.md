# AIOS Chat

AIOS Chat is the L0 unified conversation surface for the control plane. It is
not a direct provider shell. Every turn passes through `scripts/aios_chat_router.py`
before any substrate can answer.

## Surfaces

CLI:

```bash
python scripts/aios_chat.py --message "summarize this short text" --conversation demo --json
python scripts/aios_chat.py --list --json
```

Global launcher:

```bash
bin/aios chat --message "continue AIOS interface work" --conversation founder --json
```

Web:

```bash
python scripts/aios_local_app.py up --json
```

Then open `http://127.0.0.1:8765/chat.html`.

## Mandatory Behavior

- Every turn first passes through the AIOS Gate/Chair decision layer. This is
  the explicit replacement for the hidden Codex/Claude operator judgment that
  decides whether to answer locally, ask for missing input, route to
  CapabilityOS, consult MemoryOS, invoke GenesisOS, or promote work to Hive.
- Substrate selection happens in the router first.
- `@claude`, `@codex`, `@local`, `@ollama`, and `@gemini` are operator
  overrides.
- Conversation history is append-only under `.aios/chat/<conversation>/`.
- Every turn writes `messages.jsonl`, `cost.json`, and `memory_drafts.json`.
- Every turn writes a `gate_decision` artifact so provider/chatbot execution is
  not a hidden direct answer path.
- MemoryOS context is requested when available and degrades without blocking.
- Memory questions such as "나에 대한 기억은?" must surface selected MemoryOS
  memory content, IDs, and provenance hints in the answer. Returning only
  `MemoryOS returned N context item(s)` is a routing receipt, not a useful chat
  answer.
- The main `response` is conversational text only. Route, MemoryOS, session,
  stop-condition, and next-step diagnostics are returned separately as
  `operating_receipt` and evidence artifacts so the chat does not read like a
  system log.
- Provider turns may execute only after the Gate decision. When execution is
  attempted, the router writes `.aios/chat/<conversation>/provider_turns.jsonl`
  and keeps provider output behind the same message, cost, memory-draft, and
  gate-decision receipts.
- Gate Chair synthesis is automatic when an active
  `.aios/gate/<user>/gate_pack.json` exists. `AIOS_GATE_AGENT_COMMAND` can
  provide an explicit command, local Ollama can act as the Chair runtime, and
  `AIOS_GATE_CHAIR_ENABLED=0` disables Chair synthesis even when a gate pack is
  active. Held Gate answers such as memory, failure-evidence, identity, and
  architecture questions may be rewritten by a provider-backed Chair using only
  the current Gate/MemoryOS evidence. These turns are written to
  `.aios/chat/<conversation>/gate_chair_turns.jsonl`. If no local Chair command
  or Ollama runtime is available, AIOS falls back to an internal deterministic
  `internal_evidence_synthesizer`; the Chair does not use Codex/Claude fallback
  by default.
- Runtime candidate selection can be made explicit with
  `.aios/gate/<user>/chair_runtime.json`:

```json
{
  "schema_version": "aios.gate.chair_runtime.v1",
  "status": "active",
  "mode": "internal_evidence_synthesizer"
}
```

Supported modes are `internal_evidence_synthesizer`, `ollama`, `claude`,
`codex`, and `gemini`. The file stores only the whitelisted runtime mode and an
optional non-secret model name; it does not store secrets, provider PINs,
arbitrary shell commands, or auth paths.
The Control Center may post to `POST /api/gate_chair_runtime` after explicit
confirmation. `internal_evidence_synthesizer` writes the active
`chair_runtime.json`. Provider-like modes (`ollama`, `claude`, `codex`,
`gemini`) write `.aios/gate/<user>/chair_candidate_runtime.json` by default so
normal chat cannot silently start calling a provider before eval. The endpoint
accepts only supported modes and an optional non-secret model name; it rejects
private markers and arbitrary shell commands. If a candidate command is missing,
the API returns `command_available=false` plus an `internal fallback expected`
marker. `scripts/aios_gate_chair_eval.py` can evaluate the candidate runtime
through an explicit override path without activating it.
`POST /api/gate_chair_promote` is the only Control Center activation path for a
provider-like candidate. It requires explicit confirmation and a Gate Chair eval
report with `promotion_ready=true`; otherwise the candidate remains quarantined.
- Chat responses include `gate_chair_status` so the UI can distinguish
  deterministic Gate fallback from successful Chair synthesis or missing local
  Chair runtime (`command_unavailable`).
- The web chat surfaces keep the main answer readable and render MemoryOS
  memory IDs, GenesisOS `genesis:<branch>` friction/need rows, provider-turn
  receipts, and artifact paths in a compact expandable `Trace` block. The
  primary chat bubble must read as a direct answer, not as an operating
  receipt.
- Evidence paths can be opened from the Control Center through the read-only
  `/api/artifact` endpoint. The endpoint only previews allowed relative
  control-plane paths and rejects traversal, absolute paths, `.env`, secrets,
  credentials, tokens, PINs, raw exports, and private history markers.
- Opened evidence artifacts are addressable through the browser hash
  `#artifact=<path>`, so a review can be restored from the same local URL
  without replaying the conversation turn.
- Evidence artifacts include authority/system-call labels so chat users can
  see whether AIOS is observing, ingesting, promoting, or closing a record.
- Web chat uses the local dashboard WebSocket `/chat` route.

## Gate Behavior

- Provider chatbots, Codex CLI, Claude CLI, Gemini, and local LLMs are
  provider substrates. They do not become AIOS by themselves.
- The Gate/Chair Agent decides the route before substrate use:
  `user -> AIOS Gate -> MemoryOS/CapabilityOS/GenesisOS/Hive -> provider`.
- GenesisOS branch artifacts are projected into chat Gate decisions as
  `genesis_friction`. For action-like turns, the deterministic answer and
  optional Chair prompt can surface the first discomfort/need pair before
  promoting work to Hive. GenesisOS remains speculative and does not select
  final truth or execute tools.
- Friction questions such as "불편함과 숨은 필요성을 찾아줘" are answered
  directly from `genesis_friction` without provider execution when GenesisOS
  branch evidence is available.
- When GenesisOS friction is present, `memory_drafts.json` includes an
  additional draft of type `genesis_friction_signal` so discomfort/need
  candidates can enter the MemoryOS review lifecycle instead of staying only
  in the chat transcript.
- The Control Center snapshot scans `.aios/chat/*/memory_drafts.json` and
  renders draft candidates in the Memory Drafts queue. This is review
  visibility only: the queue does not auto-accept or mutate MemoryOS records.
- The Memory Drafts queue can request MemoryOS review for one candidate. The
  request writes `.aios/memory_draft_reviews/<id>/request.json` and a
  MemoryOS-owned inbox packet at `.aios/inbox/memoryOS/<id>.memoryOS.json`;
  MemoryOS must still decide accept, reject, or needs_more_evidence.
- The child watcher recognizes `aios.memory_draft_review_request.v1` packets
  and writes a dispatch result without calling a provider. The Control Center
  then joins `.aios/state/memory_draft_reviews.jsonl` and
  `.aios/outbox/memoryOS/mdrev-*.result.json` back into the draft card, showing
  whether the request is queued or needs attention.
- Current factual questions such as weather, stock prices, exchange rates, or
  breaking news must not be answered by a cheap local turn. The Gate either
  asks for missing inputs, such as location, or requires a CapabilityOS
  current-info route with source evidence.
- Architecture questions about AIOS itself can be answered directly by the Gate
  while still recording MemoryOS, cost, and invocation receipts.
- Architecture questions about whether AIOS has a Gate/Chair Agent must also
  disclose the current Chair runtime class. If `AIOS_GATE_AGENT_COMMAND` or
  local Ollama is not available, the honest answer is that the Gate exists but
  the Chair is currently the deterministic `internal_evidence_synthesizer`, not
  a provider-grade conversational model.
- A connected Gate is not the same thing as a provider-grade conversational
  Chair. Until a non-internal Chair runtime passes the Gate Chair eval, AIOS
  should describe itself as `Gate + deterministic evidence synthesizer` and
  keep provider/runtime details inside `Trace`, not in the main answer.
- Memory questions are answered by the Gate using MemoryOS-selected memories
  before any provider fallback. Founder/user-intent memories are ranked ahead
  of generic closeout receipts for these answers.
- Failure/blocker questions are answered by the Gate using MemoryOS
  `negative_evidence` when available. Provider failures, rejected ingests,
  privacy holds, stale memories, and bad-tool memories must be surfaced as
  route evidence rather than hidden behind generic context counts.
- CapabilityOS provider recommendations are filtered through MemoryOS negative
  evidence before substrate selection. If accepted or projected failure
  evidence names a bad provider/tool, the Gate records
  `capability_route_audit` and skips that candidate when another CapabilityOS
  candidate is available.
- If MemoryOS returns relevant context but no accepted failure memory, the Gate
  may project recent local AIOS failure receipts as
  `negative_evidence_source=aios_receipts`. This is a fallback route signal,
  not an accepted MemoryOS memory, and should be reviewed before promotion.
- Local chat provider execution uses `AIOS_LOCAL_AGENT_COMMAND` when set. If no
  local command or Ollama command is available, the router can try
  `AIOS_CHAT_FALLBACK_PROVIDERS` in order, defaulting to
  `codex,claude,gemini`, and records degraded provider metadata instead of
  hiding the failure.

## Sleep Consolidation

AIOS Gate personalization starts with consolidation, not fine-tuning.

```bash
python scripts/aios_gate_sleep.py --json
```

The sleep loop reads append-only chat/Gate artifacts and accepted MemoryOS
hints, then writes:

- `.aios/gate/founder/loop_pairs.jsonl`
- `.aios/gate/founder/gate_pack.json`
- `.aios/gate/founder/sleep_report.json`

The active Gate pack is projected into later `aios.chat.gate_decision.v1`
artifacts. It is a few-shot/policy pack only. `finetune_ready` remains `false`
until a separate eval, rollback, privacy, and dataset-quality contract exists.

## Gate Chair Eval

Gate connection is not the same as Gate quality. Use the eval loop before
promoting a provider/local model to Chair authority:

```bash
python scripts/aios_gate_chair_eval.py --json
python scripts/aios_gate_chair_eval.py --mode internal --json
python scripts/aios_gate_chair_eval.py --mode current --prompt "나에 대한 기억은?" --json
```

The eval writes `.aios/evals/gate_chair/<eval_id>/report.json`. In `both`
mode it runs the deterministic internal Chair baseline with
`AIOS_GATE_CHAIR_FORCE_INTERNAL=1` and compares it to the currently configured
Chair runtime. The report records answer previews, `gate_chair_status`, basic
quality checks, scores, a verdict, and `promotion_ready`. A connected provider
should not be treated as better unless it is a non-internal Chair runtime and
beats the internal baseline while preserving evidence discipline. A
`1.0 / 1.0` tie with `current_runtime_external=false` means the current runtime
is still the deterministic internal Chair, not a provider-grade upgrade.

The Control Center exposes the same loop through `POST /api/gate_chair_eval`
and the Runtime band `Eval Chair` action. This keeps Chair quality visible to
end users instead of burying it in CLI logs.

## Boundary

The chat surface is not a raw provider shell. Provider calls remain attachable
only behind the router so cost, history, override, gate decision, provider-turn
receipt, and memory draft evidence cannot be skipped. Secrets, PINs, raw
private exports, and provider auth files must not be copied into chat
artifacts.
