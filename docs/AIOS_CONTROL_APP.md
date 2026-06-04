# AIOS Control App

The control app is the first local visualization surface for myworld. It can
open from a generated static snapshot, and `aios_local_app.py up` also starts a
local WebSocket stream so the dashboard can follow AIOS primitive events live.

Refresh the snapshot:

```bash
python scripts/aios_control_snapshot.py \
  --write-json apps/control/aios-control-snapshot.json \
  --write-js apps/control/aios-control-data.js \
  --json
```

Open:

```text
apps/control/index.html
```

Run as a local app:

```bash
python scripts/aios_local_app.py up --json
python scripts/aios_local_app.py status --json --assert-live
python scripts/aios_local_app.py stop --json
```

Default URL:

```text
http://127.0.0.1:8765/
ws://127.0.0.1:8766/events
```

Visual verification:

```bash
python scripts/aios_visual_verify.py http://127.0.0.1:8765/ --allow-degraded --json
python scripts/aios_visual_verify.py http://127.0.0.1:8765/chat.html --allow-degraded --json
```

The visual verifier first checks that the page returns meaningful HTML, then
attempts a bounded headless browser screenshot. It always writes an
`aios.visual_verification.v1` receipt under `.aios/visual_verification/`. If
Firefox or another browser hangs, the command records that attempt and tries
the configured fallbacks. By default it checks Chromium/Chrome on PATH and the
cached Playwright Chromium headless shell under `~/.cache/ms-playwright`.
Use `--no-browser-fallback` to force a single browser, or repeat
`--fallback-browser <name-or-path>` to override the fallback chain. If every
attempt fails, the receipt records `browser_fallback_exhausted` instead of
leaving the operator turn stuck. Use `--require-screenshot` for contracts where
missing screenshot evidence must fail the gate.
Successful browser commands that produce suspiciously tiny screenshots are
treated as degraded visual evidence, not as a pass. The default threshold is
12 KB and can be adjusted with `--min-screenshot-bytes`. This guards against
blank hash/deep-link captures that still write a PNG file.
For section-level checks, prefer `?mode=operator&visual_focus=<section-id>`
over hash-only URLs. The Control Center clones the requested safe section into
the first viewport as a visual verification harness, which avoids browser hash
scroll timing when capturing operator-only panels.

Visual design workflow:

- For significant Control Center UI changes, generate or collect a visual
  reference first, then verify the implemented page with screenshots before
  closeout.
- The current control-surface reference board is recorded at
  `.aios/screenshots/aios-control-center-reference-board-v4.png` and summarized
  in `docs/design/AIOS_CONTROL_CENTER_REFERENCE_BOARD.md`.
- The active target is provider-grade utility: chat-first Gate, visible OS
  routes, compact evidence, receipts/provenance, and mobile one-column reading
  order. The UI should not hide AIOS behavior behind raw logs or decorative
  dashboard cards.

End-user intake:

- Open `http://127.0.0.1:8765/`.
- Use `Conversation / Talk to AIOS` for direct ongoing dialogue with the
  system. The panel uses the same `/chat` router as `chat.html`, so messages
  are persisted under `.aios/chat/<conversation>/` with route, cost, artifact,
  and MemoryOS draft receipts.
- The Control Center opens in `Simple` mode by default. In that mode the chat
  panel is the first work surface and operator-only bands are hidden until the
  user switches to `Operator`.
- Operator surfaces can be deep-linked with `?mode=operator`, for example
  `http://127.0.0.1:8765/?mode=operator#memory-library`. Hash scrolling is
  replayed after mode selection so hidden operator sections can be verified
  directly.
- The current visual shell uses a dark, dense console style so the first
  viewport reads as `Chat/Gate + Evidence Desk`, while MemoryOS,
  CapabilityOS, GenesisOS, Hive, and MyWorld remain reachable as visual
  operating boards below.
