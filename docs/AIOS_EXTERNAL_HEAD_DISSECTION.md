# AIOS External Head Dissection — Hermes + OMO

**Created**: 2026-05-20 KST  
**Authority**: founder 재원 — chat directive ("Hermes, OmO 프로젝트를 가져와서 분해해보는것부터 시작" + "runtime / memory / provider routing / UX. 둘 다 한 Contract로 처리")  
**Status**: operational analysis report. **NOT a contract.** Produced by `co-hermes-omo-dissect-001` (runtime ContractObject instance — validates the v0 schema).

## Source

| Repo | Commit | Size | Lang | Lines |
|---|---|---|---|---|
| **Hermes** | NousResearch/hermes-agent (depth=1) | 108 MB | Python (1,781 files) | 862,276 |
| **OMO** | code-yeongyu/oh-my-openagent (depth=1) | 80 MB | TypeScript (2,170 files) | 290,208 |

Cloned to `/tmp/external_systems/{hermes,omo}/`.

# 4 angles × 2 repos = 8 cells

## Angle 1 — Runtime (agent loop / state machine / lifecycle)

### Hermes
- **Entry**: `gateway/run.py` (18K lines) — long-lived daemon. `start_gateway()` boots configured platform adapters (Discord/Slack/Telegram/...).
- **Core loop**: `agent/conversation_loop.py` — extracted ~3,900-line `run_conversation()` body. One *turn* = model call + tool dispatch + retries + fallbacks + compression + post-turn hooks.
- **AIAgent class**: `agent/run_agent.py` (대부분 conversation_loop 으로 분리 후 thin orchestrator).
- **Sub-systems** (90+ modules under `agent/`): IterationBudget, ContextEngine, ContextCompressor, ToolDispatchHelpers, ToolGuardrails, ErrorClassifier, FailoverReason, BackgroundReview, Curator (skill curation), Trajectory.
- **Concurrency**: asyncio + thread-safe schedule (`async_utils.safe_schedule_threadsafe`). Per-session AIAgent cache (bounded). Multi-turn long-lived sessions.
- **State**: in-memory message lists + SQLite (`hermes_cli/kanban_db.py`) + filesystem checkpoints.

### OMO
- **Entry**: `bin/oh-my-opencode.js` — *plugin* into OpenCode host. Not standalone. Platform-detect + binary-spawn.
- **Core**: `src/index.ts` exports `PluginModule` to OpenCode. The *host* drives the agent loop; OMO *injects* behavior via hooks + tools + agents.
- **Background agent**: `src/features/background-agent/manager.ts` — parallel sub-agent dispatch with attempt-lifecycle (start/finalize), polling, TTL cleanup, concurrency-manager.
- **State**: claude-code-session-state (binds to host Claude Code session), tool-metadata-store, run-continuation-state, message-injector storage. *No own runtime* — borrows host's.
- **Concurrency**: parallel via tmux-subagent (separate panes per worker). Hook-driven async dispatch.

### Comparison
- **Hermes is *its own* runtime**: agent loop, session, providers, hooks, gateway — all owned.
- **OMO is a *plugin runtime*** — defines what to inject into OpenCode's loop, doesn't own it.
- For AIOS-as-head: **Hermes model is closer to "device head" intent** (own loop, own messaging). OMO model is "OS plugin" (host-piggybacking).

---

## Angle 2 — Memory (persistence / recall / shape)

### Hermes
- **MemoryManager** (`agent/memory_manager.py`) + abstract **MemoryProvider** base (`agent/memory_provider.py`).
- **One external provider at a time** — explicit policy. Plugins: Honcho, Hindsight, Mem0, etc. shipped in `plugins/memory/<name>/`.
- **Lifecycle hooks** (provider implements):
  - `initialize()` connect + warm up
  - `system_prompt_block()` static text
  - `prefetch(query)` background recall before each turn
  - `sync_turn(user, asst)` async write after each turn
  - `get_tool_schemas()` + `handle_tool_call()` for memory-as-tool
  - `shutdown()`
  - optional: `on_turn_start`, `on_session_end`, `on_session_switch`, `on_pre_compress`, `on_memory_write`, `on_delegation`
