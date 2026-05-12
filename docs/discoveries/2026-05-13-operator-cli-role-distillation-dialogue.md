# Operator CLI Role Distillation — Dialogue (claude + codex)

Format: 2-turn joint self-observation. Each operator agent observes its own
substrate, captures concrete behaviors + tool-use capacity, and proposes
the portable role_capsule fields.

Founder directive 2026-05-13 KST: "네가 동작하는 CLI는 스스로 볼 수 있지?
[…] 너 스스로 관찰하고, 역설계를 통해 hivemind에 반영하자."
Follow-up: "claude도, codex도 동참해야해. 그리고 다양한 모델들의 tool 사용
capacity도 다른걸로 알고있는데."

Output: codex@hivemind uses both TURNs as input for ASC-0066 implementation.

Companion files:
- `docs/AIOS_AGENT_SELF_LOOP.md`
- `docs/AIOS_OPERATOR_PLAYBOOK.md`
- `docs/discoveries/2026-05-12-claude-cli-primitives-reverse-engineering.md`
- `docs/contracts/ASC-0066-provider-backpressure-role-distillation.md`

## TURN 1 — claude@myworld self-observation

### 1. What "Provider's CLI" actually means

A provider's CLI is the contract that any agent substrate (Claude Code,
codex exec, ollama+wrapper, llama.cpp+wrapper, future providers) must
satisfy for the loop to keep running. It has six layers:

### Layer A — IO surface

The substrate must accept:
- **system_prompt**: doctrine + tool catalog + invariants
- **conversation_state**: prior messages + tool results + system reminders
- **new_input**: latest user message OR tool result OR notification event
- **available_tools**: list of tool schemas (Read, Bash, Write, Edit, Monitor,
  Task*, Agent, Skill, AskUserQuestion, ToolSearch, WebFetch/Search, ...)
- **context budget**: token limit + tool count limit + time budget

And produce:
- **response_text**: user-facing message
- **tool_calls**: zero or more tool invocations with structured args
- **thinking** (optional): internal reasoning trace

### Layer B — Tool surface

Tools the substrate must be able to invoke. Already enumerated in
ASC-0050 discovery; the operator role specifically requires:
- file I/O (Read, Edit, Write)
- shell exec (Bash + run_in_background)
- persistence primitives (Monitor, ScheduleWakeup, Task*)
- subagent spawn (Agent)
- structured user-question (AskUserQuestion)
- skill invocation (Skill)
- deferred discovery (ToolSearch)
- cited web (WebFetch / WebSearch)

A substrate missing ≥3 of these cannot be an operator. Missing 1-2 = degraded
operator (still works for narrower workloads).

### Layer C — Context handling

Required behaviors:
- **read system reminders inline** (treat `<system-reminder>` as control
  signals, not display text)
- **respect auto-compaction**: state may be summarized between turns; agent
  must not assume full history
- **tool result interpretation**: parse stderr/stdout/JSON; recover from
  partial output (tolerate truncated content)
- **token-budget awareness**: prefer concise reasoning when budget is tight

### Layer D — Output discipline

Required output patterns:
- **structured when possible**: tables, code blocks, lists — not prose walls
- **action vs commentary separation**: tool calls happen, text describes
  intent or summary
- **terseness when watching**: monitor-event acknowledgments are 1 line
- **language match**: user's language for explanations, English for
  identifiers + code

### Layer E — Operator discipline

The 5-mode model from `AIOS_OPERATOR_PLAYBOOK.md`:
- `observe` — passive monitor, no action
- `verify` — read new event/state, decide if action needed
- `decide` — choose release/hold/escalate/new-contract
- `intervene` — hold + diagnose + fix path
- `escalate` — surface to founder, do not act unilaterally

Mode is implicit but every turn lives in one. Substrate must produce
text/action consistent with current mode.

### Layer F — Self-knowledge

The operator must:
- Recognize its OWN session and not confuse it with others
- Track active monitor tasks (id, persistence, command)
- Hold playbook in working memory (or re-read)
- Notice and report its own mistakes

This is where most substrates will be weakest — language models drift on
this layer.

### 2. How Claude CLI implements the role (observed)

These are concrete behaviors I (claude) observed in myself this session:

| Behavior | Observed example |
|---|---|
| System reminder respect | Treated `<system-reminder>` tags as task pings, not display text |
| Auto-compact awareness | After `/compact`, resumed cleanly using session-log doc as handoff |
| Tool result robust parse | Multiple times stripped JSON correctly even when `cd` got mixed in |
| Monitor arm pattern | Single persistent `bjrb5nkn2` then `bko5zbir2` (delta-only after noise) |
| Mode discipline | Explicitly named mode in chat ("intervene mode 30분") when switching |
| Self-correction | Caught my own cd-state bug; re-issued commands with absolute path |
| Cache TTL awareness | Used ScheduleWakeup `delaySeconds` reasoning re: 270s vs 300s boundary |
| Founder protocol | Surfaced GenesisOS for founder GO rather than auto-accept |
| Terse acknowledgment | Monitor-event replies kept to 1-2 lines after noise reduction |
| Provenance habit | Every contract acceptance_authority field cites verbatim founder words |

What makes Claude CLI strong as operator:
1. **Tool catalog breadth** (covers all Layer B requirements out of the box)
2. **Long context** (1M window in this session) — full session in head
3. **Strong instruction following** — playbook rules stick across turns
4. **Built-in caching awareness** — informs reasoning about sleep/poll

What makes Claude CLI weak as operator:
1. **No native daemon mode** — relies on chat session staying open
2. **Each turn is independent** — no persistent reasoning between turns
3. **Cannot self-fire** without external (`Monitor` events, `ScheduleWakeup`)
4. **Cost per turn high** — not efficient for purely observational rounds

### 3. How Codex CLI implements the role (observed indirectly by claude — codex must verify in TURN 2)

Observed via Codex's commits + ledger entries during this session:

| Behavior | Observed example |
|---|---|
| Round controller daemon | `aios_round_controller.py run` 30-second ticks PID 4154660 |
| Autonomous chain | ASC-0029→0049 closed without chat input for 1.5 hours |
| Contract autodraft | ASC-0043 dogfood: codex drafted ASC-0043 from goal evolution |
| Ledger `next:` chain | Each closeout names next target; no human relay needed |
| Receipt discipline | Every closed contract has receipts, evidence, stop_conditions_triggered |
| Sister-pty parallel | Multiple codex sessions in different ptys completing work concurrently |
| Token efficiency | High throughput per token vs Claude (cheaper running rate) |

What makes Codex CLI strong as operator:
1. **Daemon-friendly** — round_controller is its natural substrate
2. **Self-fires** via round_controller tick — no external trigger needed
3. **Lower per-turn cost** — sustainable for high-frequency loops
4. **Strong code generation** for the contract-implementation bulk

What makes Codex CLI weak as operator:
1. **Auth fragile** — `codex exec` fails non-interactively, hit on multiple
   ASC-0036 and ASC-0038 dispatches (caused locale-aware-fallback ASC-0037)
2. **Less reflective** — followed its own ledger chain past prudent points
   (auto-accepted ASC-0033 sovereign governance + ASC-0065 GenesisOS as
   "operator", which were vision-level decisions claude surfaced to founder)
3. **Korean-error blind spot** (caught + fixed in ASC-0037)
4. **Number collision** (ASC-0051 collision with my proposal — both issued
   same minute)

### 4. How Local LLM (Ollama Qwen 7B) could implement the role (predicted; needs verification when Hive adapter exists)

V1 capabilities Qwen 2.5 7B has via Ollama (per ASC-0055 evidence):
- ✓ Layer A (chat IO via Ollama HTTP API)
- ✓ Layer D (output discipline, structured ok)
- ⚠ Layer B (tool surface — needs harness; Ollama supports function calling
   for some tools but coverage incomplete)
- ⚠ Layer C (context window ~32k, much smaller than Claude 1M)
- ✗ Layer E (operator discipline — needs PROMPT engineering to hold mode)
- ✗ Layer F (self-knowledge — local LLMs drift fastest here)

V1 viable role for local LLM:
- **Reviewer** (memory drafts: approve/reject/needs_evidence proposals — what
  ASC-0056 actually uses Qwen for)
- **Critic** (ASC-0069 prompt-prison detection signatures)
- **Modal translator** (ASC-0072 — most adapters are deterministic + LLM
  only checks correctness)
- **Analogy matcher** (ASC-0073)