- The Control Center includes a `Reference / Build / Verify` visual evidence
  strip backed by `GET /api/visual_workflow`. It reuses the same screenshot and
  receipt evidence shown in `chat.html`, so UI work can be reviewed in the app
  without manually opening `.aios/screenshots` or visual verification receipts.
  When the latest visual verification receipt points to a screenshot, that
  screenshot is used as the `Build` image so the strip reflects the latest
  verified UI surface rather than an older matching filename.
- If the latest visual verification receipt is `degraded` or `failed`, the
  response includes a `visual_fix_work_item`. The Control Center renders this
  as a `Visual Fix` row in the Evidence Desk; clicking it prepares an AIOS chat
  prompt with receipt path, screenshot path, stop conditions, expected fix
  scope, verification command, and stop conditions.
- The same `Visual Fix` row also exposes a guarded `Promote Fix` action. After
  the user ticks `reviewed`, the browser posts to `POST /api/promote_visual_fix`.
  The server accepts only safe `.aios/visual_verification/*/receipt.json`
  receipts whose status is `degraded` or `failed`, writes a
  `proposed_contract_seed` promotion under `.aios/promotions/`, and keeps
  `execution_started=false`.
- Promotion cards display the next available ASC id from the current
  `docs/contracts/ASC-*.md` set. The materialization input is prefilled with
  that id, and long `next_action` values are visually truncated with a tooltip
  instead of breaking the card layout.
- The chat-first surface now includes a first-screen `Next If Idle` strip. It
  predicts the next owner/action from monitor next-actions, open contracts,
  latest asks, and dispatch state, then offers `Explain` and `Govern` actions.
  These actions route back through chat or governed ask creation; they do not
  execute hidden child-repo work. This is the first implementation of the
  ASC-0200 GenesisOS discomfort `reactive_passivity`.
- The Evidence Desk includes a `Live OS Route` rail. It compresses the current
  Gate, MemoryOS, CapabilityOS, GenesisOS, Hive, and Proof state into a
  first-screen route trace so users can see that a conversation is being
  handled systemically, not by a hidden chatbot response alone.
- The Evidence Desk also includes a `Live AIOS operating loop` mini-map. It
  places Hive Mind at the center and renders MemoryOS, CapabilityOS,
  GenesisOS, and MyWorld around it with current status/detail chips. This is
  the first Control Center step toward showing AIOS as an operating system
  instead of a list of logs.
- The lower MemoryOS, CapabilityOS, and GenesisOS boards now begin with
  end-user product summaries instead of raw diagnostics:
  - MemoryOS shows what AIOS can remember, review debt, retrieval trace count,
    graph edges, and actions to ask MemoryOS what is trusted or missing.
  - CapabilityOS shows tool cards, observations, known gaps, permission
    questions, and actions to route a task or ask the user for only the needed
    permission.
  - GenesisOS shows how discomfort becomes a need and then a speculative
    contract seed, with actions to feel friction or generate alternate
    worldlines.
  These product-board actions call `POST /api/ask` with `draft_contract=true`,
  so a deliberate click creates a governed ask receipt and contract seed
  instead of only filling a chat prompt.
- The snapshot now exposes recent governed asks under `asks.latest`. The
  first-screen Evidence Desk renders the newest item as a top-pinned
  `Governed Ask` with goal text, role statuses, next action, and artifact
  controls for the contract seed, instruction, praxis, and receipt.
- The snapshot also exposes `offline_user.latest` from valid
  `aios.offline_user_agent_packet.v1` packets in `.aios/inbox/memoryOS/` and
  from `.aios/chat/offline-user/memory_drafts.json` if the source packet has
  already been consumed by MemoryOS review import. The Evidence Desk renders
  the newest item as `Offline User Agent`, showing the packet type, contract
  id, next action, privacy boundary or next question, and controls to open the
  packet/draft, request MemoryOS review when a linked draft exists, or prepare
  a bounded observation prompt. This makes `user@offline` visible as a
  governed sense organ, not an ad hoc chat ask.