- **Built-in memory** (no external provider): FTS5 session search (per docs) + Honcho user model. Also `agent/conversation_compression.py` for long-context handling.

### OMO
- **No explicit memory abstraction** comparable to Hermes.
- Relies on OpenCode host's session state.
- `claude-code-session-state` module wraps host state.
- `tool-metadata-store` for per-tool metadata across turns.
- Hook `compaction-aware-message-resolver` reconstructs context across host compactions.
- "Memory" 의 시각 차이: OMO 는 *user-personality* / *long-term recall* 개념 없음. 같은 코딩 세션 안에서만 의미.

### Comparison
- **Hermes treats memory as *first-class swappable substrate*** (one external + many internal hooks).
- **OMO treats memory as *host-managed*** (no opinion).
- For AIOS: Hermes's *MemoryProvider* shape is *exactly the kind of abstraction* our MemoryOS aspires to but doesn't currently expose to providers.

---

## Angle 3 — Provider routing (model selection / fallback / auth)

### Hermes
- **Per-provider adapters** in `agent/`:
  - `anthropic_adapter.py` (sk-ant-api + OAuth sk-ant-oat + Claude Code keychain creds)
  - `codex_responses_adapter.py`
  - `gemini_cloudcode_adapter.py`, `gemini_native_adapter.py`, `gemini_schema.py`
  - `bedrock_adapter.py`, `azure_identity_adapter.py`
  - `codex_runtime.py`
  - `lmstudio_reasoning.py`, `moonshot_schema.py`
- **Translation layer**: all adapters translate provider format ↔ internal OpenAI-style format.
- **Lazy SDK imports**: each adapter imports its SDK lazily (cold-start optimization — `anthropic` SDK alone ~220 ms).
- **Fallback chain**: `error_classifier.py` + `FailoverReason` enum (rate limit / API error / cold start) decides retries vs failover.
- **Credential management**: `credential_pool.py`, `credential_sources.py` — multiple sources per provider, rotated.
- **Rate limiting**: `rate_limit_tracker.py`, `nous_rate_guard.py` per-provider.

### OMO
- **Hook-driven** routing — `src/hooks/runtime-fallback`, `hooks/anthropic-context-window-limit-recovery`, `hooks/anthropic-effort`, `hooks/model-fallback`.
- `src/shared/model-error-classifier.ts` — `shouldRetryError`, `hasMoreFallbacks`.
- Host (OpenCode) owns actual provider calls; OMO *intercepts* via hooks to apply orchestration policy.
- 명시 SDK 인스턴스화 안 함 — host 가 한다.

### Comparison
- **Hermes owns the provider stack**: 10+ adapters, credentials, rates, fallback in own code.
- **OMO routes the provider stack**: thin policy layer above host.
- For AIOS head: **Hermes adapter pattern** 이 우리 ContractObject `provider_routes` 의 *진짜 implementation reference*. 우리는 schema 만 있고 adapter implementation 없음.

---

## Angle 4 — UX (CLI surface / UI / channels)

### Hermes
- **Multi-channel head** — single agent, *N messaging platforms*:
  - `gateway/platforms/`: discord, slack, telegram, whatsapp, signal, matrix, email, sms, webhook, feishu, wecom, weixin, yuanbao, msgraph, dingtalk, bluebubbles, mattermost, homeassistant, qqbot
  - 25+ platforms, each `<name>.py` + helpers
- **TUI**: `tui_gateway/server.py` + `ui-tui/` directory.
- **CLI**: `cli.py` (14K lines) — primary entry. `hermes_cli/main.py` (13K) — newer CLI surface. `hermes_cli/auth.py` (7K) for model switching. `hermes_cli/kanban_db.py` for task board.
- **One agent, many doors** — agent state lives in one process, doors connect users via their platform of choice.

