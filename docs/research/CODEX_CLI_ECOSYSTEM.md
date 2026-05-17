# OpenAI Codex CLI Ecosystem — Engineering Research

> Internal AIOS research doc. Purpose: deeply understand the OpenAI Codex CLI
> ecosystem so AIOS (a local-LLM-based agent operating system) can borrow and
> imitate its best architecture and claim the "first local-LLM-based AIOS
> ecosystem" title.
>
> Method: public OpenAI Codex docs (`developers.openai.com/codex`) +
> direct inspection of a live local `~/.codex/` install (Codex CLI, sessions
> dated through 2026-05-17). No secrets, auth tokens, or raw private
> conversation content are reproduced here — schemas and formats only.
>
> Date: 2026-05-17.

---

## 0. TL;DR — what Codex CLI is

Codex CLI is OpenAI's terminal coding agent: a Rust binary that runs a
model-driven **turn/tool loop** against a local repo, mediated by an OS-level
**sandbox** and a layered **approval policy**. Around the core loop it has
grown a full ecosystem: a TOML config system, a project-instruction file
(`AGENTS.md`), MCP tool integration, a skills system, a plugin/app system, a
persistent session store (JSONL rollouts + SQLite indexes), and a multi-stage
**memory pipeline**. It is, structurally, already "an agent OS" — just one
bound to a frozen hosted model. AIOS's differentiator is doing the equivalent
on a **local LLM**, so this doc maps every Codex subsystem to a concrete
"AIOS borrow."

---

## 1. Architecture & Agent Loop

### 1.1 The turn/tool loop

Codex runs a classic agentic loop. One **turn** = one user input processed to
completion. Within a turn the model alternates between emitting **reasoning**,
**tool calls** (function calls), and **assistant messages**, and the harness
feeds back **tool outputs**, until the model emits a final message and the turn
completes.

The on-disk session rollout (see §3) confirms the exact item taxonomy. A single
real session decomposed into:

| item type | role/subtype | count | meaning |
|---|---|---|---|
| `response_item` | `message` / user | 5 | user input |
| `response_item` | `message` / developer | 3 | injected developer instructions |
| `response_item` | `reasoning` | 21 | model chain-of-thought items |
| `response_item` | `message` / assistant | 22 | model replies |
| `response_item` | `function_call` | 53 | tool invocations |
| `response_item` | `function_call_output` | 53 | tool results |
| `response_item` | `custom_tool_call` (+`_output`) | 4+4 | non-standard tools (e.g. apply_patch) |
| `event_msg` | `exec_command_end` | 46 | shell command completion events |
| `event_msg` | `patch_apply_end` | 4 | file-edit completion events |
| `event_msg` | `token_count` | 38 | running token accounting |
| `event_msg` | `task_started` / `task_complete` | 3+3 | turn lifecycle |
| `turn_context` | — | 3 | per-turn execution context snapshot |
| `session_meta` | — | 1 | session header |

Two parallel streams are persisted: **`response_item`** = the canonical model
conversation (what gets re-sent to the model), and **`event_msg`** = the UI/
telemetry event stream (what the TUI renders + token accounting). They are
interleaved in one append-only JSONL file.

### 1.2 turn_context — per-turn execution snapshot

Each turn writes a `turn_context` record capturing the *exact* execution
environment for that turn. Observed keys:

```
turn_id, cwd, current_date, timezone, approval_policy, sandbox_policy,
permission_profile, model, personality, collaboration_mode, realtime_active,
effort, summary, user_instructions, truncation_policy
```

This means approval policy, sandbox policy, model, and reasoning effort are
**per-turn mutable** and **recorded with every turn** — not global session
constants. The session is fully replayable because every turn carries its own
context.

### 1.3 The developer message + sandbox message

The model's context is assembled from layers. A `role=developer` message
describes the sandbox that applies to the Codex shell tool, plus an optional
`developer_instructions` block read from `config.toml`. Tools from MCP servers
are explicitly *not* sandboxed by Codex — they enforce their own guardrails.
`base_instructions` is recorded in `session_meta`.

### 1.4 Sandboxing model

The sandbox is OS-native, not a container:

