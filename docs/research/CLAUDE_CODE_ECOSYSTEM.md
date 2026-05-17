# Claude Code Ecosystem — Internal Engineering Research

> Purpose: deeply understand Anthropic's Claude Code CLI ecosystem so AIOS (local-LLM
> agent operating system) can borrow/imitate its best architecture and credibly claim
> the "first local-LLM-based AIOS ecosystem" title.
>
> Method: current public Anthropic docs (`code.claude.com/docs`, `claude.com/blog`) +
> direct inspection of the local `~/.claude/` directory on this machine (CLI version
> 2.1.143 observed). No secrets, auth tokens, or private conversation content are
> reproduced — only formats and schemas.
>
> Date: 2026-05-17

---

## 0. Executive framing

Claude Code is not "a CLI tool" — it is an **agentic harness**: a thin, well-factored
runtime that wraps a frozen LLM and turns it into an operating environment. Everything
that makes it a *platform* is in the harness, not the model:

- a deterministic **turn/tool loop** with named exit conditions,
- **layered, file-based configuration** (managed → user → project → local),
- a **lazy-loading context economy** (skills, MCP tool search, subagents),
- a **plaintext, append-only session store** (`~/.claude/projects/*/*.jsonl`),
- a **two-track memory system** (human-written `CLAUDE.md` + agent-written `MEMORY.md`),
- an **extension surface** (MCP, skills, hooks, subagents, output styles, plugins,
  marketplaces) with consistent definition formats and clear precedence rules.

Strategically: AIOS already has many isomorphic primitives (contracts ≈ skills/tasks,
ledger ≈ session JSONL, dispatch ≈ subagents, MemoryOS ≈ auto-memory). The borrowable
asset is mostly **the discipline of the harness**: stable on-disk formats, precedence
order, context budgeting, and lazy loading — done so a *local* LLM (smaller context,
weaker instruction-following) survives long sessions.

---

## 1. Architecture & the agent loop

### 1.1 The agentic loop

A task runs as: **gather context → take action → verify results → repeat**. The phases
blend; Claude chains "dozens of actions" and course-corrects from each tool result.
Two components power it: the **model** (reasons) and **tools** (act). Claude Code is
the harness providing tools, context management, and the execution environment.

### 1.2 The turn / tool loop (concrete mechanics)

- A **turn** = one round trip: the model emits output that may include tool calls →
  the harness executes the tools → results are fed back automatically.
- Turns continue until the model emits output with **no tool calls** → loop ends, final
  result delivered. This is the **named exit condition** of the loop.
- Tools fall into 5 categories: file ops, search, execution (shell/git), web, code
  intelligence. Plus orchestration tools (spawn subagents, ask the user).
- The user is *inside* the loop — interruption at any point re-steers without restart.

### 1.3 Permission modes

Cycled with `Shift+Tab`; recorded per-message in the transcript as `permissionMode`:

| Mode | Behavior |
|---|---|
| `default` | Asks before file edits and shell commands |
| `acceptEdits` | Auto-accepts edits + safe FS commands (`mkdir`, `mv`); still asks for others |
| `plan` | Read-only tools only; produces an approvable plan before execution |
| `auto` | Evaluates every action with background safety checks (research preview) |
| `dontAsk` / `bypassPermissions` | Reduced/no prompting (seen in transcripts as `bypassPermissions` for SDK-driven runs) |

Permissions are also declaratively allow/deny-listed in `settings.json`
(`permissions.allow`, `permissions.deny`) and scoped from org policy down to personal.
Two safety layers: **checkpoints** (every file edit is snapshotted before write; `Esc Esc`
rewinds — local, separate from git) and **permissions** (gate side-effecting actions).

### 1.4 Context management & compaction

The context window holds: conversation history, file contents, command outputs,
`CLAUDE.md`, auto-memory, loaded skills, system instructions. As it fills:

1. Older **tool outputs are cleared first**.
2. If still over budget, the conversation is **summarized** (auto-compaction).
3. User requests and key code snippets are preserved; early detailed instructions can be lost.
4. If a single file/output is so large that context refills immediately, the harness
   **stops after a few attempts and errors out** instead of looping (anti-thrash guard).

Survival rules: project-root `CLAUDE.md` is **re-read from disk and re-injected** after
compaction; invoked skills are re-attached (first 5,000 tokens each, shared 25,000-token
budget, most-recent-first). `/context` shows the budget; `/compact focus on X` steers it.

### 1.5 Session structure

A session = one conversation tied to a working directory, with a UUID `sessionId`.
`--continue`/`--resume` reopens under the same ID and appends; `--fork-session`/`/branch`
copies history into a new ID. Each new session starts with a **fresh context window** —
cross-session continuity comes *only* from `CLAUDE.md` + auto-memory, not history.

> **AIOS borrow:** Adopt the explicit turn loop with a *named exit condition*
> ("no tool calls = done") — this is AIOS DNA invariant #4 ("every loop has a named
> exit") made concrete. For a local LLM, copy the **tiered context-eviction order**
> (tool outputs first, then summarize) and the **anti-thrash circuit breaker** (stop
> after N failed compactions, surface an error) — a small-context local model hits
> this far sooner than Claude. Make the AIOS round controller re-inject the active
> contract from disk after every compaction, exactly as Claude re-injects `CLAUDE.md`.
> Treat permission modes as a first-class AIOS concept: `observe`-only ≈ `plan` mode,
> `intervene` ≈ `default`, autonomous codex chain ≈ `bypassPermissions`.

---

## 2. Extension / plugin system

Claude Code's extensibility is **five composable layers + a packaging/distribution
layer**. Each has a fixed definition format, a fixed config location, and explicit
precedence.

### 2.1 MCP servers (external tools/data)

- **Protocol:** Model Context Protocol — open standard for AI↔tool integration.
- **Transports:** `stdio` (local process), `sse`, `http` (alias `streamable-http`).
- **Scopes** (where the config lives, what it applies to):
  | Scope | Applies to | Shared | File |
  |---|---|---|---|
  | `local` (default) | current project, private | No | `~/.claude.json` (under project path) |
  | `project` | current project, team | Yes (VCS) | `.mcp.json` in project root |
  | `user` | all your projects | No | `~/.claude.json` |
  | managed | org-wide | — | managed settings |
- **Invocation namespace:** tools are exposed as `mcp__<server>__<tool>`.
- **Tool search / deferred tools:** MCP tool *definitions* are deferred by default —
  only tool **names** consume context; the full schema loads on demand via tool search.
  (Observed live: this very research session received a `deferred_tools_delta` attachment
  and had to `ToolSearch` to load `WebSearch`/`WebFetch` schemas before calling them.)
- **Resilience:** HTTP/SSE servers auto-reconnect with exponential backoff (5 attempts,
  1s→2s→…); stdio servers are not auto-reconnected.
- Spawned stdio servers get `CLAUDE_PROJECT_DIR` in their environment.

### 2.2 Skills (formerly "custom commands" — now unified)

- A skill = a directory `<name>/SKILL.md` (+ optional supporting files/scripts).
- `SKILL.md` = YAML frontmatter + markdown body. The directory name becomes `/name`.
- Locations & precedence: enterprise > personal (`~/.claude/skills/`) >
  project (`.claude/skills/`) > plugin (`<plugin>/skills/`, namespaced `plugin:skill`).
- Key frontmatter: `description` (drives auto-invocation; capped 1,536 chars),
  `disable-model-invocation` (manual-only), `user-invocable` (hide from `/` menu),
  `allowed-tools` (pre-approve tools while active), `context: fork` + `agent` (run in a
  subagent), `model`/`effort`, `paths` (glob-scoped auto-activation), `hooks`.
- **Lazy loading:** only descriptions are in context at session start; full body loads
  on invocation, then *persists for the rest of the session*.