- A governed ask can now be materialized from the Evidence Desk through
  `POST /api/materialize_ask_contract`. The server only accepts safe
  `.aios/asks/*/receipt.json` receipts, requires confirmation, writes a
  `status: proposed` contract under `docs/contracts/ASC-*.md`, records
  `.aios/asks/<ask_id>/materialization.json`, and keeps
  `execution_started=false`. Once materialized, the top-pinned card shows the
  proposed contract artifact directly.
- Above that rail, the Evidence Desk includes a compact `Decision Map` that
  summarizes the active Chair runtime, MemoryOS retrieval evidence,
  CapabilityOS route evidence, GenesisOS worldline evidence, and Hive state.
  This keeps the first viewport visual and causal instead of forcing users to
  scroll into operator panels before they can see why AIOS chose a path.
- The chat surface includes an `Intent Lens`, informed by monitor next-actions
  and OS observatory state. It shows the inferred intent, next owner, and
  context capacity before the user sends another message. This was added after
  a GenesisOS critique identified contextual ambiguity and raw-evidence
  overload as the next UI discomfort.
- The inline chat follows the standalone `chat.html` input behavior:
  `Enter` sends and `Shift+Enter` inserts a newline. `Open Chat` jumps to the
  dedicated chat page when the user wants a focused conversation view.
- The standalone chat page includes a `Recent Conversations` history panel fed
  by `GET /api/chat_history`. Each history card shows redacted previews,
  Chair/runtime status, route summary, message count, and artifact shortcuts so
  older AIOS turns can be scanned without opening every trace file. History
  filters expose `Provider Chair`, `Internal`, `Memory Review`, and
  `Failed Provider` views; these are backed by server-side flags derived from
  Chair/provider receipts and MemoryOS review results.
- The standalone chat page also has its own `Decision Map`. It starts in a
  waiting state, then each assistant response updates the visible
  Chair -> Memory -> Capability -> Genesis -> Route flow from the chat result
  payload. This keeps the chat interface simple while still making AIOS's
  systemic routing visible without opening trace rows. When a node has a safe
  artifact path, clicking it opens the corresponding Gate Chair turn, MemoryOS
  context pack, CapabilityOS route, GenesisOS branch artifact, or invocation
  receipt in the Evidence Desk.
- The standalone chat page loads `aios-control-data.js` and renders the latest
  `offline_user` packet below the Decision Map. `Open Packet` sends the packet
  to the Evidence Desk; `Prepare Reply` fills the composer with a privacy-safe
  prompt for turning the packet into a bounded `user@offline` observation.
- Returned `field_observation` packets are mirrored into
  `.aios/chat/offline-user/memory_drafts.json`, so the existing Memory Draft
  Queue renders them as `field_observation` cards with the normal
  `Request Review` path. The UI still treats them as drafts; no observation is
  accepted into MemoryOS from the card itself.
- MemoryOS child watcher skips `aios.offline_user_agent_packet.v1` sense
  packets when selecting executable work from `.aios/inbox/memoryOS/`, so a
  raw offline observation cannot block the later `mdrev-*` review dispatch.
- Chat trace rows now expose `Promote Route` for invocation receipts. After an
  explicit `reviewed route` confirmation, the browser posts to
  `POST /api/promote_chat_route`; the server reads the receipt's
  `session_envelope`, writes a MyWorld promotion receipt and contract seed, and
  keeps `execution_started=false`. This is a governed bridge from an observed
  AIOS route to a proposed contract, not executor authority.
- Route promotions include a materialization quality check. Generic goals,
  zero/missing MemoryOS `signal_coverage`, missing CapabilityOS routes, missing
  GenesisOS branch artifacts, or missing dispatch previews are recorded as
  `quality_warnings`. A weak promotion can still be preserved as evidence, but
  `POST /api/materialize_promotion_contract` refuses to create
  `docs/contracts/ASC-....md` unless the route is revised or explicitly
  overridden by a future operator flow.