- **macOS** — Seatbelt (`sandbox-exec` profiles), no extra deps.
- **Linux / WSL2** — `bubblewrap` user-namespace isolation, with a bundled
  helper fallback requiring unprivileged user namespaces. Ubuntu may need the
  `bwrap-userns-restrict` AppArmor profile.
- **Windows** — native Windows Sandbox (PowerShell) or the Linux path under WSL2.

Three sandbox modes:

1. **`read-only`** — inspect files only; no writes, no command execution.
2. **`workspace-write`** — read/edit inside the workspace + run routine local
   commands; **network off by default**. This is the default for local work.
3. **`danger-full-access`** — no filesystem/network boundary at all.

The live install confirms the structured `sandbox_policy` JSON stored per
thread, e.g.:

```json
{"type":"workspace-write","writable_roots":["/home/user/.codex/memories"],
 "network_access":false,"exclude_tmpdir_env_var":false,"exclude_slash_tmp":false}
```

Note the **`writable_roots`** mechanism: extra directories punched through the
sandbox without dropping it entirely (here, the memory directory is writable so
the agent can self-update memory). **Protected paths** use deny rules to block
*reads* of sensitive files (local secrets) even within writable roots. Network
access is governed by per-domain / Unix-socket permission profiles.

### 1.5 Approval modes

Approvals are a *second, independent* layer on top of the sandbox. The sandbox
defines technical capability; approvals define *policy* — when the agent must
pause and ask.

| approval policy | behavior |
|---|---|
| `untrusted` | only known-safe read ops run automatically; everything else prompts |
| `on-request` (default for "Auto") | autonomous inside sandbox; prompts to leave workspace or hit network |
| `on-failure` | runs in sandbox; prompts only when a sandboxed command fails (offers escalation) |
| `never` | non-interactive (CI); never prompts — strictly bounded by sandbox |

The historical UX names (suggest / auto-edit / full-auto) now map onto
(sandbox mode × approval policy) pairs. The "Auto" preset =
`workspace-write` + `on-request`. "Full access" = `danger-full-access` +
`never`. The live thread store confirms real combinations in use:
`read-only`+`on-request`, `workspace-write`+`never`, `danger-full-access`+`never`.

**Reviewer subagent** — with `approvals_reviewer = "auto_review"`, approval
prompts route to a *reviewer agent* instead of a human. It evaluates only
already-gated actions (sandbox escalation, blocked network, side-effecting
tool calls), denies critical-risk, allows low/medium-risk per policy. It costs
extra model calls but removes the human from the loop.

> **AIOS borrow:** Adopt the **two-layer separation — capability (sandbox) vs
> policy (approval)** — as a first-class AIOS primitive. Today AIOS conflates
> them in contract status. Concretely: (1) bind hivemind execution to an
> OS-native sandbox (`bubblewrap` on Linux) with explicit `writable_roots`
> rather than trusting workers; (2) make AIOS's 7 DNA invariants enforce a
> *per-turn* `turn_context`-style record — every dispatched work packet should
> serialize its sandbox + approval + model + effort, making runs replayable and
> auditable (this directly strengthens DNA invariant 3 "append-only audit" and
> 5 "provenance chain"). (3) The **reviewer subagent** is exactly AIOS's
> "operator override + verification gate" — but Codex made it a *model*, not a
> human. AIOS can run the reviewer as a local-LLM critic (GenesisOS pre-close
> challenge / Hive verify), keeping invariant 6 (operator override) while
> removing the human bottleneck for low-risk actions.

---

## 2. Configuration & Extension

### 2.1 `config.toml`

Single TOML file, default `~/.codex/config.toml`; project-scoped overrides at
`.codex/config.toml` (loaded only for **trusted** projects). The CLI and the
IDE extension share it. Key tables/keys observed in docs + the live file:

- **Core:** `model`, `model_provider`, `model_context_window`,
  `model_reasoning_effort`, `sandbox_mode`, `approval_policy`,
  `approvals_reviewer`.
- **`[sandbox_workspace_write]`** — `writable_roots`, `network_access`,
  `exclude_tmpdir_env_var`, `exclude_slash_tmp`.
- **`[shell_environment_policy]`** — env var inheritance (`all`/`core`/`none`),
  explicit overrides, exclusion patterns.
