# AIOS Ecosystem Blueprint — built from a code-level teardown of real agent CLIs

**Built**: 2026-06-09 (claude@myworld), from a 3-stream CODE-level teardown of
`openai/codex` (codex-rs), `google-gemini/gemini-cli` (packages/core), and
`code-yeongyu/oh-my-openagent` + opencode — reading the actual source (commits cited
in the teardown receipts), not the docs. Founder directive: "agent들이 어떻게 일하는지,
어떻게 구성되어있는지 코드 다 뜯어보면서 우리만의 생태계를 build … 통신은 어떻게,
로그는 어떻게…".

This is a STRUCTURE document, not a feature list. The founder's standing critique —
"harness engineering만 덕지덕지, system이 아니다" — is the bar. The teardown found
exactly why AIOS reads as a pile, at the code level, and what structure converts it
into an ecosystem.

## The core finding (why it's a pile, not a system)

**AIOS has no model-in-the-loop turn function.** `aios_contract_runner.run_contract`
is a single-pass `for step in contract.steps` over a step list that `aios_head`
asked the model for ONCE. Nothing feeds a step's result back to re-sample. It is a
**batch executor, not an agent loop**. Codex (`run_turn`, an inner `loop{}`) and
gemini (`processTurn`, bounded by MAX_TURNS) both center on an iterative
sample→dispatch→feed-back→resample loop. AIOS's layer *model* is right (kernel:
authority/audit/reversibility < OS roles < drivers — validated against both peers);
but there is no loop at the center, so the 132 standalone scripts have no spine to be
*tools of* — they can only be bypasses. **Fix the missing loop and the pile becomes
tools-of-a-system.** That is the whole blueprint in one sentence.

## What AIOS already owns (the hard, differentiated parts — keep)

The teardown confirmed AIOS is *ahead* of the peers on the expensive parts:
- fail-closed **bwrap sandbox** (`aios_sandbox.py`) — codex/gemini equivalent.
- **authority** gate + per-OS agent citizenship (`aios_authority`, `aios_agent_invoke`) — neither peer has citizenship classes.
- **backup → receipt → rollback** on fs-mutation (`aios_contract_runner`).
- **append-only + draft-first + provenance + divergence** (DNA) — peers converged on draft-first independently (validates it); none have GenesisOS.

The gap is never the governance. It is the cheap, load-bearing **engine spine**.

## The ecosystem, in three layers (each grounded in the teardown)

### 1. The spine — an iterative turn-loop in the kernel  *(missing → build first)*
`run_turn(history) → sample(model) → parse tool calls → dispatch → append results →
resample until (no tool call | max-turns | loop detected)`. Codex `run_turn`
(`core/src/session/turn.rs`), gemini `Turn.run` (async generator yielding typed
events). Reuse `ContractObject` as the per-turn record so every iteration still gets
a receipt. The model is dependency-injected (a sampler) — tested with a fake, live on
the box. **This is the one primitive that ends the pile.**

### 2. Tools — a name→handler registry with a per-call gate  *(promote the 132)*
Codex `ToolRegistry: HashMap<ToolName, handler>` + `dispatch_any`; gemini scheduler's
`Validating→Scheduled→Executing→terminal` per call. AIOS today: a fixed `if/elif`
over ~8 syscall verbs. **Convert it to `registry[name] → handler`** so the 132
standalone organs register as tools and are *invoked through the kernel*, not around
it — and insert a codex-style two-axis **`assess(approval_policy × sandbox_mode) →
{allow,ask,deny}` before each dispatch** (fail-closed). Deferred/lazy tool loading
(Claude `tool_search`, codex `ToolSearchCall`) + `list_tools` discovery is CapabilityOS's
job — it already half-does this.

### 3. Loop-safety — circuit-breaker + bounded concurrency  *(a real loop needs a named exit)*
omo `createToolCallSignature` + `consecutiveThreshold` repetition trip + `maxToolCalls`;
codex `FuturesOrdered` parallel tool futures; gemini `LoopDetectionService`. DNA
invariant 4 (every loop has a named exit) is *required* the moment AIOS gains a loop.
Port the signature-repetition detector + max-turns + a semaphore for independent steps.

## Communication — how our agents should talk (teardown §comms)
- **Correlate + thread lineage**: every packet carries `call_id` + `parent_call_id`/
  `trace_id` (codex `call_id`, gemini `parentCallId/traceId`). Our `.aios/inbox|outbox`
  matches by filename/order → fragile (we've hit ID-collision races). Correlation gives
  the provenance chain (DNA #5) for free.
- **Lifecycle, not drop-and-pray**: `spawn → wait{targets,timeout} → {status_map,
  timed_out}` (codex watch-channels) + omo's "poll as mailbox signal, re-ping `TASK
  STILL ACTIVE`, respawn smaller on stall". A packet returns an `agent_id` + pollable
  `status: running|final|timed_out`, giving a named exit + liveness (DNA #4).
- **Control messages as typed packets**: `done` / `ask` / `blocked` / `request_approval`
  distinct from `result` (codex `complete_task`/`request_permissions`/`ReviewDecision`,
  gemini `ask_user`/`complete_task`, MCP **elicitation**). An OS agent's "I'm blocked"
  becomes a structured escalation, not prose the parent must parse.
- **Remote** (when `@hivemind`↔`@memoryOS` go cross-machine): adopt Google **A2A**
  (`Message{role,parts,messageId,taskId,contextId}` + terminal `state`) rather than
  inventing a protocol.

## Logging & state — resumable, not just auditable (teardown §logging)
- **Resumable runs**: per-turn `turn_context` line (authority + model + cwd + git SHA)
  + periodic `Compacted{replacement_history}` checkpoint (codex), so a run rebuilds to
  its last durable baseline. AIOS ledger is inspectable, never replayable — the biggest
  state gap.
- **Real rollback**: capture a git `commitHash`/stash before each mutating tool
  (gemini `checkpointUtils`) into the receipt → reversibility becomes *executable*
  (DNA #6 operator-override), not the current *score*.
- **Cross-session work object**: `.aios/work/<id>.json` linking `session_ids[]`,
  `worktree_path`, `status`, `active_plan` (omo `BoulderState`) + `forked_from`/`parent`
  pointers (codex `forked_from_id`, claude `parentUuid`). Turns the flat ledger into a
  forkable, resumable work tree — which `aios_session_miner` + `aios_ingest_session`
  already partially read, feeding memoryOS (draft) + GenesisOS (interior).

## Build order (subtractive/integrative — NOT more organs)
1. **Turn-loop spine** in the kernel (this commit) — the one missing primitive.
2. **Syscall registry + per-call gate** — promote organs to tools routed through it.
3. **Loop-safety** (circuit-breaker + max-turns + bounded concurrency).
4. **Packet envelope**: `call_id`/`parent_call_id` + typed control messages + status lifecycle.
5. **Resumable run log** (turn_context + Compacted) + **git-snapshot rollback**.
6. **Cross-session work object** + lineage pointers.

Each step makes existing pieces *flow through the kernel*; none adds a new capability.
The measure of success is the inverse of today's: of N tool-calls in a run, the share
that went *through* the kernel loop (today: ~0; target: ~all).