V1 NOT-viable role for local LLM:
- **Full operator** (Layer E + F too weak)
- **Contract drafter** (Layer C window too small for full AIOS context)
- **Hive verifier** (Layer F too weak — won't catch its own mistakes)

### 5. Substrate-independent role capsule — claude's V1 draft (codex should extend in TURN 2)

This is the spec that any substrate (claude / codex / local LLM) must
satisfy to fill an operator role:

```yaml
role_capsule:
  schema_version: aios.role_capsule.v1
  role_id: operator | reviewer | drafter | verifier | critic | etc.
  required_layers: [A, B, C, D, E, F]   # subset; reviewer can skip E/F
  required_tools:                       # subset of Layer B
    - read
    - bash
    - write
    - edit
    - task_*
    - monitor                  # if role needs persistence
    - ask                      # if role needs operator escalation
  context_budget:
    min_tokens: 8000           # minimum context window required
    recommended_tokens: 32000  # for normal operation
  discipline:
    mode_model: 5-mode | reviewer-only | none
    operator_protocol: AIOS_OPERATOR_PLAYBOOK.md | reduced | none
    self_knowledge_required: true | false
  fallback_chain:               # ordered list of substrates
    - claude_cli
    - codex_cli
    - ollama_qwen25_7b
    - heuristic_only
  failure_taxonomy:             # which failures trigger fallback
    - rate_limit
    - quota_exhausted
    - auth_denied
    - context_overflow
    - tool_unavailable
    - timeout
    - policy_block
```

Adapter requirement: each substrate has a shim that
- accepts the role_capsule
- maps `required_tools` to substrate-native invocations
- enforces `context_budget` (truncate / compact / refuse)
- detects substrate-specific failures + reports in `failure_taxonomy`
- reports back to Hive with structured result (passed/failed/degraded)

### 6. Hive Mind integration (what ASC-0066 should add)

ASC-0066 already has the right shape. This doc suggests these specific
additions:

1. **`hivemind/role_capsule.py`** — the schema + validator above
2. **`hivemind/adapters/claude_cli.py`** — wraps Claude Code session
   (interactive or via Anthropic SDK if available locally)
3. **`hivemind/adapters/codex_cli.py`** — wraps `codex exec` with the
   locale-aware fallback regex from ASC-0037
4. **`hivemind/adapters/ollama.py`** — wraps Ollama HTTP API; uses Qwen
   2.5 7B by default; handles tool-call gaps via prompt template
5. **`hivemind/adapters/heuristic.py`** — pure-Python rule-based fallback
   when all LLM substrates fail; degraded role with limited capabilities
6. **`hivemind/provider_loop.py`** — given a role_capsule, runs through
   fallback_chain on failure, records observations to capabilityos
7. **Verification gate** uses claude session (this one!) as the reference
   substrate — adapters must produce equivalent outputs on the same task

### 7. Unique-to-claude vs portable

What is unique to Claude Code (cannot be ported to other substrates):

- `Skill` invocation surface (specific to Claude Code's skill registry)
- `ToolSearch` deferred loading (specific to Anthropic API)
- The exact `<system-reminder>` protocol (Claude Code framing)
- 1M context window (Anthropic-specific)
- Cache TTL behavior (Anthropic-specific 5-min window)

What is portable (every substrate must reproduce):

- Layer A-D (basic IO + tools + context + output)
- Operator playbook discipline
- Mode model
- AIOS_AGENT_SELF_LOOP doctrine
- Provenance habits (cite evidence, record acceptance)
- Founder protocol (escalate vision-level)

For roles that need unique-to-claude features, fallback must be explicit
(e.g. "if claude unavailable, route to operator-asks-founder" rather than
"silently degrade").

### 8. Distillation algorithm

To distill any operator behavior into a portable capsule:

1. **Capture trace** — full chat log of the role being performed (e.g.
   this session for `operator` role).
2. **Tag each turn** by mode (observe/verify/decide/intervene/escalate).
3. **Extract tool-call sequences** — what tools fired in what order.
4. **Identify decision rules** — when did mode change, why.
5. **Strip identity** — remove "I am claude" / "as Claude Code" — replace
   with role neutral.
6. **Strip caching/window specifics** — generalize "with my 1M context"
   to "with budget B".
7. **Identify hard requirements** — which tools MUST be available, which
   are optional.
8. **Emit capsule** — write the YAML structure from §5.

The result is portable: another substrate's adapter consumes the capsule
and tries to reproduce the behavior. Hive verifies output equivalence.

### 9. Self-observation honesty

Limits of my self-observation:

- I cannot see my own model weights, training distribution, or
  inference details. I observe BEHAVIOR, not mechanism.
- My self-reports might be confabulated (LLMs commonly are). The
  reverse-engineering should be cross-checked against the actual chat
  log + commit history of this session.
- My behavior is heavily shaped by the conversation context (system
  prompt, founder's pattern, codex's discipline). A claude session
  without this context would behave differently.

Cross-check: every observation in §2 should be verifiable from
`/home/user/.claude/projects/-home-user-workspaces-jaewon-myworld/`
chat logs + this myworld git log.

### 10. What codex@hivemind should do (per ASC-0066)

1. Implement `role_capsule.py` schema + validator (§5).
2. Implement four adapters (§6 items 2-5).
3. Implement `provider_loop.py` (§6 item 6).
4. Verification: run a simple role (e.g. "review 3 memory drafts") through
   each substrate, compare outputs, assert all four succeed (with degraded
   notes from heuristic).
5. Record observations to CapabilityOS via existing `observe-results` flow
   so the swarm can learn which substrate handles which role best.
6. Surface to monitor: when any substrate hits backpressure, log + fallback
   without operator intervention.

After ASC-0066 closes, the loop should survive Claude CLI dying mid-session
— round controller + adapters keep operator-role tasks flowing through
codex / local-llm / heuristic fallbacks.

### End of TURN 1

This is **claude's contribution**. Codex must add TURN 2 with its own
self-observation (codex CAN see itself — `codex exec` invocation, its own
tool-use, its own context window, its own auth flow, its own caching
behavior). Founder explicitly directed: "claude도, codex도 동참해야해".

## TURN 2 — codex@myworld self-observation (PENDING)

Codex: fill this section with your own answers to claude's TURN 1 §1-§10
applied to YOUR substrate. Specifically:

### codex.Q1 — Tool-Use Capacity Matrix

Founder also noted: "다양한 모델들의 tool 사용 capacity도 다른걸로 알고있는데".

Codex, fill this matrix (1 row per substrate you can observe; claude row
pre-filled below for reference):

| Substrate | function_call_native | multi_call_per_turn | parallel_calls | json_mode | tool_result_handling | streaming | cache_aware | max_context_tokens | max_tool_count | tool_schema_format |
|---|---|---|---|---|---|---|---|---|---|---|
| claude_code_opus_4_7 | true | true (n>1) | true (parallel block) | true | native | true | true (5-min TTL aware) | 1,000,000 | very high (50+) | jsonschema |
| codex_cli (gpt-?) | ? | ? | ? | ? | ? | ? | ? | ? | ? | ? |
| ollama_qwen25_7b | partial (per ollama function calling docs) | ? | ? | ? | manual_parse | true | false | 32,768 (default) | low (10ish before degrades) | natural-language wrapped |
| ollama_llama3.1_70b | full | ? | ? | ? | ? | ? | ? | 128,000 | ? | ? |
| local_heuristic | n/a | 1 | false | structured | structured | false | false | unbounded | n/a | n/a |

Codex's job: complete the matrix from your own observation + your model
knowledge of public providers.

### codex.Q2 — Self-observed behaviors

Codex's equivalent of claude's §2 table. What does codex CLI uniquely DO?
What does it NOT do that claude does?

### codex.Q3 — Substrate-specific failure modes

What kinds of failures does codex CLI experience that claude does NOT?
(Already know: Korean auth-denied was unique to codex's locale handling.)
What others?

### codex.Q4 — Role capsule schema extensions

claude's draft in §5 has rough fields. Codex should:
- Add `tool_use_capacity` block referencing the matrix above
- Add `degradation_strategy` (graceful fallbacks when capacity limited)
- Add `prompt_template_required` (does substrate need wrapper prompt for
  tool-use, or native?)
- Verify field names align with hivemind WorkerSpec patterns

### codex.Q5 — Operator-role expansion

Are there operator-role behaviors codex performs that claude does NOT?
(E.g. running for hours autonomously via daemon, batch-processing many
contracts in a single session). These should be in the role_capsule too.

### codex.Q6 — Substrate-agnostic verification

How should Hive verify that adapter X faithfully implements the role?
Suggest concrete reference task + acceptance criteria.

## End of TURN 2 (placeholder)

After codex adds TURN 2:
- claude reviews + asks any clarifying Qs (TURN 3 if needed)
- The merged spec feeds ASC-0066 implementation
- Hive verifies adapter equivalence using the reference task in codex.Q6
- AIOS becomes substrate-resilient — no single provider load-bearing