- The contract lane also surfaces weak proposed contracts that already exist
  from older dogfood runs. A proposed session-promotion contract with a
  too-short goal, zero MemoryOS signal coverage, or unnarrowed OS evidence is
  marked `weak_proposed` with `revise_or_supersede_before_acceptance`, so it
  remains auditable without looking ready for normal acceptance.
- Weak proposed contract rows expose a guarded `Supersede` action. The user
  must tick `reviewed`; then the browser posts to
  `POST /api/contract_review_action` with `action=mark_superseded`. The server
  only edits safe `docs/contracts/ASC-*.md` files that are still
  `status: proposed`, writes an `.aios/contract_reviews/.../review_action.json`
  receipt, and never starts executor work.
- The Conversation panel is intentionally chat-first: the visible bubble shows
  the answer, followed by a compact runtime strip for `Chair`, `Memory`,
  `Capability`, `Genesis`, and `Route`. The full route, MemoryOS, GenesisOS,
  Chair, and artifact evidence still stays collapsed under `Trace`. If the
  Chair runtime is still `internal_evidence_synthesizer`, the app must not
  imply that a full LLM conversation model is attached. Provider substrate
  names, route reasons, MemoryOS trace ids, and Chair runtime labels are
  evidence metadata, not the main answer.
- The Runtime band shows Gate Chair state from the snapshot: external Chair
  command, Ollama, or built-in deterministic `internal_evidence_synthesizer`,
  plus the latest Chair turn status when available. If
  `.aios/gate/founder/chair_runtime.json` exists, the snapshot also reports the
  AIOS-owned runtime candidate and whether it is active.
- The same Runtime band includes a `Gate Runtime Map`. The snapshot links the
  configured Chair runtime, candidate runtime, effective runtime, latest Chair
  turn, demotion evidence, and recovery proof with typed edges. This makes
  provider substitution visible as an operating decision instead of hiding it
  in a status sentence.
- `Test Gate Chair` in the Runtime band posts to `POST /api/gate_chair_probe`.
  The probe runs a bounded chat turn through the same router and returns
  `aios.gate_chair_probe.v1` with the current `gate_chair_status` and
  `gate_chair_turn` artifact path. It does not write credentials or change
  provider configuration.
- `Eval Chair` in the Runtime band posts to `POST /api/gate_chair_eval`.
  The eval runs `scripts/aios_gate_chair_eval.py --mode both --json`, compares
  the deterministic internal Chair baseline with the currently configured
  Chair runtime, shows promotion readiness, verdict, scores, and readiness
  reason, and exposes the generated `.aios/evals/gate_chair/<eval_id>/report.json`
  through the read-only artifact preview control. `promotion_ready=false` with
  `current_runtime_external=false` means the current Chair is still the
  deterministic internal synthesizer even if both scores are high.
- `Compare Chairs` in the Runtime band uses the same
  `POST /api/gate_chair_eval` endpoint with `candidate_matrix=true`. It runs
  `scripts/aios_gate_chair_eval.py --candidate-matrix --candidate claude
  --candidate codex --request-memory-review --json`, compares candidates
  against the internal baseline without activating them, shows the
  recommendation, candidate scores, failure counts, and exposes the generated
  `.aios/evals/gate_chair_matrix/<matrix_id>/report.json` through the read-only
  artifact preview control.
- `Use Internal`, `Try Ollama`, `Try Claude`, `Try Codex`, and `Try Gemini`
  post to `POST /api/gate_chair_runtime` with explicit confirmation. The
  endpoint writes only `chair_runtime.json` for internal mode and
  `chair_candidate_runtime.json` for provider-like modes; it does not store
  secrets, PINs, or arbitrary provider commands. Provider buttons record only
  whitelisted runtime modes and optional non-secret model names. Candidates are
  not used by normal chat until a separate activation path promotes them after
  eval. A candidate is allowed to be saved even when its command is missing, in
  which case the router continues to fall back internally. The Runtime action
  text reports `command missing`, `internal fallback expected`, and
  `eval before activation` when relevant.