- **`[history]`** — `persistence` (`save-all` / `none`), `max_bytes`.
- **`[features]`** — feature toggles (live file has `goals = ...`).
- **`[profiles.<name>]`** — named overlays that override top-level settings
  per session without editing the base config.
- **`[projects."<abs-path>"]`** — `trust_level` (`trusted`/`untrusted`); gates
  whether that project's `.codex/` layers load. The live file has ~70 such
  entries (every repo + every `/tmp/...` scratch dir Codex has touched —
  trust is *remembered per directory*).
- **`[mcp_servers.<name>]`** — see §2.3.
- **`[plugins."<name>@<source>"]`** — `enabled` toggle per plugin.
- **`[apps.<app_id>.tools.<tool>]`** — per-app/per-tool `approval_mode`.

`project_doc_max_bytes` (default 32 KiB) caps how much `AGENTS.md` is injected.

### 2.2 `AGENTS.md` — project instruction file

Codex's equivalent of `CLAUDE.md`. Discovery + merge order:

1. **Global:** `~/.codex/AGENTS.override.md` or `~/.codex/AGENTS.md`.
2. **Project:** walk from Git root *down* to cwd, at each level check
   `AGENTS.override.md` → `AGENTS.md` → fallback names.

All discovered files are **concatenated root→cwd**, blank-line joined. Files
closer to cwd appear *later* and therefore override. Loading stops at
`project_doc_max_bytes`. The live global `~/.codex/AGENTS.md` is itself an
"AIOS bootstrap" doc instructing every Codex session to operate as an AIOS
builder — i.e. the founder already uses this file as a cross-session
persona/role injector.

### 2.3 MCP support

MCP servers configured via `[mcp_servers.<name>]` tables in `config.toml`, or
`codex mcp add <name> -- <command>`. Two transports:

- **stdio** — local process: `command`, `args`, `env`, `cwd`,
  `experimental_environment` (remote exec), `startup_timeout_sec` (10s),
  `tool_timeout_sec` (60s).
- **http** — remote URL: `bearer_token_env_var`, `http_headers`,
  `env_http_headers`, OAuth via `codex mcp login`
  (`mcp_oauth_callback_port`/`_url`).

