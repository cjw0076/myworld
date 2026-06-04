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
- The Control Center now treats chat as the default end-user surface: Simple
  mode opens with `Talk to AIOS` before the operator bands, and the inline
  composer sends on `Enter` with `Shift+Enter` reserved for newlines.
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
- `chat.html` can still send through `POST /api/chat` when the WebSocket is
  unavailable or reconnecting. This keeps the direct chat surface usable over
  SSH/Tailscale/browser environments where WebSocket transport may be flaky.

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
- When the user explicitly asks for friction/need or sends an action-like turn
  with GenesisOS friction available, chat also writes
  `.aios/chat/<conversation>/friction_contract_seed.md`. The seed is
  `status: proposed`, `authority: speculative_only`, and is not execution
  authority. It exists to bridge a conversation into a reviewable ASC contract
  candidate without letting GenesisOS execute work or pick final truth.
- The web chat Trace can promote that seed through
  `POST /api/promote_friction_seed` after an explicit reviewed-seed
  confirmation. Promotion only copies the seed into `.aios/promotions/<id>/`
  with a receipt; it does not assign an ASC id, accept a contract, dispatch a
  packet, or start executor work.
- The Control Center promotion queue can then materialize the reviewed seed
  through `POST /api/materialize_promotion_contract` after the operator enters
  an `ASC-NNNN` id. This creates a `docs/contracts/*.md` file with
  `status: proposed` only; acceptance and dispatch remain separate operator
  gates.
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
- When MemoryOS returns `needs_more_evidence`, the Control Center must show the
  draft as still unaccepted and surface a concrete next-evidence hint such as
  a corroborating artifact, operator review note, or repeated future turns.
  This keeps failed or weak memory candidates useful without pretending they
  are accepted MemoryOS knowledge.
- A `needs_more_evidence` draft can record corroborating evidence through
  `POST /api/memory_review_evidence`. The endpoint writes
  `.aios/memory_review_evidence/<id>/evidence.json` and appends
  `.aios/state/memory_review_evidence.jsonl`; it does not accept the memory or
  rerun MemoryOS review automatically.
- Once a `needs_more_evidence` draft has supplemental evidence, the Control
  Center shows `Request Re-review`. This uses the existing
  `POST /api/memory_draft_review` path again, but the packet now carries
  `supplemental_evidence` plus the evidence receipt/artifact refs in
  `draft.raw_refs`. MemoryOS still owns the accept/reject/needs-more-evidence
  decision; the re-review button is not an auto-accept path.
- The chat Gate also projects recent MemoryOS review gaps from
  `.aios/outbox/memoryOS/mdrev-*.result.json` into memory/friction/action
  turns. If a similar draft is still `needs_more_evidence`, the answer must
  say that the draft is not durable memory yet and ask for stronger evidence
  before promotion.
- Standalone chat loads the current Control Center snapshot and renders the
  latest `offline_user` packet. These packets come from the ASC-0210
  offline-user-agent primitive and are still draft-first MemoryOS inbox
  records. If the source packet has already been consumed by a MemoryOS review
  import, chat falls back to the linked `.aios/chat/offline-user/memory_drafts.json`
  draft so the offline-user panel stays visible with the review result. Chat
  may request MemoryOS review for a linked draft or help prepare a bounded
  reply, but it must keep raw private data, credentials, screenshots, and
  provider logs outside the shared packet.
- If MemoryOS returns `needs_more_evidence`, the standalone chat offline-user
  panel shows the evidence count, an `Add Evidence` form backed by
  `POST /api/memory_review_evidence`, and `Request Re-review` when
  supplemental evidence exists. Re-review packets preserve evidence refs in
  `supplemental_evidence` and draft `raw_refs`; MemoryOS still decides the
  review outcome.
- A returned `field_observation` can be created with
  `scripts/aios_offline_user_agent.py new-field-observation`. By default it
  also writes `.aios/chat/offline-user/memory_drafts.json`, making the
  observation visible in the same Memory Draft Queue as chat/Genesis signals
  before any MemoryOS acceptance.
- Current factual questions such as weather, stock prices, exchange rates, or
  breaking news must not be answered by a cheap local turn. The Gate either
  asks for missing inputs, such as location, or requires a CapabilityOS
  current-info route with source evidence.
- Bare time words such as `지금` or `current` are not enough to trigger the
  current-info hold. AIOS self-diagnosis, discomfort/need, and operating-state
  questions must stay conversational unless they ask for external facts such as
  weather, market prices, exchange rates, releases, versions, or news.
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
- Gate Chair eval failures are also projected as local negative evidence.
  Recent `.aios/evals/gate_chair/*/report.json` statuses such as
  `gate_chair_timeout` can demote a provider Chair candidate without accepting
  that failure as a permanent MemoryOS record.
- Active provider Chair runtimes are also protected by the same negative
  evidence. If the active runtime mode accumulates repeated recent
  `gate_chair_timeout`, `provider_access_denied`, `provider_backpressure`,
  `pin_required_noninteractive`, `empty_output`, or execution-failure evidence
  in Gate Chair eval/chat receipts, the effective runtime falls back to
  `internal_evidence_synthesizer` until a later eval proves recovery. Candidate
  eval overrides are not demoted while being tested; only normal active chat is
  shielded from a known-bad runtime.
- Demotion recovery is evidence-based. A newer Gate Chair eval report must show
  `promotion_ready=true`, the same active runtime mode/model, no failed current
  runs, and `scores.current > scores.internal`. Older failure receipts remain
  on disk, but the newer recovery proof clears their effect on normal chat.
- Live Gate Chair chat failures are projected the same way from recent
  `.aios/chat/*/gate_chair_turns.jsonl` rows. This keeps ordinary UI/runtime
  failures visible to the next provider route even before a formal eval report
  or MemoryOS acceptance pass exists.
- When a chat turn uses negative evidence, the router also writes a
  `negative_evidence_signal` memory draft. This is still draft-first: the
  evidence can guide the next route immediately, but it must pass MemoryOS
  review before becoming accepted memory.
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
python scripts/aios_gate_chair_eval.py --mode current --request-memory-review --json
python scripts/aios_gate_chair_eval.py --candidate-matrix --candidate claude --candidate codex --request-memory-review --json
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

When the eval observes a failed Gate Chair run, it also writes a draft
`negative_evidence_signal` at
`.aios/chat/gate-chair-eval-<eval_id>-failures/memory_drafts.json`. The draft
uses the same Memory Drafts queue as normal chat turns, so MemoryOS can review
provider/runtime failure evidence without waiting for a user to ask a failure
question first. Add `--request-memory-review` when the eval should also write
the corresponding MemoryOS inbox packet; the MemoryOS child watcher still owns
the actual review/import step.

Use `--candidate-matrix` to compare provider Chair candidates without
activating them. The matrix temporarily writes
`.aios/gate/founder/chair_candidate_runtime.json` for each candidate, evaluates
it as the current Chair, restores the prior candidate config, and writes
`.aios/evals/gate_chair_matrix/<matrix_id>/report.json`. A candidate is
promotion-eligible only when it is a non-internal runtime, has no failed Chair
runs, and beats the deterministic baseline score.

The Control Center exposes the same loop through `POST /api/gate_chair_eval`
and the Runtime band `Eval Chair` action. This keeps Chair quality visible to
end users instead of burying it in CLI logs.

## Boundary

The chat surface is not a raw provider shell. Provider calls remain attachable
only behind the router so cost, history, override, gate decision, provider-turn
receipt, and memory draft evidence cannot be skipped. Secrets, PINs, raw
private exports, and provider auth files must not be copied into chat
artifacts.