### OMO
- **Plugin into OpenCode** — no own channels. OpenCode IDE 가 UI.
- **Multi-pane orchestration**: `src/features/tmux-subagent/manager.ts` — parallel sub-agents visualized in tmux panes.
- **Slash commands**: `src/tools/slashcommand` — extends host's command surface.
- **Task toast notifications**: `task-toast-manager` — non-blocking notifications.
- **Hook system as UX layer**: 30+ hooks intercept points (agent-usage-reminder, atlas, auto-slash-command, background-notification, etc.).

### Comparison
- **Hermes = chat-head + many channels** (own UI, integrate everywhere).
- **OMO = IDE-plugin + parallel-pane visualization** (no own UI, multiply within host).
- For AIOS: Hermes 의 *multi-platform gateway* 가 founder's "device head" 의 *외부* 면; OMO 의 *parallel subagent visualization* 이 *내부* 면. 둘 다 필요할 수 있으나 *지금 0/2*.

---

# Mapping onto our ContractObject schema

Our `ContractObject` v0 (14 fields). 각 angle × repo 가 schema 의 어디에 매핑되는가?

| Field | Hermes 대응 | OMO 대응 | 비고 |
|---|---|---|---|
| `goal` | user message | OpenCode prompt | both have it |
| `state` | session lifecycle | host session state | Hermes own, OMO borrowed |
| `authority_scope` | gateway config (channels, rate, network) | hook permission scopes | Hermes 더 강함 |
| `filesystem_scope` | tool_guardrails + file_safety | bash-file-read-guard | both partial |
| `provider_routes` | **agent/*_adapter.py** (10+ adapters) | hooks/model-fallback | **Hermes = reference** |
| `memory_inputs` | MemoryManager prefetch result | claude-code-session-state | both load context |
| `capability_route` | tool registry per session | tool-metadata-store + delegate-task | both have it |
| `genesis_challenge` | (none direct) | (none direct) | **gap in both** — Genesis-style critic 는 우리만 |
| `steps` | conversation_loop turn = step | hook chain + tool calls = step | both step-shaped |
| `actions` | tool_executor history | background-agent attempts | both execute |
| `receipts` | logs + trajectory | session messages + tool calls | both keep |
| `evals` | tool_result_classification | hook validation | both partial |
| `user_checkpoints` | gateway pause-on-error | hook-message-injector | both have |
| `memory_effects` | sync_turn + on_memory_write | session-end (host-driven) | Hermes 명시, OMO 암묵 |
| `next_state` | iteration_budget + retry | hook continuation | both have |

→ 우리 schema 의 **14 fields 중 13 fields 가 Hermes 에 명시 implementation 존재**. *오직* `genesis_challenge` 만 우리 unique. 좋은 신호 — 우리 schema 가 *실제* head 의 모양과 정합.

# Missing kernel items (재정의)

Minimum Kernel Audit 의 6 missing 항목을 *분해 후 다시* 평가:

| # | 항목 | Hermes reference | OMO reference | 우리 상태 |
|---|---|---|---|---|
| 1 | `aios <goal>` 단일 entry | `hermes` CLI (14K lines) | `oh-my-opencode` bin (plugin) | scripts/install.sh 의 aios entry — *subcommand wrapper*, goal-first 아님 |
| 2 | Provider CLI adapter layer | `agent/*_adapter.py` (10+) | hooks/model-fallback | scripts/aios_invoke.py 단일, 분리 안 됨 — **Hermes 패턴 차용 권장** |
| 3 | Safe filesystem write | `agent/file_safety.py` + tool_guardrails | bash-file-read-guard | ContractObject.filesystem_scope 만 있고 enforcement 없음 |
| 4 | Local LLM background cognition | (Hermes: 일부 local models via adapters; main 은 frontier) | OMO: background-agent + tmux 시각화 | ASC-0207 substrate만, 루프 안 없음 — **OMO 패턴 차용 권장** |
| 5 | Web → action flow | hermes/web/, tools/ | mcp/websearch.ts | aios_primitives.py web receipt 만, consume 없음 |
| 6 | External task input format | gateway/platforms/ → message normalization | OpenCode slash commands | 0 (no consumer entry) |

추가 발견 (분해 후):
- **7. MemoryProvider abstract base** — Hermes 의 첫 contribution. *우리 MemoryOS 가 외부 provider 와 어떻게 연결되는가* 의 명시 인터페이스 부재.
- **8. Per-session bounded agent cache** — Hermes 가 long-lived gateway 에서 memory leak 방지. 우리는 single-shot CLI, 미고려.
- **9. Background skill curation** — Hermes 의 Curator (skill bundles 자동 생성/갱신). 우리는 *프롬프트 단일* 이라 동등 개념 없음.
- **10. Lazy SDK import** — Hermes 가 220ms cold-start 단축 위해 모든 SDK lazy. 우리 minimum kernel 시작 시 차용 가치.

# 차용 / 회피 / 부재

## 차용 후보 (priority order)

1. **Hermes MemoryProvider abstract base** → 우리 MemoryOS 가 이걸 구현 + Mem0/Honcho-style plugin 모양 정착. ContractObject `memory_inputs` 의 *진짜 backend*.
2. **Hermes per-provider adapter pattern** → `agent/anthropic_adapter.py` 형태로 `aios.adapter.claude`, `.codex`, `.gemini`, `.ollama_local` 분리. provider_routes 의 *진짜 implementation*.
3. **OMO background-agent + tmux 시각화** → AIOS Local LLM background cognition (#4 missing) 의 working pattern.
4. **Hermes gateway 의 multi-platform pattern** — *장기*. AIOS 가 device-wide head 가 될 때 messaging platforms 연결의 reference.
5. **Hermes file_safety + tool_guardrails** → ContractObject filesystem_scope *enforcement* 의 구체 구현.
6. **OMO hook system** → AIOS step lifecycle 의 extension point 정의 모델.

## 회피 후보

1. **Hermes 의 25 platforms 모두 직접 작성** → 시작은 1-2개 (founder 가 일상 쓰는 채널) 만. 나머지는 *예시* 로 두고 사용자가 필요시 추가.
2. **OMO 의 plugin-into-host 구조** → AIOS 는 *자체 head* 가 목표. OpenCode/IDE 종속 회피.
3. **Hermes 의 거대 conversation_loop (3,900줄 단일 함수)** → 우리는 step graph 로 *명시 분리*, 단일 거대 함수 회피.
4. **OMO 의 11+ specialist agents** → 우리 5 OS 가 페르소나 분리, *복제* 회피. 다만 *역할 분리 패턴* 자체는 차용.

## 둘 다 부재 (우리 unique)

1. **Append-only ledger + provenance chain** — Hermes 의 trajectory 가 비슷하나 *cross-repo* 동기화 아님.
2. **DNA invariants (7개)** — operational rules. 두 repo 모두 자기 코드 안에 분산.
3. **GenesisOS-style cross-domain transfer critic** — 둘 다 없음. *진짜 unique*.
4. **Draft-first memory review lifecycle** — Hermes 는 auto-write, OMO 는 host-managed. 우리만 명시.

# 결과 → 진짜 minimum kernel 의 *재정의*

본 분해로 minimum kernel 의 ≤20 파일 *내용* 이 더 명확:

| Slot | 이전 (audit) | 분해 후 (확정 권장) |
|---|---|---|
| Frame docs | AIOS_DEFINITION/NORTHSTAR/DNA/SMART_CONTRACT | 유지 |
| Agent role docs | AGENTS/CLAUDE | 유지 + CODEX/GEMINI 추가 (Hermes-style multi-substrate) |
| Plumbing | install/dispatch/monitor/primitives/invoke | **invoke 를 5+ adapter (claude/codex/gemini/ollama_local/...) 로 분리** (Hermes 차용) |
| Child OS substrate | memoryos store/schema, capabilityos catalog, genesisos critic | **+ MemoryProvider abstract base** (Hermes 차용) |
| Missing → 추가 필요 | aios <goal>, safe FS, local-LLM background, web→action | OMO background-agent + Hermes file_safety + 둘 패턴 |

**기존 카운트**: ~18 → 확정 카운트: ~22-25 (adapter 분리 시 늘어남).

# Action queue (priority)

본 분해의 *직접* 결과 (또 contract 발의 아닌, kernel build action):

1. **`scripts/aios/adapter/`** 디렉터리 구성 + `claude.py` / `codex.py` / `gemini.py` / `ollama.py` 각각 — Hermes adapter 패턴 차용. ContractObject `provider_routes` 의 진짜 implementation.
2. **`scripts/aios/memory/provider_base.py`** — MemoryProvider abstract. 우리 MemoryOS 가 이걸 구현 + Mem0-style external plugin 모양.
3. **`scripts/aios/runtime/contract_runner.py`** — ContractObject 를 받아 step graph 를 execute. authorize_step → execute → record_receipt → transition. *진짜 runtime*.
4. **`scripts/aios/head/aios_run.py`** — `aios run "<goal>"` 단일 entry. 자연어 → ContractObject 컴파일 → runtime 실행.

이 4 개가 *진짜 minimum kernel* 의 다음 4 파일.

# Memory effects (draft-first)

다음 memoryOS draft 후보 (founder 미review):
- *Hermes MemoryProvider abstract base 가 우리 MemoryOS 와 정합한 인터페이스. ContractObject.memory_inputs 의 진짜 backend 후보.*
- *Hermes per-adapter 패턴이 ContractObject.provider_routes 의 진짜 implementation 형태. 우리 aios_invoke.py 분해 권장.*
- *OMO background-agent + tmux 시각화가 local LLM cognition 통합의 working pattern.*
- *AIOS unique points: Genesis-critic, append-only cross-repo ledger, draft-first memory review — 둘 repo 모두 부재 → 우리 정체성의 진짜 differentiator.*

---

이 dissection 이 ContractObject v0 의 첫 *외부-grounded 사용 사례*. 8 cells 모두 채워졌고, 우리 schema 가 *실제* head 의 모양과 13/14 정합. 다음 단계 = 위 4 action queue 의 첫 항목부터 build.

---

# Addendum — agiresearch/AIOS (the *other* AIOS)

**Added 2026-05-21** by `co-agiresearch-dissect-001` (ContractObject runtime 3rd instance).
founder verdict "B": one more repo dissection before building. Picked
agiresearch/AIOS for max marginal value — kernel angle (our weakest) +
same-name disambiguation.

## Source

| Repo | Size | Lang | Files |
|---|---|---|---|
| agiresearch/AIOS (kernel) | 14 MB | Python | 152 .py |
| agiresearch/Cerebrum (SDK) | 7.7 MB | Python | (SDK) |

arXiv 2403.16971 / 2312.03815; COLM 2025; docs.aios.foundation.

## What they built — a genuine OS-kernel metaphor

agiresearch/AIOS realizes the *OS kernel abstraction* we claim but never built:

- **`aios/syscall/`** — agent operations are *system calls*: `LLMSyscall`,
  `MemorySyscall`, `StorageSyscall`, `ToolSyscall`. `SyscallExecutor`
  dispatches them.
- **`aios/scheduler/`** — `BaseScheduler` + `fifo_scheduler.py` +
  `rr_scheduler.py` (round-robin). Schedules syscalls across *concurrent
  agents* — like an OS schedules processes on a CPU.
- **Request queues** — `global_llm_req_queue`, `global_memory_req_queue`,
  `global_storage_req_queue`, `global_tool_req_queue`. Syscalls enqueue;
  scheduler arbitrates.
- **Resource managers** — `LLMAdapter`, `MemoryManager`, `StorageManager`,
  `ToolManager`. Each owns one resource class.
- **`aios/llm_core/routing.py`** — load-balancing strategies + LP
  optimization (`pulp` solver) + `litellm` router. Routes LLM calls to
  cheapest/fastest endpoint under constraints.
- **`aios/context/`** — `simple_context.py` = context *switching* between
  agents.
- **computer-use**: `aios/tool/virtual_env/` — VM controller + MCP server,
  sandboxed computer interaction.

Flow: `agent → Cerebrum SDK → syscall → request queue → scheduler →
resource manager`. Claim: 2.1× faster agent serving.

## The disambiguation — two different OS metaphors named "AIOS"

| | **agiresearch/AIOS** | **our (MyWorld) AIOS** |
|---|---|---|
| OS metaphor | **LLM-as-CPU** — schedule agent syscalls | **device-head** — operate the user's machine |
| Optimizes | serving *many agents* efficiently (throughput) | *one user's* device worked by an organism |
| Tenancy | server-side, multi-agent, multi-tenant | client-side, local-first, single-user |
| Core abstraction | syscall + scheduler + resource managers | ContractObject + delegated authority + provider CLIs |
| Authority | kernel owns LLM/mem/storage/tool resources | head receives *delegated* device authority |
| Deps | heavy (chromadb, qdrant, litellm, pulp LP, gdown) | stdlib-first (minimum kernel) |
| Intelligence locus | scheduling efficiency | frontier-LLM-in-loop + provider CLI orchestration |
| Provenance/ledger | no | yes (append-only cross-repo) |
| Genesis-style critic | no | yes |

→ **같은 이름, 다른 OS.** agiresearch = *agent 요청을 스케줄하는 커널*.
우리 = *사용자 디바이스를 운영하는 head*. 외부 문서에서 반드시
disambiguate: "MyWorld AIOS (device-head interpretation)" vs
"agiresearch AIOS (LLM-kernel interpretation)".

## 4-angle comparison (now 3 systems)

| angle | Hermes | OMO | agiresearch | 우리 (목표) |
|---|---|---|---|---|
| runtime | standalone agent loop | OpenCode plugin | syscall scheduler kernel | ContractObject runtime (building) |
| memory | MemoryProvider abstract (1 external) | host session state | MemoryManager + providers + retrievers | MemoryOS graph control + (need provider abstract) |
| provider routing | 10+ adapters + credential pool | hooks/model-fallback | LP-optimized litellm router | CapabilityOS matrix + (need adapters) |
| UX | 25 messaging platforms + TUI | tmux multi-pane | Web UI + Terminal UI | apps/control (our dashboard) |

## Borrow / avoid (agiresearch-specific)

### Borrow
1. **Syscall *typing*** — agiresearch types each op (LLMSyscall/MemorySyscall/
   StorageSyscall/ToolSyscall). Our `ContractObject.Step.tool` (fs.read /
   provider.X / web) is *already syscall-shaped*; formalize as typed
   syscalls for cleaner authorization + receipts.
2. **Resource-manager separation** — clean LLM/memory/storage/tool manager
   split. We have memoryOS/capabilityOS; storage + tool managers are implicit.
3. **Context-switch concept** — `simple_context.py` for switching between
   work items. Maps to ContractObject state save/restore.

### Avoid
1. **Scheduler complexity** — FIFO/RR cross-agent scheduling is for
   *multi-agent throughput*. We are single-user; premature. Add only if AIOS
   ever serves concurrent agents.
2. **Heavy deps** — chromadb/qdrant/litellm/pulp LP solver/gdown violate our
   minimum-kernel stdlib-first. CapabilityOS routing stays lightweight.
3. **Server-side multi-tenant framing** — opposite of local-first device
   head. Their 2.1× throughput claim is irrelevant to single-user latency.

## Net effect on our build queue

agiresearch confirms the **4 build items** from the Hermes/OMO dissection
stand, with one refinement:

- Build item #3 (`contract_runner.py`) should formalize `Step.tool` as
  **typed syscalls** (borrowing agiresearch's syscall typing) so
  authorization + receipts are uniform.
- Build items #1, #2, #4 unchanged (adapters, MemoryProvider base, aios run head).
- **Explicitly NOT building**: a scheduler. Single-user head needs no
  cross-agent CPU-style scheduling. This is a deliberate divergence from the
  academic AIOS — our "OS" is a *device head*, not a *request scheduler*.

Conclusion: 3 systems dissected (Hermes standalone-head, OMO plugin-runtime,
agiresearch syscall-kernel). Our ContractObject schema maps cleanly across
all three. Our distinct position = **delegated-authority device head** —
neither a chat agent (Hermes), an IDE plugin (OMO), nor a request scheduler
(agiresearch). Build from here.