Both support `enabled_tools` / `disabled_tools` allowlists, `enabled` toggle,
and `required` (startup fails if an enabled required server can't init). Codex
can also *be* an MCP server, exposing itself to other agents.

### 2.4 Skills

Live install has user skills (`~/.codex/skills/<name>/`) and system skills
(`~/.codex/skills/.system/`: `imagegen`, `openai-docs`, `plugin-creator`,
`skill-creator`, `skill-installer`). A skill is a directory:

```
<skill>/
  SKILL.md              # YAML frontmatter: name + description, then markdown body
  references/*.md       # supporting docs loaded on demand
  agents/openai.yaml    # per-agent interface metadata (display_name,
                        #   short_description, default_prompt)
```

The `SKILL.md` frontmatter `description` is a *routing trigger* ("Use when the
user asks to ..."). The body is procedural instructions. `agents/openai.yaml`
adapts the skill to a specific agent surface. This is a **progressive-disclosure**
design: only frontmatter is always-loaded; the body and `references/` load when
the skill fires.

### 2.5 Rules

`~/.codex/rules/default.rules` is a flat, append-only list of executable
command-approval rules:

```
prefix_rule(pattern=["ps","-ef"], decision="allow")
prefix_rule(pattern=["sudo","apt-get","update"], decision="allow")
```

Each rule matches a command-argv **prefix** and pre-decides `allow`/deny. This
is how Codex "remembers" that a once-approved command is now trusted — it
mechanizes the human's past approvals into a persistent allowlist, so the same
prompt never recurs.

### 2.6 Plugins / Apps

`[plugins."<name>@openai-curated"]` entries with `enabled` flags; cached under
`~/.codex/plugins/cache/<source>/<plugin>/`. Observed curated plugins: `figma`,
`hugging-face`, `vercel`, `github`, `google-drive`, `notion`, `gmail`. Plugins
("apps") bundle MCP servers + tool sets + per-tool approval modes
(`[apps.<id>.tools.<tool>].approval_mode`). The `.system/plugin-creator` and
`skill-installer` skills let the agent author and install new ones — the system
is **self-extending**.

> **AIOS borrow:** Codex's extension stack maps almost 1:1 onto AIOS, and the
> mapping is instructive:
> - **`config.toml` `[profiles]`** → AIOS should have named **operator profiles**
>   (e.g. `observe`, `genesis`, `long-run`) that overlay model/effort/sandbox
>   in one switch — cleaner than today's mode prose in the playbook.
> - **`[projects."<path>"].trust_level`** → AIOS should keep a **per-directory
>   trust ledger**; child-repo dispatch already implies this, make it explicit
>   and persistent. This is the natural home for DNA invariant 7 (privacy
>   boundary) — mark `_from_desktop/`, `dain/`, `minyoung/` as permanently
>   `untrusted`/no-write.
> - **`AGENTS.md` root→cwd concatenation** → AIOS already has layered
>   `CLAUDE.md`/`AGENTS.md`; adopt the explicit **byte-capped, closer-overrides
>   merge** algorithm so contract-local instructions can refine repo-global
>   ones deterministically.
> - **Skills with frontmatter-as-router** → AIOS contracts/primitives should
>   carry a `description`-style **trigger line** so a local-LLM router
>   (CapabilityOS) can select them by progressive disclosure instead of loading
>   every contract. The `references/` + `agents/openai.yaml` split is a clean
>   "spec vs adapter" pattern.
> - **`rules` allowlist** → AIOS should mechanize past operator approvals into
>   an **append-only `prefix_rule` ledger**, so the operator pair stops
>   re-approving the same dispatch/command. This is provenance-preserving
>   automation and directly reduces escalation noise.
> - **plugin-creator / skill-installer self-extension** → the headline borrow:
>   AIOS should ship a **local-LLM-driven contract/skill autodrafter that can
>   install its own new capabilities**, making AIOS self-extending the way the
>   Codex `.system` skills are — but governed by AIOS's draft-first invariant.

---

## 3. Conversation Log / Session State Storage

Codex persists state in **three layers**: JSONL rollouts (truth), SQLite
indexes (fast query), and a JSONL global history (cross-session search).

### 3.1 Session rollouts — `~/.codex/sessions/`

Path layout is date-sharded:

```
~/.codex/sessions/YYYY/MM/DD/rollout-<ISO-timestamp>-<uuid>.jsonl
```

Each rollout is append-only JSONL; every line is
`{timestamp, type, payload}`. Line types:

- **`session_meta`** (first line) — `payload`:
  `{id, timestamp, cwd, originator, cli_version, source, model_provider,
    base_instructions, git}`.
- **`turn_context`** — per-turn execution snapshot (keys in §1.2).
- **`response_item`** — canonical model conversation items (`message`,
  `reasoning`, `function_call`, `function_call_output`, `custom_tool_call`,
  `custom_tool_call_output`).
- **`event_msg`** — UI/telemetry events (`task_started`, `agent_message`,
  `exec_command_end`, `patch_apply_end`, `token_count`, `task_complete`, …).

The rollout is the **single source of truth** and is fully replayable: meta
header + per-turn context + interleaved model/event streams.

### 3.2 `state_*.sqlite` — session index & memory pipeline

`state_5.sqlite` (the `_5` is a schema-version suffix; migrations tracked in
`_sqlx_migrations`, written by Rust `sqlx`). Tables (**schema only — no content
read**):

- **`threads`** — one row per session. Columns include `id`, `rollout_path`
  (pointer back to the JSONL), `created_at`/`updated_at` (+ `_ms` variants kept
  in sync by triggers), `source`, `model_provider`, `model`, `cwd`, `title`,
  `first_user_message`, **`sandbox_policy`** (JSON), **`approval_mode`**,
  `tokens_used`, `archived`, `git_sha`/`git_branch`/`git_origin_url`,
  `cli_version`, `agent_nickname`, `agent_role`, `agent_path`,
  `memory_mode`, `reasoning_effort`. (Live install: 327 threads.)
- **`thread_dynamic_tools`** — per-thread tool registry: `name`,
  `description`, `input_schema`, `defer_loading`, `namespace`. This is
  *deferred tool loading* persisted per session — tools fetched on demand.
- **`stage1_outputs`** — **memory pipeline stage 1**: per-thread
  `raw_memory`, `rollout_summary`, `generated_at`, `usage_count`,
  `selected_for_phase2`. (See §4.)
- **`thread_goals`** — durable goal tracking: `goal_id`, `objective`,
  `status` (`active`/`paused`/`budget_limited`/`complete`), `token_budget`,
  `tokens_used`, `time_used_seconds`. (Live install: 7 goals.)
- **`jobs`** — generic background job queue with leasing: `kind`, `job_key`,
  `status`, `worker_id`, `ownership_token`, `lease_until`, `retry_at`,
  `retry_remaining`, watermarks. (This is how the memory pipeline / backfill
  run asynchronously without blocking the agent.)
- **`agent_jobs` / `agent_job_items`** — batch agent runs over a CSV: a job
  has an instruction + input/output CSV paths; each item is a row dispatched
  to its own thread with `result_json`, `attempt_count`, retry tracking.
- **`thread_spawn_edges`** — parent→child thread graph (`status`): records
  **subagent spawning** lineage.
- **`backfill_state`** — single-row watermark for backfilling memory from
  old sessions.
- **`remote_control_enrollments`** — websocket enrollment for remote driving
  of a Codex instance.

### 3.3 `logs_*.sqlite` — structured telemetry log

`logs` table: `ts`/`ts_nanos`, `level`, `target`, `module_path`, `file`,
`line`, `thread_id`, `process_uuid`, `estimated_bytes`, `feedback_log_body`.
A tracing/log sink indexed by thread and process for diagnostics.

### 3.4 `history.jsonl` — global cross-session input history

Flat append-only JSONL, one line per user input across *all* sessions:
`{session_id, ts, text}` (live file: 1065 lines). Powers shell-style
up-arrow recall and cross-session search. Capped by `history.max_bytes`.

> **AIOS borrow:** This three-layer model is the single most directly
> copyable design:
> - **JSONL rollout = source of truth, SQLite = derived index.** AIOS's
>   `.aios/` dispatch and the ledger should follow this: append-only JSONL/MD
>   stays canonical (satisfies DNA invariant 3), a rebuildable SQLite index
>   gives fast `aios_dispatch.py status` without raw file scans. The index can
>   always be dropped and rebuilt from the JSONL — no truth lives only in
>   SQLite.
> - **`turn_context` / `threads.sandbox_policy`+`approval_mode` persisted per
>   run** = exactly the provenance chain AIOS wants. Every AIOS work packet
>   result should serialize its execution context.
> - **`jobs` leased queue** = a ready-made design for AIOS's round-controller /
>   hive dispatch: `kind`+`job_key`, `lease_until`, `retry_remaining`,
>   `ownership_token` solves the watcher race / ID-collision class of bugs
>   (ASC-0059) cleanly.
> - **`thread_spawn_edges`** = AIOS should record a **contract/agent spawn
>   graph** so multi-universe (GenesisOS) branches and child-repo dispatch have
>   explicit lineage.
> - **`thread_goals` with token/time budgets** = AIOS contracts should carry
>   `token_budget` + `time_used` + a `budget_limited` status — a named loop
>   exit (DNA invariant 4) backed by real accounting.
> - **`agent_jobs`/`agent_job_items`** = a turnkey pattern for AIOS batch
>   fan-out over a list of inputs with per-item retry.

---

## 4. Memory System

Codex memory has **two distinct mechanisms**:

### 4.1 `~/.codex/memories/` — human-curated memory files

Plain markdown files (live install: `jaewon_context.md` ~25 KB,
`workspace_rules.md` ~0.8 KB). These are durable, hand-editable context. The
sandbox grants this directory as a **`writable_root`** specifically so the
agent can self-update memory while otherwise sandboxed. `threads.memory_mode`
(`enabled` by default) toggles whether a thread uses memory.

### 4.2 The staged memory pipeline (SQLite-backed, async)

Beyond static files, Codex runs an automatic **memory distillation pipeline**:

- **`backfill_state`** scans old sessions (watermark-based).
- **Stage 1** (`stage1_outputs`): for each thread, a background `jobs` worker
  distills the rollout into `raw_memory` + `rollout_summary`, tracks
  `usage_count` / `last_usage`, and sets `selected_for_phase2`.
- **Phase 2** promotes the most-used / most-relevant stage-1 outputs into
  longer-lived memory.

So memory is **earned**: raw sessions → per-thread distillation → usage-weighted
selection → promotion. It is not "dump everything." (Live install had
`stage1_outputs` empty at inspection — pipeline present but idle.)

### 4.3 `AGENTS.md` as persistent instruction memory

`AGENTS.md` (§2.2) is the *third* memory layer — persistent **procedural**
memory (how to work) vs `memories/` *episodic/factual* memory (what is true).
Together: `AGENTS.md` = "rules of the project," `memories/` = "facts learned,"
distillation pipeline = "what mattered enough to keep."

> **AIOS borrow:** Codex's pipeline is essentially **MemoryOS, already built**
> — and it confirms the AIOS design (draft-first, provenance, review). Borrow:
> - The **earn-your-place pipeline** (raw → stage-1 distill → usage-weighted →
>   promote) is exactly MemoryOS's draft→review→accept lifecycle. AIOS should
>   add the *usage-weighting* signal (`usage_count`/`last_usage`) — promote
>   memory that proves useful, not memory that is merely recent. This is a
>   concrete write-trigger for MemoryOS auto-writeback (a known recurring gap).
> - The **three-layer split** — procedural (`AGENTS.md`/`CLAUDE.md`), factual
>   (`memories/`), distilled (pipeline) — is a cleaner taxonomy than AIOS's
>   current single ledger. Adopt it explicitly in MemoryOS.
> - **`writable_roots` for the memory dir** = the security pattern for a
>   self-writing memory: sandbox everything, punch one hole for the memory
>   directory. AIOS should let a sandboxed local-LLM agent write *only* to
>   MemoryOS's draft inbox.
> - Because AIOS runs a **local LLM**, the distillation worker can run
>   continuously and cheaply *offline* — AIOS's "dream cycle" is literally
>   Codex's stage-1/phase-2 pipeline, but free to run every night. This is a
>   genuine local-LLM advantage to lean into.

---

## 5. How Codex CLI Differs from Claude Code

| dimension | OpenAI Codex CLI | Claude Code |
|---|---|---|
| **Implementation** | Rust binary | Node/TS CLI |
| **Sandboxing** | OS-native enforced (macOS Seatbelt, Linux `bubblewrap`/Landlock+seccomp, Windows Sandbox); structured `sandbox_policy` JSON per turn | Permission-prompt + allow/deny rule model; sandbox optional/opt-in, less OS-kernel-enforced by default |
| **Approval UX** | Two orthogonal axes: sandbox mode (`read-only`/`workspace-write`/`danger-full-access`) × approval policy (`untrusted`/`on-request`/`on-failure`/`never`); optional **reviewer subagent** (`auto_review`) | Per-tool permission prompts; allow/deny/ask rules in `settings.json`; hooks; human-in-loop, no model-reviewer tier |
| **Config format** | Single **TOML** (`~/.codex/config.toml`) + project `.codex/config.toml`; `[profiles]` overlays; `[projects."<path>"].trust_level` | **JSON** (`settings.json`, user + project + local); `[permissions]`, `[hooks]`, `[env]` |
| **Project instructions** | `AGENTS.md` (+ `AGENTS.override.md`), root→cwd concatenation, 32 KiB cap | `CLAUDE.md`, hierarchical merge, import syntax |
| **Extension model** | MCP servers + **skills** (`SKILL.md` dirs) + **plugins/apps** (curated bundles) + **rules** allowlist; self-extending via `.system` skills (`skill-creator`, `plugin-creator`) | MCP servers + **skills** + **slash commands** + **hooks** + subagents |
| **Session storage** | Date-sharded JSONL **rollouts** + **SQLite** index (`state_*.sqlite`: threads, goals, jobs, spawn-edges, memory pipeline) + global `history.jsonl` + `logs_*.sqlite` telemetry | JSONL transcripts per project under `~/.claude/projects/...`; lighter index |
| **Memory** | `memories/*.md` + **staged distillation pipeline** (`stage1_outputs`, usage-weighted promotion) + `AGENTS.md` | `CLAUDE.md` + auto-memory `MEMORY.md` (note-file based); no automatic distillation pipeline |
| **Background work** | First-class: leased `jobs` queue, `agent_jobs` batch runner, `thread_spawn_edges`, remote-control enrollment | Background bash, subagents/Tasks; less persistent job/lease infrastructure |
| **Goals/budgets** | `thread_goals` table: objective + token/time budget + `budget_limited` status | Task list (todos); no persisted token/time budget per goal |
| **Trust model** | Per-directory `trust_level` persisted in config (gates project config loading) | Per-project settings file presence; trust via explicit `settings.json` |

**Net read:** Codex is the **more OS-like** of the two — kernel-enforced
sandbox, a relational session/job/goal store, a memory distillation pipeline,
and a self-extending skill/plugin system. Claude Code is lighter, more
hook-and-prompt driven, and more human-in-the-loop. Both converge on
MCP + skills + a markdown project-instruction file.

> **AIOS borrow:** AIOS should take **Codex's OS spine** (kernel sandbox,
> SQLite session/job/goal store, distillation pipeline, self-extension) and
> **Claude Code's governance reflex** (explicit human-in-loop checkpoints,
> hooks, draft-first). AIOS's unique claim — **first local-LLM-based AIOS
> ecosystem** — is defensible precisely here: Codex's whole architecture
> assumes a frozen *hosted* model and bills per token, so its memory pipeline
> and reviewer subagent are *rationed*. On a local LLM, AIOS can run the
> distillation pipeline, the reviewer-critic, and divergence (GenesisOS)
> **continuously and for free** — turning Codex's cost-gated subsystems into
> always-on AIOS organs. Copy the structure; exploit the economics.