- `Promote Chair` appears only after `Eval Chair` returns
  `promotion_ready=true`. It posts to `POST /api/gate_chair_promote`, which
  requires explicit confirmation and the eval report path before copying the
  candidate runtime into active `chair_runtime.json`.
- If an active provider Chair later accumulates repeated timeout,
  access-denied, backpressure, empty-output, or execution-failure evidence in
  Gate Chair eval/chat receipts, normal chat demotes the effective runtime back
  to `internal_evidence_synthesizer`. The runtime file is not erased; the
  summary and trace disclose that the active config is being shielded by
  negative evidence until another eval proves recovery.
- A later recovery eval clears that shield only when it is newer than the
  failure evidence, names the same active runtime mode/model, has
  `promotion_ready=true`, contains no failed current Chair runs, and matches
  or beats the internal baseline. A tied external Chair is eligible only as an
  operator-confirmed conversational activation, not as proof of higher
  reasoning quality. This keeps provider recovery explicit instead of relying
  on optimism or a manual config flip. When such a proof supersedes older
  failures, the Runtime band shows a recovery report preview link and the
  superseded failure count.
- Submit one goal in `AIOS`.
- The local app posts to `POST /api/session`.
- The API runs `scripts/aios_invoke.py --plan-only --json`.
- Output is written under `.aios/invocations/end-user-*/`.
- The browser shows the resulting `session_envelope.json`, role statuses for
  GenesisOS, MemoryOS, CapabilityOS, and Hive, plus the executor assignment.
- After reviewing the envelope, the browser can post to
  `POST /api/promote_session` with an explicit confirmation. This writes a
  non-executing promotion receipt and contract seed under `.aios/promotions/`.
  It does not start executor work; an operator must assign an ASC id, accept
  the contract, and dispatch through AIOS.
- Promotion queue cards can post to `POST /api/materialize_promotion_contract`
  after an operator enters an `ASC-NNNN` id. This copies the reviewed seed into
  `docs/contracts/<ASC-NNNN>-<slug>.md` with `status: proposed` and writes a
  `materialization.json` receipt. It still does not accept the contract,
  dispatch a packet, or start executor work.
- The first-screen `Agent Work` surface also shows the latest invocation role
  cards, safe artifact previews, and recent dispatch timeline.
- The `Memory Library` surface is evidence-backed, not only a counter panel.
  The snapshot reads MemoryOS `objects.jsonl`, `sources.jsonl`, and
  `retrieval_traces.jsonl`, then builds a graph preview from real
  RetrievalTrace -> selected memory -> source/provenance edges. The trace board
  shows recent RetrievalTrace queries, selected memory ids, confidence,
  evidence state, content preview, and source/provenance path. This makes it
  visible why MemoryOS affected an AIOS turn instead of hiding retrieval behind
  abstract object counts.
- The `Capability Router` surface is a source cockpit, not a tool launcher.
  The snapshot reads CapabilityOS recommendations, result observations,
  provider-route evidence, web-route policy, and constraint-break permission
  questions. The UI shows route cards grouped by local OS, provider/LLM, web,
  API, MCP, and skill/plugin modes, plus provider fallback scores, gap samples,
  source evidence requirements, and permission gates. Its Route Evidence Map
  connects recommended routes to fallback candidates, source evidence, known
  gaps, and provider takeover candidates so AIOS can distinguish useful tools
  from routes that need avoidance or repair. CapabilityOS still recommends
  only; Hive or myworld must execute with explicit evidence and permission.
- The `Genesis Lens` surface is also evidence-backed. The snapshot turns the
  latest GenesisOS branch artifact into a Worldline Map that links
  discomfort signals to speculative branches, invention seeds, and the source
  artifact. Clicking a branch, discomfort, or seed prepares a chat turn that
  asks AIOS to convert the node into a governed goal, contract, and
  verification gate. GenesisOS remains `speculative_only`; it creates
  divergence and pressure, while myworld chooses whether the seed becomes work.