- **Dynamic context injection:** `` !`shell command` `` lines run *before* the model sees
  the skill — output is inlined (preprocessing, not a tool call).
- String substitution: `$ARGUMENTS`, `$0/$1/$N`, named `$arg`, `${CLAUDE_SESSION_ID}`,
  `${CLAUDE_SKILL_DIR}`.
- Follows the open **Agent Skills standard** (agentskills.io) — portable across tools.
- Bundled skills (`/simplify`, `/loop`, `/debug`, `/batch`, `/claude-api`) are
  prompt-based skills, not hardcoded logic.

### 2.3 Slash commands

Merged into skills. `.claude/commands/deploy.md` and `.claude/skills/deploy/SKILL.md`
both produce `/deploy`. Built-in commands (`/init`, `/agents`, `/doctor`, `/context`,
`/memory`, `/mcp`, `/compact`, `/model`, `/resume`) are fixed harness logic; bundled
skills are prompt-driven.

### 2.4 Hooks (deterministic automation around lifecycle events)

- Config in `settings.json` (`~/.claude/`, `.claude/`, `.claude/settings.local.json`),
  plugin `hooks/hooks.json`, or skill/agent frontmatter.
- **Events** include: session (`SessionStart`, `Setup`, `SessionEnd`), per-turn
  (`UserPromptSubmit`, `Stop`, `StopFailure`), tool loop (`PreToolUse`, `PostToolUse`,
  `PermissionRequest`, `PostToolBatch`), async (`SubagentStart/Stop`, `TaskCreated/
  Completed`, `PreCompact/PostCompact`, `FileChanged`, `InstructionsLoaded`, …).
- Each event has a `matcher` (exact / `|`-list / regex; e.g. `mcp__memory__.*`).
- Handler types: `command`, `http`, `mcp_tool`, `prompt`, `agent`.
- I/O contract: hook receives JSON on stdin (`session_id`, `transcript_path`, `cwd`,
  `permission_mode`, `tool_name`, `tool_input`, …); returns JSON on stdout
  (`continue`, `decision: "block"`, `hookSpecificOutput.permissionDecision`,
  `additionalContext`, `modifiedToolInput`, …). **Exit 0** = ok, **exit 2** = blocking
  error (for blockable events), other = non-blocking.
- Hooks are the *enforcement* layer — they run regardless of what the model decides.

### 2.5 Subagents (delegated, context-isolated workers)

- Markdown file + YAML frontmatter; body = the subagent's *entire* system prompt
  (it does NOT inherit the main system prompt).
- Locations & precedence: managed > `--agents` JSON flag > `.claude/agents/` (project) >
  `~/.claude/agents/` (user) > plugin `agents/`.
- Built-in types: **Explore** (read-only codebase search, thoroughness levels),
  **Plan** (research during plan mode), **general-purpose**.
- Frontmatter: `name`, `description` (delegation trigger), `tools`/`disallowedTools`,
  `model` (incl. routing to cheaper Haiku), `permissionMode`, `maxTurns`, `skills`
  (preload full skill content), `mcpServers`, `hooks`, `memory` (`user`/`project`/
  `local` — cross-session learning), `isolation: worktree`, `effort`, `background`.
- **Each subagent gets a fresh, isolated context window**; returns only a summary.
  Subagents **cannot spawn subagents** (no infinite nesting).

### 2.6 Output styles & plugins/marketplaces

- **Output styles** alter how the agent presents responses (e.g. `explanatory`,
  `learning` — both shipped as official plugins).
- **Plugin** = a bundle of skills + agents + hooks + MCP servers + commands; one-click
  install. Plugin root holds `plugin.json` and `skills/`, `agents/`, `hooks/`, `.mcp.json`.