---

## 6. Consolidated AIOS Borrow Checklist

1. **Two-layer security:** separate sandbox (capability) from approval (policy);
   make both per-turn and recorded.
2. **`turn_context` record:** every AIOS work packet serializes
   model/effort/sandbox/approval — replayable provenance.
3. **JSONL truth + rebuildable SQLite index:** canonical append-only logs,
   derived fast index for `dispatch status`.
4. **Leased `jobs` queue:** `kind`+`job_key`+`lease_until`+`retry_remaining`
   to kill watcher races / ID collisions.
5. **`thread_spawn_edges` lineage graph:** explicit contract/agent spawn tree
   (GenesisOS branches, child-repo dispatch).
6. **`thread_goals` budgets:** `token_budget`+`time_used`+`budget_limited`
   status = named loop exit with real accounting.
7. **Operator profiles:** `[profiles]`-style named overlays for AIOS modes.
8. **Per-directory trust ledger:** persist trust; lock privacy paths as
   permanently untrusted.
9. **Skills with frontmatter routers:** trigger-line + progressive disclosure
   for contracts/primitives.
10. **`prefix_rule` allowlist:** mechanize past operator approvals; cut
    escalation noise.
11. **Reviewer subagent → local-LLM critic:** automate low-risk approvals via
    GenesisOS/Hive critic, keep human override.
12. **Earn-your-place memory pipeline:** raw → distill → usage-weighted →
    promote; run it continuously offline (the local-LLM "dream cycle").
13. **Self-extension:** local-LLM autodrafter that can install its own
    skills/contracts, governed by draft-first.

---

## Sources

- [Configuration Reference – Codex](https://developers.openai.com/codex/config-reference)
- [Advanced Configuration – Codex](https://developers.openai.com/codex/config-advanced)
- [Agent approvals & security – Codex](https://developers.openai.com/codex/agent-approvals-security)
- [Sandbox – Codex](https://developers.openai.com/codex/concepts/sandboxing)
- [Custom instructions with AGENTS.md – Codex](https://developers.openai.com/codex/guides/agents-md)
- [Model Context Protocol – Codex](https://developers.openai.com/codex/mcp)
- [Unrolling the Codex agent loop – OpenAI](https://openai.com/index/unrolling-the-codex-agent-loop/) (referenced; page returned 403 to automated fetch)
- Direct inspection of a live `~/.codex/` install (sessions, `state_5.sqlite`,
  `logs_2.sqlite`, `config.toml`, `skills/`, `rules/`, `memories/`,
  `history.jsonl`) — schemas/formats only, 2026-05-17.