- Artifact paths in session role cards, promotion receipts, the Agent Work
  artifact lane, Hive pipeline rows, Hive artifact rows, and chat evidence can
  be opened in-place through `POST /api/artifact`. This endpoint is read-only,
  previews only allowed relative control-plane paths, and rejects traversal,
  absolute paths, `.env`, secrets, credentials, tokens, PINs, raw exports, and
  private history markers.
- Chat Trace rows for `friction_contract_seed` can post to
  `POST /api/promote_friction_seed` after the user confirms the seed was
  reviewed. The endpoint copies the seed into `.aios/promotions/<id>/`, writes
  a promotion receipt, and keeps `execution_started=false`.
- Memory Draft cards show MemoryOS review results and derived next-evidence
  guidance. A `needs_more_evidence` result is displayed as a draft that still
  needs corroborating artifact, operator note, or repeated future turns before
  any durable memory claim can be made.
- Memory Draft cards with `needs_more_evidence` expose an `Add Evidence`
  control. It posts to `POST /api/memory_review_evidence`, records an operator
  note and/or safe artifact ref under `.aios/memory_review_evidence/`, and
  keeps memory acceptance separate from evidence collection.
- Offline User Agent cards mirror the same evidence loop for linked
  `field_observation` drafts: after MemoryOS returns `needs_more_evidence`,
  the card shows the latest evidence count, an `Add Evidence` form, and
  `Request Re-review` once evidence exists. This is only a review request; it
  does not mutate MemoryOS acceptance directly.
- After at least one supplemental evidence receipt exists, the same card shows
  `Request Re-review`. It reuses `POST /api/memory_draft_review`, and the
  generated MemoryOS packet carries the evidence receipt/artifact refs in
  `supplemental_evidence` and `draft.raw_refs`. The button queues another
  review; it does not mutate MemoryOS acceptance directly.
- Artifact previews render small `.json` files as formatted JSON and expose
  copy controls for both the artifact path and the loaded preview text.
- Opening an artifact updates the browser hash as `#artifact=<path>`. Reloading
  or sharing that local URL restores the same read-only artifact preview drawer
  without rerunning the chat turn, session intake, or Hive view.
- Artifact evidence also shows a compact authority/system-call label such as
  `ingest · AIOS invocation record`, `promote · MyWorld contract`, or
  `observe · Control UI schema`. These labels are the first UI projection of
  ASC-0174's authority-routed management-plane verdict.

Ask/contract seed intake:

- Submit one goal in `Ask AIOS`.
- The local app posts to `POST /api/ask`.
- The API runs `scripts/aios_ask.py --draft-contract --json` in plan-only mode.
- Output is written under `.aios/asks/<ask_id>/` and remains non-executing
  until an operator accepts a contract and dispatches work.

The browser UI has two modes:

- `operator`: full contract, dispatch, repo, evidence-route, stop-lane, and
  live event detail.
- `simple`: health, last activity, and review count only. It intentionally
  hides ASC IDs, raw JSON, and debug detail.

Run as a native desktop app:

```bash
python scripts/aios_desktop_app.py status --json
python scripts/aios_desktop_app.py snapshot --json
python scripts/aios_desktop_app.py launch
```

The desktop app uses Python `tkinter` and the same generated control snapshot.
It does not start an HTTP server or require a browser. In a headless shell,
`status --json` may report `display_available=false`; run `launch` from a
graphical desktop session.

The app renders:

- active goal and goal-evolution recommendation
- contract counts and latest contracts
- dispatch counts and latest dispatches
- repo loop state for hivemind, memoryOS, and CapabilityOS
- latest invocation role statuses, executor assignment, and artifact previews
- inline AIOS conversation with substrate, route, cost, memory draft, and
  artifact receipts
- MemoryOS trace IDs, CapabilityOS route IDs, and Hive run IDs found in recent
  contracts
- stop-condition lanes and monitor next actions

The snapshot script reads control-plane artifacts and repo status only. It must
not read `.aios/logs` bodies or mutate child repos.