- **Marketplace** = a collection of plugins from one source. Inspected locally:
  `~/.claude/plugins/known_marketplaces.json` points at the GitHub repo
  `anthropics/claude-plugins-official`, cloned into
  `~/.claude/plugins/marketplaces/claude-plugins-official/` with ~35 first-party plugins
  (`code-review`, `feature-dev`, `skill-creator`, `mcp-server-dev`, `plugin-dev`,
  per-language LSP plugins, output-style plugins, `ralph-loop`, …) plus an
  `external_plugins/` set (asana, github, linear, playwright, serena, …).
- Plugin path placeholders: `${CLAUDE_PLUGIN_ROOT}`, `${CLAUDE_PLUGIN_DATA}` (survives
  updates). Security: plugin subagents may **not** declare `hooks`, `mcpServers`, or
  `permissionMode`.

> **AIOS borrow:** This five-layer model maps almost 1:1 onto AIOS organs and is the
> single most copyable thing in the ecosystem:
> - **MCP** → AIOS already has `mcp__aios__*`; adopt the **deferred-tool / tool-search**
>   pattern so a local LLM's small context isn't eaten by tool schemas (critical — a
>   local model can't afford 50 tool definitions resident).
> - **Skills** → AIOS contracts/playbooks should become skill-shaped: directory +
>   frontmatter + lazy body + `!`-injection. The Agent Skills open standard means AIOS
>   skills could be *cross-compatible* with Claude Code — a real differentiator.
> - **Hooks** → AIOS needs a deterministic enforcement layer separate from the LLM.
>   This is exactly how to make DNA invariants *binding* (the recurring "spec without
>   enforcement" gap, ASC-0122): a `PreToolUse`-style hook can hard-block a privacy-
>   boundary violation or a non-recommendation-only auto-bind regardless of model intent.
> - **Subagents** → AIOS dispatch/fan-out should formalize fresh-context isolation +
>   summary-only return + no-nesting. Borrow `model` routing (cheap local model for
>   Explore-type work, bigger model for reasoning).
> - **Marketplace** → an AIOS plugin marketplace (a git repo + `known_marketplaces.json`
>   equivalent) is the concrete artifact behind the "ecosystem" claim. Ship it.

---

## 3. Conversation log / session-state storage (local filesystem)

Inspected directly under `~/.claude/`. Structure observed:

```
~/.claude/
├── CLAUDE.md                 # user-level instructions (loaded every session)
├── settings.json             # user settings (e.g. effortLevel, theme)
├── history.jsonl             # flat prompt history across all projects
├── .credentials.json         # auth — NOT inspected
├── projects/<slug>/          # one dir per project, slug = path with / → -
│   ├── <session-uuid>.jsonl  # the conversation transcript (append-only)
│   ├── <session-uuid>/       # per-session sidecar dir
│   │   └── tool-results/     # large tool outputs spilled to disk
│   └── memory/               # auto-memory for this project (see §4)
├── sessions/<pid>.json       # live session registry (pid, sessionId, cwd, status)
├── tasks/<session-uuid>/     # per-session task list (todo items as N.json)
├── plans/*.md                # saved plan-mode outputs
├── file-history/<uuid>/      # checkpoint snapshots of edited files
├── plugins/                  # known_marketplaces.json + marketplaces/
├── ide/                      # IDE integration lock files
├── shell-snapshots/, session-env/, telemetry/, backups/, stats-cache.json
```

### 3.1 Transcript format — `projects/<slug>/<uuid>.jsonl`

One JSON object per line, append-only. Observed `type` values and their key sets:

- **`user`** — `{ type, uuid, parentUuid, message, sessionId, timestamp,
  promptId, permissionMode, userType, entrypoint, cwd, version, gitBranch, isSidechain }`
- **`assistant`** — adds `requestId`, `apiErrorStatus`/`isApiErrorMessage`/`error`;
  `message` carries `{ id, role, model, content[], usage{...}, stop_reason,
  stop_details, context_management }`. `content[]` blocks are typed
  (`text`, `tool_use`, `tool_result`, `thinking`). `usage` records
  `input_tokens`, `output_tokens`, `cache_creation_input_tokens`,
  `cache_read_input_tokens`, `iterations`, `service_tier`, `speed`.
- **`attachment`** — injected context deltas, e.g. `deferred_tools_delta` with
  `addedNames`/`removedNames`/`pendingMcpServers` (the tool-search mechanism on disk).
- **`queue-operation`** — `enqueue`/`dequeue` of pending user input.
- **`last-prompt`** — `{ lastPrompt, leafUuid }` pointer to resume position.

Key design points: the transcript is a **DAG, not a list** — every entry has `uuid` +
`parentUuid`, which is what makes fork/branch (`--fork-session`) cheap. It is
**plaintext, append-only, human-readable**, and large tool outputs are **spilled to a
sidecar `tool-results/` dir** so the JSONL stays lean.

### 3.2 `history.jsonl`

Flat cross-project prompt log: `{ display, pastedContents, project, sessionId,
timestamp }` — one line per user prompt, powering prompt history recall.

### 3.3 `sessions/<pid>.json`

Live process registry: `{ pid, sessionId, cwd, startedAt, procStart, version,
peerProtocol, kind, entrypoint, status, updatedAt }` — lets the CLI find running
sessions for `/resume` and multi-terminal detection.

### 3.4 `tasks/<session-uuid>/`

Per-session todo list. Each todo item is a numbered file `N.json` with fields
`{ id, status, description, activeForm, subject, blockedBy[], blocks[] }`. Note
`blockedBy`/`blocks` — the task list is a **dependency graph**, not a flat list.
A `.lock` and `.highwatermark` file coordinate concurrent writers.

### 3.5 `file-history/` (checkpoints)

Per-edit snapshots of file contents keyed by session UUID — the backing store for the
`Esc Esc` rewind / checkpoint feature, independent of git.

> **AIOS borrow:** The AIOS ledger should adopt the **DAG transcript** shape
> (`uuid` + `parentUuid`) — it gives branch/fork/replay for free and is a cleaner
> provenance chain (DNA invariant #5) than a flat append log. Copy the **sidecar
> spill** (`tool-results/`): keep the durable record lean by moving big payloads to
> path-referenced sidecars — AGENTS.md already says "link to evidence by path, don't
> paste bodies"; this is the mechanism. The **task-as-dependency-graph** (`blockedBy`/
> `blocks`) is directly applicable to AIOS contract work-packets. Plaintext JSONL +
> `.lock`/`.highwatermark` is a robust, dependency-free persistence model ideal for a
> sovereign local system with no provider backend.

---

## 4. Memory system

Two complementary, both-loaded-every-session tracks:

### 4.1 `CLAUDE.md` — human-written instructions

- **Hierarchy & load order** (broad → specific; later wins on conflict):
  managed policy (`/etc/claude-code/CLAUDE.md` on Linux) → user (`~/.claude/CLAUDE.md`)
  → project (`./CLAUDE.md` or `./.claude/CLAUDE.md`) → local (`./CLAUDE.local.md`,
  gitignored).
- Loaded by **walking up the directory tree**; all discovered files are *concatenated*
  (root→cwd order), not overridden. Subdirectory `CLAUDE.md` files load **on demand**
  when Claude reads files there.
- **Imports:** `@path/to/file` syntax, recursive up to 5 hops, relative-to-importer.
- **`.claude/rules/`:** topic-split instruction files; `paths:` frontmatter scopes a
  rule to globs so it loads only when matching files are touched (path-specific rules).
- Delivered as a **user message after the system prompt** — guidance, not enforcement.
  Project-root `CLAUDE.md` is re-injected after compaction. Target <200 lines.
- `AGENTS.md` is *not* read directly — convention is `@AGENTS.md` import or symlink.

### 4.2 Auto-memory — agent-written `MEMORY.md`

- Stored per-repository at `~/.claude/projects/<project>/memory/`, shared across all
  worktrees of that repo. Machine-local.
- `MEMORY.md` is a **concise index**; detailed notes go in topic files
  (`debugging.md`, `api-conventions.md`, …).
- **Recall:** only the first **200 lines / 25KB of `MEMORY.md`** is auto-loaded each
  session. Topic files are **not** preloaded — the agent reads them on demand via normal
  file tools, using `MEMORY.md` as the map of what's stored where.
- The agent decides what is worth remembering (build commands, debugging insights,
  preferences) based on whether it would help a future session. Toggle via `/memory`,
  `autoMemoryEnabled` setting, or `CLAUDE_CODE_DISABLE_AUTO_MEMORY=1`.
- Subagents can have their own persistent memory (`~/.claude/agent-memory/`) via the
  `memory:` frontmatter field.
- All memory is **plain markdown** — auditable, editable, deletable.

Observed live: this machine's `~/.claude/projects/-home-user-workspaces-jaewon-myworld/
memory/` contains exactly this pattern — a `MEMORY.md` index of ~21 link lines, each
pointing to a `feedback_*.md` / `project_*.md` / `reference_*.md` topic file.

> **AIOS borrow:** This is *literally MemoryOS*, and the borrowable insight is the
> **index-plus-lazy-topic-files split**: a small local LLM cannot afford to load all
> memory every session, so keep a tiny always-loaded index and let the agent pull
> topic files on demand. AIOS should also keep the **two-track separation** explicit:
> human-authored instructions (= `CLAUDE.md` / contracts, *guidance*) vs agent-authored
> learnings (= MemoryOS drafts, *accumulated*). Critically, Claude's auto-memory
> *auto-writes* — AIOS's invariant #2 (draft-first, no auto-accept) is *stricter* and
> correct; keep it, but copy the **trigger discipline** ("would this help a future
> session?") to decide *when* to draft. The directory-walk + concatenate + path-scoped
> rules model is a clean way to give AIOS contracts per-subsystem scoping.

---

## 5. The ecosystem — why it is a platform, not a tool

### 5.1 Settings — layered configuration

`settings.json` exists at managed / user (`~/.claude/`) / project (`.claude/`) /
local (`.claude/settings.local.json`) layers; arrays merge, scalars follow precedence.
Managed settings enforce hard limits (`permissions.deny`, `sandbox.enabled`, `env`,
`forceLoginOrgUUID`) that users cannot override — the org-control story. A clear split
is documented: **settings = technical enforcement; `CLAUDE.md` = behavioral guidance.**

### 5.2 The Claude Agent SDK

Formerly the "Claude Code SDK" — the **same agent harness, generalized**. Core principle:
"give the agent a computer" (filesystem, terminal, command execution). It provides:
agent harness, automatic context management/compaction, the tool layer, subagents
(parallel + isolated context), and permissions. It exposes the **gather-context →
take-action → verify-work** loop as a reusable substrate so developers build finance
agents, assistants, support bots, research tools — all on one standardized pattern.
This is the platform proof: the harness Claude Code uses *is* a published SDK.

### 5.3 Interfaces & execution environments

- **Environments:** Local (your machine), Cloud (Anthropic VMs), Remote Control
  (local execution, browser-driven).
- **Interfaces:** terminal, desktop app, VS Code / JetBrains extensions, claude.ai/code,
  Slack, CI/CD (GitHub Actions). The agent loop is *identical* across all of them — the
  interface only changes presentation. Background agents + agent teams allow many
  parallel/communicating sessions.

### 5.4 What makes it a platform (synthesis)

1. The harness is **decoupled and shippable** (Agent SDK).
2. **Open standards** at the seams: MCP (tools), Agent Skills (skills) — third parties
   can build without permission.
3. **Uniform extension formats** with documented precedence — skills, agents, hooks,
   plugins all look the same everywhere.
4. **Distribution exists**: plugins + marketplaces turn extensions into shareable units.
5. **Stable, inspectable on-disk contracts** (`~/.claude/` JSONL, markdown) — tooling
   can be built around the data without an API.
6. **Multi-interface, multi-environment** with one loop — the product is the loop, not
   the terminal.

> **AIOS borrow:** To credibly be "the first local-LLM AIOS ecosystem," AIOS must do
> the *platform* moves, not just the agent moves:
> 1. **Publish the AIOS harness as an SDK/substrate** — the round controller + dispatch
>    + 5-OS organs, decoupled from any one provider (the "1 AIOS per person" thesis and
>    "no hard provider dependency" already point here). A local LLM swappable behind a
>    stable harness *is* the moat.
> 2. **Commit to open seams**: speak MCP and the Agent Skills standard so AIOS
>    extensions interoperate with the Claude Code ecosystem instead of competing format-
>    by-format. Interop is faster than rebuilding.
> 3. **Standardize AIOS extension formats** with explicit precedence (contracts, skills,
>    hooks, organ-plugins) — the precedence tables in §2 are the template.
> 4. **Ship an AIOS plugin marketplace** — a git repo + a `known_marketplaces.json`
>    equivalent. This concrete artifact is what lets the "ecosystem" word be true.
> 5. **Keep all state as plaintext, inspectable, append-only files** — already AIOS's
>    instinct (ledger, contracts); make it a guarantee so external tooling can grow.
> 6. **One loop, many interfaces** — the AIOS control plane should be reachable from
>    CLI, an MCP server, and the existing control-app dashboard with the *same* loop
>    underneath.
> The differentiator AIOS can claim that Claude Code cannot: **provider sovereignty** —
> the harness runs on a local LLM, so the ecosystem keeps working with no API, no
> account lock, no backpressure. That is the honest, defensible "first" claim.

---

## 6. Condensed borrow checklist

| Claude Code mechanism | AIOS target | Priority |
|---|---|---|
| Turn loop with "no tool calls = exit" | Round controller exit condition | High |
| Tiered context eviction + anti-thrash breaker | Local-LLM context manager | High |
| Re-inject contract from disk post-compaction | Round controller | High |
| Deferred tools / tool search | `mcp__aios__*` surface | High |
| Skills = dir + frontmatter + lazy body + `!`-injection | Contracts/playbooks as skills | High |
| Hooks as deterministic enforcement layer | Make DNA invariants binding (ASC-0122) | High |
| Subagent: fresh context, summary-only, no nesting | AIOS dispatch/fan-out | Med |
| DAG transcript (`uuid`/`parentUuid`) + sidecar spill | AIOS ledger format | Med |
| Task-as-dependency-graph (`blockedBy`/`blocks`) | Contract work-packets | Med |
| Memory: tiny index + lazy topic files | MemoryOS recall budget | High |
| Layered settings, enforcement vs guidance split | AIOS settings model | Med |
| Plugin + marketplace distribution | AIOS ecosystem artifact | High |
| Publish harness as SDK; speak MCP + Agent Skills | Platform/interop strategy | High |

---

## Sources

- [How Claude Code works](https://code.claude.com/docs/en/how-claude-code-works)
- [Extend Claude with skills](https://code.claude.com/docs/en/skills)
- [How Claude remembers your project (memory)](https://code.claude.com/docs/en/memory)
- [Hooks reference](https://code.claude.com/docs/en/hooks)
- [Create custom subagents](https://code.claude.com/docs/en/sub-agents)
- [Connect Claude Code to tools via MCP](https://code.claude.com/docs/en/mcp)
- [Building agents with the Claude Agent SDK](https://claude.com/blog/building-agents-with-the-claude-agent-sdk)
- Direct inspection of local `~/.claude/` (CLI v2.1.143): `projects/*/*.jsonl`
  transcripts, `history.jsonl`, `sessions/*.json`, `tasks/*/`, `memory/`,
  `plugins/known_marketplaces.json`, `settings.json`. No secrets reproduced.
