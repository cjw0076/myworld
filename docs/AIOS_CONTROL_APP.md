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

End-user intake:

- Open `http://127.0.0.1:8765/`.
- Use `Conversation / Talk to AIOS` for direct ongoing dialogue with the
  system. The panel uses the same `/chat` router as `chat.html`, so messages
  are persisted under `.aios/chat/<conversation>/` with route, cost, artifact,
  and MemoryOS draft receipts.
- The Conversation panel is intentionally chat-first: the visible bubble shows
  the answer, while route, MemoryOS, GenesisOS, Chair, and artifact evidence
  stays collapsed under `Trace`. If the Chair runtime is still
  `internal_evidence_synthesizer`, the app must not imply that a full LLM
  conversation model is attached.
- The Runtime band shows Gate Chair state from the snapshot: external Chair
  command, Ollama, or built-in deterministic `internal_evidence_synthesizer`,
  plus the latest Chair turn status when available. If
  `.aios/gate/founder/chair_runtime.json` exists, the snapshot also reports the
  AIOS-owned runtime candidate and whether it is active.
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
- The first-screen `Agent Work` surface also shows the latest invocation role
  cards, safe artifact previews, and recent dispatch timeline.
- Artifact paths in session role cards, promotion receipts, the Agent Work
  artifact lane, Hive pipeline rows, Hive artifact rows, and chat evidence can
  be opened in-place through `POST /api/artifact`. This endpoint is read-only,
  previews only allowed relative control-plane paths, and rejects traversal,
  absolute paths, `.env`, secrets, credentials, tokens, PINs, raw exports, and
  private history markers.
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
